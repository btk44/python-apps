from decimal import Decimal

class Error(str): pass # only to make return type explicit

def float_to_decimal(number: float) -> Decimal:
    return Decimal(str(number)) # this is to avoid precision issues
