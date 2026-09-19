"""RGB-driven PNG compilation, historical identity and editor round trips."""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.gfx_assets import (compile_assets, decode_pc1, planar_decode,
                              read_png, PNG_PALETTE, pillow)


class GraphicsTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='test-gfx-', dir=ROOT/'build')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'gfx', self.root/'gfx')
        self.layout = json.loads((self.root/'gfx/layout.json').read_text())
        self.Image = pillow()

    def edit(self, name, x, y, value=None):
        path = self.root/'gfx'/f'{name}.png'
        with self.Image.open(path) as original:
            image = original.convert('RGB')
        if value is None:
            value = (PNG_PALETTE.index(image.getpixel((x, y)))+1) % 16
        image.putpixel((x, y), PNG_PALETTE[value])
        image.save(path)
        return value

    def test_default_identity_when_sources_are_unmodified(self):
        reference = json.loads((ROOT/'tests/gfx-default-hashes.json').read_text())
        for name, digest in reference.items():
            if name != 'outputs' and hashlib.sha256((self.root/'gfx'/name).read_bytes()).hexdigest() != digest:
                self.skipTest('PNG sources have been customized; historical identity no longer applies')
        compile_assets(self.root)  # Must work without any pre-existing binary assets.
        for name, digest in reference['outputs'].items():
            self.assertEqual(hashlib.sha256((self.root/'assets'/name).read_bytes()).hexdigest(), digest, name)

    def test_edited_screens_roundtrip_including_broken_runs(self):
        for name in ('cockpit', 'textscr'):
            self.edit(name, 1, 0)
            self.edit(name, 159, 77)
            self.edit(name, 319, 199)
        compile_assets(self.root)
        for name in ('cockpit', 'textscr'):
            expected = read_png(self.root/'gfx'/f'{name}.png', (320,200))
            actual, _ = decode_pc1((self.root/'assets'/(name.upper()+'.PC1')).read_bytes())
            self.assertEqual(actual, expected)
            self.assertEqual(struct.unpack_from('>16H', (self.root/'assets'/(name.upper()+'.PC1')).read_bytes(), 2),
                             tuple(self.layout['screens'][name]['palette']))

    def test_every_bitmap_sheet_edit_reaches_binary(self):
        edited = []
        for name in self.layout['sheets']:
            entry = next(e for e in self.layout['bitmaps'] if e['sheet'] == name)
            x,y,w,h = entry['rect']
            edited.append((entry, self.edit(name,x,y)))
        compile_assets(self.root)
        data = (self.root/'assets/BITMAPS.IMG').read_bytes()
        for entry, value in edited:
            start = entry['offset']+4
            w,h = entry['rect'][2:]
            self.assertEqual(planar_decode(data[start:start+w*h//2],w,h)[0], value)

    def test_font_and_embedded_missiles_are_editable(self):
        path = self.root/'gfx/font.png'
        with self.Image.open(path) as image:
            value = 15-PNG_PALETTE.index(image.convert('RGB').getpixel((0,0)))
        self.edit('font',0,0,value)
        entry = self.layout['missiles'][0]
        x,y,_,_ = entry['rect']
        pixel = self.edit('gadgets',x,y)
        compile_assets(self.root)
        self.assertEqual((self.root/'assets/ELITECHR.IMG').read_bytes()[0] >> 7, value//15)
        data = (self.root/'assets'/entry['file']).read_bytes()
        self.assertEqual(struct.unpack_from('>H',data,4)[0],63)
        self.assertEqual(planar_decode(data[6:14],16,1)[0],pixel)

    def test_invalid_colour_does_not_update_any_output(self):
        compile_assets(self.root)
        before = {p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}
        self.edit('cockpit',1,1)
        path = self.root/'gfx/textscr.png'
        with self.Image.open(path) as source:
            image = source.convert('RGB')
        image.putpixel((0,0),(1,2,3)); image.save(path)
        with self.assertRaisesRegex(ValueError,r'colour #010203 at \(0, 0\).*outside the PNG palette'):
            compile_assets(self.root)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'assets').iterdir()})

    def test_dimensions_partial_alpha_and_invalid_font_colours_are_rejected(self):
        path = self.root/'gfx/font.png'
        original = path.read_bytes()
        self.Image.new('RGB',(8,8)).save(path)
        with self.assertRaisesRegex(ValueError,'128 x 48'):
            compile_assets(self.root)
        path.write_bytes(original)
        with self.Image.open(path) as source:
            image = source.convert('RGBA')
        image.putpixel((0,0),(0,0,0,128)); image.save(path)
        with self.assertRaisesRegex(ValueError,'partial transparency'):
            compile_assets(self.root)
        path.write_bytes(original)
        self.edit('font',0,0,14)
        with self.assertRaisesRegex(ValueError,'only palette indices'):
            compile_assets(self.root)

    def test_all_pngs_allow_rgb_and_rgba_exports_without_binary_changes(self):
        compile_assets(self.root)
        expected = {p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}
        for mode in ('RGB','RGBA'):
            for path in (self.root/'gfx').glob('*.png'):
                with self.Image.open(path) as source:
                    image = source.convert(mode)
                image.save(path)
            compile_assets(self.root)
            self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()},expected)

    def test_indexed_editor_can_reorder_colours_and_use_high_palette_indices(self):
        compile_assets(self.root)
        expected = {p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}
        # Put all 16 colours at unrelated PNG slots 200..215, in reverse order.
        slots = {colour:215-index for index,colour in enumerate(PNG_PALETTE)}
        palette = [1,2,3]*256  # Unused palette entries do not constrain the artwork.
        for colour,index in slots.items():
            palette[index*3:index*3+3] = colour
        for path in (self.root/'gfx').glob('*.png'):
            with self.Image.open(path) as source:
                rgb = source.convert('RGB')
                image = self.Image.new('P',source.size)
            colours = zip(*[iter(rgb.tobytes())]*3)
            image.putdata([slots[colour] for colour in colours])
            image.putpalette(palette)
            image.save(path)
        compile_assets(self.root)
        self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()},expected)

    def test_user_palette_maps_every_rgb_swatch_to_its_game_index(self):
        # Exact colours supplied by the user, independent of the PNG's storage mode.
        swatches = ('00FFFF 929292 494949 FF6D00 FF00FF FFFF00 DB0000 92FF00 '
                    '66AA00 496D00 92B6FF 496DDB 0024DB 000000 FF0000 FFFFFF')
        pixels = bytes.fromhex(swatches)
        path = self.root/'swatches.png'
        self.Image.frombytes('RGB',(16,1),pixels).save(path)
        self.assertEqual(read_png(path,(16,1)),list(range(16)))

    def test_full_alpha_transparency_maps_to_zero_regardless_of_hidden_rgb(self):
        path = self.root/'alpha.png'
        image = self.Image.new('RGBA',(4,1))
        image.putdata([(1,2,3,0),(0,255,255,255),(0,0,0,255),(255,0,0,255)])
        image.save(path)
        self.assertEqual(read_png(path,(4,1)),[0,0,13,14])
        # Palette transparency is interpreted through its displayed RGBA colour too.
        image = self.Image.new('P',(2,1))
        image.putdata([200,201])
        palette = [1,2,3]*256
        palette[603:606] = [0,0,0]
        image.putpalette(palette)
        image.save(path,transparency=200)
        self.assertEqual(read_png(path,(2,1)),[0,13])

    def test_missile_padding_must_remain_transparent(self):
        x,y,_,_ = self.layout['missiles'][0]['rect']
        self.edit('gadgets',x+10,y,13)
        with self.assertRaisesRegex(ValueError,'missile padding'):
            compile_assets(self.root)


if __name__ == '__main__':
    unittest.main()
