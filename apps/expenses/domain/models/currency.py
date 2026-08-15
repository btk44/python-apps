from __future__ import annotations

from dataclasses import dataclass

from apps.expenses.domain.common.entity import Entity
from apps.expenses.domain.common.exceptions import InvalidCurrencyError

# _CODE_LENGTH = 3  # ISO 4217
MAX_CURRENCY_DECIMALS = 4

@dataclass(kw_only=True, eq=False)
class Currency(Entity):
    code: str
    name: str
    symbol: str
    decimals: int = 2
    is_active: bool = True

    # def __post_init__(self) -> None:
    #     self.code = self.code.strip().upper()
    #     self.name = self.name.strip()
    #     self.symbol = self.symbol.strip()
    #     if len(self.code) != _CODE_LENGTH or not self.code.isalpha():
    #         raise InvalidCurrencyError(
    #             f"Currency code must be {_CODE_LENGTH} letters (ISO 4217), got '{self.code}'."
    #         )
    #     if not self.name:
    #         raise InvalidCurrencyError("Currency name must not be empty.")
    #     if not self.symbol:
    #         raise InvalidCurrencyError("Currency symbol must not be empty.")
    #     if self.decimals < 0:
    #         raise InvalidCurrencyError(f"decimals must be >= 0, got {self.decimals}.")

    # def deactivate(self) -> None:
    #     self.is_active = False

    # def activate(self) -> None:
    #     self.is_active = True
