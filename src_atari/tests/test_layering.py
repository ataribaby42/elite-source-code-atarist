"""Check flight occlusion with actual MC68000 list traversal and raster code.

Scene content is stubbed with overlapping coloured spans and single-pixel stars.
Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import struct
import unittest

from test_raster import BACKGROUND, GUARD, SCREEN, OTHER, paint, routine
from test_viewport import assemble, preamble

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, STACK = 0x10000, 0x1000, 0x30000, 0x90000
OBJECTS, LIST, COLOURS, TRACE, CURSOR = 0x60000, 0x68000, 0x73000, 0x74000, 0x76000
STARS = (40, 80, 120, 160, 200, 240)


def colour(value):
    return tuple(65535 if value & (1 << plane) else 0 for plane in range(4))


@unittest.skipIf(Uc is None, 'optional layering tests require unicorn==2.1.4')
class LayeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vector = (ROOT / 'asm/vector.m68').read_text()
        graphics = (ROOT / 'asm/graphics.m68').read_text()
        names = ['draw_all', 'draw_space', 'draw_space_layer']
        constants = ['next_record', 'list_ptr', 'obj_ptr', 'next_ptr', 'prev_ptr',
                     'draw_len', 'type', 'flags', 'point', 'xpos', 'ypos', 'zpos',
                     'planet', 'sun', 'photon', 'scr_base', 'colour_ptr']
        assembly = preamble() + 'max_lines equ 10\n'
        assembly += vector[vector.index('\trsset 0'):vector.index('* ---- LOCAL MACROS ----')]
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + constants) + '\n'
        assembly += '\n'.join(routine(vector, name) for name in names)
        assembly += '\n'.join(routine(graphics, name) for name in
                              ['dot_to_addr', 'plotxy', 'line', 'horiz_line', 'vert_line', 'mask_plot'])
        assembly += graphics[graphics.index('\tq_global bit_masks'):graphics.index('clip_list:')]
        # Stubs deliberately clobber drawing scratch registers; selectors/list
        # pointers must survive just as they do across real object rendering.
        assembly += f"""
draw_it:
    move.l a5,d0
    bsr trace_event
    move.w xpos+2(a5),d0
    move.w ypos+2(a5),d2
    moveq #20,d1
    moveq #20,d3
    move.l zpos(a5),colour_ptr(a6)
    bsr line
    bra clobber_scratch
dust_cloud:
    moveq #0,d0
    bsr trace_event
    move.l #{COLOURS+15*8},colour_ptr(a6)
"""
        for x in STARS:
            assembly += f'    move.w #{x},d0\n    moveq #20,d1\n    bsr plotxy\n'
        assembly += f"""
draw_ai_laser:
    rts
clobber_scratch:
    move.l #$5a5a5a5a,d0
    move.l d0,d1
    move.l d0,d2
    move.l d0,d3
    move.l d0,d4
    move.l d0,d5
    move.l d0,d6
    move.l d0,d7
    move.l d0,a0
    move.l d0,a1
    move.l d0,a2
    move.l d0,a3
    move.l d0,a4
    move.l d0,a5
    rts
trace_event:
    move.l {CURSOR},a1
    move.l d0,(a1)+
    move.l a1,{CURSOR}
    rts
