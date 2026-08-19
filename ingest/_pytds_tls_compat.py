"""Replaces pytds's TLS hostname check with one that doesn't call the
pyOpenSSL X509.get_extension()/get_extension_count() methods pyOpenSSL
26.2 removed - see GHSA-537c-gmf6-5ccf in requirements.txt for why this
was previously pinning pyOpenSSL/cryptography down. Applying this patch
lets those two packages float to a version with the CVE fixed.

pytds's establish_channel() looks up validate_host as a module global
at call time, so reassigning pytds.tls.validate_host here is enough -
no need to touch pytds's own source.

The verification itself is delegated to `service_identity`, the audited
RFC 6125 implementation the pyOpenSSL/Twisted ecosystem uses. This file
previously hand-rolled it, and hand-rolled hostname matching is a bad
trade at any size: it decides whether the server we reached is the
server we asked for, and every subtlety it has to get right - CN being
inadmissible when subjectAltName is present, wildcards spanning exactly
one label, case-insensitivity, trailing root dots, IDNA, IP SANs - is a
documented way to accept the wrong certificate. See ADR-013.
"""

from service_identity import CertificateError, VerificationError
from service_identity.cryptography import verify_certificate_hostname
import pytds.tls


def _validate_host(cert, name: bytes) -> bool:
    """Same contract as pytds.tls.validate_host: cert is a pyOpenSSL
    X509 object, name is the ascii-encoded server hostname. Returns a
    bool rather than raising, because that is what pytds expects."""
    try:
        verify_certificate_hostname(cert.to_cryptography(),
                                     name.decode("ascii"))
    except (VerificationError, CertificateError,
            UnicodeDecodeError, ValueError):
        # VerificationError  - the certificate is valid but not for us.
        # CertificateError   - it carries no subjectAltName at all, which
        #                      modern verification refuses outright; a
        #                      CN-only certificate is not acceptable.
        # The two are siblings, not parent and child, so both must be
        # named: catching only VerificationError let a SAN-less
        # certificate raise out of a function pytds expects to return a
        # bool, crashing mid-handshake instead of rejecting cleanly.
        return False
    return True


pytds.tls.validate_host = _validate_host
