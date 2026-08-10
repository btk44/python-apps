from fastapi import Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import and_, select
from collections.abc import AsyncIterator

from pydantic import BaseModel

from apps.exp.domain.models.currency import Currency
from apps.exp.features.common.helpers import Error
from apps.exp.infrastructure.mappers.currency_mapper import row_to_currency
from apps.exp.infrastructure.session import get_connection
from apps.exp.infrastructure.tables import currencies

from apps.exp.features.a_router import router

# DTOs and command models will have camel case properties to be more convenient for frontend
class CurrencySearchCommand(BaseModel):
    code: str | None = None
    id: int | None = None
    name: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None


class CurrencyDto(BaseModel):
    id: int
    code: str
    name: str
    decimals: int
    symbol: str
    active: bool


async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn

def map_currency_entity_to_dto(entity: Currency) -> CurrencyDto | Error:
    if entity.id is None:
        return Error("entity id is not assigned!")

    return CurrencyDto(
        id=entity.id,
        code=entity.code,
        name=entity.name,
        decimals=entity.decimals,
        symbol=entity.symbol,
        active=entity.is_active
    )


def build_currency_query(command: CurrencySearchCommand):
    conditions = []
    
    if command.active is not None:
        conditions.append(currencies.c.is_active == command.active)
    
    if command.id is not None:
        conditions.append(currencies.c.id == command.id)
    
    if command.code is not None:
        conditions.append(currencies.c.code.ilike(f"%{command.code}%"))
    
    if command.name is not None:
        conditions.append(currencies.c.name.ilike(f"%{command.name}%"))
    
    query = select(currencies)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)
    
    return query.order_by(currencies.c.code.asc())

@router.post("/currency/search")
async def search_currencies(command: CurrencySearchCommand, conn: AsyncConnection = Depends(get_db)):
    result = await conn.execute(build_currency_query(command))
    currency_entities = [row_to_currency(row) for row in result ]
    result_list = []
    for entity in currency_entities:
        dto = map_currency_entity_to_dto(entity) if entity is not None else None
        if isinstance(dto, Error):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"status": "broken data in currencies table!"})
        elif dto is not None:
           result_list.append(dto)

    return result_list
