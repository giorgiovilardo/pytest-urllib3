from pytest_urllib3._request import Request
from pytest_urllib3._request_matcher import _RequestMatcher


def describe_request(
    request: Request,
    matchers: list[_RequestMatcher],
) -> str:
    expected_headers = {
        header for matcher in matchers if matcher.headers for header in matcher.headers
    }
    expect_body = any(
        matcher.content is not None or matcher.json is not None for matcher in matchers
    )

    description = f"{request.method} request on {request.url}"

    extra = []
    if expected_headers:
        lower_expected = {h.lower() for h in expected_headers}
        present_headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() in lower_expected
        }
        extra.append(f"{present_headers} headers")
    if expect_body:
        extra.append(f"{request.content} body")
    if extra:
        description += f" with {' and '.join(extra)}"

    return description


def explain_no_response_found(
    request: Request,
    matchers: list[_RequestMatcher],
) -> str:
    message = f"No response can be found for {describe_request(request, matchers)}"

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
