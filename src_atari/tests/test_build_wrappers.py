"""Exercise Windows distribution wrappers without assembling or publishing files."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


@unittest.skipUnless(os.name == 'nt', 'Windows batch wrappers')
class BuildWrapperTests(unittest.TestCase):
    def run_wrapper(self, name, fail_at=0):
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='wrapper-test-', dir=ROOT / 'build') as directory:
            fixture = Path(directory)
            shutil.copyfile(REPO / name, fixture / name)
            child = fixture / 'src_atari'
            child.mkdir()
            (child / 'build.bat').write_text(
                '@echo off\nset /a QA_WRAPPER_CALLS+=1 >nul\n'
                '>>"%QA_WRAPPER_LOG%" echo %*\n'
                'if "%QA_WRAPPER_CALLS%"=="%QA_WRAPPER_FAIL_AT%" exit /b 23\n'
                'exit /b 0\n')
            log = fixture / 'calls.txt'
            env = dict(os.environ, QA_WRAPPER_CALLS='0', QA_WRAPPER_FAIL_AT=str(fail_at),
                       QA_WRAPPER_LOG=str(log))
            result = subprocess.run(['cmd', '/d', '/c', name, 'noprotect=no'],
                                    cwd=fixture, env=env, capture_output=True, text=True)
            return result.returncode, log.read_text().splitlines()

    def test_stop_on_first_failure(self):
        for name in ('build_atari.bat', 'build_atari_test.bat'):
            with self.subTest(wrapper=name):
                code, calls = self.run_wrapper(name, 1)
                self.assertEqual(code, 23)
                self.assertEqual(len(calls), 1)

    def test_success_and_final_failure(self):
        for name in ('build_atari.bat', 'build_atari_test.bat'):
            for failure in (0, 2):
                with self.subTest(wrapper=name, fail_at=failure):
                    code, calls = self.run_wrapper(name, failure)
                    self.assertEqual(code, 23 if failure else 0)
                    self.assertEqual(len(calls), 2)
                    self.assertTrue(all(call.endswith('noprotect=no') for call in calls))


if __name__ == '__main__':
    unittest.main()
