"""Read back AUTO-folder disks and reject broken directory/FAT metadata."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.make_disk import make_disk, verify_disk


class DiskTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='test-disk-', dir=ROOT/'build')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.files = [self.directory/name for name in ('ELITE.TOS', 'LOADER.IMG', 'ELITE.IMG')]
        for n, path in enumerate(self.files):
            path.write_bytes(bytes(range(256))*(n+1)*7)
        self.auto = self.directory/'ELITE.PRG'
        self.auto.write_bytes(b'\x60\x1a'+bytes(range(256))*9)
        self.disk = self.directory/'ELITE.ST'

    def auto_directory(self, image):
        entries = [image[pos:pos+32] for pos in range(3584, 7168, 32)]
        auto = next(entry for entry in entries if entry[:11] == b'AUTO       ')
        self.assertEqual(auto[11], 0x10)
        self.assertEqual(struct.unpack_from('<I', auto, 28)[0], 0)
        cluster = struct.unpack_from('<H', auto, 26)[0]
        return 7168+(cluster-2)*1024

    def test_auto_disk_and_manual_launcher_round_trip(self):
        make_disk(self.files, self.disk, auto_program=self.auto)
        verify_disk(self.disk, self.files, auto_program=self.auto)
        image = self.disk.read_bytes()
        self.assertEqual(len(image), 737280)
        self.assertNotEqual(sum(struct.unpack('>256H', image[:512])) & 65535, 0x1234)
        pos = self.auto_directory(image)
        self.assertEqual(image[pos+64:pos+75], b'ELITE   PRG')
        self.assertEqual(image[pos+75], 0x20)
        self.assertEqual(struct.unpack_from('<I', image, pos+92)[0], self.auto.stat().st_size)
        make_disk(self.files, self.disk, auto_program=self.auto)
        self.assertEqual(self.disk.read_bytes(), image)

    def test_plain_disk_still_round_trips(self):
        make_disk(self.files, self.disk)
        verify_disk(self.disk, self.files)

    def test_rejects_wrong_parent_and_cross_linked_auto_program(self):
        for damage in ('parent', 'cross_link'):
            with self.subTest(damage=damage):
                make_disk(self.files, self.disk, auto_program=self.auto)
                image = bytearray(self.disk.read_bytes())
                pos = self.auto_directory(image)
                if damage == 'parent':
                    struct.pack_into('<H', image, pos+32+26, 2)
                else:
                    # Point the launcher at a root file's already-owned clusters.
                    image[pos+64+26:pos+64+28] = image[3584+26:3584+28]
                self.disk.write_bytes(image)
                with self.assertRaises(ValueError):
                    verify_disk(self.disk, self.files, auto_program=self.auto)


if __name__ == '__main__':
    unittest.main()
