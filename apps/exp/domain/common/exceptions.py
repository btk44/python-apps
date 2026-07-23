class DomainError(Exception):
    pass


class InvalidEmailError(DomainError):
    pass


class InvalidMoneyError(DomainError):
    pass


class InvalidUserError(DomainError):
    pass


class InvalidCurrencyError(DomainError):
    pass


class InvalidCategoryError(DomainError):
    pass


class InvalidAccountError(DomainError):
    pass


class InvalidTransactionError(DomainError):
    pass


class InvalidTransferError(DomainError):
    pass
