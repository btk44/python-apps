from fastapi import Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import and_, func, select
from collections.abc import AsyncIterator

from pydantic import BaseModel

from apps.expenses.domain.common.enums import CategoryType
from apps.expenses.domain.models.category import Category
from apps.expenses.features.common.helpers import Error
from apps.expenses.infrastructure.mappers.category_mapper import row_to_category
from apps.expenses.infrastructure.session import get_connection
from apps.expenses.infrastructure.tables import categories

from apps.expenses.features.a_router import router

# DTOs and command models will have camel case properties to be more convenient for frontend
class CategorySearchCommand(BaseModel):
    userId: int | None
    codes: list[str] | None = None
    ids: list[int] | None = None
    name: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None

class CategoryDto(BaseModel):
    id: int
    userId: int
    parentId: int | None = None
    code: str
    name: str
    active: bool
    icon: str | None
    version: int
    type: CategoryType


async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn

def map_category_entity_to_dto(entity: Category) -> CategoryDto | Error:
    if entity.id is None:
        return Error("entity id is not assigned!")

    return CategoryDto(
        id=entity.id,
        userId=entity.user_id,
        parentId=entity.parent_id,
        code=entity.code,
        name=entity.name,
        icon=entity.icon,
        type=entity.type,
        active=entity.is_active,
        version=entity.version
    )

def build_category_query(command: CategorySearchCommand):
    conditions = []

    if command.active is not None:
        conditions.append(categories.c.active == command.active)

    if command.userId is not None:
        conditions.append(categories.c.user_id == command.userId)

    if command.ids is not None and len(command.ids) > 0:
        conditions.append(categories.c.id.in_(command.ids))

    if command.codes is not None and len(command.codes) > 0:
        lowered_codes = [c.lower() for c in command.codes]
        conditions.append(func.lower(categories.c.unique_code).in_(lowered_codes))

    if command.name is not None and command.name != "":
        lowered_name = command.name.lower()
        conditions.append(func.lower(categories.c.name).like(f"%{lowered_name}%"))

    query = select(categories)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)

    return query

@router.post("/category/search")
async def search_categories(command: CategorySearchCommand, conn: AsyncConnection = Depends(get_db)):
    result = await conn.execute(build_category_query(command))
    category_entities = [row_to_category(row) for row in result]
    result_list = []
    for entity in category_entities:
        dto = map_category_entity_to_dto(entity) if entity is not None else None
        if isinstance(dto, Error):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"status": "broken data in categories table!"})

        elif dto is not None:
           result_list.append(dto)

    return result_list
