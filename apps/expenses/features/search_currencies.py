from . import router
from sqlalchemy import select, and_
from ..database.models.currency import Currency
from ..database.session import SessionLocal
from pydantic import BaseModel

# DTOs and command models will have camel case properties to be more convenient for frontend
class CurrencySearchCommand(BaseModel):
    code: str | None = None
    id: int | None = None
    description: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None


class CurrencyDto(BaseModel):
    id: int
    code: str
    description: str
    active: bool


def map_currency_entity_to_dto(entity: Currency) -> CurrencyDto:
    return CurrencyDto(
        id=entity.id,
        code=entity.code,
        description=entity.description,
        active=entity.active
    )


def build_currency_query(command: CurrencySearchCommand):
    conditions = []
    
    if command.active is not None:
        conditions.append(Currency.active == command.active)
    
    if command.id is not None:
        conditions.append(Currency.id == command.id)
    
    if command.code is not None:
        conditions.append(Currency.code.ilike(f"%{command.code}%"))
    
    if command.description is not None:
        conditions.append(Currency.description.ilike(f"%{command.description}%"))
    
    query = select(Currency)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)
    
    return query

@router.post("/currency/search")
async def search_currencies(command: CurrencySearchCommand):
    async with SessionLocal() as session:
        query = build_currency_query(command)
        result = await session.scalars(query)
        return [map_currency_entity_to_dto(entity) for entity in result.all()]
