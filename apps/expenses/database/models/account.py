from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, validates

from .base import Base


class Account(Base):
    __tablename__ = "Account"
    __table_args__ = (
        UniqueConstraint("UniqueCode", name="UQ_Account_UniqueCode"),
        Index("IX_Account_CurrencyId", "CurrencyId"),
        CheckConstraint("UniqueCode = lower(UniqueCode)", name="CHK_Account_UniqueCode_lowercase"),
    )

    id = Column("Id", Integer, primary_key=True)
    owner_id = Column("OwnerId", Integer, nullable=False)
    unique_code = Column("UniqueCode", String(10), nullable=False)
    name = Column("Name", Text, nullable=False)
    currency_id = Column("CurrencyId", Integer, ForeignKey("Currency.Id", ondelete="CASCADE"), nullable=False)
    active = Column("Active", Boolean, nullable=False, default=True)

    currency = relationship("Currency", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    transfers_from = relationship(
        "Transfer",
        back_populates="account_from",
        foreign_keys="Transfer.account_from_id",
    )
    transfers_to = relationship(
        "Transfer",
        back_populates="account_to",
        foreign_keys="Transfer.account_to_id",
    )

    @validates("unique_code")
    def _lower_unique_code(self, key, value):
        if value is None:
            return value
        return value.lower()
