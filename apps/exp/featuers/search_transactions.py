from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import and_, func, select
from collections.abc import AsyncIterator

from pydantic import BaseModel
from datetime import datetime

from apps.exp.domain.common.enums import TransactionDirection
from apps.exp.domain.models.transaction import Transaction
from apps.exp.infrastructure.mappers.transaction_mapper import row_to_transaction
from apps.exp.infrastructure.session import get_connection
from apps.exp.infrastructure.tables import transactions

from apps.exp.featuers.a_router import router

# DTOs and command models will have camel case properties to be more convenient for frontend
class TransactionSearchCommand(BaseModel):
    userId: int | None
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
    userId: int
    amount: float
    direction: TransactionDirection
    accountId: int
    categoryId: int
    date: datetime
    comment: str
    active: bool


class TransactionSearchResult(BaseModel):
    transactions: list[TransactionDto]
    totalCount: int


async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn


def map_transaction_entity_to_dto(entity: Transaction) -> TransactionDto:
    return TransactionDto(
        id=entity.id,
        userId=entity.user_id,
        accountId=entity.account_id,
        categoryId=entity.category_id,
        amount=entity.amount,
        date=entity.transacted_at,
        comment=entity.comment,
        active=entity.is_active,
        version=entity.version,
        direction=entity.direction
    )

def build_transaction_conditions(command: TransactionSearchCommand):
    conditions = []

    if command.active is not None:
        conditions.append(transactions.c.active == command.active)

    if command.userId is not None:
        conditions.append(transactions.c.user_id == command.userId)

    if command.id is not None:
        conditions.append(transactions.c.id == command.id)

    if command.amountFrom is not None:
        conditions.append(transactions.c.amount >= command.amountFrom)

    if command.amountTo is not None:
        conditions.append(transactions.c.amount <= command.amountTo)

    if command.categories is not None and len(command.categories) > 0:
        conditions.append(transactions.c.category_id.in_(command.categories))

    if command.accounts is not None and len(command.accounts) > 0:
        conditions.append(transactions.c.account_id.in_(command.accounts))

    if command.dateFrom is not None:
        conditions.append(transactions.c.date >= command.dateFrom)

    if command.dateTo is not None:
        conditions.append(transactions.c.date <= command.dateTo)

    if command.comment is not None and command.comment != "":
        lowered_comment = command.comment.lower()
        conditions.append(func.lower(transactions.c.comment).like(f"%{lowered_comment}%"))

    return conditions


def build_transaction_query(command: TransactionSearchCommand):
    conditions = build_transaction_conditions(command)
    query = select(transactions)
    if conditions:
        query = query.where(and_(*conditions))

    if command.offset is not None:
        query = query.offset(command.offset)
    if command.take is not None:
        query = query.limit(command.take)

    return query


def build_transaction_count_query(command: TransactionSearchCommand):
    conditions = build_transaction_conditions(command)
    query = select(func.count()).select_from(transactions)
    if conditions:
        query = query.where(and_(*conditions))

    return query


@router.post("/transaction/search")
async def search_transactions(command: TransactionSearchCommand, conn: AsyncConnection = Depends(get_db)):
    result = await conn.execute(build_transaction_query(command))
    total_count_result = await conn.execute(build_transaction_count_query(command))

    return TransactionSearchResult(
        transactions=[map_transaction_entity_to_dto(row_to_transaction(row, currency_decimals=4)) for row in result.all()],
        totalCount=total_count_result.scalar_one()
    )
