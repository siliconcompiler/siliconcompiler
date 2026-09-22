'''
Identifiers for the v1 store.

Every id in this schema is a UUIDv7: 48 bits of millisecond timestamp followed
by randomness, so ids sort by when they were minted. That is not decoration --
``GET /v1/jobs`` is ordered by creation and its ``?cursor=`` is a keyset over
that ordering, so a time-sortable primary key is the tiebreaker the cursor
already needs.
'''

import secrets
import time
import uuid

__all__ = ["uuid7"]


def _uuid7_fallback() -> uuid.UUID:
    '''RFC 9562 section 5.7, for interpreters without :func:`uuid.uuid7`.

    Layout, most significant bit first: 48 bits of Unix time in milliseconds,
    4 bits of version, 12 bits of randomness, 2 bits of variant, 62 more bits
    of randomness.
    '''
    unix_ts_ms = time.time_ns() // 1_000_000

    octets = bytearray(unix_ts_ms.to_bytes(6, "big") + secrets.token_bytes(10))
    octets[6] = (octets[6] & 0x0F) | 0x70   # version 7
    octets[8] = (octets[8] & 0x3F) | 0x80   # variant 0b10

    return uuid.UUID(bytes=bytes(octets))


# Added to the standard library in 3.14; SiliconCompiler supports 3.10 up.
uuid7 = getattr(uuid, "uuid7", _uuid7_fallback)
