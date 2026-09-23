"""Compile editable, fixed-palette PNG sources into the game's original formats."""
from pathlib import Path
import json
import struct


# Use the screen's original ST RGB colours, with cyan distinguishing index 0
# from opaque black 13. The cockpit also needs a visible marker for pulse 14.
# PC1 hardware palettes remain unchanged in layout.json.
UI_PNG_PALETTE = tuple(tuple(bytes.fromhex(colour)) for colour in (
    '00FFFF', '929292', '494949', 'FF6D00', 'FF00FF', 'FFFF00', 'FF0000', '92FF00',
    '6DB600', '496D00', '92B6FF', '496DDB', '0024DB', '000000', '6D4900', 'FFFFFF'))
COCKPIT_PNG_PALETTE = tuple(
    (219, 0, 0) if index == 6 else (255, 0, 0) if index == 14 else colour
    for index, colour in enumerate(UI_PNG_PALETTE))


def png_palette(path):
    """Select the cockpit palette by filename; all other PNGs use the UI base."""
    return COCKPIT_PNG_PALETTE if Path(path).stem == 'cockpit' else UI_PNG_PALETTE


def pillow():
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError('PNG graphics require Pillow. Install it with your build Python: '
                           'python -m pip install Pillow') from exc
    return Image


def palette_rgb(words):
    return [tuple(round(((word >> shift) & 7) * 255 / 7)
                  for shift in (8, 4, 0)) for word in words]


def read_png(path, size, allowed=None):
    """Map exact RGB to game indices using this PNG's cockpit or UI palette."""
    Image = pillow()
    with Image.open(path) as image:
        if image.format != 'PNG' or image.size != tuple(size):
            raise ValueError(f'{path}: expected a {size[0]} x {size[1]} PNG')
        rgba = image.convert('RGBA')
        lookup = {colour: index for index, colour in enumerate(png_palette(path))}
        pixels = []
        for position, colour in enumerate(zip(*[iter(rgba.tobytes())]*4)):
            rgb, alpha = colour[:3], colour[3]
            x, y = position % size[0], position // size[0]
            if alpha == 0:
                pixels.append(0)  # Fully transparent pixels mean the same as cyan.
            elif alpha != 255:
                raise ValueError(f'{path}: partial transparency at ({x}, {y}); '
                                 'use opaque palette colours or fully transparent pixels')
            elif rgb not in lookup:
                colour_hex = '#' + bytes(rgb).hex().upper()
                raise ValueError(f'{path}: colour {colour_hex} at ({x}, {y}) is outside the PNG palette; '
                                 'use exact RGB swatches without antialiasing or colour conversion')
            else:
                pixels.append(lookup[rgb])
        if allowed is not None and not set(pixels) <= set(allowed):
            raise ValueError(f'{path}: only palette indices {allowed} are allowed')
        return pixels


def planar_decode(data, width, height):
    pixels = []
    for offset in range(0, len(data), 8):
        words = struct.unpack_from('>4H', data, offset)
        pixels.extend(sum(((word >> bit) & 1) << plane for plane, word in enumerate(words))
                      for bit in range(15, -1, -1))
    if len(pixels) != width * height:
        raise ValueError('Invalid planar bitmap length')
    return pixels


def planar_encode(pixels, width, height):
    if width % 16 or len(pixels) != width * height:
        raise ValueError('Invalid planar bitmap dimensions')
    data = bytearray()
    for offset in range(0, len(pixels), 16):
        group = pixels[offset:offset+16]
        data.extend(struct.pack('>4H', *(sum(((value >> plane) & 1) << (15-x)
                                           for x, value in enumerate(group)) for plane in range(4))))
    return bytes(data)


