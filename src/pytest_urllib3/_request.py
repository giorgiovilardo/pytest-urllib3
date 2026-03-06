from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Request:
    method: str
    url: str
    body: Optional[bytes] = None
    headers: dict = field(default_factory=dict)

    @property
    def content(self) -> bytes:
        if self.body is None:
            return b""
        if isinstance(self.body, str):
            return self.body.encode("utf-8")
        return self.body
