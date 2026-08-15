from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass(kw_only=True)
class Entity:
    id: Optional[int] = None
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        if self.id is None or other.id is None:
            return self is other
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        if self.id is None:
            return id(self)
        return hash((type(self), self.id))

    @property
    def is_persisted(self) -> bool:
        return self.id is not None