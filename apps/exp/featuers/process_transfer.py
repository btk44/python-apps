from dataclasses import replace

from fastapi import Depends
from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import and_, insert, select, update
from collections.abc import AsyncIterator

from pydantic import BaseModel
from datetime import datetime

from apps.exp.domain.common.enums import CategoryType, TransactionDirection
from apps.exp.domain.models.account import Account
from apps.exp.domain.models.currency import MAX_CURRENCY_DECIMALS
from apps.exp.domain.models.transaction import Transaction
from apps.exp.domain.models.transfer import Transfer
from apps.exp.domain.value_objects.money import Money
from apps.exp.infrastructure.mappers.account_mapper import row_to_account
from apps.exp.infrastructure.mappers.category_mapper import row_to_category
from apps.exp.infrastructure.mappers.currency_mapper import row_to_currency
from apps.exp.infrastructure.mappers.transfer_mapper import row_to_transfer, transfer_to_insert_values
from apps.exp.infrastructure.mappers.transaction_mapper import row_to_transaction, transaction_to_insert_values, transaction_to_update_values
from apps.exp.infrastructure.session import get_connection
from apps.exp.infrastructure.tables import transactions, categories, accounts, currencies, transfers
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

class TransferProcessCommand(BaseModel):
    processingUserId: int = 1
    transferId: int | None = None
    categoryId: int
    date: datetime
    comment: str | None = None
    active: bool
    fromAccountId: int
    fromAmount: float
    toAccountId: int
    toAmount: float

async def get_db() -> AsyncIterator[AsyncConnection]:
    async with get_connection() as conn:
        yield conn


def map_transaction_entity_to_dto(entity: Transaction, transfer_id: int) -> TransactionDto:
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
        version=entity.version,
        transferId=transfer_id
    )

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


async def get_transfer_transactions(conn: AsyncConnection, user_id: int, transfer_id: int) -> set[Transaction] | None:
    from_transaction_alias = transactions.alias("from_tx")
    to_transaction_alias = transactions.alias("to_tx")

    query = (
        select(transfers, from_transaction_alias, to_transaction_alias)
        .select_from(
            transfers
            .join(from_transaction_alias, transfers.c.from_tx_id == from_transaction_alias.c.id)
            .join(to_transaction_alias, transfers.c.to_tx_id == to_transaction_alias.c.id)
        )
        .where(and_(transfers.c.id == transfer_id, from_transaction_alias.c.user_id == user_id, to_transaction_alias.c.user_id == user_id))
    )

    transfer_row = (await conn.execute(query)).one_or_none()

    if transfer_row is None:
        return None

    transfer = row_to_transfer(transfer_row)
    from_transaction = row_to_transaction(transfer_row, from_transaction_alias, currency_decimals=MAX_CURRENCY_DECIMALS) # to do
    to_transaction = row_to_transaction(transfer_row, to_transaction_alias, currency_decimals=MAX_CURRENCY_DECIMALS)

    return {from_transaction, to_transaction}

async def get_accounts_with_currencies(conn: AsyncConnection, user_id: int, from_account_id: int, to_account_id: int) -> set[Account] | None:
    account_ids = {from_account_id, to_account_id}
    query = (
        select(accounts, currencies)
        .select_from(accounts.join(currencies, currencies.c.id == accounts.c.currency_id))
        .where(and_(accounts.c.id.in_(account_ids), accounts.c.user_id == user_id))
    )

    result = await conn.execute(query)

    if result.rowcount != 2:
        return None

    result_rows = result.all()
    from_account_row = next(r for r in result_rows if r.id == from_account_id)
    to_account_row = next(r for r in result_rows if r.id == to_account_id)

    from_account = row_to_account(from_account_row)
    from_account.currency = row_to_currency(from_account_row)
    to_account = row_to_account(to_account_row)
    to_account.currency = row_to_currency(to_account_row)

    return {from_account, to_account}


# for transfer transactions there are always both transactions required!

@router.post("/transaction/process-transfer", status_code=status.HTTP_200_OK)
async def process_transactions(command: TransferProcessCommand, conn: AsyncConnection = Depends(get_db)):
    command.processingUserId = 1  # this must be forced for now

    # simple validation of the command:
    if command.processingUserId is None or command.processingUserId != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "invalid processing user id"})

    if command.fromAccountId == command.toAccountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transfer accounts must differ"})
    
    # validate that all referenced account, category, and transaction exist and belong to the processing user:
    categories_query = select(categories).where(and_(categories.c.id == command.categoryId, categories.c.user_id == command.processingUserId))
    category_result = await conn.execute(categories_query)

    if category_result.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transactions reference non-existing category"})

    category = row_to_category(category_result.one())

    if category.type != CategoryType.BOTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transfer category must be BOTH type"})

    transfer_accounts = await get_accounts_with_currencies(conn, command.processingUserId, command.fromAccountId, command.toAccountId)

    if transfer_accounts is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transaction reference non-existing account"})

    from_account, to_account = transfer_accounts

    if from_account.currency_id == to_account.currency_id and command.fromAmount != command.toAmount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "when currency is the same the amount must be the same as well"})

    transfer_id = command.transferId

    try:
        if command.transferId is not None and command.transferId > 0:
            transfer_transactions = await get_transfer_transactions(conn, command.processingUserId, command.transferId)

            if transfer_transactions is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "transfer does not exist or is broken"})

            from_transaction, to_transaction = transfer_transactions
            
            new_from_transaction = await update_existing_transaction(conn, from_transaction, \
                                                                    command.fromAccountId, command.fromAmount, from_account.currency.decimals, \
                                                                    command.categoryId, TransactionDirection.DEBIT, command.comment)
            
            new_to_transaction = await update_existing_transaction(conn, to_transaction, \
                                                                command.toAccountId, command.toAmount, to_account.currency.decimals, \
                                                                command.categoryId, TransactionDirection.CREDIT, command.comment)
        else:
            new_from_transaction = await create_new_transaction(conn, command.processingUserId, command.date, \
                                                                command.fromAccountId, command.fromAmount, from_account.currency.decimals, \
                                                                command.categoryId, TransactionDirection.DEBIT, command.comment)

            new_to_transaction = await create_new_transaction(conn, command.processingUserId, command.date, \
                                                            command.toAccountId, command.toAmount, to_account.currency.decimals, \
                                                            command.categoryId, TransactionDirection.CREDIT, command.comment)

            new_transfer = Transfer(from_tx_id=new_from_transaction.id, to_tx_id=new_to_transaction.id)
            stmt = insert(transfers).values(**transfer_to_insert_values(new_transfer)).returning(transfers.c.id)
            transfer_id = (await conn.execute(stmt)).one().id


    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, \
                            detail={"status": "error processing transactions", "error": str(e)})
    
    await conn.commit()

    return [
        map_transaction_entity_to_dto(new_from_transaction, transfer_id),
        map_transaction_entity_to_dto(new_to_transaction, transfer_id)
    ]


