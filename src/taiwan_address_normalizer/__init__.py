"""Taiwan address normalization without geocoding or external services."""

from .normalizer import (
    AddressResult,
    NormalizationMode,
    address_house_number,
    address_key,
    area_tokens,
    normalize,
    normalize_many,
    normalize_with_report,
)

__all__ = [
    "AddressResult",
    "NormalizationMode",
    "address_house_number",
    "address_key",
    "area_tokens",
    "normalize",
    "normalize_many",
    "normalize_with_report",
]

__version__ = "0.1.0"
