from dataclasses import replace

from fastapi import Depends
from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import Row, and_, insert, select, update
from collections.abc import AsyncIterator

from pydantic import BaseModel
from datetime import datetime

from apps.exp.domain.common.enums import CategoryType, TransactionDirection
from apps.exp.domain.models.account import Account
from apps.exp.domain.models.transaction import Transaction
from apps.exp.domain.value_objects.money import Money
from apps.exp.infrastructure.mappers.account_mapper import row_to_account
from apps.exp.infrastructure.mappers.category_mapper import row_to_category
from apps.exp.infrastructure.mappers.currency_mapper import row_to_currency
from apps.exp.infrastructure.mappers.transaction_mapper import row_to_transaction, transaction_to_insert_values, transaction_to_update_values
from apps.exp.infrastructure.session import get_connection
from apps.exp.infrastructure.tables import transactions, categories, accounts, currencies
from apps.exp.featuers.a_router import router

# DTOs and command models will have camel case properties to be more convenient for frontend
class TransactionDto(BaseModel):
    id: int
    userId: int
    amount: float
    direction: TransactionDirection
    categoryId: int
    accountId: int
    date: datetime
    comment: str | None = None
    active: bool
    transferId: int | None = None
    
class TransactionProcessCommand(BaseModel):
    processingUserId: int = 1
    transaction: TransactionDto


async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn


def map_transaction_entity_to_dto(entity: Transaction, transfer_id: int | None = None) -> TransactionDto:
    return TransactionDto(
        id=entity.id,
        userId=entity.user_id,
        accountId=entity.account_id,
        categoryId=entity.category_id,
        direction=entity.direction,
        amount=entity.amount,
        date=entity.transacted_at,
        comment=entity.comment,
        active=entity.is_active,
        version=entity.version
    )

async def get_account_with_currency(conn: AsyncConnection, user_id: int, account_id: int) -> Account | None:
    query = (
        select(accounts, currencies)
        .select_from(accounts.join(currencies, currencies.c.id == accounts.c.currency_id))
        .where(and_(accounts.c.id == account_id, accounts.c.user_id == user_id))
    )

    account_row = (await conn.execute(query)).one_or_none()
    account = row_to_account(account_row)
    account.currency = row_to_currency(account_row)

    return account

async def update_existing_transaction(conn: AsyncConnection, tx: Transaction, \
                                      account_id: int, amount: float, currency_decimals: int, \
                                      category_id: int, direction: TransactionDirection, comment: str | None) -> Transaction:
    tx.update_account(account_id)
    tx.recategorize(category_id, direction)
    tx.update_amount(amount, currency_decimals)
    tx.update_comment(comment)
    values = transaction_to_update_values(tx)
    stmt = update(transactions).where(transactions.c.id == tx.id).values(**values).returning(
        transactions.c.id,
        transactions.c.version,
        transactions.c.created_at,
        transactions.c.updated_at,
    )
    result = await conn.execute(stmt)
    row = result.one()
    return replace(
        tx,
        id=row.id,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at
    )

async def create_new_transaction(conn: AsyncConnection, user_id: int, date: datetime, \
                                 account_id: int, amount: float, currency_decimals: int, \
                                 category_id: int, direction: TransactionDirection, comment: str | None) -> Transaction:            
    tx = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        money=Money(amount=amount, decimals=currency_decimals),
        direction=direction,
        comment=comment,
        transacted_at=date
        # all other fields are defaulted (is_active=True, version=1, etc.)
    )
    values = transaction_to_insert_values(tx)
    stmt = insert(transactions).values(**values).returning(
        transactions.c.id,
        transactions.c.version,
        transactions.c.created_at,
        transactions.c.updated_at
    )

    result = await conn.execute(stmt)
    row = result.one()
    return replace(
        tx,
        id=row.id,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at
    )


# for transfer transactions there are always both transactions required!

@router.post("/transaction/process-single", status_code=status.HTTP_200_OK)
async def process_transactions(command: TransactionProcessCommand, conn: AsyncConnection = Depends(get_db)):
    command.processingUserId = 1  # this must be forced for now

    # simple validation of the command:
    if command.transaction is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "no transactions to process"})

    if command.processingUserId is None or command.processingUserId != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "invalid processing user id"})

    if command.processingUserId != command.transaction.userId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transaction has invalid user id"})

    # validate that all referenced account, categorie, and transaction exist and belong to the processing user:
    category_query = select(categories).where(and_(categories.c.id == command.transaction.categoryId, categories.c.user_id == command.processingUserId))
    category_result = await conn.execute(category_query)

    if category_result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transactions reference non-existing category"})

    transaction_query = select(transactions).where(and_(transactions.c.id == command.transaction.id, transactions.c.user_id == command.processingUserId))
    transaction_result = await conn.execute(transaction_query)
    
    if command.transaction.id > 0 and transaction_result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transactions does not exist"})

    account = await get_account_with_currency(conn, command.processingUserId, command.transaction.accountId)

    if account is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transaction reference non-existing account"})

    category = row_to_category(category_result.one())

    if category.type == CategoryType.BOTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transaction category must be expense or income"})

    # start processing the transaction:
    try:
        tx_direction = TransactionDirection.CREDIT if category.type == CategoryType.INCOME else TransactionDirection.DEBIT

        if transaction_result.rowcount == 1:
            transaction = row_to_transaction(transaction_result.one())
            transaction_dto = command.transaction
            processed_transaction = await update_existing_transaction(conn, transaction, \
                                                                      transaction_dto.accountId, transaction_dto.amount, account.currency.decimals, \
                                                                      category.id, tx_direction, transaction_dto.comment)
        else:
            transaction_dto = command.transaction
            processed_transaction = await create_new_transaction(conn, command.processingUserId, transaction_dto.date, \
                                                                 transaction_dto.accountId, transaction_dto.amount, account.currency.decimals, \
                                                                 category.id, tx_direction, transaction_dto.comment)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, \
                            detail={"status": "error processing transaction", "error": str(e)})
        
    await conn.commit()

    return map_transaction_entity_to_dto(processed_transaction)


