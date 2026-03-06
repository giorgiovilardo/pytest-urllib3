import io
import json
import re
from unittest.mock import ANY

import pytest
import urllib3.exceptions

import urllib3
from pytest_urllib3 import Urllib3Mock

# Phase 1: Core tests


@pytest.mark.urllib3_mock(assert_all_requests_were_expected=False)
def test_without_response(urllib3_mock: Urllib3Mock):
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request("GET", "https://example.com", retries=False)


def test_default_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response()
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.status == 200
    assert response.data == b""


def test_response_with_status_code(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(status_code=201)
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.status == 201


def test_response_with_content(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(content=b"hello")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.data == b"hello"


def test_response_with_text(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(text="hello")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.data == b"hello"
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"


def test_response_with_json(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(json={"key": "value"})
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert json.loads(response.data) == {"key": "value"}
    assert response.headers["Content-Type"] == "application/json"


def test_response_with_headers(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(headers={"X-Custom": "test"})
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.headers["X-Custom"] == "test"


# URL matching


def test_url_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://example.com/path")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/path")
    assert response.status == 200


@pytest.mark.urllib3_mock(
    assert_all_requests_were_expected=False, assert_all_responses_were_requested=False
)
def test_url_not_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://example.com/other")
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request("GET", "https://example.com/path", retries=False)


def test_url_query_string_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://example.com/path?a=1&b=2")
    http = urllib3.PoolManager()
    # Order of query params doesn't matter
    response = http.request("GET", "https://example.com/path?b=2&a=1")
    assert response.status == 200


def test_multi_value_query_params(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://example.com/path?a=1&a=3")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/path?a=1&a=3")
    assert response.status == 200


def test_url_pattern_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url=re.compile(r".*example.*"))
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/anything")
    assert response.status == 200


# Method matching


def test_method_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="POST")
    http = urllib3.PoolManager()
    response = http.request("POST", "https://example.com")
    assert response.status == 200


@pytest.mark.urllib3_mock(
    assert_all_requests_were_expected=False, assert_all_responses_were_requested=False
)
def test_method_not_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="POST")
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request("GET", "https://example.com", retries=False)


def test_method_case_insensitive(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="post")
    http = urllib3.PoolManager()
    response = http.request("POST", "https://example.com")
    assert response.status == 200


# Header matching


def test_headers_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_headers={"Authorization": "Bearer token"})
    http = urllib3.PoolManager()
    response = http.request(
        "GET", "https://example.com", headers={"Authorization": "Bearer token"}
    )
    assert response.status == 200


@pytest.mark.urllib3_mock(
    assert_all_requests_were_expected=False, assert_all_responses_were_requested=False
)
def test_headers_not_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_headers={"Authorization": "Bearer token"})
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request(
            "GET",
            "https://example.com",
            headers={"Authorization": "Bearer wrong"},
            retries=False,
        )


# Content matching


def test_content_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_content=b"request body")
    http = urllib3.PoolManager()
    response = http.request("POST", "https://example.com", body=b"request body")
    assert response.status == 200


