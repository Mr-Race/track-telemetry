"""Certificate hostname verification (ingest/_pytds_tls_compat.py).

This code decides whether the server we reached is the server we asked
for. Chain validation runs first, so this is the second half of the
check - but a mistake here accepts a different host's certificate
silently, which is why it is tested rather than trusted.

The cases below are the ones that must FAIL. A hostname matcher that
only has passing tests has not been tested.
"""

import pytest

from ingest._pytds_tls_compat import _is_san_matching, _normalise


class TestExactMatch:
    def test_identical_names_match(self):
        assert _is_san_matching("db.example.com", "db.example.com")

    def test_different_names_do_not(self):
        assert not _is_san_matching("db.example.com", "other.example.com")

    @pytest.mark.parametrize("cert,host", [
        ("DB.Example.COM", "db.example.com"),   # DNS is case-insensitive
        ("db.example.com.", "db.example.com"),  # trailing root dot
        ("db.example.com", "DB.EXAMPLE.COM."),
    ])
    def test_case_and_trailing_dot_are_not_a_mismatch(self, cert, host):
        """These previously failed closed - safe, but they broke valid
        connections rather than rejecting invalid ones."""
        assert _is_san_matching(cert, host)


class TestWildcard:
    def test_wildcard_matches_one_label(self):
        assert _is_san_matching("*.database.windows.net",
                                "myserver.database.windows.net")

    def test_wildcard_does_not_span_a_dot(self):
        """The bug this class exists for: `*.example.com` must not match
        `a.b.example.com`, or one certificate would cover a whole tree."""
        assert not _is_san_matching("*.example.com", "a.b.example.com")

    def test_wildcard_does_not_match_the_bare_domain(self):
        assert not _is_san_matching("*.example.com", "example.com")

    def test_wildcard_does_not_match_a_different_domain(self):
        assert not _is_san_matching("*.example.com", "evil.com")

    def test_suffix_confusion_is_rejected(self):
        """`*.example.com` must not match `attacker-example.com` - the
        classic incomplete-sanitization shape."""
        assert not _is_san_matching("*.example.com", "x.attackerexample.com")
        assert not _is_san_matching("*.example.com", "notexample.com")


class TestMalformedWildcards:
    """None of these are wildcards we honour; each must fall through to
    an exact comparison and fail."""

    @pytest.mark.parametrize("cert,host", [
        ("*", "anything.example.com"),
        ("*.", "a.example.com"),
        ("*.*", "a.b"),
        ("*.*.example.com", "a.b.example.com"),
        ("a.*.example.com", "a.b.example.com"),
        ("*a.example.com", "ba.example.com"),
    ])
    def test_rejected(self, cert, host):
        assert not _is_san_matching(cert, host)

    def test_bare_host_cannot_be_wildcard_matched(self):
        assert not _is_san_matching("*.localhost", "localhost")


class TestEmptyInput:
    @pytest.mark.parametrize("cert,host", [
        ("", "db.example.com"),
        ("db.example.com", ""),
        ("", ""),
        (".", "db.example.com"),
    ])
    def test_empty_never_matches(self, cert, host):
        assert not _is_san_matching(cert, host)


class TestNormalise:
    def test_lowercases_and_strips_root_dot(self):
        assert _normalise("  DB.Example.COM.  ") == "db.example.com"


# --------------------------------------------------------------------
# The substantive security change: Common Name must be ignored when the
# certificate carries subjectAltName (RFC 6125 §6.4.4, and the CA/Browser
# Forum baseline requirements).
#
# The previous implementation checked CN *first* and returned on a match,
# so a certificate whose SAN covered one host and whose CN named another
# was accepted for the CN. Chain validation makes that hard to reach in
# practice; hostname verification is not held to "hard to reach".
# --------------------------------------------------------------------

from cryptography import x509  # noqa: E402
from cryptography.x509.oid import ExtensionOID, NameOID  # noqa: E402

from ingest import _pytds_tls_compat as tls  # noqa: E402


class _Attr:
    def __init__(self, value):
        self.oid = NameOID.COMMON_NAME
        self.value = value


class _SanValue:
    def __init__(self, names):
        self._names = names

    def get_values_for_type(self, _type):
        return self._names


class _Ext:
    def __init__(self, names):
        self.value = _SanValue(names)


class _Extensions:
    def __init__(self, san_names):
        self._san = _Ext(san_names) if san_names is not None else None

    def get_extension_for_oid(self, oid):
        if oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME and self._san:
            return self._san
        raise x509.ExtensionNotFound("no san", oid)


class _Cert:
    """Minimal stand-in for the cryptography certificate object."""

    def __init__(self, cn=None, san=None):
        self.subject = [_Attr(cn)] if cn else []
        self.extensions = _Extensions(san)

    def to_cryptography(self):
        return self


class TestCommonNameIsNotAuthoritative:
    def test_cn_is_ignored_when_san_is_present(self):
        """The fix. SAN covers attacker.example.com; CN claims the real
        database host. The certificate must NOT be accepted for it."""
        cert = _Cert(cn="myserver.database.windows.net",
                     san=["attacker.example.com"])

        assert tls._validate_host(cert, b"myserver.database.windows.net") \
            is False

    def test_san_still_authorises_when_it_matches(self):
        cert = _Cert(cn="something.else",
                     san=["myserver.database.windows.net"])

        assert tls._validate_host(cert, b"myserver.database.windows.net")

    def test_san_wildcard_still_works(self):
        """Azure SQL presents a wildcard; this must keep connecting."""
        cert = _Cert(cn=None, san=["*.database.windows.net"])

        assert tls._validate_host(cert, b"myserver.database.windows.net")

    def test_cn_is_used_only_when_there_is_no_san(self):
        """Legacy certificates without SAN still verify against CN."""
        cert = _Cert(cn="legacy.example.com", san=None)

        assert tls._validate_host(cert, b"legacy.example.com")
        assert tls._validate_host(cert, b"other.example.com") is False

    def test_cn_wildcards_are_not_honoured(self):
        """A wildcard in CN is not expanded - only SAN wildcards are."""
        cert = _Cert(cn="*.example.com", san=None)

        assert tls._validate_host(cert, b"a.example.com") is False

    def test_no_cn_and_no_san_is_rejected(self):
        assert tls._validate_host(_Cert(cn=None, san=None),
                                  b"db.example.com") is False
