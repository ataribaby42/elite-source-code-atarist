"""Execute the real auto-pilot rotations on a 68000.

Both auto-pilots divide a dot product by the length of the vector to the
target. That length is zero when the target sits on the axis being measured,
and the division then raises a zero-divide exception. The docking computer
reaches it because launching leaves the station at (0,0,-2500) with an
identity orientation, so its first turning point is exactly axial. The object
auto-pilot reaches it when an object arrives at its target point, which
missiles and attacking ships homing on the player at the origin can do. TOS
resumes after a zero divide instead of aborting, so the ST survived the
exception; the guards make the intended result explicit.

Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_raster import routine
from test_viewport import assemble, preamble, variable_block

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_A5,
        UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

CODE, STOP, VARIABLES, OBJECT, STACK = 0x10000, 0x1000, 0x30000, 0x50000, 0x90000

NAMES = ['auto_rotate', 'auto_pilot', 'magnitude', 'roll_angle', 'climb_angle',
         'xpos', 'ypos', 'zpos', 'x_vector', 'y_vector', 'z_vector',
         'on_course', 'turn_rate', 'obj_len']

UNIT = 16384  # a full-length direction vector component


def signed(value):
    return struct.unpack('>h', struct.pack('>H', value & 0xffff))[0]


def build():
    """Assemble both auto-pilots with the ship rotations stubbed out."""
    auto = (ROOT / 'asm/auto.m68').read_text()
    maths = (ROOT / 'asm/maths.m68').read_text()
    data = (ROOT / 'asm/data.m68').read_text()
    asm = preamble()
    asm += auto[auto.index('roll_rate:'):auto.index('; ---- LOCAL VARIABLES ----')]
    asm += variable_block(auto, 'auto')
    asm += auto[auto.index('; ---- LOCAL MACROS ----'):auto.index('\tq_module auto')]
    asm += '\tsection text,code\n\torg $10000\n\tdc.l ' + ','.join(NAMES) + '\n'
    asm += '\n'.join(routine(auto, name) for name in
                     ('auto_pilot', 'auto_rotate', 'angle_diff', 'set_roll', 'set_climb'))
    # The angles themselves are the only part of the ship state under test.
    asm += ('\nset_roll_angles:\nset_climb_angles:\ncalc_yvector:\n'
            'local_z_rotate:\nlocal_x_rotate:\n\trts\n')
    asm += routine(maths, 'sqrt')
    asm += '\nreturn: set *\n\trts\n'
    asm += auto[auto.index('object_windows:'):auto.index('text1:')]
    asm += '\n' + data[data.index('\tq_global magnitude_table'):
                       data.index('* Table of cosines')] + '\n'
    return assemble(asm, NAMES)


class AutoPilotTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.sym = build()

    def start(self, model):
        cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        cpu.ctl_set_cpu_model(model)
        cpu.mem_map(0, 0x100000)
        cpu.mem_write(CODE, self.code)
        cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        cpu.mem_write(STACK - 4, struct.pack('>I', STOP))
        return cpu

    def finish(self, cpu, entry):
        cpu.emu_start(self.sym[entry], STOP, count=200000)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_A7), STACK)


@unittest.skipIf(Uc is None, 'optional docking tests require unicorn==2.1.4')
class AutoRotateTests(AutoPilotTestCase):
    def rotate(self, x, y, z, model=UC_CPU_M68K_M68000 if Uc else 0):
        """Return (on course flag, magnitude, roll angle, climb angle)."""
        cpu = self.start(model)
        for register, value in ((UC_M68K_REG_D0, x), (UC_M68K_REG_D1, y),
                                (UC_M68K_REG_D2, z)):
            cpu.reg_write(register, value & 0xffffffff)
        self.finish(cpu, 'auto_rotate')
        read = lambda name: signed(int.from_bytes(
            cpu.mem_read(VARIABLES + self.sym[name], 2), 'big'))
        return (signed(cpu.reg_read(UC_M68K_REG_D0)), read('magnitude'),
                read('roll_angle'), read('climb_angle'))

    def test_target_ahead_on_the_line_of_sight(self):
        """The first turning point after launch is exactly ahead."""
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for z in (500, 3000, 40000, 200000):
                course, magnitude, roll, climb = self.rotate(0, 0, z, model)
                self.assertEqual(course, -1, z)
                self.assertEqual((roll, climb), (0, 0), z)
                self.assertGreater(magnitude, 0, z)

    def test_target_behind_on_the_line_of_sight(self):
        """Engaging straight after launch leaves the station directly behind."""
        course, _, roll, climb = self.rotate(0, 0, -2500)
        self.assertEqual(course, 0)
        self.assertEqual(roll, 0)
        self.assertNotEqual(climb, 0)

    def test_target_within_the_reduction_step_of_the_line_of_sight(self):
        """Distant targets reduce to zero across the line of sight."""
        for x, y, z in ((5, 5, 200000), (1, 0, 200000), (0, -3, 65536)):
            course, magnitude, _, _ = self.rotate(x, y, z)
            self.assertEqual(course, -1, (x, y, z))
            self.assertGreater(magnitude, 0, (x, y, z))

    def test_target_reached(self):
        """A target at the ship's own position leaves no direction to fly."""
        course, magnitude, roll, climb = self.rotate(0, 0, 0)
        self.assertEqual((course, magnitude, roll, climb), (-1, 0, 0, 0))

    def test_off_axis_target_still_rolls(self):
        """Ordinary targets keep taking the dot product as before."""
        course, magnitude, roll, climb = self.rotate(20000, 0, 40000)
        self.assertEqual(course, 0)
        self.assertEqual(magnitude, 0)  # the roll branch returns before the range
        self.assertGreater(roll, 0)
        self.assertEqual(climb, 0)
        course, _, mirrored, _ = self.rotate(-20000, 0, 40000)
        self.assertEqual(course, 0)
        self.assertEqual(mirrored, -roll)


