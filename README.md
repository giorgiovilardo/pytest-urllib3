# pytest-urllib3

A pytest plugin to mock urllib3 requests, inspired by [pytest-httpx](https://github.com/Colin-b/pytest_httpx).

Once installed, `urllib3_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture will make sure every [`urllib3`](https://urllib3.readthedocs.io/) request will be replied to with user provided responses ([unless some requests are explicitly skipped](#do-not-mock-some-requests)).

- [Installation](#installation)
- [Add responses](#add-responses)
  - [JSON body](#add-json-response)
  - [Custom body](#reply-with-custom-body)
  - [HTTP status code](#add-non-200-response)
  - [HTTP headers](#reply-with-custom-headers)
- [Add dynamic responses](#dynamic-responses)
- [Raising exceptions](#raising-exceptions)
- [Check sent requests](#check-sent-requests)
- [Configuration](#configuring-urllib3_mock)
  - [Register more responses than requested](#allow-to-register-more-responses-than-what-will-be-requested)
  - [Register less responses than requested](#allow-to-not-register-responses-for-every-request)
  - [Allow to register a response for more than one request](#allow-to-register-a-response-for-more-than-one-request)
  - [Do not mock some requests](#do-not-mock-some-requests)
- [Resetting state](#resetting-state)
- [Migrating](#migrating-to-pytest-urllib3)
  - [responses](#from-responses)
- [Architecture](#architecture)

## Installation

```shell
pip install pytest-urllib3
```

## Add responses

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_something(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response()

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url")
```

If all registered responses are not sent back during test execution, the test case will fail at teardown [(unless you turned `assert_all_responses_were_requested` option off)](#allow-to-register-more-responses-than-what-will-be-requested).

Default response is a `200 (OK)` without any body.

### How response is selected

In case more than one response match request, the first one not yet sent (according to the registration order) will be sent.

In case all matching responses have been sent once, the request will [not be considered as matched](#in-case-no-response-can-be-found) [(unless you turned `can_send_already_matched_responses` option on)](#allow-to-register-a-response-for-more-than-one-request).

You can add criteria so that response will be sent only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string or a python [re.Pattern](https://docs.python.org/3/library/re.html) instance.

Matching is performed on the full URL, query parameters included.

Order of parameters in the query string does not matter, however order of values do matter if the same parameter is provided more than once.

```python
import re
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_url(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://test_url?a=1&b=2")

    http = urllib3.PoolManager()
    response1 = http.request("DELETE", "https://test_url?a=1&b=2")
    response2 = http.request("GET", "https://test_url?b=2&a=1")


def test_url_as_pattern(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url=re.compile(".*test.*"))

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url")
```

#### Matching on query parameters

Use `match_params` to partially match query parameters without having to provide a regular expression as `url`.

If this parameter is provided, `url` parameter must not contain any query parameter.

All query parameters have to be provided (as `str`). You can however use `unittest.mock.ANY` to do partial matching.

```python
import urllib3
from unittest.mock import ANY
from pytest_urllib3 import Urllib3Mock


def test_partial_params_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://test_url", match_params={"a": "1", "b": ANY})

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url?a=1&b=2")
```

#### Matching on HTTP method

Use `method` parameter to specify the HTTP method (POST, PUT, DELETE, PATCH, HEAD) to reply to.

`method` parameter must be a string. It will be upper-cased, so it can be provided lower cased.

Matching is performed on equality.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_post(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="POST")

    http = urllib3.PoolManager()
    response = http.request("POST", "https://test_url")


def test_put(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="PUT")

    http = urllib3.PoolManager()
    response = http.request("PUT", "https://test_url")


def test_delete(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="DELETE")

    http = urllib3.PoolManager()
    response = http.request("DELETE", "https://test_url")


def test_patch(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="PATCH")

    http = urllib3.PoolManager()
    response = http.request("PATCH", "https://test_url")


def test_head(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="HEAD")

    http = urllib3.PoolManager()
    response = http.request("HEAD", "https://test_url")
```

#### Matching on HTTP headers

Use `match_headers` parameter to specify the HTTP headers (as a dict) to reply to.

Matching is performed on equality for each provided header. Header name matching is case-insensitive.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_headers_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_headers={"Authorization": "Bearer token"})

    http = urllib3.PoolManager()
    response = http.request(
        "GET", "https://test_url", headers={"Authorization": "Bearer token"}
    )
```

#### Matching on HTTP body

Use `match_content` parameter to specify the full HTTP body (as bytes) to reply to.

Matching is performed on equality.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_content_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_content=b"This is the body")

    http = urllib3.PoolManager()
    response = http.request("POST", "https://test_url", body=b"This is the body")
```

##### Matching on HTTP JSON body

Use `match_json` parameter to specify the JSON decoded HTTP body to reply to.

Matching is performed on equality. You can however use `unittest.mock.ANY` to do partial matching.

```python
import json
import urllib3
from unittest.mock import ANY
from pytest_urllib3 import Urllib3Mock


def test_json_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_json={"a": "json", "b": 2})

    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        "https://test_url",
        body=json.dumps({"a": "json", "b": 2}).encode(),
        headers={"Content-Type": "application/json"},
    )


def test_partial_json_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_json={"a": "json", "b": ANY})

    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        "https://test_url",
        body=json.dumps({"a": "json", "b": 2}).encode(),
        headers={"Content-Type": "application/json"},
    )
