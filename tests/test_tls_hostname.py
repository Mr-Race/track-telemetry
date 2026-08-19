"""Certificate hostname verification (ingest/_pytds_tls_compat.py).

This decides whether the server we reached is the server we asked for.
Chain validation runs first against certifi's bundle, so this is the
second half of the check - but a mistake accepts a different host's
certificate silently.

The verification is delegated to `service_identity` (ADR-013). These
tests do not re-test that library; they pin the *contract* our shim
exposes to pytds - returns a bool, never raises - and the behaviours the
previous hand-rolled version got wrong, so a future change back to
hand-rolling fails here rather than in production.

Certificates are built for real rather than stubbed: a stub would only
prove our stub agrees with itself.
"""

import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from OpenSSL import crypto

from ingest._pytds_tls_compat import _validate_host

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_cert(cn=None, san=None):
    """A self-signed certificate with the given CN and DNS SANs, handed
    back as the pyOpenSSL X509 object pytds passes to validate_host."""
    name_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, cn)] if cn else []
    subject = x509.Name(name_attrs)
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(KEY.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
    )
    if san is not None:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(n) for n in san]),
            critical=False)
    cert = builder.sign(KEY, hashes.SHA256())
    return crypto.X509.from_cryptography(cert)


class TestContract:
    """pytds calls this expecting a bool. Raising would surface as an
    unhandled error mid-handshake instead of a rejected certificate."""

    def test_returns_true_not_truthy(self):
        assert _validate_host(make_cert(san=["db.example.com"]),
                              b"db.example.com") is True

    def test_returns_false_not_raising(self):
        assert _validate_host(make_cert(san=["other.example.com"]),
                              b"db.example.com") is False

    def test_certificate_with_neither_cn_nor_san_is_rejected(self):
        assert _validate_host(make_cert(), b"db.example.com") is False

    def test_non_ascii_hostname_bytes_do_not_raise(self):
        assert _validate_host(make_cert(san=["db.example.com"]),
                              b"\xff\xfe") is False


class TestExactAndWildcard:
    def test_exact_san_match(self):
        assert _validate_host(make_cert(san=["db.example.com"]),
                              b"db.example.com")

    def test_wildcard_matches_one_label(self):
        """Azure SQL presents a wildcard certificate; this is the path
        production actually takes."""
        assert _validate_host(make_cert(san=["*.database.windows.net"]),
                              b"myserver.database.windows.net")

    def test_wildcard_does_not_span_a_dot(self):
        assert _validate_host(make_cert(san=["*.example.com"]),
                              b"a.b.example.com") is False

    def test_wildcard_does_not_match_the_bare_domain(self):
        assert _validate_host(make_cert(san=["*.example.com"]),
                              b"example.com") is False

    def test_suffix_confusion_is_rejected(self):
        """The shape this whole class of bug takes: a check that would
        accept `notexample.com` for `*.example.com`."""
        assert _validate_host(make_cert(san=["*.example.com"]),
                              b"notexample.com") is False

    def test_case_is_not_a_mismatch(self):
        """DNS is case-insensitive. The hand-rolled version compared raw
        bytes and failed closed here - safe, but it rejected valid
        connections."""
        assert _validate_host(make_cert(san=["DB.Example.COM"]),
                              b"db.example.com")


class TestCommonNameIsNotAuthoritative:
    """RFC 6125 section 6.4.4 and the CA/Browser Forum baseline
    requirements: when subjectAltName is present the Common Name must be
    ignored entirely.

    The hand-rolled version checked CN *first* and returned on a match,
    so a certificate whose SAN covered one host and whose CN named
    another was accepted for the CN. Chain validation makes that hard to
    reach; hostname verification is not held to 'hard to reach'.
    """

    def test_cn_is_ignored_when_san_is_present(self):
        cert = make_cert(cn="myserver.database.windows.net",
                         san=["attacker.example.com"])

        assert _validate_host(cert, b"myserver.database.windows.net") is False

    def test_san_authorises_even_when_cn_disagrees(self):
        cert = make_cert(cn="something.else",
                         san=["myserver.database.windows.net"])

        assert _validate_host(cert, b"myserver.database.windows.net")


class TestRegressionAgainstTheOldImplementation:
    """Pins the two behaviours that changed, so reverting to the
    hand-rolled matcher fails here."""

    @pytest.mark.parametrize("cn,san,host,expected", [
        # CN naming the target while SAN names someone else.
        ("db.example.com", ["attacker.example.com"], b"db.example.com", False),
        # Case-only difference, which used to fail closed.
        (None, ["DB.EXAMPLE.COM"], b"db.example.com", True),
    ])
    def test_changed_behaviours(self, cn, san, host, expected):
        assert _validate_host(make_cert(cn=cn, san=san), host) is expected
