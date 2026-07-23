"""SQLAlchemy Core table definitions.

These mirror the DDL 1:1 and are the *only* place that knows the physical
schema. Nothing outside `app/infrastructure` should import from here —
the application/domain layers only ever see domain entities
(`app.domain.models`), never `Table`/`Row` objects.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(256), nullable=False, unique=True),
    Column("display_name", String(128), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)

currencies = Table(
    "currencies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(3), nullable=False, unique=True),
    Column("name", String(64), nullable=False),
    Column("symbol", String(8), nullable=False),
    Column("decimals", Integer, nullable=False, server_default=text("2")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)

categories = Table(
    "categories",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("parent_id", Integer, ForeignKey("categories.id", ondelete="SET NULL")),
    Column("code", String(8), nullable=False),
    Column("name", String(64), nullable=False),
    Column("icon", String(32)),
    Column("type", String(8), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("user_id", "code"),
    CheckConstraint("type IN ('expense', 'income', 'both')"),
)

accounts = Table(
    "accounts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("currency_id", Integer, ForeignKey("currencies.id"), nullable=False),
    Column("code", String(8), nullable=False),
    Column("name", String(64), nullable=False),
    Column("type", String(16), nullable=False),
    Column("icon", String(32)),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("user_id", "code"),
    CheckConstraint("type IN ('cash', 'bank', 'credit', 'savings')"),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("account_id", Integer, ForeignKey("accounts.id"), nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="SET NULL")),
    Column("amount", Numeric(18, 4), nullable=False),
    Column("direction", String(6), nullable=False),
    Column("comment", String(1000)),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("transacted_at", TIMESTAMP(timezone=True), nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("amount > 0"),
    CheckConstraint("direction IN ('debit', 'credit')"),
)

transfers = Table(
    "transfers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("from_tx_id", Integer, ForeignKey("transactions.id"), nullable=False, unique=True),
    Column("to_tx_id", Integer, ForeignKey("transactions.id"), nullable=False, unique=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)