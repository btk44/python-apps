from sqlalchemy.engine import Row

from apps.exp.domain.models.currency import Currency
from apps.exp.infrastructure.tables import currencies

def row_to_currency(row: Row, currencies_alias=currencies) -> Currency | None:
    m = row._mapping
    if currencies_alias.c.id not in m:
        return None
    else:
        return Currency(
            id=m[currencies_alias.c.id],
            code=m[currencies_alias.c.code],
            name=m[currencies_alias.c.name],
            symbol=m[currencies_alias.c.symbol],
            decimals=m[currencies_alias.c.decimals],
            is_active=m[currencies_alias.c.is_active],
            created_at=m[currencies_alias.c.created_at],
            updated_at=m[currencies_alias.c.updated_at]
        )   