"""Check scanner zoom and both instrument buffers across a system reset."""
from pathlib import Path
import re
import struct
import unittest

from test_raster import routine
from test_viewport import assemble, preamble

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE,
                         UC_PROT_READ, UC_PROT_EXEC)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D2,
        UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, VARIABLES, STACK, STOP = 0x10000, 0x30000, 0x90000, 0x1000
SCREENS = (0x40000, 0x48000)


@unittest.skipIf(Uc is None, 'optional scanner tests require unicorn==2.1.4')
class ScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init = (ROOT/'asm/init.m68').read_text()
        main = (ROOT/'asm/main.m68').read_text()
        cockpit = (ROOT/'asm/cockpit.m68').read_text()
        names = ['reset_system', 'magnification', 'instruments', 'update_inst',
                 'radar_scale', 'radar_range', 'f_magnify', 'f_front', 'no_flags',
                 'screen1_ptr', 'scr_base', 'bit_magnify', 'put_bitmap']
        assembly = preamble() + '\tinclude "bitlist.m68"\n'
        for name in ('magnify_x', 'magnify_y'):
            assembly += re.search(r'^'+name+r': equ[^\n]*\n', cockpit, re.M).group(0)
        assembly += '\torg $10000\n\tdc.l '+','.join(names)+'\n'
        assembly += 'return: set *\n\trts\n'
        assembly += routine(init, 'reset_system') + routine(main, 'magnification')
        assembly += ''.join(routine(cockpit, name) for name in
                            ('instruments', 'update_inst', 'inst_magnify'))
        assembly += re.search(r'^reset_table:\s*\n(?:\s*dc\.w[^\n]*\n)+',
                              init, re.M).group(0)
        table = cockpit[cockpit.index('inst_list:'):cockpit.index('* Missile - not installed.')]
        assembly += table
        # Keep the real instrument dispatcher and bitmap selection. Only the
        # unrelated instruments, drawing backend and reset helpers are stubbed.
        for name in sorted(set(re.findall(r'\binst_\w+', table)) - {'inst_list', 'inst_magnify'}):
            assembly += name+':\n'
        assembly += 'set_roll_angles:\nset_climb_angles:\nquiet:\n\trts\n'
        assembly += 'rand:\n\tmoveq #0,d0\n\trts\n'
        assembly += 'find_bitmap:\n\tmove.w d0,d2\n\trts\nput_bitmap:\n\trts\n'
        cls.code, cls.symbols = assemble(assembly, names)

    def prepare(self, model):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, (len(self.code)+4095)//4096*4096,
                             UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.var('screen1_ptr', SCREENS[0], 4)
        self.var('radar_scale', self.symbols['radar_range'], 4)
        self.drawn = {}
        self.draw_count = 0
        self.cpu.hook_add(UC_HOOK_CODE, self.bitmap,
                         begin=self.symbols['put_bitmap'], end=self.symbols['put_bitmap'])
        self.call('instruments')
        self.frames()

    def var(self, name, value, size=2):
        self.cpu.mem_write(VARIABLES+self.symbols[name], value.to_bytes(size, 'big'))

    def read(self, name, size=2):
        return int.from_bytes(self.cpu.mem_read(VARIABLES+self.symbols[name], size), 'big')

    def call(self, name):
        self.cpu.reg_write(UC_M68K_REG_A7, STACK-4)
        self.cpu.mem_write(STACK-4, struct.pack('>I', STOP))
        self.cpu.emu_start(self.symbols[name], STOP, count=10000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK)

    def bitmap(self, cpu, address, size, user):
        self.assertEqual(cpu.reg_read(UC_M68K_REG_D0) & 65535, 100)
        self.drawn[self.read('scr_base', 4)] = (
            cpu.reg_read(UC_M68K_REG_D2) & 65535) - self.symbols['bit_magnify'] + 1
        self.draw_count += 1

    def frames(self):
        for screen in SCREENS:
            self.var('scr_base', screen, 4)
            self.call('update_inst')

    def assert_zoom(self, zoom):
        self.assertEqual(self.read('radar_scale', 4), self.symbols['radar_range']//zoom)
        self.assertEqual(self.drawn, dict.fromkeys(SCREENS, zoom))

    def test_relaunch_refreshes_both_buffers_before_next_zoom_key(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            with self.subTest(model=model):
                self.prepare(model)
                for _ in range(3):
                    self.call('magnification')
                    self.frames()
                    self.assert_zoom(2)
                    # The launch animation has drawn x2 on both screens before
                    # LAUNCH calls RESET_SYSTEM. Both buffers are marked clean.
                    self.assertEqual(self.read('f_magnify'), 0x0300)
                    self.call('reset_system')
                    self.frames()
                    self.assert_zoom(1)
                    # Each subsequent press changes the actual and shown zoom.
                    for zoom in (2, 1):
                        self.call('magnification')
                        self.frames()
                        self.assert_zoom(zoom)
                    count = self.draw_count
                    self.frames()
                    self.assertEqual(self.draw_count, count)

    def test_reset_during_partial_refresh_or_at_normal_zoom(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for screen in SCREENS:
                with self.subTest(model=model, screen=screen):
                    self.prepare(model)
                    self.call('magnification')
                    self.var('scr_base', screen, 4)
                    self.call('update_inst')
                    self.call('reset_system')
                    self.frames()
                    self.assert_zoom(1)
                    self.call('reset_system')
                    self.frames()
                    self.assert_zoom(1)


if __name__ == '__main__':
    unittest.main()
