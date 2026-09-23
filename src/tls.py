"""Narrow compatibility for the legacy TWCA chain's missing SKI extension."""
import ssl

import certifi
import requests


def verification_error(error):
    pending, seen = [error], set()
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, ssl.SSLCertVerificationError):
            return item
        if isinstance(item, BaseException):
            pending.extend(item.args)
            pending.extend([item.__cause__, item.__context__, getattr(item, "reason", None)])
    return None


class CwaTLSAdapter(requests.adapters.HTTPAdapter):
    """Keep authenticated TLS, using pre-Python-3.13 X.509 extension rules."""

    def __init__(self):
        self.context = ssl.create_default_context(cafile=certifi.where())
        self.context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        super().__init__()

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        if verify is not True:
            raise ValueError("CWA TLS verification must stay enabled")
        host, settings = super().build_connection_pool_key_attributes(request, verify, cert)
        settings["ssl_context"] = self.context
        return host, settings


def get_cwa(url, **kwargs):
    try:
        return requests.get(url, **kwargs)
    except requests.exceptions.SSLError as error:
        certificate_error = verification_error(error)
        # Retry only the known missing-SKI incompatibility, never bad certificates
        # caused by expiration, unknown issuer, or a hostname mismatch.
        if certificate_error is None or getattr(certificate_error, "verify_code", None) != 86:
            raise
        with requests.Session() as session:
            session.mount("https://opendata.cwa.gov.tw/", CwaTLSAdapter())
            return session.get(url, **kwargs)
