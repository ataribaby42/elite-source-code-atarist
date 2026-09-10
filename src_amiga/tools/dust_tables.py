"""Extend the original dust lookup tables to include abs(x) == 128."""
from math import isqrt
import struct

ROWS, ORIGINAL_COLUMNS, COLUMNS, MAGNITUDE = 57, 128, 129, 30000


def expand_dust_tables(cosine: bytes, sine: bytes) -> tuple[bytes, bytes]:
    """Preserve original cells and append the exact truncated edge vector."""
    expected = ROWS * ORIGINAL_COLUMNS * 2
    if len(cosine) != expected or len(sine) != expected:
        raise ValueError('Expected two original 57 x 128 dust tables')
    expanded_cos, expanded_sin = bytearray(), bytearray()
    for y in range(ROWS):
        start, end = y * ORIGINAL_COLUMNS * 2, (y + 1) * ORIGINAL_COLUMNS * 2
        expanded_cos.extend(cosine[start:end])
        expanded_sin.extend(sine[start:end])
        radius_squared = ORIGINAL_COLUMNS ** 2 + y ** 2
        # floor(a / sqrt(b)) == isqrt(a*a // b), without floating-point rounding.
        expanded_cos.extend(struct.pack('>H', isqrt((MAGNITUDE * ORIGINAL_COLUMNS) ** 2 // radius_squared)))
        expanded_sin.extend(struct.pack('>H', isqrt((MAGNITUDE * y) ** 2 // radius_squared)))
    return bytes(expanded_cos), bytes(expanded_sin)
