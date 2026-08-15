from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.expenses.domain.common.entity import Entity
from apps.expenses.domain.common.enums import CategoryType
from apps.expenses.domain.common.exceptions import InvalidCategoryError

# _CODE_LENGTH = 8
# _MAX_NAME_LENGTH = 64


@dataclass(kw_only=True, eq=False)
class Category(Entity):
    user_id: int
    parent_id: Optional[int] = None
    code: str
    name: str
    icon: Optional[str] = None
    type: CategoryType
    is_active: bool = True

    # below methods are not yet needed 

    # def __post_init__(self) -> None:
    #     self.code = self.code.strip().upper()
    #     self.name = self.name.strip()
    #     if not self.code or len(self.code) > _CODE_LENGTH:
    #         raise InvalidCategoryError(
    #             f"Category code must be 1-{_CODE_LENGTH} characters, got '{self.code}'."
    #         )
    #     if not self.name or len(self.name) > _MAX_NAME_LENGTH:
    #         raise InvalidCategoryError(
    #             f"Category name must be 1-{_MAX_NAME_LENGTH} characters."
    #         )
    #     self._assert_not_own_parent(self.parent_id)

    # def _assert_not_own_parent(self, parent_id: Optional[int]) -> None:
    #     if self.id is not None and parent_id is not None and parent_id == self.id:
    #         raise InvalidCategoryError("A category cannot be its own parent.")

    # def rename(self, new_name: str) -> None:
    #     new_name = new_name.strip()
    #     if not new_name or len(new_name) > _MAX_NAME_LENGTH:
    #         raise InvalidCategoryError(
    #             f"Category name must be 1-{_MAX_NAME_LENGTH} characters."
    #         )
    #     self.name = new_name

    # def move_under(self, new_parent_id: Optional[int]) -> None:
    #     self._assert_not_own_parent(new_parent_id)
    #     self.parent_id = new_parent_id

    # def deactivate(self) -> None:
    #     self.is_active = False

    # def activate(self) -> None:
    #     self.is_active = True

    # def supports(self, direction_type: CategoryType) -> bool:
    #     """Whether this category may be used for the given transaction type."""
    #     return self.type in (CategoryType.BOTH, direction_type)
