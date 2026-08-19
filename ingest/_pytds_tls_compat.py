"""Replaces pytds's TLS hostname check with one that doesn't call the
pyOpenSSL X509.get_extension()/get_extension_count() methods pyOpenSSL
26.2 removed - see GHSA-537c-gmf6-5ccf in requirements.txt for why this
was previously pinning pyOpenSSL/cryptography down. Applying this patch
lets those two packages float to a version with the CVE fixed.

pytds's establish_channel() looks up validate_host as a module global
at call time, so reassigning pytds.tls.validate_host here is enough -
no need to touch pytds's own source.

This is certificate hostname verification: it decides whether the server
we reached is the server we asked for. Chain validation happens first
(pytds is given certifi's CA bundle), so this is the second half of the
check, not the whole of it - but a mistake here silently accepts a
different host's certificate. It is written to fail closed.
"""

from cryptography import x509
from cryptography.x509.oid import ExtensionOID, NameOID
import pytds.tls


def _normalise(name: str) -> str:
    """DNS names are case-insensitive, and a fully-qualified name may
    carry a trailing root dot. Comparing raw strings makes both of those
    a spurious mismatch - which fails closed, but breaks valid
    connections rather than rejecting invalid ones."""
    return name.strip().rstrip(".").lower()


def _is_san_matching(dns_name: str, host_name: str) -> bool:
    dns_name = _normalise(dns_name)
    host_name = _normalise(host_name)
    if not dns_name or not host_name:
        return False
    if dns_name == host_name:
        return True

    # A wildcard is only ever valid as the entire leftmost label, and it
    # matches exactly one label - `*.example.com` covers `a.example.com`
    # but neither `example.com` nor `a.b.example.com`. Anything else
    # (`*`, `a.*.example.com`, `*a.example.com`) is not a wildcard we
    # honour, and falls through to the exact comparison above.
    if dns_name.startswith("*."):
        suffix = dns_name[2:]
        # Refuse a wildcard with nothing behind it, or one that would
        # span a dot - both would widen the match far past one label.
        if not suffix or "*" in suffix:
            return False
        host_labels = host_name.split(".")
        if len(host_labels) < 2:
            return False
        if ".".join(host_labels[1:]) == suffix:
            return True
    return False


def _validate_host(cert, name: bytes) -> bool:
    """Same contract as pytds.tls.validate_host: cert is a pyOpenSSL
    X509 object, name is the ascii-encoded server hostname."""
    x509_cert = cert.to_cryptography()
    host_name = name.decode("ascii")

    try:
        san_ext = x509_cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    except x509.ExtensionNotFound:
        san_ext = None

    # RFC 6125 §6.4.4 and the CA/Browser Forum baseline requirements:
    # when a certificate carries subjectAltName, the Common Name must be
    # ignored entirely. The previous version checked CN *first* and
    # returned on a match, so a certificate whose SAN covered one host
    # and whose CN named another would have been accepted for the CN.
    # Chain validation makes that hard to reach, but "hard to reach" is
    # not the standard hostname verification is held to.
    if san_ext is not None:
        for dns_name in san_ext.value.get_values_for_type(x509.DNSName):
            if _is_san_matching(dns_name, host_name):
                return True
        return False

    for attr in x509_cert.subject:
        if attr.oid == NameOID.COMMON_NAME:
            # CN is a legacy fallback and only ever names one host; it is
            # compared the same normalised way, and wildcards in a CN are
            # deliberately not honoured.
            return _normalise(str(attr.value)) == _normalise(host_name)
    return False


pytds.tls.validate_host = _validate_host
