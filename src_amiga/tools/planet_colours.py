"""Derive flight colours from the actual Planet Data texture and palettes."""
from collections import Counter
import colorsys
from functools import lru_cache
import re
import struct
from pathlib import Path

if __package__:
    from .gfx_assets import decode_pc1
else:
    from gfx_assets import decode_pc1


EXCLUDED = {0, 13}  # transparent and black; UI index 14 is brown, not pulsing
LIGHT_GREY = 1


def advance(seed):
    return seed[1], seed[2], sum(seed) & 65535


def description_tokens(source):
    """Read numeric control bytes from the real description grammar."""
    result = {}
    for name, body in re.findall(r'^(tok\d+[a-e]|base_string):\s*dc\.b\s+(.+)$', source, re.M):
        # Quoted text has no RNG effects, including doubled apostrophes.
        body = re.sub(r"'(?:[^']|'')*'", '', body)
        result[name] = [int(n) for n in re.findall(r'\b\d+\b', body)]
    if len(result) != 196:
        raise ValueError('Unexpected planet description grammar')
    return result


def texture_centre(seed, tokens):
    """Reproduce name_tokens, description RNG side effects, then getrandx."""
    state = seed
    for _ in range(4):
        state = advance(state)
    a, b = seed[0] ^ seed[1], seed[0] ^ seed[1] ^ seed[2]

    def expand(name, depth=0):
        nonlocal a, b, state
        if depth > 64:
            raise ValueError('Recursive planet description')
        for value in tokens[name]:
            if value >= 128:
                a, b = b, (a+b) & 65535
                expand(f'tok{value}{"abcde"[(b & 255)//52]}', depth+1)
            elif value == 3:  # RNDNAME replaces all three galaxy RNG words.
                state = (a, b, a ^ b)
                for _ in range(4):
                    state = advance(state)

    expand('base_string')
    state = advance(state)
    return 40 + state[0]*240//65536, 40 + state[1]*120//65536


def circle_spans():
    """Exact inclusive scanlines of pdata.m68's radius-40 midpoint circle."""
    spans = {}
    x, y, decision = 0, 40, -77
    while x <= y:
        for row, extent in ((y, x), (x, y), (-x, y), (-y, x)):
            spans[row] = max(spans.get(row, 0), extent)
        if decision < 0:
            decision += 4*x+6
        else:
            decision += 4*(x-y)+10
            y -= 1
        x += 1
    return sorted(spans.items())


def rgb(word):
    return tuple(((word >> shift) & 7)*2 + (((word >> shift) & 7) >> 2)
                 for shift in (8, 4, 0))


def inhabitant_rgb(word):
    # pdata imports the ST table with the same conversion as the UI palette.
    return rgb(word)


def family(colour):
    hue, saturation, _ = colorsys.rgb_to_hsv(*colour)
    if saturation < 0.2:
        return -1
    degrees = hue*360
    return next((i for i, limit in enumerate((15, 45, 75, 165, 195, 255, 285, 345))
                 if degrees < limit), 0)


def dominant_colour(counts, palette, cockpit):
    """Combine shades, take the most common shade, then map to flight RGB."""
    eligible = {i: count for i, count in enumerate(counts)
                if count and i not in EXCLUDED and any(palette[i])}
    if not eligible:
        return LIGHT_GREY
    groups = Counter()
    for i, count in eligible.items():
        groups[family(palette[i])] += count
    group = max(groups, key=groups.get)
    winner = max((i for i in eligible if family(palette[i]) == group),
                 key=eligible.get)
    # UI brown occupies the cockpit's pulse slot; use steady red in flight.
    if winner == 14:
        return 6
    candidates = [i for i in range(1, 16) if i != 14]
    target = min(candidates, key=lambda i: sum((a-b)**2 for a, b in zip(palette[winner], cockpit[i])))
    # Reserve yellow for the sun so planets remain visually distinct.
    if target == 5:
        return 6
    # Black and dark grey must stay visible against the flight background.
    return LIGHT_GREY if target in (2, 13) or not any(cockpit[target]) else target


def build_table(root):
    pixels, _ = decode_pc1((root/'assets/TEXTURE.PC1').read_bytes())
    tokens = description_tokens((root/'asm/funny.m68').read_text())
    words = lambda name: struct.unpack_from('>16H', (root/'assets'/name).read_bytes(), 2)
    ui, cockpit = list(map(rgb, words('TEXTSCR.PC1'))), list(map(rgb, words('COCKPIT.PC1')))
    source = (root/'asm/pdata.m68').read_text().split('inhab_palette:', 1)[1]
    inhabitants = [tuple(int(v, 16) for v in row) for row in
                   re.findall(r'dc\s+\$([0-9a-f]+),\$([0-9a-f]+),\$([0-9a-f]+)', source, re.I)]
    if len(inhabitants) != 8:
        raise ValueError('Unexpected inhabitant palette table')
    spans = circle_spans()

    @lru_cache(None)
    def histogram(centre):
        cx, cy = centre
        counts = [0]*16
        for row, extent in spans:
            start = (cy+row)*320+cx-extent
            for index in pixels[start:start+2*extent+1]:
                counts[index] += 1
        return counts

    table = bytearray()
    records = []
    galaxy = (0x5a4a, 0x0248, 0xb753)
    for g in range(8):
        seed = galaxy
        for number in range(256):
            palette = ui[:]
            if seed[2] & 128:
                palette[7:10] = map(inhabitant_rgb, inhabitants[(seed[2] >> 13) & 7])
            centre = texture_centre(seed, tokens)
            table.append(dominant_colour(histogram(centre), palette, cockpit))
            records.append((g, number, seed, centre))
            for _ in range(4):
                seed = advance(seed)
        raw = struct.pack('>3H', *galaxy)
        galaxy = struct.unpack('>3H', bytes(((v << 1) | (v >> 7)) & 255 for v in raw))
    return bytes(table), records


def write_table(root):
    """Explicit maintenance command; normal builds only embed the saved table."""
    table, _ = build_table(root)
    output = root/'assets/PLANET_COL.BIN'
    output.write_bytes(table)
    return output


if __name__ == '__main__':
    output = write_table(Path(__file__).resolve().parents[1])
    print(f'Wrote {output.stat().st_size} precomputed planet colours to {output}')
