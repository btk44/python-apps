from fastapi import Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import and_, func, select
from collections.abc import AsyncIterator

from pydantic import BaseModel

from apps.exp.domain.common.enums import AccountType
from apps.exp.domain.models.account import Account
from apps.exp.features.common.helpers import Error
from apps.exp.infrastructure.mappers.account_mapper import row_to_account
from apps.exp.infrastructure.session import get_connection
from apps.exp.infrastructure.tables import accounts

from apps.exp.features.a_router import router

# DTOs and command models will have camel case properties to be more convenient for frontend
class AccountSearchCommand(BaseModel):
    userId: int | None
    currencies: list[int] | None = None
    codes: list[str] | None = None
    ids: list[int] | None = None
    name: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None

class AccountDto(BaseModel):
    id: int
    userId: int
    currencyId: int
    code: str
    name: str
    active: bool
    type: AccountType
    version: int
    icon: str | None


async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn

def map_account_entity_to_dto(entity: Account) -> AccountDto | Error:
    if entity.id is None:
        return Error("entity id is not assigned!")

    return AccountDto(
        id=entity.id,
        userId=entity.user_id,
        currencyId=entity.currency_id,
        code=entity.code,
        name=entity.name,
        type=entity.type,
        icon=entity.icon,
        active=entity.is_active,
        version=entity.version
    )

def build_account_query(command: AccountSearchCommand):
    conditions = []
    
    if command.active is not None:
        conditions.append(accounts.c.is_active == command.active)

    if command.userId is not None:
        conditions.append(accounts.c.user_id == command.userId)

    if command.ids is not None and len(command.ids) > 0:
        conditions.append(accounts.c.id.in_(command.ids))

    if command.currencies is not None and len(command.currencies) > 0:
        conditions.append(accounts.c.currency_id.in_(command.currencies))

    if command.codes is not None and len(command.codes) > 0:
        # exact, case-insensitive match for each code
        lowered_codes = [c.lower() for c in command.codes]
        conditions.append(func.lower(accounts.c.code).in_(lowered_codes))

    if command.name is not None and command.name != "":
        # contains, explicit case-insensitive comparison
        lowered_name = command.name.lower()
        conditions.append(func.lower(accounts.c.name).like(f"%{lowered_name}%"))

    query = select(accounts)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)

    return query

@router.post("/account/search")
async def search_accounts(command: AccountSearchCommand, conn: AsyncConnection = Depends(get_db)):
    result = await conn.execute(build_account_query(command))
    account_entities = [row_to_account(row) for row in result.all()]
    result_list = []
    for entity in account_entities:
        dto = map_account_entity_to_dto(entity) if entity is not None else None
        if isinstance(dto, Error):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"status": "broken data in account table!"})
        elif dto is not None: 
           result_list.append(dto)

    return result_list