```

Note that `match_content` cannot be provided if `match_json` is also provided.

### Add JSON response

Use `json` parameter to add a JSON response using python values.

```python
import json as json_module
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_json(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(json=[{"key1": "value1", "key2": "value2"}])

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url")
    assert json_module.loads(response.data) == [{"key1": "value1", "key2": "value2"}]
```

Note that the `content-type` header will be set to `application/json` by default in the response.

### Reply with custom body

Use `text` parameter to reply with a custom body by providing UTF-8 encoded string.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_str_body(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(text="This is my UTF-8 content")

    http = urllib3.PoolManager()
    assert http.request("GET", "https://test_url").data == b"This is my UTF-8 content"
```

Use `content` parameter to reply with a custom body by providing bytes.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_bytes_body(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(content=b"This is my bytes content")

    http = urllib3.PoolManager()
    assert http.request("GET", "https://test_url").data == b"This is my bytes content"
```

### Add non 200 response

Use `status_code` parameter to specify the HTTP status code (as an int) of the response.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_status_code(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(status_code=404)

    http = urllib3.PoolManager()
    assert http.request("GET", "https://test_url").status == 404
```

### Reply with custom headers

Use `headers` parameter to specify the extra headers (as a dict) of the response.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_headers(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(headers={"X-Header1": "Test value"})

    http = urllib3.PoolManager()
    assert http.request("GET", "https://test_url").headers["X-Header1"] == "Test value"
```

#### Reply with cookies

Cookies are sent in the `set-cookie` HTTP header.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_cookie(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(headers={"set-cookie": "key=value"})

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url")
    assert response.headers["set-cookie"] == "key=value"
```

## Add callbacks

You can perform custom manipulation upon request reception by registering callbacks.

Callback should expect one parameter, the received `Request` (from `pytest_urllib3`).

If all callbacks are not executed during test execution, the test case will fail at teardown [(unless you turned `assert_all_responses_were_requested` option off)](#allow-to-register-more-responses-than-what-will-be-requested).

Note that callbacks are considered as responses, and thus are [selected the same way](#how-response-is-selected).

### Dynamic responses

Callback should return a `urllib3.HTTPResponse` instance.

```python
import io
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_dynamic_response(urllib3_mock: Urllib3Mock):
    def custom_response(request):
        return urllib3.HTTPResponse(
            body=io.BytesIO(f"url={request.url}".encode()),
            status=200,
            preload_content=False,
        )

    urllib3_mock.add_callback(custom_response)

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url")
    assert response.data == b"url=https://test_url"
```

### Raising exceptions

You can simulate urllib3 exception throwing by raising an exception in your callback or use `urllib3_mock.add_exception` with the exception instance.

```python
import urllib3
import pytest
from pytest_urllib3 import Urllib3Mock


def test_exception_raising(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_exception(
        urllib3.exceptions.ConnectTimeoutError(None, None, "Unable to connect")
    )

    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.ConnectTimeoutError):
        http.request("GET", "https://test_url", retries=False)
```

#### In case no response can be found

The default behavior is to instantly raise a `urllib3.exceptions.TimeoutError` in case no matching response can be found.

The exception message will display the request and every registered responses to help you identify any possible mismatch.

```python
import urllib3
import pytest
from pytest_urllib3 import Urllib3Mock


@pytest.mark.urllib3_mock(assert_all_requests_were_expected=False)
def test_timeout(urllib3_mock: Urllib3Mock):
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request("GET", "https://test_url", retries=False)
```

## Check sent requests

The best way to ensure the content of your requests is still to use the `match_headers` and/or `match_content` parameters when adding a response. In the same spirit, ensuring that no request was issued does not necessarily require any code [(unless you turned `assert_all_requests_were_expected` option off)](#allow-to-not-register-responses-for-every-request).

In any case, you always have the ability to retrieve the requests that were issued.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_many_requests(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)

    http = urllib3.PoolManager()
    response1 = http.request("GET", "https://test_url")
    response2 = http.request("GET", "https://test_url")

    requests = urllib3_mock.get_requests()


def test_single_request(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response()

    http = urllib3.PoolManager()
    response = http.request("GET", "https://test_url")

    request = urllib3_mock.get_request()


def test_no_request(urllib3_mock: Urllib3Mock):
    assert not urllib3_mock.get_request()
```

### How requests are selected

You can add criteria so that requests will be returned only in case of a more specific matching.

Note that requests are [selected the same way as responses](#how-response-is-selected). Meaning that you can transpose `urllib3_mock.add_response` calls in the related examples into `urllib3_mock.get_requests` or `urllib3_mock.get_request`.

## Configuring urllib3_mock

The `urllib3_mock` marker is available and can be used to change the default behavior of the `urllib3_mock` fixture.

Refer to [available options](#available-options) for an exhaustive list of options that can be set [per test](#per-test), [per module](#per-module) or even [on the whole test suite](#for-the-whole-test-suite).

### Per test

```python
import pytest

@pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
def test_something(urllib3_mock):
    ...
```

### Per module

```python
import pytest

pytestmark = pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
```

### For the whole test suite

This should be set in the root `conftest.py` file.

```python
import pytest

def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item.add_marker(pytest.mark.urllib3_mock(assert_all_responses_were_requested=False))
```

### Available options

#### Allow to register more responses than what will be requested

By default, `pytest-urllib3` will ensure that every response was requested during test execution.

If you want to add an optional response, you can use the `is_optional` parameter when [registering a response](#add-responses) or [a callback](#add-callbacks).

```python
def test_fewer_requests_than_expected(urllib3_mock):
    # Even if this response never received a corresponding request, the test will not fail at teardown
    urllib3_mock.add_response(is_optional=True)
```

If you don't have control over the response registration process (shared fixtures), and you want to allow fewer requests than what you registered responses for, you can use the `urllib3_mock` marker `assert_all_responses_were_requested` option.

```python
import pytest

@pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
def test_fewer_requests_than_expected(urllib3_mock):
    # Even if this response never received a corresponding request, the test will not fail at teardown
    urllib3_mock.add_response()
```

Note that the `is_optional` parameter will take precedence over the `assert_all_responses_were_requested` option.

```python
import pytest

@pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
def test_force_expected_request(urllib3_mock):
    # Even if the option is set, the test will fail at teardown if this is not matched
    urllib3_mock.add_response(is_optional=False)
```

#### Allow to not register responses for every request

By default, `pytest-urllib3` will ensure that every request that was issued was expected.

You can use the `urllib3_mock` marker `assert_all_requests_were_expected` option to allow more requests than what you registered responses for.

```python
import pytest
import urllib3

@pytest.mark.urllib3_mock(assert_all_requests_were_expected=False)
def test_more_requests_than_expected(urllib3_mock):
    http = urllib3.PoolManager()
    # Even if this request was not expected, the test will not fail at teardown
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request("GET", "https://test_url", retries=False)
```

#### Allow to register a response for more than one request

If you want to add a response once, while allowing it to match more than once, you can use the `is_reusable` parameter when [registering a response](#add-responses) or [a callback](#add-callbacks).

```python
import urllib3

def test_more_requests_than_responses(urllib3_mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    http.request("GET", "https://test_url")
    # Even if only one response was registered, the test will not fail as this request will also be matched
    http.request("GET", "https://test_url")
```

If you don't have control over the response registration process (shared fixtures), and you want to allow multiple requests to match the same registered response, you can use the `urllib3_mock` marker `can_send_already_matched_responses` option.

With this option, in case all matching responses have been sent at least once, the last one (according to the registration order) will be sent.

```python
import pytest
import urllib3

@pytest.mark.urllib3_mock(can_send_already_matched_responses=True)
def test_more_requests_than_responses(urllib3_mock):
    urllib3_mock.add_response()
    http = urllib3.PoolManager()
    http.request("GET", "https://test_url")
    # Even if only one response was registered, the test will not fail as this request will also be matched
    http.request("GET", "https://test_url")
```

#### Do not mock some requests

By default, `pytest-urllib3` will mock every request.

But, for instance, in case you want to write integration tests with other servers, you might want to let some requests go through.

To do so, you can use the `urllib3_mock` marker `should_mock` option and provide a callable expecting a `Request` as parameter and returning a boolean.

Returning `True` will ensure that the request is handled by `pytest-urllib3` (mocked), `False` will let the request pass through (not mocked).

```python
import pytest
import urllib3

@pytest.mark.urllib3_mock(should_mock=lambda request: "localhost" not in request.url)
def test_partial_mock(urllib3_mock):
    urllib3_mock.add_response()

    http = urllib3.PoolManager()
    # This request will be mocked
    response = http.request("GET", "https://test_url")
    # This request will NOT be mocked
    # response = http.request("GET", "http://localhost:8080/health")
```

## Resetting state

You can reset the mock state at any point during a test using `reset()`. This clears all registered responses, callbacks, and captured requests.

```python
import urllib3
from pytest_urllib3 import Urllib3Mock


def test_reset(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_optional=True)
    urllib3_mock.reset()

    # All previous responses are cleared, register new ones
    urllib3_mock.add_response(status_code=201)

    http = urllib3.PoolManager()
    assert http.request("GET", "https://test_url").status == 201
```

## Migrating to pytest-urllib3

Here is how to migrate from well-known testing libraries to `pytest-urllib3`.

### From responses

| Feature | responses | pytest-urllib3 |
|:--------|:----------|:---------------|
| Add a response | `responses.add()` | `urllib3_mock.add_response()` |
| Add a callback | `responses.add_callback()` | `urllib3_mock.add_callback()` |
| Retrieve requests | `responses.calls` | `urllib3_mock.get_requests()` |

#### Add a response or a callback

Below is a list of parameters that will require a change in your code.

| Parameter | responses | pytest-urllib3 |
|:----------|:----------|:---------------|
| body (as bytes) | `body=b"sample"` | `content=b"sample"` |
| body (as str) | `body="sample"` | `text="sample"` |
| status code | `status=201` | `status_code=201` |
| headers | `adding_headers={"name": "value"}` | `headers={"name": "value"}` |

Sample adding a response with `responses`:

```python
from responses import RequestsMock

def test_response(responses: RequestsMock):
    responses.add(
        method=responses.GET,
        url="https://test_url",
        body=b"This is the response content",
        status=400,
    )
```

Sample adding the same response with `pytest-urllib3`:

```python
from pytest_urllib3 import Urllib3Mock

def test_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(
        method="GET",
        url="https://test_url",
        content=b"This is the response content",
        status_code=400,
    )
```

## Architecture

This section describes the internals of `pytest-urllib3` for contributors and anyone curious about how it works.

### How mocking works

`pytest-urllib3` intercepts all urllib3 requests by monkeypatching `urllib3.HTTPConnectionPool.urlopen` — the low-level method that both `PoolManager.request()` and direct pool usage ultimately call. This single patch point catches everything.

When a request is intercepted, the plugin:

1. Reconstructs the full URL from the pool's `scheme`, `host`, `port` and the relative `url` path
2. Builds a `Request` dataclass (since urllib3 has no first-class request object)
3. Checks the `should_mock` option to decide whether to intercept or pass through
4. If mocking, delegates to the `Urllib3Mock._handle_request` method

### Project structure

```
src/pytest_urllib3/
    __init__.py            Fixture definition, monkeypatch hook, pytest_configure
    _mock.py               Core mock class: add_response, add_callback, add_exception,
                           get_requests, response selection algorithm, teardown assertions
    _request_matcher.py    Request matching (URL, method, headers, content, JSON, params)
    _request.py            Request dataclass (method, url, body, headers)
    _options.py            Configuration options dataclass (4 options + should_mock)
    _pretty_print.py       Error message formatting for unmatched requests
    version.py             Package version
```

### Key design decisions

**Custom Request dataclass** — urllib3 has no first-class request object. The `Request` dataclass wraps method, URL, body, and headers into a single object that users receive from `get_requests()` and that callbacks accept as a parameter.

**Responses are callbacks internally** — `add_response()` wraps its parameters in a closure and calls `add_callback()`. This means responses and callbacks share the same selection algorithm and storage. `add_exception()` works the same way.

**Response selection algorithm** — When a request comes in, all registered matchers are checked. The first matching callback that hasn't been called yet (by registration order) is selected. If all matching callbacks have been called, the last one is reused only if it's marked as reusable. Otherwise, the request is unmatched.

**Matcher composition** — All matchers (URL, method, headers, body) are combined with AND logic. A request must satisfy every specified criterion. Matchers that aren't specified always match.

**Teardown assertions** — After each test, the fixture checks two things:
  1. Were all non-optional responses matched? (controlled by `assert_all_responses_were_requested` / `is_optional`)
  2. Were all requests expected? (controlled by `assert_all_requests_were_expected`)

**Marker aggregation** — Options set via `@pytest.mark.urllib3_mock(...)` at the test, class, module, and suite levels are merged. More specific levels (test) override less specific ones (suite) for the same key.

### Differences from pytest-httpx

| Aspect | pytest-httpx | pytest-urllib3 |
|:-------|:-------------|:---------------|
| Patch target | `httpx.HTTPTransport.handle_request` | `urllib3.HTTPConnectionPool.urlopen` |
| Request type | `httpx.Request` (built-in) | Custom `Request` dataclass |
| Response type | `httpx.Response` | `urllib3.HTTPResponse` via `io.BytesIO` |
| URL handling | `httpx.URL` | `urllib.parse` (stdlib) |
| Async support | Yes | No (urllib3 is sync-only) |
| Proxy matching | Yes | Deferred |
| Multipart matching | Yes (`match_files`, `match_data`) | Deferred |
| Extensions matching | Yes | Dropped (httpx-specific) |
| HTML responses | Yes (`html=`) | Dropped (not idiomatic for urllib3) |
| Streaming | Yes (`stream=`) | Deferred (urllib3 responses are already stream-like) |
