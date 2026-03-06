import copy
import http.client
import io
import json as json_module
from collections.abc import Callable
from typing import Any, NoReturn, Optional

import urllib3.exceptions

import urllib3
from pytest_urllib3._options import _Urllib3MockOptions
from pytest_urllib3._pretty_print import RequestDescription
from pytest_urllib3._request import Request
from pytest_urllib3._request_matcher import _RequestMatcher


def _build_response(
    status_code: int = 200,
    headers: Optional[dict[str, str]] = None,
    content: Optional[bytes] = None,
    text: Optional[str] = None,
    json: Any = None,
) -> urllib3.HTTPResponse:
    final_headers = dict(headers or {})

    if json is not None:
        body = json_module.dumps(json).encode("utf-8")
        final_headers.setdefault("Content-Type", "application/json")
    elif text is not None:
        body = text.encode("utf-8")
        final_headers.setdefault("Content-Type", "text/plain; charset=utf-8")
    elif content is not None:
        body = content
    else:
        body = b""

    final_headers.setdefault("Content-Length", str(len(body)))

    return urllib3.HTTPResponse(
        body=io.BytesIO(body),
        status=status_code,
        headers=final_headers,
        preload_content=False,
        decode_content=False,
        version=11,
        version_string="HTTP/1.1",
        reason=http.client.responses.get(status_code, "Unknown"),
    )


class Urllib3Mock:
    def __init__(self, options: _Urllib3MockOptions) -> None:
        self._options = options
        self._requests: list[Request] = []
        self._callbacks: list[
            tuple[_RequestMatcher, Callable[[Request], Optional[urllib3.HTTPResponse]]]
        ] = []
        self._requests_not_matched: list[Request] = []

    def add_response(
        self,
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        json: Any = None,
        **matchers: Any,
    ) -> None:
        """Queue a response to return when a matching request is made.

        :param status_code: HTTP status code (default 200).
        :param headers: Response headers dict.
        :param content: Response body as bytes.
        :param text: Response body as string (sets Content-Type: text/plain).
        :param json: Response body as JSON-serializable object (sets Content-Type: application/json).
        :param **matchers: Request matching criteria (url, method, match_headers, match_content, match_json, match_params, is_optional, is_reusable).
        """
        json = copy.deepcopy(json) if json is not None else None

        def response_callback(request: Request) -> urllib3.HTTPResponse:
            return _build_response(
                status_code=status_code,
                headers=headers,
                content=content,
                text=text,
                json=json,
            )

        self.add_callback(response_callback, **matchers)

    def add_callback(
        self,
        callback: Callable[[Request], Optional[urllib3.HTTPResponse]],
        **matchers: Any,
    ) -> None:
        """Register a callback to handle matching requests.

        :param callback: Callable receiving a Request, must return a urllib3.HTTPResponse (or None).
        :param **matchers: Request matching criteria.
        """
        self._callbacks.append((_RequestMatcher(self._options, **matchers), callback))

    def add_exception(self, exception: BaseException, **matchers: Any) -> None:
        """Raise an exception when a matching request is made.

        :param exception: The exception to raise.
        :param **matchers: Request matching criteria.
        """

        def exception_callback(request: Request) -> None:
            raise exception

        self.add_callback(exception_callback, **matchers)

    def _handle_request(self, request: Request) -> urllib3.HTTPResponse:
        self._requests.append(request)

        callback = self._get_callback(request)
        if callback:
            response = callback(request)
            if response:
                return response

        self._request_not_matched(request)

    def _request_not_matched(self, request: Request) -> NoReturn:
        self._requests_not_matched.append(request)
        raise urllib3.exceptions.TimeoutError(
            self._explain_that_no_response_was_found(request)
        )

    def _explain_that_no_response_was_found(self, request: Request) -> str:
        matchers = [matcher for matcher, _ in self._callbacks]

        message = (
            f"No response can be found for {RequestDescription(request, matchers)}"
        )

        already_matched = []
        unmatched = []
        for matcher in matchers:
            if matcher.nb_calls:
                already_matched.append(matcher)
            else:
                unmatched.append(matcher)

        matchers_description = "\n".join(
            [f"- {matcher}" for matcher in unmatched + already_matched]
        )
        if matchers_description:
            message += f" amongst:\n{matchers_description}"
            if any(not matcher.is_reusable for matcher in already_matched):
                message += "\n\nIf you wanted to reuse an already matched response instead of registering it again, refer to is_reusable=True or can_send_already_matched_responses option."

        return message

    def _get_callback(
        self, request: Request
    ) -> Optional[Callable[[Request], Optional[urllib3.HTTPResponse]]]:
        callbacks = [
            (matcher, callback)
            for matcher, callback in self._callbacks
            if matcher.match(request)
        ]

        if not callbacks:
            return None

        for matcher, callback in callbacks:
            if not matcher.nb_calls:
                matcher.nb_calls += 1
                return callback

        # Or the last registered (if it can be reused)
        if matcher.is_reusable:
            matcher.nb_calls += 1
            return callback

        return None

    def get_requests(self, **matchers: Any) -> list[Request]:
        """Return all captured requests matching the given criteria.

        :param **matchers: Request matching criteria (url, method, match_headers, match_content, match_json, match_params).
        """
        matcher = _RequestMatcher(self._options, **matchers)
        return [request for request in self._requests if matcher.match(request)]

    def get_request(self, **matchers: Any) -> Optional[Request]:
        """Return the single captured request matching the criteria, or None.

        :param **matchers: Request matching criteria.
        :raises AssertionError: If more than one request matches.
        """
        requests = self.get_requests(**matchers)
        assert len(requests) <= 1, (
            f"More than one request ({len(requests)}) matched, use get_requests instead or refine your filters."
        )
        return requests[0] if requests else None

    def reset(self) -> None:
        """Clear all registered responses, callbacks, and captured requests."""
        self._requests.clear()
        self._callbacks.clear()
        self._requests_not_matched.clear()

    def _assert_options(self) -> None:
        callbacks_not_executed = [
            matcher for matcher, _ in self._callbacks if matcher.should_have_matched()
        ]
        matchers_description = "\n".join(
            [f"- {matcher}" for matcher in callbacks_not_executed]
        )

        assert not callbacks_not_executed, (
            f"The following responses are mocked but not requested:\n{matchers_description}\n\nIf this is on purpose, use is_optional=True or assert_all_responses_were_requested=False option."
        )

        if self._options.assert_all_requests_were_expected:
            requests_description = "\n".join(
                [
                    f"- {request.method} request on {request.url}"
                    for request in self._requests_not_matched
                ]
            )
            assert not self._requests_not_matched, (
                f"The following requests were not expected:\n{requests_description}\n\nIf this is on purpose, use assert_all_requests_were_expected=False option."
            )
