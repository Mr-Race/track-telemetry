"""Replaces pytds's TLS hostname check with one that doesn't call the
pyOpenSSL X509.get_extension()/get_extension_count() methods pyOpenSSL
26.2 removed - see GHSA-537c-gmf6-5ccf in requirements.txt for why this
was previously pinning pyOpenSSL/cryptography down. Applying this patch
lets those two packages float to a version with the CVE fixed.

pytds's establish_channel() looks up validate_host as a module global
at call time, so reassigning pytds.tls.validate_host here is enough -
no need to touch pytds's own source.
"""

from cryptography import x509
from cryptography.x509.oid import ExtensionOID, NameOID
import pytds.tls


def _is_san_matching(dns_name: str, host_name: str) -> bool:
    if dns_name == host_name:
        return True
    if dns_name.startswith("*."):
        afterstar_parts = dns_name[2:]
        afterstar_parts_sname = ".".join(host_name.split(".")[1:])
        if afterstar_parts == afterstar_parts_sname:
            return True
    return False


def _validate_host(cert, name: bytes) -> bool:
    """Same contract as pytds.tls.validate_host: cert is a pyOpenSSL
    X509 object, name is the ascii-encoded server hostname."""
    x509_cert = cert.to_cryptography()

    cn = None
    for attr in x509_cert.subject:
        if attr.oid == NameOID.COMMON_NAME:
            cn = attr.value.encode()
            break
    if cn == name:
        return True

    host_name = name.decode("ascii")
    try:
        san_ext = x509_cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    except x509.ExtensionNotFound:
        return False
    for dns_name in san_ext.value.get_values_for_type(x509.DNSName):
        if _is_san_matching(dns_name, host_name):
            return True
    return False


pytds.tls.validate_host = _validate_host
