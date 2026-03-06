import pytest

pytest_plugins = ["pytester"]


def test_fixture_is_available(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import urllib3


        def test_http(urllib3_mock):
            urllib3_mock.add_response(url="https://foo.tld")
            http = urllib3.PoolManager()
            http.request("GET", "https://foo.tld")
            assert urllib3_mock.get_request() is not None
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_urllib3_mock_unused_response(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_unused_response(urllib3_mock):
            urllib3_mock.add_response()
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match any request",
            "*  ",
            "*  If this is on purpose, use is_optional=True or assert_all_responses_were_requested=False option.",
        ],
        consecutive=True,
    )


def test_urllib3_mock_unused_response_without_assertion(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
        def test_unused_response(urllib3_mock):
            urllib3_mock.add_response()
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_urllib3_mock_unused_callback(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_unused_callback(urllib3_mock):
            def unused(*args, **kwargs):
                pass

            urllib3_mock.add_callback(unused)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match any request",
            "*  ",
            "*  If this is on purpose, use is_optional=True or assert_all_responses_were_requested=False option.",
        ],
        consecutive=True,
    )


def test_urllib3_mock_unused_callback_without_assertion(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
        def test_unused_callback(urllib3_mock):
            def unused(*args, **kwargs):
                pass

            urllib3_mock.add_callback(unused)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_urllib3_mock_unexpected_request(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        def test_unexpected_request(urllib3_mock):
            http = urllib3.PoolManager()
            with pytest.raises(urllib3.exceptions.TimeoutError):
                http.request("GET", "https://foo.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*  - GET request on https://foo.tld*",
            "*  ",
            "*  If this is on purpose, use assert_all_requests_were_expected=False option.",
        ],
        consecutive=True,
    )


def test_urllib3_mock_unexpected_request_without_assertion(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        @pytest.mark.urllib3_mock(assert_all_requests_were_expected=False)
        def test_unexpected_request(urllib3_mock):
            http = urllib3.PoolManager()
            with pytest.raises(urllib3.exceptions.TimeoutError):
                http.request("GET", "https://foo.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_urllib3_mock_already_matched_response(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        def test_already_matched(urllib3_mock):
            urllib3_mock.add_response()
            http = urllib3.PoolManager()
            http.request("GET", "https://foo.tld")
            with pytest.raises(urllib3.exceptions.TimeoutError):
                http.request("GET", "https://foo.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*  - GET request on https://foo.tld*",
            "*  ",
            "*  If this is on purpose, use assert_all_requests_were_expected=False option.",
        ],
        consecutive=True,
    )


def test_urllib3_mock_reusing_matched_response(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import pytest

        @pytest.mark.urllib3_mock(can_send_already_matched_responses=True)
        def test_reusing(urllib3_mock):
            urllib3_mock.add_response()
            http = urllib3.PoolManager()
            http.request("GET", "https://foo.tld")
            http.request("GET", "https://foo.tld")
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_urllib3_mock_should_mock(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        @pytest.mark.urllib3_mock(should_mock=lambda request: "localhost" not in request.url)
        def test_should_mock(urllib3_mock):
            urllib3_mock.add_response()
            http = urllib3.PoolManager()
            # Mocked request
            http.request("GET", "https://foo.tld")

            # Non-mocked request (goes to real network, expect connection error)
            with pytest.raises(urllib3.exceptions.MaxRetryError):
                http.request("GET", "http://localhost:59999", retries=1)

            assert len(urllib3_mock.get_requests()) == 1
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_urllib3_mock_options_on_multi_levels_are_aggregated(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        import pytest


        def pytest_collection_modifyitems(session, config, items):
            for item in items:
                item.add_marker(pytest.mark.urllib3_mock(assert_all_responses_were_requested=False))
    """
    )
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        pytestmark = pytest.mark.urllib3_mock(assert_all_requests_were_expected=False, should_mock=lambda request: "foo.tld" not in request.url)

        @pytest.mark.urllib3_mock(should_mock=lambda request: "localhost" not in request.url)
        def test_multi_level(urllib3_mock):
            urllib3_mock.add_response(url="https://foo.tld", headers={"x-test": "mocked"})

            # This response will never be used (testing assert_all_responses_were_requested from conftest)
            urllib3_mock.add_response(url="https://never_called.url")

            http = urllib3.PoolManager()

            # Assert that test-level should_mock overrides module-level
            response = http.request("GET", "https://foo.tld")
            assert response.headers["x-test"] == "mocked"

            # Assert that latest should_mock is handled (localhost not mocked)
            with pytest.raises(urllib3.exceptions.MaxRetryError):
                http.request("GET", "http://localhost:59999", retries=1)

            # Assert that assert_all_requests_were_expected from module level works
            with pytest.raises(urllib3.exceptions.TimeoutError):
                http.request("GET", "https://unexpected.url", retries=False)

            # 2 requests mocked out of 3 (localhost went through)
            assert len(urllib3_mock.get_requests()) == 2
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_invalid_marker(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.urllib3_mock(foo=123)
        def test_invalid(urllib3_mock):
            pass
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.re_match_lines([r".*got an unexpected keyword argument 'foo'"])


def test_mandatory_response_not_matched(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.urllib3_mock(assert_all_responses_were_requested=False)
        def test_mandatory(urllib3_mock):
            # Optional (default when assert_all_responses_were_requested=False)
            urllib3_mock.add_response(url="https://test_url")
            # Mandatory override
            urllib3_mock.add_response(url="https://test_url2", is_optional=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match any request on https://test_url2",
            "*  ",
            "*  If this is on purpose, use is_optional=True or assert_all_responses_were_requested=False option.",
        ],
        consecutive=True,
    )


def test_reusable_response_not_matched(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_reusable_not_matched(urllib3_mock):
            urllib3_mock.add_response(url="https://test_url", is_reusable=True)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match every request on https://test_url",
            "*  ",
            "*  If this is on purpose, use is_optional=True or assert_all_responses_were_requested=False option.",
        ],
        consecutive=True,
    )


def test_urllib3_mock_unmatched_request_without_responses(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        def test_unmatched(urllib3_mock):
            http = urllib3.PoolManager()
            http.request("GET", "https://foo22.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*urllib3.exceptions.TimeoutError: No response can be found for GET request on https://foo22.tld*",
        ],
        consecutive=True,
    )


def test_urllib3_mock_unmatched_request_with_only_unmatched_responses(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        def test_unmatched(urllib3_mock):
            urllib3_mock.add_response(url="https://foo2.tld")
            urllib3_mock.add_response(url="https://foo3.tld")

            http = urllib3.PoolManager()
            http.request("GET", "https://foo22.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*urllib3.exceptions.TimeoutError: No response can be found for GET request on https://foo22.tld* amongst:",
            "*- Match any request on https://foo2.tld",
            "*- Match any request on https://foo3.tld",
        ],
        consecutive=True,
    )


def test_urllib3_mock_unmatched_request_with_only_matched_responses(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        def test_unmatched(urllib3_mock):
            urllib3_mock.add_response(url="https://foo.tld")
            urllib3_mock.add_response(url="https://foo.tld")

            http = urllib3.PoolManager()
            http.request("GET", "https://foo.tld")
            http.request("GET", "https://foo.tld")
            http.request("GET", "https://foo22.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*urllib3.exceptions.TimeoutError: No response can be found for GET request on https://foo22.tld* amongst:",
            "*- Already matched any request on https://foo.tld",
            "*- Already matched any request on https://foo.tld",
            "*",
            "*If you wanted to reuse an already matched response*is_reusable=True or can_send_already_matched_responses option.",
        ],
        consecutive=True,
    )


def test_get_request_with_more_than_one(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import urllib3

        def test_more_than_one(urllib3_mock):
            urllib3_mock.add_response(is_reusable=True)
            http = urllib3.PoolManager()
            http.request("GET", "https://test_url")
            http.request("GET", "https://test_url")
            urllib3_mock.get_request(url="https://test_url")
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: More than one request (2) matched, use get_requests instead or refine your filters."
        ]
    )


def test_urllib3_mock_unmatched_request_with_matched_and_unmatched_responses(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        import urllib3
        import urllib3.exceptions
        import pytest

        def test_unmatched(urllib3_mock):
            urllib3_mock.add_response(url="https://foo.tld")
            urllib3_mock.add_response(url="https://foo2.tld")
            urllib3_mock.add_response(url="https://foo.tld")
            urllib3_mock.add_response(url="https://foo3.tld")

            http = urllib3.PoolManager()
            http.request("GET", "https://foo.tld")
            http.request("GET", "https://foo.tld")
            http.request("GET", "https://foo22.tld", retries=False)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*urllib3.exceptions.TimeoutError: No response can be found for GET request on https://foo22.tld* amongst:",
            "*- Match any request on https://foo2.tld",
            "*- Match any request on https://foo3.tld",
            "*- Already matched any request on https://foo.tld",
            "*- Already matched any request on https://foo.tld",
            "*",
            "*If you wanted to reuse an already matched response*is_reusable=True or can_send_already_matched_responses option.",
        ],
        consecutive=True,
    )
