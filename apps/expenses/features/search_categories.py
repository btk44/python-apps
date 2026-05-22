from . import router
from sqlalchemy import select, and_, func
from ..database.models.category import Category
from ..database.session import SessionLocal
from pydantic import BaseModel

# DTOs and command models will have camel case properties to be more convenient for frontend
class CategorySearchCommand(BaseModel):
    ownerId: int | None
    codes: list[str] | None = None
    ids: list[int] | None = None
    name: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None

class CategoryDto(BaseModel):
    id: int
    ownerId: int
    uniqueCode: str
    name: str
    active: bool

def map_category_entity_to_dto(entity: Category) -> CategoryDto:
    return CategoryDto(
        id=entity.id,
        ownerId=entity.owner_id,
        uniqueCode=entity.unique_code,
        name=entity.name,
        active=entity.active
    )


def build_category_query(command: CategorySearchCommand):
    conditions = []

    if command.active is not None:
        conditions.append(Category.active == command.active)

    if command.ownerId is not None:
        conditions.append(Category.owner_id == command.ownerId)

    if command.ids is not None and len(command.ids) > 0:
        conditions.append(Category.id.in_(command.ids))

    if command.codes is not None and len(command.codes) > 0:
        lowered_codes = [c.lower() for c in command.codes]
        conditions.append(func.lower(Category.unique_code).in_(lowered_codes))

    if command.name is not None and command.name != "":
        lowered_name = command.name.lower()
        conditions.append(func.lower(Category.name).like(f"%{lowered_name}%"))

    query = select(Category)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)

    return query


@router.post("/category/search")
async def search_categories(command: CategorySearchCommand):
    async with SessionLocal() as session:
        query = build_category_query(command)
        result = await session.scalars(query)
        return [map_category_entity_to_dto(entity) for entity in result.all()]