def decode_pc1(data):
    """Return indices and packet layout; Elite requires packets within 40-byte rows."""
    if data[:2] != b'\x80\x00':
        raise ValueError('Expected compressed low-resolution DEGAS PC1')
    position, rows, controls = 34, [], []
    for _ in range(800):
        row, commands = bytearray(), bytearray()
        while len(row) < 40:
            control = data[position]
            position += 1
            commands.append(control)
            count = control + 1 if control < 128 else 257-control
            if control < 128:
                row.extend(data[position:position+count])
                position += count
            else:
                row.extend(data[position:position+1] * count)
                position += 1
        if len(row) != 40:
            raise ValueError('PC1 packet crosses a plane scanline')
        rows.append(row)
        controls.append(commands.hex())
    planar = bytearray()
    for y in range(200):
        for word in range(20):
            for plane in range(4):
                planar.extend(rows[y*4+plane][word*2:word*2+2])
    metadata = {'palette': list(struct.unpack_from('>16H', data, 2)),
                'packets': controls, 'trailer': data[position:].hex()}
    return planar_decode(planar, 320, 200), metadata


def pack_row(row):
    """Optimal bounded PackBits encoding, without the unsupported $80 command."""
    costs, choices = [0] * (len(row)+1), [None] * len(row)
    for start in range(len(row)-1, -1, -1):
        candidates = [(1+n+costs[start+n], n, False) for n in range(1, len(row)-start+1)]
        run = 1
        while start+run < len(row) and row[start+run] == row[start]:
            run += 1
        candidates += [(2+costs[start+n], n, True) for n in range(2, run+1)]
        costs[start], count, repeated = min(candidates)
        choices[start] = count, repeated
    result, start = bytearray(), 0
    while start < len(row):
        count, repeated = choices[start]
        result.append(257-count if repeated else count-1)
        result.extend(row[start:start+1] if repeated else row[start:start+count])
        start += count
    return bytes(result)


def encode_pc1(pixels, metadata):
    planar = planar_encode(pixels, 320, 200)
    result = bytearray(b'\x80\x00' + struct.pack('>16H', *metadata['palette']))
    for y in range(200):
        for plane in range(4):
            row = b''.join(planar[y*160+word*8+plane*2:y*160+word*8+plane*2+2]
                           for word in range(20))
            packed, position, valid = bytearray(), 0, True
            for control in bytes.fromhex(metadata['packets'][y*4+plane]):
                count = control+1 if control < 128 else 257-control
                part = row[position:position+count]
                if len(part) != count or (control >= 128 and len(set(part)) != 1):
                    valid = False
                    break
                packed.append(control)
                packed.extend(part if control < 128 else part[:1])
                position += count
            # Retain historical packet boundaries when they represent the new pixels.
            # An edited run is recompressed, never replaced with historical artwork.
            result.extend(packed if valid and position == 40 else pack_row(row))
    result.extend(bytes.fromhex(metadata['trailer']))
    return bytes(result)


def crop(pixels, size, rect):
    x, y, width, height = rect
    if x < 0 or y < 0 or x+width > size[0] or y+height > size[1]:
        raise ValueError('Bitmap rectangle is outside its PNG sheet')
    return [value for line in range(y, y+height)
            for value in pixels[line*size[0]+x:line*size[0]+x+width]]


