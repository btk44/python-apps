"""Transfer entity.

An immutable correlation record linking two transaction legs (the source
debit and the destination credit). Deliberately does *not* extend
`Entity`: it has no `version` and no `updated_at`, since a transfer is
never edited once created — mirroring the "immutable by design" note on
the `transfers` table. Soft-delete happens on the linked transaction legs
via `Transaction.void()`, not here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from apps.exp.domain.common.exceptions import InvalidTransferError
from apps.exp.domain.models.transaction import Transaction


@dataclass(frozen=True, kw_only=True)
class Transfer:
    id: Optional[int] = None
    from_tx_id: int
    to_tx_id: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    from_transaction: Transaction = None
    to_transaction: Transaction = None

    def __post_init__(self) -> None:
        if self.from_tx_id == self.to_tx_id:
            raise InvalidTransferError("A transfer cannot link a transaction to itself.")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transfer):
            return NotImplemented
        if self.id is None or other.id is None:
            return self is other
        return self.id == other.id

    def __hash__(self) -> int:
        if self.id is None:
            return id(self)
        return hash((Transfer, self.id))