def test_json_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_json={"key": "value"})
    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        "https://example.com",
        body=json.dumps({"key": "value"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200


def test_json_partial_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_json={"key": "value", "other": ANY})
    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        "https://example.com",
        body=json.dumps({"key": "value", "other": "anything"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200


@pytest.mark.urllib3_mock(
    assert_all_requests_were_expected=False, assert_all_responses_were_requested=False
)
def test_match_json_invalid_json(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_json={"key": "value"})
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request(
            "POST",
            "https://example.com",
            body=b"not json at all",
            retries=False,
        )


@pytest.mark.urllib3_mock(
    assert_all_requests_were_expected=False, assert_all_responses_were_requested=False
)
def test_json_not_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_json={"key": "value"})
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request(
            "POST",
            "https://example.com",
            body=json.dumps({"key": "other"}).encode(),
            headers={"Content-Type": "application/json"},
            retries=False,
        )


# Params matching


def test_match_params(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(
        url="https://example.com/path", match_params={"a": "1", "b": "2"}
    )
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/path?a=1&b=2")
    assert response.status == 200


def test_match_params_with_any(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(
        url="https://example.com/path", match_params={"a": "1", "b": ANY}
    )
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/path?a=1&b=anything")
    assert response.status == 200


# Multiple responses


def test_with_many_responses(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(status_code=200)
    urllib3_mock.add_response(status_code=201)
    http = urllib3.PoolManager()
    response1 = http.request("GET", "https://example.com")
    response2 = http.request("GET", "https://example.com")
    assert response1.status == 200
    assert response2.status == 201


def test_with_many_responses_methods(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(method="GET", text="get response")
    urllib3_mock.add_response(method="POST", text="post response")
    http = urllib3.PoolManager()
    get_response = http.request("GET", "https://example.com")
    post_response = http.request("POST", "https://example.com")
    assert get_response.data == b"get response"
    assert post_response.data == b"post response"


# Callbacks


def test_callback_returning_response(urllib3_mock: Urllib3Mock):
    def custom_response(request):
        return urllib3.HTTPResponse(
            body=io.BytesIO(f"received {request.method}".encode()),
            status=200,
            preload_content=False,
        )

    urllib3_mock.add_callback(custom_response)
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.data == b"received GET"


def test_callback_raising_exception(urllib3_mock: Urllib3Mock):
    def error_callback(request):
        raise urllib3.exceptions.ConnectTimeoutError(None, None, "timeout")

    urllib3_mock.add_callback(error_callback)
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.ConnectTimeoutError):
        http.request("GET", "https://example.com", retries=False)


def test_callback_executed_twice(urllib3_mock: Urllib3Mock):
    def custom_response(request):
        return urllib3.HTTPResponse(
            body=io.BytesIO(b"reusable callback"),
            status=200,
            preload_content=False,
        )

    urllib3_mock.add_callback(custom_response, is_reusable=True)
    http = urllib3.PoolManager()
    response1 = http.request("GET", "https://example.com")
    response2 = http.request("POST", "https://example.com")
    assert response1.data == b"reusable callback"
    assert response2.data == b"reusable callback"


def test_callback_registered_after_response(urllib3_mock: Urllib3Mock):
    def custom_response(request):
        return urllib3.HTTPResponse(
            body=io.BytesIO(b"from callback"),
            status=200,
            preload_content=False,
        )

    urllib3_mock.add_response(text="from response")
    urllib3_mock.add_callback(custom_response, is_reusable=True)
    http = urllib3.PoolManager()
    r1 = http.request("GET", "https://example.com")
    r2 = http.request("GET", "https://example.com")
    r3 = http.request("GET", "https://example.com")
    assert r1.data == b"from response"
    assert r2.data == b"from callback"
    assert r3.data == b"from callback"


def test_response_registered_after_callback(urllib3_mock: Urllib3Mock):
    def custom_response(request):
        return urllib3.HTTPResponse(
            body=io.BytesIO(b"from callback"),
            status=200,
            preload_content=False,
        )

    urllib3_mock.add_callback(custom_response)
    urllib3_mock.add_response(text="from response", is_reusable=True)
    http = urllib3.PoolManager()
    r1 = http.request("GET", "https://example.com")
    r2 = http.request("GET", "https://example.com")
    r3 = http.request("GET", "https://example.com")
    assert r1.data == b"from callback"
    assert r2.data == b"from response"
    assert r3.data == b"from response"


# Exceptions


def test_add_exception(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_exception(
        urllib3.exceptions.ConnectTimeoutError(None, None, "timeout")
    )
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.ConnectTimeoutError):
        http.request("GET", "https://example.com", retries=False)


# Request retrieval


def test_get_requests(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    http.request("GET", "https://example.com/1")
    http.request("POST", "https://example.com/2", body=b"data")

    requests = urllib3_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].method == "GET"
    assert requests[1].method == "POST"
    assert requests[1].content == b"data"


def test_get_request(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    http.request("GET", "https://example.com/1")
    http.request("POST", "https://example.com/2")

    request = urllib3_mock.get_request(method="POST")
    assert request is not None
    assert request.method == "POST"


def test_get_request_none(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response()
    http = urllib3.PoolManager()
    http.request("GET", "https://example.com")

    request = urllib3_mock.get_request(method="POST")
    assert request is None


def test_reset(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_optional=True)
    urllib3_mock.reset()
    assert urllib3_mock.get_requests() == []


# Reusable / optional


def test_reusable_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    response1 = http.request("GET", "https://example.com")
    response2 = http.request("GET", "https://example.com")
    assert response1.status == 200
    assert response2.status == 200


def test_optional_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_optional=True)
    # Test passes even though the response was never matched


def test_optional_response_matched(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_optional=True, text="optional but matched")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.data == b"optional but matched"


# JSON deep copy


def test_mutating_json(urllib3_mock: Urllib3Mock):
    mutating_json = {"key": "value"}
    urllib3_mock.add_response(json=mutating_json)
    mutating_json["key"] = "mutated"
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert json.loads(response.data) == {"key": "value"}


# Validation errors


def test_match_json_and_match_content_error(urllib3_mock: Urllib3Mock):
    with pytest.raises(ValueError, match="Only one way"):
        urllib3_mock.add_response(match_content=b"body", match_json={"key": "value"})


def test_match_params_without_url_error(urllib3_mock: Urllib3Mock):
    with pytest.raises(ValueError, match="URL must be provided"):
        urllib3_mock.add_response(match_params={"a": "1"})


def test_match_params_with_regex_url_error(urllib3_mock: Urllib3Mock):
    with pytest.raises(ValueError, match="match_params cannot be used"):
        urllib3_mock.add_response(url=re.compile(r".*"), match_params={"a": "1"})


def test_match_params_with_url_query_string_error(urllib3_mock: Urllib3Mock):
    with pytest.raises(ValueError, match="must not contain any query parameter"):
        urllib3_mock.add_response(
            url="https://example.com?a=1", match_params={"b": "2"}
        )


# PoolManager interception


def test_pool_manager_intercepted(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(json={"ok": True})
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/api")
    assert json.loads(response.data) == {"ok": True}


# Phase 2: Missing matching tests


def test_multi_value_headers_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(match_headers={"Accept": "text/html, application/json"})
    http = urllib3.PoolManager()
    response = http.request(
        "GET",
        "https://example.com",
        headers={"Accept": "text/html, application/json"},
    )
    assert response.status == 200


def test_headers_matching_case_insensitive(urllib3_mock: Urllib3Mock):
    """Header name matching is case-insensitive (urllib3 uses HTTPHeaderDict)."""
    urllib3_mock.add_response(match_headers={"authorization": "Bearer token"})
    http = urllib3.PoolManager()
    response = http.request(
        "GET",
        "https://example.com",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status == 200


# Phase 3: Missing callback test


def test_callback_matching_method(urllib3_mock: Urllib3Mock):
    def post_callback(request):
        return urllib3.HTTPResponse(
            body=io.BytesIO(b"post callback"),
            status=200,
            preload_content=False,
        )

    urllib3_mock.add_response(method="GET")
    urllib3_mock.add_callback(post_callback, method="POST")
    http = urllib3.PoolManager()
    get_response = http.request("GET", "https://example.com")
    post_response = http.request("POST", "https://example.com")
    assert get_response.data == b""
    assert post_response.data == b"post callback"


# Phase 4: Missing retrieval tests


def test_requests_retrieval_on_same_url(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    http.request("GET", "https://example.com/1")
    http.request("GET", "https://example.com/2")
    http.request("GET", "https://example.com/1")

    requests = urllib3_mock.get_requests(url="https://example.com/1")
    assert len(requests) == 2


def test_requests_json_body(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response()
    http = urllib3.PoolManager()
    http.request(
        "POST",
        "https://example.com",
        body=json.dumps({"key": "value"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    request = urllib3_mock.get_request()
    assert json.loads(request.content) == {"key": "value"}


def test_requests_retrieval_content_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    http.request("POST", "https://example.com", body=b"body 1")
    http.request("POST", "https://example.com", body=b"body 2")

    requests = urllib3_mock.get_requests(match_content=b"body 1")
    assert len(requests) == 1
    assert requests[0].content == b"body 1"


def test_requests_retrieval_json_matching(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(is_reusable=True)
    http = urllib3.PoolManager()
    http.request("POST", "https://example.com", body=json.dumps({"a": 1}).encode())
    http.request("POST", "https://example.com", body=json.dumps({"b": 2}).encode())

    requests = urllib3_mock.get_requests(match_json={"a": 1})
    assert len(requests) == 1
    assert json.loads(requests[0].content) == {"a": 1}


# Phase 6: Edge case tests


def test_with_many_reused_responses(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(
        url="https://example.com", is_reusable=True, status_code=200
    )
    urllib3_mock.add_response(
        url="https://example.com", is_reusable=True, status_code=201
    )
    http = urllib3.PoolManager()
    r1 = http.request("GET", "https://example.com")
    r2 = http.request("GET", "https://example.com")
    r3 = http.request("GET", "https://example.com")
    assert r1.status == 200
    assert r2.status == 201
    assert r3.status == 201  # reuses last matching


def test_url_matching_reusing_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(
        url="https://example.com/1", is_reusable=True, text="first"
    )
    urllib3_mock.add_response(url="https://example.com/2", text="second")
    http = urllib3.PoolManager()
    assert http.request("GET", "https://example.com/1").data == b"first"
    assert http.request("GET", "https://example.com/2").data == b"second"
    assert http.request("GET", "https://example.com/1").data == b"first"


def test_non_ascii_url_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://example.com/données")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/données")
    assert response.status == 200


def test_url_encoded_matching_response(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(url="https://example.com/path%20with%20spaces")
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com/path%20with%20spaces")
    assert response.status == 200


@pytest.mark.urllib3_mock(
    assert_all_requests_were_expected=False, assert_all_responses_were_requested=False
)
def test_url_encoded_not_matching_unencoded(urllib3_mock: Urllib3Mock):
    """Percent-encoded characters should not match their decoded equivalents.
    e.g. /a%2Fb (literal %2F) should NOT match /a/b (path separator)."""
    urllib3_mock.add_response(url="https://example.com/a%2Fb")
    http = urllib3.PoolManager()
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http.request("GET", "https://example.com/a/b", retries=False)


@pytest.mark.urllib3_mock(
    can_send_already_matched_responses=True,
    assert_all_responses_were_requested=False,
)
def test_multi_response_matched_once(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(status_code=200)
    urllib3_mock.add_response(status_code=201)
    http = urllib3.PoolManager()
    response = http.request("GET", "https://example.com")
    assert response.status == 200


@pytest.mark.urllib3_mock(can_send_already_matched_responses=True)
def test_multi_response_matched_twice(urllib3_mock: Urllib3Mock):
    urllib3_mock.add_response(status_code=200)
    urllib3_mock.add_response(status_code=201)
    http = urllib3.PoolManager()
    r1 = http.request("GET", "https://example.com")
    r2 = http.request("GET", "https://example.com")
    r3 = http.request("GET", "https://example.com")
    assert r1.status == 200
    assert r2.status == 201
    assert r3.status == 201  # last matching reused
