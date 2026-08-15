from sqlalchemy.engine import Row
from sqlalchemy.sql.selectable import NamedFromClause

from apps.expenses.domain.common.enums import TransactionDirection
from apps.expenses.domain.models.transaction import Transaction
from apps.expenses.domain.value_objects.money import Money
from apps.expenses.infrastructure.tables import transactions


def row_to_transaction(row: Row, transactions_alias: NamedFromClause = transactions, *, currency_decimals: int) -> Transaction | None:
    m = row._mapping
    if transactions_alias.c.id not in m:
        return None
    else:
        return Transaction(
            id=m[transactions_alias.c.id],
            user_id=m[transactions_alias.c.user_id],
            account_id=m[transactions_alias.c.account_id],
            category_id=m[transactions_alias.c.category_id],
            money=Money(m[transactions_alias.c.amount], decimals=currency_decimals),
            direction=TransactionDirection(m[transactions_alias.c.direction]),
            comment=m[transactions_alias.c.comment],
            is_active=m[transactions_alias.c.is_active],
            version=m[transactions_alias.c.version],
            transacted_at=m[transactions_alias.c.transacted_at],
            created_at=m[transactions_alias.c.created_at],
            updated_at=m[transactions_alias.c.updated_at]
        )

def transaction_to_insert_values(transaction: Transaction) -> dict:
    return {
        "user_id": transaction.user_id,
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "amount": transaction.money.amount,
        "direction": transaction.direction.value,
        "comment": transaction.comment,
        "is_active": transaction.is_active,
        "transacted_at": transaction.transacted_at,
    }

def transaction_to_update_values(transaction: Transaction) -> dict:
    return {
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "amount": transaction.money.amount,
        "direction": transaction.direction.value,
        "comment": transaction.comment,
        "is_active": transaction.is_active,
        "transacted_at": transaction.transacted_at
    }
