from sqlalchemy.engine import Row
from sqlalchemy.sql.selectable import NamedFromClause
from apps.exp.domain.models.category import Category
from apps.exp.infrastructure.tables import categories

def row_to_category(row: Row, categories_alias: NamedFromClause = categories) -> Category | None:
    m = row._mapping
    if categories_alias.c.id not in m:
        return None
    else:
        return Category(
            user_id=m[categories_alias.c.user_id],
            parent_id=m[categories_alias.c.parent_id],
            code=m[categories_alias.c.code],
            name=m[categories_alias.c.name],
            type=m[categories_alias.c.type],
            icon=m[categories_alias.c.icon],

            id=m[categories_alias.c.id],
            version=m[categories_alias.c.version],
            is_active=m[categories_alias.c.is_active],
            created_at=m[categories_alias.c.created_at],
            updated_at=m[categories_alias.c.updated_at],
        )
