"""Rebuild the classic four-colour, dual-image ELITE Workbench tool icon.

The hand-pixelled winged badge uses only standard screen pens. Pen 0 is
background, 1 lettering, 2 outline, and 3 wings; selection swaps 1 and 3.
Horizontal doubling suits the tall pixels of non-interlaced Workbench.
The checked-in assets/ELITE.info is the build input; this is an authoring tool.
"""
from pathlib import Path
import struct

WIDTH, HEIGHT = 96, 24


def badge():
    width = WIDTH // 2
    shape = set()

    def polygon(vertices):
        # Integer scan conversion of the small, explicitly authored silhouette.
        for y in range(HEIGHT):
            for x in range(width):
                inside = False
                for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1]):
                    if (ay > y + .5) != (by > y + .5):
                        if x + .5 < ax + (y + .5 - ay) * (bx - ax) / (by - ay):
                            inside = not inside
                if inside:
                    shape.add((x, y))

    wing = [(1, 2), (7, 2), (10, 4), (19, 4), (23, 7), (23, 9),
            (13, 9), (13, 13), (7, 13), (3, 10), (3, 8),
            (8, 10), (10, 10), (10, 8), (4, 7), (1, 4)]
    polygon(wing)
    polygon([(width - x, y) for x, y in wing])
    polygon([(5, 15), (10, 17), (19, 17), (19, 15), (29, 15),
             (29, 17), (38, 17), (43, 15), (41, 19), (30, 20),
             (27, 23), (21, 23), (18, 20), (7, 19)])
    pixels = [[0] * width for _ in range(HEIGHT)]
    for x, y in shape:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if 0 <= x + dx < width and 0 <= y + dy < HEIGHT:
                    pixels[y + dy][x + dx] = 2
    for x, y in shape:
        pixels[y][x] = 3
    for y in range(8, 17):
        for x in range(10, 38):
            pixels[y][x] = 2
    glyphs = {
        'E': ('11111', '10000', '10000', '11110', '10000', '10000', '11111'),
        'L': ('1000', '1000', '1000', '1000', '1000', '1000', '1111'),
        'I': ('111', '010', '010', '010', '010', '010', '111'),
        'T': ('11111', '00100', '00100', '00100', '00100', '00100', '00100'),
    }
    x = 11
    for letter in 'ELITE':
        glyph = glyphs[letter]
        for y, row in enumerate(glyph, 9):
            for dx, bit in enumerate(row):
                if bit == '1':
                    pixels[y][x + dx] = 1
        x += len(glyph[0]) + 1
    return [bytes(p for p in row for _ in range(2)) for row in pixels]


def image_record(pixels):
    data = bytearray()
    for plane in range(2):
        for row in pixels:
            for x in range(0, WIDTH, 8):
                data.append(sum(((row[x + bit] >> plane) & 1) << (7 - bit)
                                for bit in range(8)))
    return struct.pack('>hhhhhIBBI', 0, 0, WIDTH, HEIGHT, 2, 1, 3, 0, 0) + data


def make_icon():
    disk_object = bytearray(78)
    struct.pack_into('>HH', disk_object, 0, 0xe310, 1)
    # Image gadget, alternate selection image, RELVERIFY | GADGIMMEDIATE.
    struct.pack_into('>HHHHH', disk_object, 12, WIDTH, HEIGHT + 1, 6, 3, 1)
    struct.pack_into('>II', disk_object, 22, 1, 1)
    disk_object[48] = 3  # WBTOOL: execute the adjacent ELITE file.
    struct.pack_into('>II', disk_object, 58, 0x80000000, 0x80000000)
    struct.pack_into('>I', disk_object, 74, 8192)
    normal = badge()
    selected = [bytes({0: 0, 1: 3, 2: 2, 3: 1}[p] for p in row) for row in normal]
    return bytes(disk_object) + image_record(normal) + image_record(selected)


if __name__ == '__main__':
    target = Path(__file__).resolve().parents[1] / 'assets/ELITE.info'
    target.write_bytes(make_icon())
    print(f'{target}: {WIDTH} x {HEIGHT}, two 2-bit images, {target.stat().st_size} bytes')
