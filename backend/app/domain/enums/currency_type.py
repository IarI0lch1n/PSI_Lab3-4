"""Currency type enumeration distinguishing fiat and cryptocurrency."""

from enum import Enum


class CurrencyType(str, Enum):
    """Classification of currencies supported by CurrencyHub."""

    FIAT = "fiat"
    CRYPTO = "crypto"
