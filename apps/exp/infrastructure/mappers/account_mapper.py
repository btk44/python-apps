from sqlalchemy.engine import Row

from apps.exp.domain.models.account import Account
from apps.exp.infrastructure.mappers.currency_mapper import row_to_currency
from apps.exp.infrastructure.tables import accounts

def row_to_account(row: Row, accounts_alias=accounts) -> Account | None:
    m = row._mapping
    if accounts_alias.c.id not in m:
        return None
    else:
        return Account(
            user_id=m[accounts_alias.c.user_id],
            currency_id=m[accounts_alias.c.currency_id],
            code=m[accounts_alias.c.code],
            name=m[accounts_alias.c.name],
            type=m[accounts_alias.c.type],
            icon=m[accounts_alias.c.icon],

            id=m[accounts_alias.c.id],
            version=m[accounts_alias.c.version],
            is_active=m[accounts_alias.c.is_active],
            created_at=m[accounts_alias.c.created_at],
            updated_at=m[accounts_alias.c.updated_at],

            currency=row_to_currency(row)
        )