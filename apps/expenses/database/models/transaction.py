from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Index, Text
from sqlalchemy.orm import relationship

from .base import Base


class Transaction(Base):
    __tablename__ = "Transaction"
    __table_args__ = (
        Index("IX_Transaction_AccountId", "AccountId"),
        Index("IX_Transaction_CategoryId", "CategoryId"),
        Index("IX_Transaction_TransferId", "TransferId"),
    )

    id = Column("Id", Integer, primary_key=True)
    owner_id = Column("OwnerId", Integer, nullable=False)
    date = Column("Date", DateTime(timezone=True), nullable=False)
    account_id = Column("AccountId", Integer, ForeignKey("Account.Id", ondelete="CASCADE"), nullable=False)
    amount = Column("Amount", Float, nullable=False)
    category_id = Column("CategoryId", Integer, ForeignKey("Category.Id", ondelete="CASCADE"), nullable=False)
    transfer_id = Column("TransferId", Integer, ForeignKey("Transfer.Id", ondelete="SET NULL"), nullable=True)
    comment = Column("Comment", Text, nullable=True)
    active = Column("Active", Boolean, nullable=False, default=True)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    transfer = relationship("Transfer", back_populates="transactions")
