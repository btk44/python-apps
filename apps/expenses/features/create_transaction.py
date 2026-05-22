from datetime import datetime
from apps.expenses.database.models.category import Category
from apps.expenses.database.models.transaction import Transaction
from . import router
from sqlalchemy import select, and_
from ..database.models.account import Account
from ..database.session import SessionLocal
from pydantic import BaseModel
from fastapi import HTTPException, status

# DTOs and command models will have camel case properties to be more convenient for frontend
class TransactionDto(BaseModel):
    id: int
    ownerId: int
    amount: float
    categoryId: int
    accountId: int
    date: datetime
    comment: str | None = None
    active: bool

class TransactionProcessCommand(BaseModel):
    processingUserId: int = 1 
    transactions: list[TransactionDto]

def map_transaction_dto_to_entity(dto: TransactionDto, entity: Transaction):
    entity.owner_id = dto.ownerId
    entity.amount = dto.amount
    entity.category_id = dto.categoryId
    entity.account_id = dto.accountId
    entity.date = dto.date
    entity.comment = dto.comment
    entity.active = dto.active

def map_transaction_entity_to_dto(entity: Transaction) -> TransactionDto:
    return TransactionDto(
        id=entity.id,
        ownerId=entity.owner_id,
        amount=entity.amount,
        categoryId=entity.category_id,
        accountId=entity.account_id,
        date=entity.date,
        comment=entity.comment,
        active=entity.active
    )

@router.post("/transaction/process", status_code=status.HTTP_200_OK)
async def process_transactions(command: TransactionProcessCommand):
    command.processingUserId = 1  # this must be forced for now

    if command.transactions is None or len(command.transactions) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "no transactions to process"})
    
    if command.processingUserId is None or command.processingUserId != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "invalid processing user id"})
    
    invalid_transactions = [t for t in command.transactions if t.ownerId != command.processingUserId]
    if len(invalid_transactions) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "some transactions have invalid owner id", "invalid_transaction_ids": [t.id for t in invalid_transactions]})
    
    account_ids = set(t.accountId for t in command.transactions)
    category_ids = set(t.categoryId for t in command.transactions)
    transaction_ids = set(t.id for t in command.transactions if t.id > 0)

    async with SessionLocal() as session:
        accounts_query = select(Account).where(and_(Account.id.in_(account_ids), Account.owner_id == command.processingUserId))
        categories_query = select(Category).where(and_(Category.id.in_(category_ids), Category.owner_id == command.processingUserId))
        transactions_query = select(Transaction).where(and_(Transaction.id.in_(transaction_ids), Transaction.owner_id == command.processingUserId)) if len(transaction_ids) > 0 else None

        accounts = list(await session.scalars(accounts_query))
        categories = list(await session.scalars(categories_query))
        existing_transactions = list(await session.scalars(transactions_query)) if transactions_query is not None else []

        existing_transaction_ids = set(t.id for t in existing_transactions)
        missing_transaction_ids = transaction_ids - existing_transaction_ids
        if len(missing_transaction_ids) > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "some transactions do not exist", "missing_transaction_ids": list(missing_transaction_ids)})

        existing_account_ids = set(a.id for a in accounts)
        missing_account_ids = account_ids - existing_account_ids
        if len(missing_account_ids) > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "some transactions reference non-existing accounts", "missing_account_ids": list(missing_account_ids)})

        existing_category_ids = set(c.id for c in categories)
        missing_category_ids = category_ids - existing_category_ids
        if len(missing_category_ids) > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"status": "some transactions reference non-existing categories", "missing_category_ids": list(missing_category_ids)})

        processed_transactions = []

        for tx in command.transactions:
            if tx.id in existing_transaction_ids:
                current_tx = next(t for t in existing_transactions if t.id == tx.id)
            else:
                current_tx = Transaction()
                session.add(current_tx)

            map_transaction_dto_to_entity(tx, current_tx)

            processed_transactions.append(current_tx)

        if session.new or session.dirty:
            await session.commit()

    return {"status": "processed", "transactions": [map_transaction_entity_to_dto(tx) for tx in processed_transactions]}

