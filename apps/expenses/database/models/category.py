from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, validates

from .base import Base


class Category(Base):
    __tablename__ = "Category"
    __table_args__ = (
        UniqueConstraint("UniqueCode", name="UQ_Category_UniqueCode"),
        Index("IX_Category_ParentId", "ParentId"),
        CheckConstraint("UniqueCode = lower(UniqueCode)", name="CHK_Category_UniqueCode_lowercase"),
    )

    id = Column("Id", Integer, primary_key=True)
    owner_id = Column("OwnerId", Integer, nullable=False)
    unique_code = Column("UniqueCode", String(10), nullable=False)
    name = Column("Name", Text, nullable=False)
    parent_id = Column("ParentId", Integer, ForeignKey("Category.Id", ondelete="RESTRICT"), nullable=True)
    active = Column("Active", Boolean, nullable=False, default=True)

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    transactions = relationship("Transaction", back_populates="category", cascade="all, delete-orphan")

    @validates("unique_code")
    def _lower_unique_code(self, key, value):
        if value is None:
            return value
        return value.lower()
