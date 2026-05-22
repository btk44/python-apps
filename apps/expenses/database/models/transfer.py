from sqlalchemy import Column, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship

from .base import Base


class Transfer(Base):
    __tablename__ = "Transfer"
    __table_args__ = (
        Index("IX_Transfer_AccountFromId", "AccountFromId"),
        Index("IX_Transfer_AccountToId", "AccountToId"),
    )

    id = Column("Id", Integer, primary_key=True)
    account_from_id = Column("AccountFromId", Integer, ForeignKey("Account.Id", ondelete="CASCADE"), nullable=False)
    account_to_id = Column("AccountToId", Integer, ForeignKey("Account.Id", ondelete="CASCADE"), nullable=False)

    account_from = relationship(
        "Account",
        back_populates="transfers_from",
        foreign_keys=[account_from_id],
    )
    account_to = relationship(
        "Account",
        back_populates="transfers_to",
        foreign_keys=[account_to_id],
    )
    transactions = relationship("Transaction", back_populates="transfer")