def ship_atlases(gfx, zoom_x=1, zoom_y=1):
    """Compile the three ship views into a separate, masked sprite bank.

    The original BITMAPS.IMG IDs and offsets stay stable. Each table entry is
    relative to this bank and addresses the normal PUT_BITMAP record format.
    Red editing frames are outside the metadata's game-image rectangles.
    """
    metadata = json.loads((gfx / 'ship-atlases.json').read_text(encoding='utf-8'))
    names = ('ships.png', 'shipsplanetinfo.png', 'shipyards.png')
    sizes = ((128, 51), (32, 45), (64, 41))
    order = metadata['order']
    if len(order) != 13 or len(set(order)) != 13:
        raise ValueError('Ship atlases must describe exactly 13 distinct ships')
    sprites = []
    for name, dimensions in zip(names, sizes):
        atlas = metadata['atlases'][name]
        if tuple(atlas['interior_size']) != dimensions:
            raise ValueError(f'{name}: invalid game-image dimensions')
        entries = atlas['ships']
        if [entry['name'] for entry in entries] != order:
            raise ValueError(f'{name}: ship order does not match the atlas metadata')
        pixels = read_png(gfx / name, atlas['size'], set(range(16)) - {14})
        for entry in entries:
            rect = entry['rect']
            if tuple(rect[2:]) != dimensions:
                raise ValueError(f'{name}: invalid rectangle for {entry["name"]}')
            source = crop(pixels, atlas['size'], rect)
            w, h = dimensions
            width, height = w * zoom_x, h * zoom_y
            grown = [source[(y // zoom_y) * w + x // zoom_x]
                     for y in range(height) for x in range(width)]
            planar = planar_encode(grown, width, height)
            record = bytearray(struct.pack('>HH', width // 16, height))
            for offset in range(0, len(planar), 8):
                planes = struct.unpack_from('>4H', planar, offset)
                record.extend(struct.pack('>H', ~(planes[0] | planes[1] | planes[2] | planes[3]) & 65535))
                record.extend(planar[offset:offset + 8])
            sprites.append(record)
    bank = bytearray(4 * len(sprites))
    for index, sprite in enumerate(sprites):
        struct.pack_into('>I', bank, index * 4, len(bank))
        bank.extend(sprite)
    return bytes(bank)


def compile_assets(root, altgfx=False):
    """Validate every PNG before replacing any generated asset. No baseline hash gate."""
    root = Path(root)
    gfx, assets = root / ('gfx_alt' if altgfx else 'gfx'), root / 'assets'
    layout = json.loads((gfx / 'layout.json').read_text(encoding='utf-8'))
    outputs = {}
    for name, metadata in layout['screens'].items():
        pixels = read_png(gfx / f'{name}.png', (320, 200))
        outputs[name.upper()+'.PC1'] = encode_pc1(pixels, metadata)
    sheets = {name: read_png(gfx / f'{name}.png', size)
              for name, size in layout['sheets'].items()}
    entries = layout['bitmaps']
    data = bytearray(layout['bitmap_bytes'])
    struct.pack_into('>'+str(len(entries))+'I', data, 0, *(entry['offset'] for entry in entries))
    for entry in entries:
        sheet, rect, offset = entry['sheet'], entry['rect'], entry['offset']
        width, height = rect[2:]
        pixels = crop(sheets[sheet], layout['sheets'][sheet], rect)
        encoded = struct.pack('>HH', width//16, height) + planar_encode(pixels, width, height)
        data[offset:offset+len(encoded)] = encoded
    outputs['BITMAPS.IMG'] = bytes(data)
    outputs['SHIPSPRITES.IMG'] = ship_atlases(gfx)
    font = read_png(gfx / 'font.png', (128, 48), [0, 15])
    outputs['ELITECHR.IMG'] = bytes(sum((font[(glyph//16*8+y)*128+glyph%16*8+x] == 15)
                                      << (7-x) for x in range(8))
                                    for glyph in range(96) for y in range(8))
    for entry in layout['missiles']:
        pixels = crop(sheets['gadgets'], layout['sheets']['gadgets'], entry['rect'])
        # The 10-pixel missile cell is opaque, including black; six padding pixels
        # are transparent. The original mask is therefore not the bitmap OR mask.
        if any(pixels[y*16+x] != 0 for y in range(6) for x in range(10, 16)):
            raise ValueError('gadgets.png: missile padding (last six columns) must remain '
                             'index 0 (#00FFFF or fully transparent)')
        planar = planar_encode(pixels, 16, 6)
        outputs[entry['file']] = struct.pack('>HH', 1, 6) + b''.join(
            b'\x00\x3f' + planar[y*8:y*8+8] for y in range(6))
    assets.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        target = assets / name
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
    return {name: len(data) for name, data in outputs.items()}


if __name__ == '__main__':
    try:
        report = compile_assets(Path(__file__).resolve().parents[1])
        print('Generated PNG graphics: ' + ', '.join(f'{name} ({size} bytes)' for name, size in report.items()))
    except (ValueError, RuntimeError, OSError) as error:
        raise SystemExit(str(error))
