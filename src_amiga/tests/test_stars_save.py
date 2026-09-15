"""Commander persistence of Stars using the real 68K save, restore and sky code."""
import struct
import unittest
import test_registration as fixture


@unittest.skipIf(fixture.Uc is None, 'optional commander tests require unicorn==2.1.4')
class StarsSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.RegistrationTests.setUpClass()

    def setUp(self):
        self.game = fixture.RegistrationTests()

    def saved(self):
        self.game.call('save_state')
        return bytes(self.game.cpu.mem_read(self.game.at('game_state'), 256))

    def restore(self, data):
        self.game.cpu.mem_write(self.game.at('game_state'), bytes(data))
        self.game.call('restore_state')

    def test_on_off_round_trip_changes_only_the_saved_stars_bit(self):
        g = self.game
        for model in (fixture.UC_CPU_M68K_M68000, fixture.UC_CPU_M68K_M68020):
            for other_flags in range(64):
                g.boot(model)
                # Exercise all old options, the other unused high bit and low byte.
                preferences = ((other_flags | 0x80) << 8) | 0xa5
                g.word(g.at('user'), preferences)
                g.long(g.at('cash'), 12345678)
                g.word(g.at('mission'), 0x52)
                g.long(g.at('player_registration'), 0x4142ff00)
                on_save = self.saved()
                for enabled in (0, 1):
                    g.call('set_sky_enabled', d0=enabled)
                    saved = self.saved()
                    expected = bytearray(on_save)
                    expected[10] |= 0x40 if not enabled else 0
                    self.assertEqual(saved, bytes(expected))
                    # Execute the same encoding used by both disk APIs.
                    g.cpu.mem_write(g.at('io_buffer'), saved)
                    g.call('scramble')
                    encoded = bytes(g.cpu.mem_read(g.at('io_buffer'), 256))
                    self.assertEqual(encoded, bytes(v ^ (255-i) for i,v in enumerate(saved)))
                    g.call('scramble')
                    decoded = bytes(g.cpu.mem_read(g.at('io_buffer'), 256))
                    g.call('set_sky_enabled', d0=1-enabled)
                    self.restore(decoded)
                    self.assertEqual(g.word(g.at('sky_enabled')), enabled)
                    self.assertEqual(g.word(g.at('user')), preferences | (0x4000 if not enabled else 0))
                    self.assertEqual(g.long(g.at('cash')), 12345678)
                    self.assertEqual(g.word(g.at('mission')), 0x52)
                    self.assertEqual(g.long(g.at('player_registration')), 0x4142ff00)
                    self.assertEqual(self.saved(), saved)

    def test_old_commanders_restore_on_even_after_playing_with_stars_off(self):
        g = self.game
        for model in (fixture.UC_CPU_M68K_M68000, fixture.UC_CPU_M68K_M68020):
            g.boot(model)
            original = self.saved()
            for tail in (original[178:], bytes(78), b'\xff'*78):
                for preferences in range(64):
                    old = bytearray(original[:178] + tail)
                    old[10] = preferences
                    g.call('set_sky_enabled', d0=0)
                    self.restore(old)
                    self.assertEqual(g.word(g.at('sky_enabled')), 1)
                    self.assertEqual(g.word(g.at('user')), preferences << 8)

    def test_rcs_default_on_and_commander_round_trip(self):
        g = self.game
        for model in (fixture.UC_CPU_M68K_M68000, fixture.UC_CPU_M68K_M68020):
            for maximum in (0, 1):
                g.boot(model, maximum)
                original = self.saved()
                self.assertEqual(original[10] & 0x80, 0)
                for enabled in (False, True):
                    preferences = g.word(g.at('user')) & ~0x8000
                    g.word(g.at('user'), preferences | (0 if enabled else 0x8000))
                    saved = self.saved()
                    expected = bytearray(original)
                    expected[10] |= 0 if enabled else 0x80
                    self.assertEqual(saved, bytes(expected))
                    g.word(g.at('user'), 0xffff)
                    self.restore(saved)
                    self.assertEqual(g.word(g.at('user')), preferences | (0 if enabled else 0x8000))
                g.word(g.at('user'), 0xffff)
                g.call('default_game')
                g.call('restore_state')
                self.assertEqual(g.word(g.at('user')) & 0x8000, 0)

    def test_startup_and_both_default_jamesons_enable_stars(self):
        g = self.game
        identity = struct.pack('>9i', 1 << 24, 0, 0, 0, 1 << 24, 0, 0, 0, 1 << 24)
        for model in (fixture.UC_CPU_M68K_M68000, fixture.UC_CPU_M68K_M68020):
            for maximum in (0, 1):
                g.boot(model, maximum)
                initial = self.saved()
                self.assertEqual(initial[10] & 0x40, 0)
                self.assertEqual(g.word(g.at('sky_enabled')), 1)
                g.call('set_sky_enabled', d0=0)
                off_save = self.saved()
                g.call('init_sky')
                self.assertEqual(g.word(g.at('sky_enabled')), 1)
                self.assertEqual(g.word(g.at('user')) & 0x4000, 0)
                self.restore(off_save)
                self.assertEqual(g.word(g.at('sky_enabled')), 0)
                g.call('default_game')
                g.call('restore_state')
                self.assertEqual(g.word(g.at('sky_enabled')), 1)
                self.assertEqual(self.saved(), initial)
                self.assertEqual(bytes(g.cpu.mem_read(g.at('sky_basis'), 36)), identity)


if __name__ == '__main__':
    unittest.main()
