from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from apps.exp.domain.common.entity import Entity
from apps.exp.domain.common.enums import TransactionDirection
from apps.exp.domain.common.exceptions import InvalidTransactionError
from apps.exp.domain.value_objects.money import Money

_MAX_COMMENT_LENGTH = 10


@dataclass(kw_only=True, eq=False)
class Transaction(Entity):
    user_id: int
    account_id: int
    category_id: int
    money: Money
    direction: TransactionDirection
    comment: Optional[str] = None
    is_active: bool = True
    transacted_at: datetime

    def __post_init__(self) -> None:
        self.comment = self._validated_comment(self.comment)

    @staticmethod
    def _validated_comment(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > _MAX_COMMENT_LENGTH:
            raise InvalidTransactionError(
                f"Comment must be at most {_MAX_COMMENT_LENGTH} characters."
            )
        return value

    @property
    def amount(self) -> Decimal:
        return self.money.amount

    def signed_amount(self) -> Decimal:
        if self.direction == TransactionDirection.DEBIT:
            return -self.money.amount
        return self.money.amount

    def recategorize(self, new_category_id: int, new_direction: TransactionDirection) -> None:
        self.category_id = new_category_id
        self.direction = new_direction

    def update_account(self, new_account_id: int) -> None:
        self.account_id = new_account_id

    def update_amount(self, new_amount: Decimal, decimals: int) -> None:
        self.money = Money(amount=new_amount, decimals=decimals)

    def update_comment(self, new_comment: Optional[str]) -> None:
        self.comment = self._validated_comment(new_comment)

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
