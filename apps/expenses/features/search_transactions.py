from datetime import datetime
from . import router
from sqlalchemy import select, and_, func
from ..database.models.transaction import Transaction
from ..database.session import SessionLocal
from pydantic import BaseModel

# DTOs and command models will have camel case properties to be more convenient for frontend
class TransactionSearchCommand(BaseModel):
    ownerId: int | None
    id: int | None = None
    amountFrom: float | None = None
    amountTo: float | None = None
    categories: list[int] | None = None  # list of ids
    accounts: list[int] | None = None  # list of ids
    dateFrom: datetime | None = None
    dateTo: datetime | None = None
    comment: str | None = None
    active: bool | None = None
    take: int | None = None
    offset: int | None = None


class TransactionDto(BaseModel):
    id: int
    ownerId: int
    amount: float
    accountId: int
    categoryId: int
    date: datetime
    comment: str
    active: bool


def map_transaction_entity_to_dto(entity: Transaction) -> TransactionDto:
    return TransactionDto(
        id=entity.id,
        ownerId=entity.owner_id,
        amount=entity.amount,
        accountId=entity.account_id,
        categoryId=entity.category_id,
        date=entity.date,
        comment=entity.comment,
        active=entity.active
    )


def build_transaction_query(command: TransactionSearchCommand):
    conditions = []

    if command.active is not None:
        conditions.append(Transaction.active == command.active)

    if command.ownerId is not None:
        conditions.append(Transaction.owner_id == command.ownerId)

    if command.id is not None:
        conditions.append(Transaction.id == command.id)

    if command.amountFrom is not None:
        conditions.append(Transaction.amount >= command.amountFrom)

    if command.amountTo is not None:
        conditions.append(Transaction.amount <= command.amountTo)

    if command.categories is not None and len(command.categories) > 0:
        conditions.append(Transaction.category_id.in_(command.categories))

    if command.accounts is not None and len(command.accounts) > 0:
        conditions.append(Transaction.account_id.in_(command.accounts))

    if command.dateFrom is not None:
        conditions.append(Transaction.date >= command.dateFrom)

    if command.dateTo is not None:
        conditions.append(Transaction.date <= command.dateTo)

    if command.comment is not None and command.comment != "":
        lowered_comment = command.comment.lower()
        conditions.append(func.lower(Transaction.comment).like(f"%{lowered_comment}%"))

    query = select(Transaction)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)

    return query


@router.post("/transaction/search")
async def search_transactions(command: TransactionSearchCommand):
    async with SessionLocal() as session:
        query = build_transaction_query(command)
        result = await session.scalars(query)
        return [map_transaction_entity_to_dto(entity) for entity in result.all()]

