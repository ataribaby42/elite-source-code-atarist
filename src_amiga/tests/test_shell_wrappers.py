"""Run the real POSIX wrappers with an argument-recording interpreter stub."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SHELL = shutil.which('sh') or shutil.which('bash')
if not SHELL and os.name == 'nt':
    candidate = Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe'
    if candidate.is_file():
        SHELL = str(candidate)


@unittest.skipUnless(SHELL, 'POSIX shell required')
class ShellWrapperTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        (ROOT/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='shell-wrapper-',dir=ROOT/'build') as temp:
            fixture = Path(temp)
            for relative in ('build_amiga.sh','build_amiga_test.sh','src_amiga/build.sh'):
                target = fixture/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(REPO/relative,target)
                target.chmod(0o755)
            stub = fixture/'Python with spaces'/'python recorder'
            stub.parent.mkdir()
            stub.write_text('#!/bin/sh\nprintf "%s\\0" "$@" __QA_END__ >> "$QA_SHELL_LOG"\nexit "${QA_SHELL_EXIT:-0}"\n',newline='\n')
            stub.chmod(0o755)
            yield fixture,stub

    def run_wrapper(self, fixture, stub, script, arguments=(), exit_code=0):
        log = fixture/'arguments.bin'
        log.unlink(missing_ok=True)
        env = dict(os.environ,QA_SHELL_LOG=log.as_posix(),QA_SHELL_EXIT=str(exit_code))
        arguments = list(arguments)
        if arguments[:1] == ['all']:
            arguments = ['all','--python',stub.as_posix(),*arguments[1:]]
        else:
            arguments = ['--python',stub.as_posix(),*arguments]
        run = subprocess.run([SHELL,(fixture/script).as_posix(),*arguments],
                             cwd=fixture,env=env,capture_output=True,text=True)
        calls = []
        current = []
        if log.exists():
            for argument in log.read_bytes().decode().split('\0')[:-1]:
                if argument == '__QA_END__':
                    calls.append(current)
                    current = []
                else:
                    current.append(argument)
        self.assertFalse(current)
        return run,calls

    @staticmethod
    def option(call,name):
        return [v.split('=',1)[1] for v in call if v.startswith(name+'=')][-1]

    def test_child_preserves_arguments_and_last_display(self):
        with self.fixture() as (fixture,stub):
            arguments = ['outputname=Elite Review','--vasm','/tools/vasm with spaces',
                         '--vlink','/tools/link [ab]*?','literal=$(touch UNEXPECTED)',
                         'quote=" and apostrophe=\'','', 'display=pal','display=ntsc-hires']
            run,calls = self.run_wrapper(fixture,stub,'src_amiga/build.sh',arguments)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][2:],arguments[:-2]+['display=ntsc-hires'])
            self.assertFalse((fixture/'UNEXPECTED').exists())
            run,calls = self.run_wrapper(fixture,stub,'src_amiga/build.sh',['display=bad * value'])
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][-1],'display=bad * value')

    def test_default_displays_and_failure_propagation(self):
        with self.fixture() as (fixture,stub):
            for display in ([],['display=both']):
                run,calls = self.run_wrapper(fixture,stub,'src_amiga/build.sh',display)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertEqual([self.option(c,'display') for c in calls],['pal','ntsc'])
            for script in ('src_amiga/build.sh','build_amiga.sh','build_amiga_test.sh'):
                run,calls = self.run_wrapper(fixture,stub,script,exit_code=23)
                self.assertEqual(run.returncode,23,run.stderr)
                self.assertEqual(len(calls),1)

    def test_root_defaults_and_test_overrides(self):
        with self.fixture() as (fixture,stub):
            for script,test in (('build_amiga.sh',False),('build_amiga_test.sh',True)):
                run,calls = self.run_wrapper(fixture,stub,script)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertEqual([self.option(c,'outputname') for c in calls],['ELITE','ELITE_ALT'])
                self.assertEqual([self.option(c,'commander') for c in calls],['max' if test else 'default']*2)
                run,calls = self.run_wrapper(fixture,stub,script,
                    ['commander=default','outputname=Elite Review','--vasm','assembler path'])
                self.assertEqual(run.returncode,0,run.stderr)
                for call in calls:
                    self.assertEqual(self.option(call,'commander'),'default')
                    self.assertEqual(self.option(call,'outputname'),'Elite Review')
                    self.assertEqual(call[call.index('--vasm')+1],'assembler path')

    def test_release_arguments_and_test_defaults(self):
        with self.fixture() as (fixture,stub):
            for script,test in (('build_amiga.sh',False),('build_amiga_test.sh',True)):
                run,calls = self.run_wrapper(fixture,stub,script,
                    ['all','--vlink','linker with spaces','display=both','outputname=ignored'])
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertEqual(len(calls),18)
                self.assertEqual(len({self.option(c,'outputname') for c in calls}),18)
                for call in calls:
                    self.assertNotEqual(self.option(call,'display'),'both')
                    self.assertNotEqual(self.option(call,'outputname'),'ignored')
                    self.assertEqual(call[call.index('--vlink')+1],'linker with spaces')
                    self.assertEqual(self.option(call,'frametime'),'yes' if test else 'no')
                    self.assertEqual(self.option(call,'commander'),'max' if test else 'default')
                    if self.option(call,'display').startswith('dbl'):
                        self.assertEqual(self.option(call,'cpu'),'68020')
                run,calls = self.run_wrapper(fixture,stub,script,['all'],exit_code=23)
                self.assertEqual(run.returncode,23,run.stderr)
                self.assertEqual(len(calls),1)

    def test_missing_tool_or_interpreter_value(self):
        with self.fixture() as (fixture,stub):
            for flag in ('--python','--vasm','--vlink'):
                for suffix in ([flag],[flag,'']):
                    run,calls = self.run_wrapper(fixture,stub,'src_amiga/build.sh',suffix)
                    self.assertNotEqual(run.returncode,0)
                    self.assertIn('requires a path',run.stderr)
                    self.assertFalse(calls)


if __name__ == '__main__':
    unittest.main()
