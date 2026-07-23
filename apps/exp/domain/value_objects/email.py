from __future__ import annotations

import re
from dataclasses import dataclass

from apps.exp.domain.common.exceptions import InvalidEmailError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_LENGTH = 256  # matches users.email VARCHAR(256)


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized or len(normalized) > _MAX_LENGTH:
            raise InvalidEmailError(
                f"Email must be 1-{_MAX_LENGTH} characters, got {len(normalized)}."
            )
        if not _EMAIL_RE.match(normalized):
            raise InvalidEmailError(f"'{self.value}' is not a valid email address.")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
