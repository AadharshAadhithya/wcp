"""Dependency-free ULID generation and validation."""

from __future__ import annotations

import re
import secrets
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def _encode_base32(value: int, length: int) -> str:
    characters = ["0"] * length
    for index in range(length - 1, -1, -1):
        characters[index] = _ALPHABET[value & 31]
        value >>= 5
    return "".join(characters)


def new_ulid(timestamp_ms: int | None = None) -> str:
    """Create a canonical 26-character ULID.

    The timestamp occupies the first 48 bits and cryptographic randomness the
    remaining 80 bits. Monotonic ordering within a millisecond is deliberately
    not promised; uniqueness is the identity requirement here.
    """

    timestamp = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    if not 0 <= timestamp < 2**48:
        raise ValueError("ULID timestamp must fit in 48 bits")
    return _encode_base32(timestamp, 10) + _encode_base32(secrets.randbits(80), 16)


def is_ulid(value: str) -> bool:
    """Return whether *value* is a canonical Crockford Base32 ULID."""

    return bool(_ULID_PATTERN.fullmatch(value)) and value[0] <= "7"
