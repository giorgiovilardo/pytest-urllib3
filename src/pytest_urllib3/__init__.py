from collections.abc import Generator
from operator import methodcaller

import pytest
from pytest import Config, FixtureRequest, MonkeyPatch

import urllib3
from pytest_urllib3._mock import Urllib3Mock
from pytest_urllib3._options import _Urllib3MockOptions
from pytest_urllib3._request import Request
from pytest_urllib3.version import __version__

__all__ = (
    "Urllib3Mock",
    "Request",
    "__version__",
)


def _build_full_url(pool: urllib3.HTTPConnectionPool, url: str) -> str:
    port_suffix = ""
    if pool.port is not None:
        is_default = (pool.scheme == "https" and pool.port == 443) or (
            pool.scheme == "http" and pool.port == 80
        )
        if not is_default:
            port_suffix = f":{pool.port}"
    return f"{pool.scheme}://{pool.host}{port_suffix}{url}"


@pytest.fixture
def urllib3_mock(
    monkeypatch: MonkeyPatch,
    request: FixtureRequest,
) -> Generator[Urllib3Mock, None, None]:
    options = {}
    for marker in request.node.iter_markers("urllib3_mock"):
        options = marker.kwargs | options
    __tracebackhide__ = methodcaller("errisinstance", TypeError)
    options = _Urllib3MockOptions(**options)

    mock = Urllib3Mock(options)

    real_urlopen = urllib3.HTTPConnectionPool.urlopen

    def mocked_urlopen(pool, method, url, body=None, headers=None, *args, **kwargs):
        full_url = _build_full_url(pool, url)
        if isinstance(body, str):
            body = body.encode("utf-8")
        req = Request(
            method=method.upper(),
            url=full_url,
            body=body,
            headers=dict(headers) if headers else {},
        )
        if options.should_mock(req):
            return mock._handle_request(req)
        return real_urlopen(pool, method, url, body, headers, *args, **kwargs)

    monkeypatch.setattr(urllib3.HTTPConnectionPool, "urlopen", mocked_urlopen)

    yield mock
    try:
        mock._assert_options()
    finally:
        mock.reset()


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "urllib3_mock(*, assert_all_responses_were_requested=True, assert_all_requests_were_expected=True, can_send_already_matched_responses=False, should_mock=lambda request: True): Configure urllib3_mock fixture.",
    )
