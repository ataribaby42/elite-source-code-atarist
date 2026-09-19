"""Planet texture selection, shade voting, and visibility regressions."""
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.planet_colours import (build_table, description_tokens, dominant_colour,
                                  family, rgb, texture_centre)


class PlanetColourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table, cls.records = build_table(ROOT)
        cls.palette = list(map(rgb, struct.unpack_from('>16H',
            (ROOT/'assets/COCKPIT.PC1').read_bytes(), 2)))
        cls.ui_palette = list(map(rgb, struct.unpack_from('>16H',
            (ROOT/'assets/TEXTSCR.PC1').read_bytes(), 2)))

    def vote(self, values, palette=None):
        counts = [0]*16
        for index, count in values.items():
            counts[index] = count
        return dominant_colour(counts, palette or self.palette, self.palette)

    def test_one_visible_byte_per_planet_in_all_galaxies(self):
        self.assertEqual(len(self.table), 2048)
        self.assertEqual((ROOT/'assets/PLANET_COL.BIN').read_bytes(), self.table)
        self.assertTrue(set(self.table) <= {1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 15})
        for index, (galaxy, planet, _, (x, y)) in enumerate(self.records):
            self.assertEqual(index, galaxy*256+planet)
            self.assertTrue(40 <= x < 280 and 40 <= y < 160)

    def test_lave_crop_and_colour(self):
        self.assertEqual(self.records[7][2], (0xad38, 0x149c, 0x151d))
        self.assertEqual(self.records[7][3], (261, 132))
        self.assertEqual(self.table[7], 9)

    def test_transparency_and_black_cannot_win(self):
        self.assertEqual(self.vote({0: 5000, 13: 4000, 6: 1}), 6)
        self.assertEqual(self.vote({0: 5000, 13: 4000}), 1)

    def test_ui_brown_votes_and_maps_to_steady_red(self):
        self.assertEqual(self.vote({14: 100}, self.ui_palette), 6)
        self.assertEqual(self.vote({14: 100, 10: 99}, self.ui_palette), 6)
        self.assertEqual(self.vote({14: 99, 10: 100}, self.ui_palette), 10)

    def test_yellow_maps_to_orange(self):
        self.assertEqual(self.vote({5: 100}, self.ui_palette), 3)
        # A different source index can also map to cockpit yellow.
        palette = self.ui_palette[:]
        palette[7] = self.palette[5]
        self.assertEqual(self.vote({7: 100}, palette), 3)

    def test_dark_grey_and_black_mapping_fall_back_to_light_grey(self):
        self.assertEqual(self.vote({2: 100}), 1)
        palette = self.palette[:]
        palette[6] = (0.01, 0, 0)  # A very dark inhabitant shade maps to black.
        self.assertEqual(self.vote({6: 100}, palette), 1)

    def test_shades_vote_together(self):
        self.assertEqual(family(self.palette[7]), family(self.palette[9]))
        self.assertEqual(family(self.palette[10]), family(self.palette[12]))
        self.assertEqual(self.vote({6: 50, 7: 20, 8: 25, 9: 30}), 9)

    def test_description_random_names_change_texture_selection(self):
        tokens = description_tokens((ROOT/'asm/funny.m68').read_text())
        # These crops were verified against the actual Planet Data renderer.
        for index, centre in ((22, (111, 124)), (25, (135, 106)),
                              (31, (92, 83)), (40, (157, 73))):
            self.assertEqual(texture_centre(self.records[index][2], tokens), centre)
        # Hand-evaluated name RNG followed by an RNDNAME control byte.
        self.assertEqual(texture_centre((1, 2, 3), {'base_string': [3]}), (40, 40))


if __name__ == '__main__':
    unittest.main()
