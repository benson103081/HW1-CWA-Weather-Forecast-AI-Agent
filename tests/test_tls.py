import ssl
from unittest.mock import Mock

import pytest
import requests

from src import tls


def certificate_failure(code):
    inner = ssl.SSLCertVerificationError(1, "validation failed")
    inner.verify_code = code
    return requests.exceptions.SSLError(inner)


def test_compatibility_retains_certificate_and_hostname_validation():
    adapter = tls.CwaTLSAdapter()
    assert adapter.context.verify_mode == ssl.CERT_REQUIRED
    assert adapter.context.check_hostname is True
    assert adapter.context.minimum_version >= ssl.TLSVersion.TLSv1_2
    request = requests.Request("GET", "https://opendata.cwa.gov.tw/").prepare()
    _, settings = adapter.build_connection_pool_key_attributes(request, True)
    assert settings["ssl_context"] is adapter.context
    with pytest.raises(ValueError):
        adapter.build_connection_pool_key_attributes(request, False)


@pytest.mark.parametrize("code", [10, 20, 62])
def test_no_fallback_for_expired_untrusted_or_wrong_hostname(monkeypatch, code):
    monkeypatch.setattr(tls.requests, "get", Mock(side_effect=certificate_failure(code)))
    session = Mock()
    monkeypatch.setattr(tls.requests, "Session", session)
    with pytest.raises(requests.exceptions.SSLError):
        tls.get_cwa("https://opendata.cwa.gov.tw/")
    session.assert_not_called()


def test_missing_ski_uses_scoped_verified_retry(monkeypatch):
    monkeypatch.setattr(tls.requests, "get", Mock(side_effect=certificate_failure(86)))
    session = Mock()
    manager = Mock()
    manager.__enter__ = Mock(return_value=session)
    manager.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(tls.requests, "Session", Mock(return_value=manager))
    result = tls.get_cwa("https://opendata.cwa.gov.tw/", timeout=(10, 45))
    assert result is session.get.return_value
    assert session.mount.call_args.args[0] == "https://opendata.cwa.gov.tw/"
    assert isinstance(session.mount.call_args.args[1], tls.CwaTLSAdapter)
    assert "verify" not in session.get.call_args.kwargs
