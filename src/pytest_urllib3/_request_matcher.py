import json
import re
from typing import Any, Optional, Union
from urllib.parse import parse_qs, quote, urlparse

from pytest_urllib3._options import _Urllib3MockOptions
from pytest_urllib3._request import Request


def _url_match(
    url_to_match: Union[re.Pattern[str], str],
    received_url: str,
    params: Optional[dict[str, Union[str, list[str]]]],
) -> bool:
    if isinstance(url_to_match, re.Pattern):
        return url_to_match.match(received_url) is not None

    parsed_expected = urlparse(url_to_match)
    parsed_received = urlparse(received_url)

    # Compare query parameters apart as order should not matter
    if params is None:
        expected_params = _to_params_dict(parse_qs(parsed_expected.query))
    else:
        expected_params = params
    received_params = _to_params_dict(parse_qs(parsed_received.query))

    # Normalize paths: percent-encode any non-ASCII characters so that
    # user-provided Unicode paths (e.g. "/données") match urllib3's
    # percent-encoded form (e.g. "/donn%C3%A9es"), while keeping
    # already-encoded sequences (e.g. "%2F") intact.
    expected_no_query = parsed_expected._replace(
        query="",
        path=quote(parsed_expected.path or "/", safe="/:@!$&'()*+,;=-._~%"),
    )
    received_no_query = parsed_received._replace(
        query="",
        path=quote(parsed_received.path or "/", safe="/:@!$&'()*+,;=-._~%"),
    )

    return (received_params == expected_params) and (
        expected_no_query == received_no_query
    )


def _to_params_dict(
    qs: dict[str, list[str]],
) -> dict[str, Union[str, list[str]]]:
    """Convert parse_qs output to a dict where single-value params are strings."""
    return {
        key: values[0] if len(values) == 1 else values for key, values in qs.items()
    }


class _RequestMatcher:
    def __init__(
        self,
        options: _Urllib3MockOptions,
        url: Optional[Union[str, re.Pattern[str]]] = None,
        method: Optional[str] = None,
        match_headers: Optional[dict[str, Any]] = None,
        match_content: Optional[bytes] = None,
        match_json: Optional[Any] = None,
        match_params: Optional[dict[str, Union[str, list[str]]]] = None,
        is_optional: Optional[bool] = None,
        is_reusable: Optional[bool] = None,
    ):
        self._options = options
        self.nb_calls = 0
        self.url = url
        self.method = method.upper() if method else method
        self.headers = match_headers
        self.content = match_content
        self.json = match_json
        self.params = match_params
        self.is_optional = (
            not options.assert_all_responses_were_requested
            if is_optional is None
            else is_optional
        )
        self.is_reusable = (
            options.can_send_already_matched_responses
            if is_reusable is None
            else is_reusable
        )
        if self._is_matching_body_more_than_one_way():
            raise ValueError(
                "Only one way of matching against the body can be provided. Use match_json for JSON or match_content for raw bytes."
            )
        if self.params and not self.url:
            raise ValueError("URL must be provided when match_params is used.")
        if self.params is not None and isinstance(self.url, re.Pattern):
            raise ValueError("match_params cannot be used in addition to regex URL.")
        if self._is_matching_params_more_than_one_way():
            raise ValueError(
                "Provided URL must not contain any query parameter when match_params is used."
            )

    def _is_matching_body_more_than_one_way(self) -> bool:
        matching_ways = [
            self.content is not None,
            self.json is not None,
        ]
        return sum(matching_ways) > 1

    def _is_matching_params_more_than_one_way(self) -> bool:
        url_has_params = (
            bool(urlparse(self.url).query)
            if (self.url and isinstance(self.url, str))
            else False
        )
        matching_ways = [
            self.params is not None,
            url_has_params,
        ]
        return sum(matching_ways) > 1

    def match(self, request: Request) -> bool:
        return (
            self._url_match(request)
            and self._method_match(request)
            and self._headers_match(request)
            and self._content_match(request)
        )

    def _url_match(self, request: Request) -> bool:
        if not self.url:
            return True
        return _url_match(self.url, request.url, self.params)

    def _method_match(self, request: Request) -> bool:
        if not self.method:
            return True
        return request.method == self.method

    def _headers_match(self, request: Request) -> bool:
        if not self.headers:
            return True
        lower_headers = {k.lower(): v for k, v in request.headers.items()}
        return all(
            lower_headers.get(name.lower()) == value
            for name, value in self.headers.items()
        )

    def _content_match(self, request: Request) -> bool:
        if self.content is not None:
            return request.content == self.content

        if self.json is not None:
            try:
                return json.loads(request.content.decode("utf-8")) == self.json
            except (json.JSONDecodeError, UnicodeDecodeError):
                return False

        return True

    def should_have_matched(self) -> bool:
        return not self.is_optional and not self.nb_calls

    def __str__(self) -> str:
        if self.is_reusable:
            matcher_description = f"Match {self.method or 'every'} request"
        else:
            matcher_description = "Already matched" if self.nb_calls else "Match"
            matcher_description += f" {self.method or 'any'} request"
        if self.url:
            matcher_description += f" on {self.url}"
        if extra_description := self._extra_description():
            matcher_description += f" with {extra_description}"
        return matcher_description

    def _extra_description(self) -> str:
        extra_description = []
        if self.params:
            extra_description.append(f"{self.params} query parameters")
        if self.headers:
            extra_description.append(f"{self.headers} headers")
        if self.content is not None:
            extra_description.append(f"{self.content} body")
        if self.json is not None:
            extra_description.append(f"{self.json} json body")
        return " and ".join(extra_description)
