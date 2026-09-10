"""Regression checks for dialect details that can silently corrupt a port."""
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.convert_quelo import Converter, field
from build import LOADER_ORIGIN, TOOLS


class PortTests(unittest.TestCase):
    def assemble(self, source, extra_files=None):
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-port-', dir=ROOT / 'build') as directory:
            src, output = Path(directory) / 'test.s', Path(directory) / 'test.bin'
            src.write_text(source)
            for name, content in (extra_files or {}).items():
                (Path(directory) / name).write_text(content)
            result = subprocess.run([str(TOOLS / 'vasmm68k_mot.exe'),
                '-m68000', '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
                '-I' + directory, '-I' + str(ROOT / 'asm'), '-o', str(output), str(src)], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return output.read_bytes()

    def test_ascii_constants(self):
        result = Converter('test_m68').convert("\tmoveq #'A'>>8,d0\n\tdc.w '7'/256\n")
        self.assertEqual(self.assemble(result), bytes.fromhex('7041 0037'))

    def test_comma_separated_data_and_string_spaces(self):
        self.assertEqual(field("1, 2,\t3\tcomment"), ('1, 2,\t3', 'comment'))
        source = "\tdc.w 1, 2,\t3\tcomment\n\tdz <Alien Items>\n"
        binary = self.assemble(Converter('test_m68').convert(source))
        self.assertEqual(binary, bytes.fromhex('0001 0002 0003') + b'Alien Items\0')

    def test_structure_offsets_do_not_emit_bytes(self):
        source = "\toffset 0\nfirst\nflag ds.b 1\n\tds 0\nword ds.w 1\nsize equ *\n\tsection 0\n\tdc.w first,flag,word,size\n"
        self.assertEqual(self.assemble(Converter('test_m68').convert(source)),
                         bytes.fromhex('0000 0000 0002 0004'))

    def test_reused_loop_and_return_targets(self):
        source = '\tinclude "macros.m68"\n\tq_module test\n'
        source += '\tq_loop 1,3\n\tnop\n\tq_next 1\n\tq_ret\n\tq_ret eq\n'
        source += '\tq_loop 1,2\n\tnop\n\tq_next 1\n\tq_ret\n\tq_ret ne\n'
        self.assertEqual(self.assemble(source), bytes.fromhex(
            '4e75 7e02 4e71 51cf fffc 4e75 6700 fffc 7e01 4e71 51cf fffc 4e75 6600 fffc'))

    def test_tenth_macro_parameter(self):
        source = 'cross macro\n\tdc.w \\9,\\a\n\tendm\n\tcross 1,2,3,4,5,6,7,8,9,10\n'
        self.assertEqual(self.assemble(source), bytes.fromhex('0009 000a'))

    def test_short_circuit_or(self):
        source = '\tif d0 <eq> #1 or d0 <eq> #2 then.s\n\tnop\n\tendi\n\trts\n'
        binary = self.assemble(Converter('test_m68').convert(source))
        # CMP #1,D0; BEQ body; CMP #2,D0; BNE end; body: NOP; end: RTS.
        self.assertEqual(binary, bytes.fromhex('b07c 0001 6706 b07c 0002 6602 4e71 4e75'))

    def test_launcher_fits_tos104_and_error_messages_are_separate(self):
        source = (ROOT / 'asm/boot.s').read_text()
        source += '\n    dc.l memory_message,load_message,launcher_end\n'
        binary = self.assemble(source, {'boot-config.inc':
            f'loader_address equ ${LOADER_ORIGIN:x}\nloader_size equ 390\n'
            'required_ram equ $72c76\n'})
        memory_message, load_message, launcher_end = struct.unpack('>3I', binary[-12:])
        # Actual TOS 1.04 DE desktop load address from both A: and C: runs.
        self.assertLess(0xf1f8 + launcher_end, LOADER_ORIGIN)
        self.assertLessEqual(LOADER_ORIGIN + 390, 0x12000)
        for start, end in ((memory_message, load_message), (load_message, launcher_end)):
            message = binary[start:end]
            self.assertIn(b'\0', message, 'GEMDOS Cconws requires a NUL terminator')
            text = message.split(b'\0', 1)[0]
            self.assertTrue(all(len(line) <= 40 for line in text.split(b'\r\n')))


if __name__ == '__main__':
    unittest.main()