mult_by_320:
    dc.w """ + ','.join(str(y*320) for y in range(200)) + '\n'
        cls.code, cls.symbols = assemble(assembly, names + constants)

    def run_scene(self, objects, flight=True, screen=SCREEN, model=None):
        cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        cpu.ctl_set_cpu_model(model or UC_CPU_M68K_M68000)
        cpu.mem_map(0, 0x100000)
        cpu.mem_write(CODE, self.code)
        cpu.mem_protect(CODE, (len(self.code)+4095)//4096*4096, UC_PROT_READ | UC_PROT_EXEC)
        cpu.mem_write(GUARD, BACKGROUND)
        for value in range(16):
            cpu.mem_write(COLOURS+value*8, struct.pack('>4H', *colour(value)))
        def word(address, value):
            cpu.mem_write(address, struct.pack('>H', value & 65535))
        def long(address, value):
            cpu.mem_write(address, struct.pack('>I', value))
        long(CURSOR, TRACE)
        long(VARIABLES+self.symbols['scr_base'], screen)
        long(VARIABLES+self.symbols['next_record'], LIST+len(objects)*12 if objects else 0)
        # Deliberately invalid when the queue is empty.
        long(VARIABLES+self.symbols['list_ptr'], LIST if objects else 0xffffffff)
        for index, (kind, left, right, ink) in enumerate(objects):
            address = OBJECTS+index*512
            word(address+self.symbols['type'], kind)
            # A point flag alone must not put photons/small objects behind stars.
            word(address+self.symbols['flags'], (1 << self.symbols['point']) << 8)
            long(address+self.symbols['xpos'], left)
            long(address+self.symbols['ypos'], right)
            long(address+self.symbols['zpos'], COLOURS+ink*8)
            node = LIST+index*self.symbols['draw_len']
            long(node+self.symbols['obj_ptr'], address)
            long(node+self.symbols['prev_ptr'], node-12 if index else 0)
            long(node+self.symbols['next_ptr'], node+12 if index+1 < len(objects) else 0)
        queue_before = bytes(cpu.mem_read(LIST, len(objects)*12))
        cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        cpu.reg_write(UC_M68K_REG_A7, STACK-4)
        long(STACK-4, STOP)
        cpu.emu_start(self.symbols['draw_space' if flight else 'draw_all'], STOP, count=100000)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_A7), STACK)
        self.assertEqual(cpu.mem_read(LIST, len(queue_before)), queue_before)
        end, = struct.unpack('>I', cpu.mem_read(CURSOR, 4))
        trace = struct.unpack('>' + 'I'*((end-TRACE)//4), cpu.mem_read(TRACE, end-TRACE))
        return bytes(cpu.mem_read(GUARD, len(BACKGROUND))), trace

    def check_scene(self, objects, flight=True):
        celestial = {self.symbols['planet'], self.symbols['sun']}
        order = list(range(len(objects)))
        if flight:
            order = ([i for i in order if objects[i][0] in celestial] + [-1] +
                     [i for i in order if objects[i][0] not in celestial])
        expected_trace = tuple(0 if index == -1 else OBJECTS+index*512 for index in order)
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for screen in (SCREEN, OTHER):
                expected = bytearray(BACKGROUND)
                for index in order:
                    if index == -1:
                        paint(expected, ((x, 20) for x in STARS), colour(15), screen)
                    else:
                        _, left, right, ink = objects[index]
                        paint(expected, ((x, 20) for x in range(left, right+1)), colour(ink), screen)
                actual, trace = self.run_scene(objects, flight, screen, model)
                self.assertEqual(actual, expected)
                self.assertEqual(trace, expected_trace)

    def test_stars_cover_planet_and_sun_but_ships_and_other_points_cover_stars(self):
        # Deliberately interleave celestial and ordinary objects in depth order.
        self.check_scene([(0, 100, 220, 2), (self.symbols['sun'], 32, 287, 12),
                          (self.symbols['photon'], 180, 200, 5),
                          (self.symbols['planet'], 32, 160, 8), (1, 120, 140, 1)])

    def test_empty_or_single_layer_queues_draw_stars_exactly_once(self):
        for objects in ([], [(0, 32, 287, 1)], [(self.symbols['planet'], 32, 287, 8)],
                        [(self.symbols['sun'], 32, 287, 12)]):
            self.check_scene(objects)

    def test_nonflight_renderer_keeps_the_original_depth_order_without_stars(self):
        self.check_scene([(0, 32, 287, 2), (self.symbols['planet'], 80, 220, 8),
                          (1, 120, 200, 1)], flight=False)


if __name__ == '__main__':
    unittest.main()

