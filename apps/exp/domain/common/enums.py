from enum import StrEnum


class CategoryType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    BOTH = "both"


class AccountType(StrEnum):
    CASH = "cash"
    BANK = "bank"
    CREDIT = "credit"
    SAVINGS = "savings"


class TransactionDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"
