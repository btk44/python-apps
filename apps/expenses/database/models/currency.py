from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.orm import relationship

from .base import Base


class Currency(Base):
    __tablename__ = "Currency"

    id = Column("Id", Integer, primary_key=True)
    description = Column("Description", Text, nullable=False)
    code = Column("Code", Text, nullable=False)
    active = Column("Active", Boolean, nullable=False, default=True)

    accounts = relationship("Account", back_populates="currency", cascade="all, delete-orphan")
