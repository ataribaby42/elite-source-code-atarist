"""Verify that the preserved version is a conversion of the untouched archive."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.convert_quelo import Converter


class OriginalTests(unittest.TestCase):
    def test_archive_and_copied_assets_are_unchanged(self):
        provenance = json.loads((ROOT/'original-archive.json').read_text(encoding='utf-8'))
        baseline = json.loads((ROOT/'original-sha256.json').read_text(encoding='utf-8'))
        archive = ROOT.parent / provenance['path']
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), provenance['sha256'])
        with ZipFile(archive) as zipped:
            self.assertEqual(set(zipped.namelist()), set(baseline))
            self.assertEqual(len(zipped.infolist()), 307)
        for name in provenance['assets']:
            self.assertEqual(hashlib.sha256((ROOT/'assets'/name).read_bytes()).hexdigest(), baseline[name], name)

    def test_all_converted_sources_match_the_archive(self):
        # Only this provenance test needs a legacy ZIP extractor. The build and
        # other tests use checked-in sources and Python's standard library.
        unzip = shutil.which('unzip')
        if not unzip:
            candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/usr/bin/unzip.exe'
            if candidate.is_file():
                unzip = str(candidate)
        if not unzip:
            self.skipTest('optional source-fidelity test requires Info-ZIP unzip with Shrink/Implode support')
        provenance = json.loads((ROOT/'original-archive.json').read_text(encoding='utf-8'))
        baseline = json.loads((ROOT/'original-sha256.json').read_text(encoding='utf-8'))
        archive = ROOT.parent / provenance['path']
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), provenance['sha256'])
        (ROOT/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-original-', dir=ROOT/'build') as temporary:
            output = Path(temporary)
            result = subprocess.run([unzip, '-qq', str(archive), '-d', str(output)],
                cwd=output, capture_output=True, text=True, errors='replace')
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            with ZipFile(archive) as zipped:
                for info in zipped.infolist():
                    data = (output/info.filename).read_bytes()
                    self.assertEqual(zlib.crc32(data), info.CRC, info.filename)
                    self.assertEqual(hashlib.sha256(data).hexdigest(), baseline[info.filename], info.filename)
            for name in provenance['source_files']:
                converted = Converter(name.lower().replace('.', '_')).convert(
                    (output/name).read_text(encoding='latin1'))
                if name.endswith('.M68') and name not in {
                    'MACROS.M68','BITLIST.M68','ICONS.M68','NOTES.M68','OBJECTS.M68','ELITECHR.M68'}:
                    converted = '\tinclude "common.def"\n' + converted
                self.assertEqual((ROOT/'asm'/name.lower()).read_text(encoding='utf-8'), converted, name)


if __name__ == '__main__':
    unittest.main()
