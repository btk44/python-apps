from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.exp.domain.common.entity import Entity
from apps.exp.domain.common.enums import AccountType
from apps.exp.domain.common.exceptions import InvalidAccountError

# _CODE_LENGTH = 8
# _MAX_NAME_LENGTH = 64


@dataclass(kw_only=True, eq=False)
class Account(Entity):
    user_id: int
    currency_id: int
    code: str
    name: str
    type: AccountType
    icon: Optional[str] = None
    is_active: bool = True

    # below methods are not yet needed 

    # def __post_init__(self) -> None:
    #     self.code = self.code.strip().upper()
    #     self.name = self.name.strip()
    #     if not self.code or len(self.code) > _CODE_LENGTH:
    #         raise InvalidAccountError(
    #             f"Account code must be 1-{_CODE_LENGTH} characters, got '{self.code}'."
    #         )
    #     if not self.name or len(self.name) > _MAX_NAME_LENGTH:
    #         raise InvalidAccountError(
    #             f"Account name must be 1-{_MAX_NAME_LENGTH} characters."
    #         )

    # def rename(self, new_name: str) -> None:
    #     new_name = new_name.strip()
    #     if not new_name or len(new_name) > _MAX_NAME_LENGTH:
    #         raise InvalidAccountError(
    #             f"Account name must be 1-{_MAX_NAME_LENGTH} characters."
    #         )
    #     self.name = new_name

    # def deactivate(self) -> None:
    #     self.is_active = False

    # def activate(self) -> None:
    #     self.is_active = True
