"""Check batch error propagation and interpreter selection using private stubs."""
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
    def run_wrapper(self, name, release=False, fail_at=0):
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='wrapper-test-', dir=ROOT / 'build') as directory:
            fixture = Path(directory)
            shutil.copyfile(REPO / name, fixture / name)
            child = fixture / 'src_amiga'
            child.mkdir()
            (child / 'build.bat').write_text(
                '@echo off\nset /a QA_WRAPPER_CALLS+=1 >nul\n'
                '>>"%QA_WRAPPER_LOG%" echo %*\n'
                'if "%QA_WRAPPER_CALLS%"=="%QA_WRAPPER_FAIL_AT%" exit /b 23\n'
                'exit /b 0\n')
            log = fixture / 'calls.txt'
            env = dict(os.environ, QA_WRAPPER_CALLS='0', QA_WRAPPER_FAIL_AT=str(fail_at),
                       QA_WRAPPER_LOG=str(log))
            result = subprocess.run(['cmd', '/d', '/c', name] + (['all'] if release else []),
                                    cwd=fixture, env=env, capture_output=True, text=True)
            return result.returncode, log.read_text().splitlines()

    def test_stop_on_failure(self):
        for name in ('build_amiga.bat', 'build_amiga_test.bat'):
            for release, failure in ((False, 1), (False, 2), (True, 1), (True, 9), (True, 18)):
                with self.subTest(wrapper=name, release=release, fail_at=failure):
                    code, calls = self.run_wrapper(name, release, failure)
                    self.assertEqual(code, 23)
                    self.assertEqual(len(calls), failure)

    def test_success(self):
        for name in ('build_amiga.bat', 'build_amiga_test.bat'):
            for release in (False, True):
                with self.subTest(wrapper=name, release=release):
                    code, calls = self.run_wrapper(name, release)
                    self.assertEqual(code, 0)
                    self.assertEqual(len(calls), 18 if release else 2)

    def test_interpreter_paths_and_argument_order(self):
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='interpreter-test-', dir=ROOT / 'build') as directory:
            fixture = Path(directory)
            shutil.copyfile(ROOT / 'build.bat', fixture / 'build.bat')
            python_dir = fixture / 'Python with spaces'
            python_dir.mkdir()
            default = fixture / 'python.cmd'
            explicit = python_dir / 'python.cmd'
            for path, marker in ((default, 'DEFAULT'), (explicit, 'EXPLICIT')):
                path.write_text('@echo off\n>"%QA_INTERPRETER_LOG%" echo ' + marker +
                                '\n>>"%QA_INTERPRETER_LOG%" echo %*\nexit /b 23\n')
            log = fixture / 'interpreter.txt'
            for arguments, expected in ((['-Python', str(explicit)], 'EXPLICIT'),
                                        (['altgfx=yes', '-Python', str(explicit)], 'EXPLICIT'),
                                        ([], 'DEFAULT')):
                with self.subTest(arguments=arguments):
                    log.unlink(missing_ok=True)
                    env = dict(os.environ, QA_INTERPRETER_LOG=str(log),
                               PATH=str(fixture) + os.pathsep + os.environ['PATH'])
                    result = subprocess.run(['cmd', '/d', '/c', 'build.bat'] + arguments,
                                            cwd=fixture, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                    recorded = log.read_text().splitlines()
                    self.assertEqual(recorded[0], expected)
                    self.assertIn(str(fixture / 'build.py'), recorded[1])
                    self.assertIn('-B', recorded[1])


if __name__ == '__main__':
    unittest.main()
