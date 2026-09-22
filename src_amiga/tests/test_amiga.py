"""Checks for bootable OFS disks and the Kickstart 1.x loader constraints."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.amiga_assets import extract_assets
from tools.bomb_audio import generate_bomb_audio, PAL_CLOCK, NTSC_CLOCK, PERIOD
from tools.amiga_hunk import verify_hunk
from tools.make_adf import make_adf, verify_adf


class AmigaTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'build').mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='test-amiga-', dir=ROOT/'build')
        self.addCleanup(self.directory.cleanup)
        self.temp = Path(self.directory.name)
        self.boot = bytearray(1024)
        self.boot[:4] = b'DOS\0'
        struct.pack_into('>I', self.boot, 8, 880)
        struct.pack_into('>I', self.boot, 4, ~(0x444f5300+880) & 0xffffffff)

    def disk(self):
        # Multiple extension blocks, a directory and an empty file.
        files = {'ELITE': bytes(range(256))*450, 's/startup-sequence': b'ELITE\n', 'EMPTY': b''}
        target = self.temp/'test.adf'
        make_adf(files, target, self.boot)
        return bytearray(target.read_bytes()), files

    def test_ofs_directory_extensions_and_readback(self):
        image, files = self.disk()
        verify_adf(image, files)

    def test_ofs_rejects_allocated_block_marked_free(self):
        image, files = self.disk()
        start = 881*512
        word = struct.unpack_from('>I', image, start+4)[0]
        struct.pack_into('>I', image, start+4, word | 1)  # block 2 is the executable header
        struct.pack_into('>I', image, start, 0)
        checksum = -sum(struct.unpack_from('>128I', image, start)) & 0xffffffff
        struct.pack_into('>I', image, start, checksum)
        with self.assertRaisesRegex(ValueError, 'bitmap'):
            verify_adf(image, files)

    def test_ofs_rejects_damaged_data(self):
        image, files = self.disk()
        image[3*512+24] ^= 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            verify_adf(image, files)

    def test_disk_capacity(self):
        with self.assertRaisesRegex(ValueError, 'full'):
            make_adf({'TOO_BIG': bytes(901120)}, self.temp/'full.adf', self.boot)

    def test_hunk_requires_chip_ram_for_dma(self):
        words = [1011, 0, 1, 0, 0, 1, 1003, 1, 1010]
        with self.assertRaisesRegex(ValueError, 'Chip RAM'):
            verify_hunk(struct.pack('>9I', *words), ['amiga_video'])
        words[5] |= 0x40000000
        result = verify_hunk(struct.pack('>9I', *words), ['amiga_video'])
        self.assertTrue(result['amiga_video']['chip_ram'])

    def test_kickstart_bss_limit(self):
        words = [1011, 0, 1, 0, 0, 65537, 1003, 65537, 1010]
        with self.assertRaisesRegex(ValueError, 'clearing limit'):
            verify_hunk(struct.pack('>9I', *words), ['workspace'])

    def test_original_sample_bank(self):
        _, report = extract_assets(ROOT.parent/'resources/amiga/Elite 2.0.adf', self.temp)
        self.assertEqual(report['sample_count'], 19)
        self.assertEqual(report['sample_bytes'], 53908)
        self.assertEqual(report['sample_sha256'],
                         'caf263a98a7ed9222851f31df9c5a0cc4f2b4125d50e89fcc71e9fbcec101680')

    def test_original_music_assets(self):
        _, report = extract_assets(ROOT.parent/'resources/amiga/Elite 2.0.adf', self.temp)
        music = report['music']
        self.assertEqual((music['track_count'], music['channels'],
                          music['instrument_count'], music['pattern_count']), (1, 4, 7, 40))
        self.assertEqual(music['sample_bytes'], 60350)
        self.assertEqual(music['sample_sha256'],
                         '98560c1cc7ad3bbd58a7c02c0ea7fc80a0cc5d23373800bb23b8621cbc275cff')
        self.assertEqual(music['score_sha256'],
                         'de21d507e3dc4d0282522277f54be690f6da1d75789483d18539e6730fa806e8')

    def test_energy_bomb_attack_decay_and_dma_tail(self):
        report = generate_bomb_audio(self.temp)
        data = (self.temp/'bomb-sample.bin').read_bytes()
        samples = [v if v < 128 else v-256 for v in data]
        self.assertEqual(len(data) % 2, 0)  # Paula DMA counts words
        self.assertLessEqual(max(map(abs, samples)), 127)
        rate = PAL_CLOCK / PERIOD
        def power(start, end):
            part = samples[int(start*rate):int(end*rate)]
            return sum(v*v for v in part) / len(part)
        self.assertGreater(power(.50, .62), 10*power(.10, .22))
        self.assertGreater(power(.80, 1.0), 10*power(1.9, 2.1))
        for clock, hz, ticks in ((PAL_CLOCK, 50, report['pal_ticks']),
                                 (NTSC_CLOCK, 60, report['ntsc_ticks'])):
            stop = int(ticks / hz * clock / PERIOD)
            self.assertLess(stop, len(data))  # stop before DMA repeats the sample
            self.assertGreater(stop, 0)
            self.assertTrue(any(data[:stop]))
            self.assertEqual(data[stop-100:], bytes(len(data)-stop+100))


if __name__ == '__main__':
    unittest.main()