@unittest.skipIf(Uc is None, 'optional docking tests require unicorn==2.1.4')
class ObjectAutoPilotTests(AutoPilotTestCase):
    def pilot(self, position, target, facing=UNIT,
              model=UC_CPU_M68K_M68000 if Uc else 0):
        """Fly an object at `position` towards `target`; return its on course flag."""
        cpu = self.start(model)
        cpu.mem_write(OBJECT, bytes(self.sym['obj_len']))
        cpu.mem_write(OBJECT + self.sym['xpos'], struct.pack('>3i', *position))
        for axis, vector in (('x_vector', (UNIT, 0, 0)), ('y_vector', (0, UNIT, 0)),
                             ('z_vector', (0, 0, facing))):
            cpu.mem_write(OBJECT + self.sym[axis], struct.pack('>3h', *vector))
        cpu.mem_write(OBJECT + self.sym['turn_rate'], struct.pack('>h', 32))
        cpu.reg_write(UC_M68K_REG_A5, OBJECT)
        for register, value in zip((UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2),
                                   target):
            cpu.reg_write(register, value & 0xffffffff)
        self.finish(cpu, 'auto_pilot')
        return signed(int.from_bytes(
            cpu.mem_read(OBJECT + self.sym['on_course'], 2), 'big'))

    def test_object_reaches_its_target_point(self):
        """A missile homing on the player arrives at the point it aims for."""
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.assertEqual(self.pilot((0, 1, 2), (0, 1, 2), model=model), 10)

    def test_object_reaches_a_target_point_behind_it(self):
        """Arriving while pointing away still asks for a turn, not a divide."""
        self.assertEqual(self.pilot((7000, -200, 90), (7000, -200, 90), -UNIT), 0)

    def test_object_one_unit_short_of_its_target(self):
        """The reduction follows the remaining distance, so it never reaches zero."""
        self.assertEqual(self.pilot((0, 0, -1), (0, 0, 0)), 10)
        self.assertEqual(self.pilot((0, 0, 1), (0, 0, 0)), 0)

    def test_object_short_of_its_target_still_turns(self):
        """Ordinary targets keep taking the dot product as before."""
        self.assertEqual(self.pilot((0, 0, 0), (40000, 0, 40000)), 0)
        self.assertEqual(self.pilot((0, 0, 0), (0, 0, 40000)), 10)


if __name__ == '__main__':
    unittest.main()
