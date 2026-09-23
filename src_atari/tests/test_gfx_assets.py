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
                              read_png, png_palette, pillow, ship_atlases)


class GraphicsTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='test-gfx-', dir=ROOT/'build')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'gfx', self.root/'gfx')
        self.layout = json.loads((self.root/'gfx/layout.json').read_text())
        self.Image = pillow()

    def edit(self, name, x, y, value=None, gfx='gfx'):
        path = self.root/gfx/f'{name}.png'
        with self.Image.open(path) as original:
            image = original.convert('RGB')
        palette = png_palette(path)
        if value is None:
            value = (palette.index(image.getpixel((x, y)))+1) % 16
        image.putpixel((x, y), palette[value])
        image.save(path)
        return value

    def test_altgfx_switches_all_outputs_and_no_restores_default_sources(self):
        compile_assets(self.root)  # Default works without a gfx_alt directory.
        expected = {p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}
        shutil.copytree(self.root/'gfx', self.root/'gfx_alt')
        for name in ('cockpit', 'textscr'):
            self.edit(name, 0, 0, gfx='gfx_alt')
        entry = self.layout['bitmaps'][0]
        self.edit(entry['sheet'], *entry['rect'][:2], gfx='gfx_alt')
        font = read_png(self.root/'gfx_alt/font.png', (128,48))
        self.edit('font', 0, 0, 15-font[0], gfx='gfx_alt')
        for entry in self.layout['missiles']:
            self.edit('gadgets', *entry['rect'][:2], gfx='gfx_alt')
        self.edit('ships', 10, 10, gfx='gfx_alt')
        # The selected set must supply its own metadata, too.
        layout_path = self.root/'gfx/layout.json'
        layout_bytes = layout_path.read_bytes()
        layout_path.write_text('{}')
        try:
            compile_assets(self.root, altgfx=True)
        finally:
            layout_path.write_bytes(layout_bytes)
        for name, data in expected.items():
            self.assertNotEqual((self.root/'assets'/name).read_bytes(), data, name)
        compile_assets(self.root, altgfx=False)
        self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}, expected)
        compile_assets(self.root, altgfx=True)
        compile_assets(self.root)
        self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}, expected)

    def test_incomplete_altgfx_never_falls_back_or_updates_outputs(self):
        compile_assets(self.root)
        expected = {p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}
        with self.assertRaisesRegex(FileNotFoundError, 'gfx_alt'):
            compile_assets(self.root, altgfx=True)
        shutil.copytree(self.root/'gfx', self.root/'gfx_alt')
        self.edit('cockpit', 0, 0, gfx='gfx_alt')
        (self.root/'gfx_alt/font.png').unlink()
        with self.assertRaisesRegex(FileNotFoundError, 'font.png'):
            compile_assets(self.root, altgfx=True)
        self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}, expected)

    def test_default_identity_when_sources_are_unmodified(self):
        reference = json.loads((ROOT/'tests/gfx-default-hashes.json').read_text())
        for name, digest in reference.items():
            if name != 'outputs' and hashlib.sha256((self.root/'gfx'/name).read_bytes()).hexdigest() != digest:
                self.skipTest('PNG sources have been customized; historical identity no longer applies')
        compile_assets(self.root)  # Must work without any pre-existing binary assets.
        for name, digest in reference['outputs'].items():
            self.assertEqual(hashlib.sha256((self.root/'assets'/name).read_bytes()).hexdigest(), digest, name)

    def test_ship_views_export_exact_rectangles_without_editing_frames(self):
        metadata = json.loads((self.root/'gfx/ship-atlases.json').read_text())
        for zx, zy in ((1, 1), (2, 1), (2, 2)):
            bank = ship_atlases(self.root/'gfx', zx, zy)
            index = 0
            for name in ('ships.png', 'shipsplanetinfo.png', 'shipyards.png'):
                atlas = metadata['atlases'][name]
                source = read_png(self.root/'gfx'/name, atlas['size'])
                for ship in atlas['ships']:
                    offset = struct.unpack_from('>I', bank, index*4)[0]
                    words, height = struct.unpack_from('>HH', bank, offset)
                    x, y, w, h = ship['rect']
                    self.assertEqual((words*16, height), (w*zx, h*zy))
                    planar = bytearray()
                    for block in range(words*height):
                        mask, *planes = struct.unpack_from('>5H', bank, offset+4+block*10)
                        self.assertEqual(mask, ~(planes[0]|planes[1]|planes[2]|planes[3]) & 65535)
                        planar.extend(struct.pack('>4H', *planes))
                    expected = [source[(y+py//zy)*atlas['size'][0]+x+px//zx]
                                for py in range(h*zy) for px in range(w*zx)]
                    self.assertEqual(planar_decode(planar, w*zx, h*zy), expected)
                    index += 1
            self.assertEqual(index, 39)

    def test_ship_frame_is_not_exported_and_missing_alt_atlas_fails_atomically(self):
        original = ship_atlases(self.root/'gfx')
        self.edit('ships', 0, 0, 15)
        self.assertEqual(ship_atlases(self.root/'gfx'), original)
        compile_assets(self.root)
        expected = {p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}
        shutil.copytree(self.root/'gfx', self.root/'gfx_alt')
        (self.root/'gfx_alt/shipyards.png').unlink()
        with self.assertRaisesRegex(FileNotFoundError, 'shipyards.png'):
            compile_assets(self.root, altgfx=True)
        self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()}, expected)

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
            value = 15-png_palette(path).index(image.convert('RGB').getpixel((0,0)))
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
        for path in (self.root/'gfx').glob('*.png'):
            slots = {colour:215-index for index,colour in enumerate(png_palette(path))}
            palette = [1,2,3]*256  # Unused entries do not constrain the artwork.
            for colour,index in slots.items():
                palette[index*3:index*3+3] = colour
            with self.Image.open(path) as source:
                rgb = source.convert('RGB')
                image = self.Image.new('P',source.size)
            colours = zip(*[iter(rgb.tobytes())]*3)
            image.putdata([slots[colour] for colour in colours])
            image.putpalette(palette)
            image.save(path)
        compile_assets(self.root)
        self.assertEqual({p.name:p.read_bytes() for p in (self.root/'assets').iterdir()},expected)

    def test_each_screen_palette_maps_every_rgb_swatch_to_its_game_index(self):
        swatches = {
            'cockpit': ('00FFFF 929292 494949 FF6D00 FF00FF FFFF00 DB0000 92FF00 '
                        '6DB600 496D00 92B6FF 496DDB 0024DB 000000 FF0000 FFFFFF'),
            'ui': ('00FFFF 929292 494949 FF6D00 FF00FF FFFF00 FF0000 92FF00 '
                   '6DB600 496D00 92B6FF 496DDB 0024DB 000000 6D4900 FFFFFF'),
        }
        for name in ('cockpit', 'textscr', 'cargo', 'equipment', 'gadgets',
                     'panels', 'characters', 'font'):
            with self.subTest(name=name):
                path = self.root/f'{name}.png'
                colours = swatches['cockpit' if name == 'cockpit' else 'ui']
                self.Image.frombytes('RGB',(16,1),bytes.fromhex(colours)).save(path)
                self.assertEqual(read_png(path,(16,1)),list(range(16)))

    def test_same_red_rgb_selects_the_correct_index_for_each_screen(self):
        for name,red in (('cockpit',14),('textscr',6),('gadgets',6)):
            path = self.root/f'{name}.png'
            self.Image.new('RGB',(1,1),(255,0,0)).save(path)
            self.assertEqual(read_png(path,(1,1)),[red])
        for name,colour in (('cockpit',(109,73,0)),('textscr',(219,0,0)),
                            ('cockpit',(102,170,0)),('textscr',(102,170,0))):
            path = self.root/f'{name}.png'
            self.Image.new('RGB',(1,1),colour).save(path)
            with self.assertRaisesRegex(ValueError,'outside the PNG palette'):
                read_png(path,(1,1))

    def test_compiled_screens_and_sheets_keep_red_and_brown_indices_distinct(self):
        self.edit('cockpit',0,0,6)
        self.edit('cockpit',1,0,14)
        self.edit('textscr',0,0,6)
        self.edit('textscr',1,0,14)
        for sheet in ('cargo','equipment','gadgets','panels','characters'):
            entry = next(e for e in self.layout['bitmaps'] if e['sheet'] == sheet)
            x,y,_,_ = entry['rect']
            self.edit(sheet,x,y,6)
            self.edit(sheet,x+1,y,14)
        compile_assets(self.root)
        for name in ('COCKPIT.PC1','TEXTSCR.PC1'):
            pixels,_ = decode_pc1((self.root/'assets'/name).read_bytes())
            self.assertEqual(pixels[:2],[6,14])
        data = (self.root/'assets/BITMAPS.IMG').read_bytes()
        for sheet in ('cargo','equipment','gadgets','panels','characters'):
            entry = next(e for e in self.layout['bitmaps'] if e['sheet'] == sheet)
            start = entry['offset']+4
            w,h = entry['rect'][2:]
            self.assertEqual(planar_decode(data[start:start+w*h//2],w,h)[:2],[6,14])

    def test_full_alpha_transparency_maps_to_zero_regardless_of_hidden_rgb(self):
        path = self.root/'alpha.png'
        image = self.Image.new('RGBA',(4,1))
        image.putdata([(1,2,3,0),(0,255,255,255),(0,0,0,255),(255,0,0,255)])
        image.save(path)
        self.assertEqual(read_png(path,(4,1)),[0,0,13,6])
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
