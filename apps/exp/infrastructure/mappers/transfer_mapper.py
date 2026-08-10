from sqlalchemy import Row
from sqlalchemy.sql.selectable import NamedFromClause

from apps.exp.domain.models.transfer import Transfer
from apps.exp.infrastructure.tables import transfers

def row_to_transfer(row: Row, transfers_alias: NamedFromClause = transfers) -> Transfer | None:
    m = row._mapping
    if transfers_alias.c.id not in m:
        return None
    else:
        return Transfer(
            from_tx_id=m[transfers_alias.c.from_tx_id],
            to_tx_id=m[transfers_alias.c.to_tx_id],
            id=m[transfers_alias.c.id],
            created_at=m[transfers_alias.c.created_at]
        )

def transfer_to_insert_values(transfer: Transfer) -> dict:
    return {
        "from_tx_id": transfer.from_tx_id,
        "to_tx_id": transfer.to_tx_id
    }
