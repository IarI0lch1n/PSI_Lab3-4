"""Primary freshness state enumeration for exchange rate entries.

Note: In accordance with the canonical policy, 'stale' is a separate
boolean freshness condition (is_stale) and is NOT a primary FreshnessState.
"""

from enum import Enum


class FreshnessState(str, Enum):
    """Primary status of an exchange rate entry."""

    LIVE = "live"
    FALLBACK = "fallback"
    CACHED = "cached"
