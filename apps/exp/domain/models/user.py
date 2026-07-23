from __future__ import annotations

from dataclasses import dataclass

from apps.exp.domain.common.entity import Entity
from apps.exp.domain.common.exceptions import InvalidUserError
from apps.exp.domain.value_objects.email import Email

_MAX_DISPLAY_NAME = 128


@dataclass(kw_only=True, eq=False)
class User(Entity):
    email: Email
    display_name: str
    is_active: bool = True

    # def __post_init__(self) -> None:
    #     self.display_name = self._validated_display_name(self.display_name)

    # @staticmethod
    # def _validated_display_name(value: str) -> str:
    #     value = value.strip()
    #     if not value:
    #         raise InvalidUserError("Display name must not be empty.")
    #     if len(value) > _MAX_DISPLAY_NAME:
    #         raise InvalidUserError(
    #             f"Display name must be at most {_MAX_DISPLAY_NAME} characters."
    #         )
    #     return value

    # def rename(self, new_display_name: str) -> None:
    #     self.display_name = self._validated_display_name(new_display_name)

    # def change_email(self, new_email: Email) -> None:
    #     self.email = new_email

    # def deactivate(self) -> None:
    #     self.is_active = False

    # def activate(self) -> None:
    #     self.is_active = True
