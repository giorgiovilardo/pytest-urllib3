from pytest_urllib3._request import Request
from pytest_urllib3._request_matcher import _RequestMatcher


class RequestDescription:
    def __init__(
        self,
        request: Request,
        matchers: list[_RequestMatcher],
    ):
        self.request = request
        self.expected_headers = {
            header
            for matcher in matchers
            if matcher.headers
            for header in matcher.headers
        }
        self.expect_body = any(
            matcher.content is not None or matcher.json is not None
            for matcher in matchers
        )

    def __str__(self) -> str:
        request_description = f"{self.request.method} request on {self.request.url}"
        if extra_description := self._extra_description():
            request_description += f" with {extra_description}"
        return request_description

    def _extra_description(self) -> str:
        extra_description = []
        if self.expected_headers:
            lower_expected = {h.lower() for h in self.expected_headers}
            present_headers = {
                name: value
                for name, value in self.request.headers.items()
                if name.lower() in lower_expected
            }
            extra_description.append(f"{present_headers} headers")
        if self.expect_body:
            extra_description.append(f"{self.request.content} body")
        return " and ".join(extra_description)
