from fastapi import Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import and_, func, or_, select
from collections.abc import AsyncIterator

from pydantic import BaseModel
from datetime import datetime

from apps.expenses.domain.common.enums import TransactionDirection
from apps.expenses.domain.models.transaction import Transaction
from apps.expenses.features.common.helpers import Error
from apps.expenses.infrastructure.mappers.transaction_mapper import row_to_transaction
from apps.expenses.infrastructure.session import get_connection
from apps.expenses.infrastructure.tables import transactions, transfers
from apps.expenses.domain.models.currency import MAX_CURRENCY_DECIMALS

from apps.expenses.features.a_router import router

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
    comment: str | None = None
    active: bool
    transferId: int | None = None
    version: int


class TransactionSearchResult(BaseModel):
    transactions: list[TransactionDto | None]
    totalCount: int


async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn


def map_transaction_entity_to_dto(entity: Transaction, transfer_id: int | None = None) -> TransactionDto | Error:
    if entity.id is None:
        return Error("entity id is not assigned!")

    return TransactionDto(
        id=entity.id,
        userId=entity.user_id,
        accountId=entity.account_id,
        categoryId=entity.category_id,
        amount=float(entity.money.amount),
        date=entity.transacted_at,
        comment=entity.comment,
        active=entity.is_active,
        version=entity.version,
        direction=entity.direction,
        transferId=transfer_id,
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
        conditions.append(transactions.c.transacted_at >= command.dateFrom)

    if command.dateTo is not None:
        conditions.append(transactions.c.transacted_at <= command.dateTo)

    if command.comment is not None and command.comment != "":
        lowered_comment = command.comment.lower()
        conditions.append(func.lower(transactions.c.comment).like(f"%{lowered_comment}%"))

    return conditions


def build_transaction_query(command: TransactionSearchCommand):
    conditions = build_transaction_conditions(command)
    transfer_alias = transfers.alias("transfer_lookup")
    query = (
        select(transactions, transfer_alias.c.id.label("transfer_id"))
        .select_from(
            transactions.outerjoin(
                transfer_alias,
                or_(transfer_alias.c.from_tx_id == transactions.c.id, transfer_alias.c.to_tx_id == transactions.c.id),
            )
        )
    )
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
    transaction_entities = [(row_to_transaction(row, currency_decimals=MAX_CURRENCY_DECIMALS), row._mapping.get("transfer_id")) for row in result.all()]

    dto_list = []
    for entity_data in transaction_entities:
        dto = map_transaction_entity_to_dto(entity_data[0], entity_data[1]) if entity_data[0] is not None else None
        if isinstance(dto, Error):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"status": "broken data in transactions related table!"})
        elif dto is not None: 
           dto_list.append(dto)

    return TransactionSearchResult(
        transactions=dto_list,
        totalCount=total_count_result.scalar_one()
    )
