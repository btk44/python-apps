from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.expenses.domain.common.exceptions import InvalidMoneyError


@dataclass(frozen=True, slots=True)
class Money:
    """An immutable, strictly-positive monetary amount.

    `decimals` is supplied by the caller (typically `Currency.decimals`,
    e.g. 0 for JPY, 2 for USD/EUR, 3 for KWD) rather than looked up here,
    so this value object has no dependency on the `Currency` entity.

    The schema enforces `amount > 0` and lets direction (debit/credit)
    carry the sign semantics — this mirrors that: `Money` is always
    positive, and `Transaction.signed_amount()` applies the sign.
    """

    amount: Decimal
    decimals: int = 2

    def __post_init__(self) -> None:
        amount = Decimal(self.amount)
        if amount <= 0:
            raise InvalidMoneyError(f"Amount must be positive, got {amount}.")
        if self.decimals < 0:
            raise InvalidMoneyError(f"decimals must be >= 0, got {self.decimals}.")
        quantum = Decimal(1).scaleb(-self.decimals)
        object.__setattr__(self, "amount", amount.quantize(quantum, rounding=ROUND_HALF_UP))

    def __add__(self, other: "Money") -> "Money":
        self._assert_same_precision(other)
        return Money(self.amount + other.amount, self.decimals)

    def __sub__(self, other: "Money") -> Decimal:
        """Returns a plain `Decimal`, not `Money`, since the result may be
        zero or negative — which would violate Money's positivity invariant."""
        self._assert_same_precision(other)
        return self.amount - other.amount

    def __lt__(self, other: "Money") -> bool:
        self._assert_same_precision(other)
        return self.amount < other.amount

    def _assert_same_precision(self, other: "Money") -> None:
        if self.decimals != other.decimals:
            raise InvalidMoneyError(
                "Cannot combine Money values with different currency precisions."
            )

    def __str__(self) -> str:
        return f"{self.amount:.{self.decimals}f}"
