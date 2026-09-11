"""Headless Hatari diagnostic run; all output stays in src_atari/build/hatari-test."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--hatari', required=True, type=Path, help='Path to a separately installed Windows Hatari executable')
parser.add_argument('--rom', required=True, type=Path)
parser.add_argument('--floppy', action='store_true')
parser.add_argument('--vbls', type=int, default=2000)
args = parser.parse_args()
for path in (args.hatari, args.rom):
    if not path.is_file():
        parser.error(f'File not found: {path}')
out = ROOT / 'build/hatari-test' / ('floppy' if args.floppy else 'harddrive')
out.mkdir(parents=True, exist_ok=True)
(out / 'start.ini').write_text('b GemdosOpcode = $4b && OsCallParam = 0 :trace :once :file program.ini\n')
(out / 'program.ini').write_text('b pc = TEXT :trace :once :file entry.ini\n')
(out / 'entry.ini').write_text('info basepage\nr\n'
    'b GemdosOpcode = 7 :trace :once :file stop.ini\n'
    f'b VBL = "VBL+{args.vbls//2}" :trace :once :file stop.ini\n')
(out / 'stop.ini').write_text('r\nscreenshot screen.png\nquit\n')
env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
# Hatari falls back to cwd when no home is supplied. Isolate its settings and
# NVRAM in this run's output directory without changing the parent environment.
for name in ('HOME', 'HOMEDRIVE', 'HOMEPATH'):
    env.pop(name, None)
exe = args.hatari.resolve()
command = [str(exe), '--tos', str(args.rom.resolve()), '--machine', 'st', '--memsize', '1',
    '--monitor', 'rgb', '--tos-res', 'low', '--sound', 'off', '--confirm-quit', 'no',
    '--fast-forward', 'yes', '--fast-boot', 'yes', '--fastfdc', 'yes',
    '--protect-floppy', 'on', '--protect-hd', 'on',
    '--run-vbls', str(args.vbls), '--parse', str(out / 'start.ini'),
    '--trace', 'gemdos', '--trace-file', str(out / 'gemdos.log'),
    '--log-file', str(out / 'hatari.log'), '--screenshot-dir', str(out)]
# Floppy startup must use TOS's real AUTO scan, not Hatari's desktop autorun.
if not args.floppy:
    command += ['--auto', 'C:\\ELITE.TOS']
command += ['--disk-a', str(ROOT.parent / 'output_atari/ELITE.ST')] if args.floppy else ['--harddrive', str(ROOT.parent / 'output_atari/ELITE')]
result = subprocess.run(command, cwd=out, env=env, capture_output=True, text=True,
    creationflags=subprocess.CREATE_NO_WINDOW, timeout=55)
(out / 'console.log').write_text(result.stdout + result.stderr)
print('Hatari exit:', result.returncode)
print((result.stdout + result.stderr)[-11000:])
sys.exit(result.returncode)
