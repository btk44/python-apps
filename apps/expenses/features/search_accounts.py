from . import router
from sqlalchemy import select, and_, func
from ..database.models.account import Account
from ..database.session import SessionLocal
from pydantic import BaseModel

# DTOs and command models will have camel case properties to be more convenient for frontend
class AccountSearchCommand(BaseModel):
    ownerId: int | None
    currencies: list[int] | None = None
    codes: list[str] | None = None
    ids: list[int] | None = None
    name: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None

class AccountDto(BaseModel):
    id: int
    ownerId: int
    currencyId: int
    uniqueCode: str
    name: str
    active: bool

def map_account_entity_to_dto(entity: Account) -> AccountDto:
    return AccountDto(
        id=entity.id,
        ownerId=entity.owner_id,
        currencyId=entity.currency_id,
        uniqueCode=entity.unique_code,
        name=entity.name,
        active=entity.active
    )

def build_account_query(command: AccountSearchCommand):
    conditions = []

    if command.active is not None:
        conditions.append(Account.active == command.active)

    if command.ownerId is not None:
        conditions.append(Account.owner_id == command.ownerId)

    if command.ids is not None and len(command.ids) > 0:
        conditions.append(Account.id.in_(command.ids))

    if command.currencies is not None and len(command.currencies) > 0:
        conditions.append(Account.currency_id.in_(command.currencies))

    if command.codes is not None and len(command.codes) > 0:
        # exact, case-insensitive match for each code
        lowered_codes = [c.lower() for c in command.codes]
        conditions.append(func.lower(Account.unique_code).in_(lowered_codes))

    if command.name is not None and command.name != "":
        # contains, explicit case-insensitive comparison
        lowered_name = command.name.lower()
        conditions.append(func.lower(Account.name).like(f"%{lowered_name}%"))

    query = select(Account)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)

    return query


@router.post("/account/search")
async def search_accounts(command: AccountSearchCommand):
    async with SessionLocal() as session:
        query = build_account_query(command)
        result = await session.scalars(query)
        return [map_account_entity_to_dto(entity) for entity in result.all()]

