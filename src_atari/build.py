"""Build Atari ST Elite with native Windows vasm and vlink (Python 3.10+)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

from tools.make_disk import make_disk, verify_disk

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT.parent / 'tools'
BUILD = ROOT / 'build'
OUTPUT = ROOT.parent / 'output_atari'
GAME = OUTPUT / 'ELITE'
ORIGIN = 0x12000
LOADER_ORIGIN = 0x11e00
ASSET_NAMES = ('BITMAPS.IMG', 'COCKPIT.PC1', 'TEXTSCR.PC1', 'TEXTURE.PC1',
               'LOGO.PC1', 'TITLE.PC1')
FLAGS = ['-m68000', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
         '-nowarn=40', '-nowarn=41', '-nowarn=62']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log):
    result = subprocess.run([str(arg) for arg in command], cwd=BUILD,
                            capture_output=True, text=True, errors='replace')
    output = result.stdout + result.stderr
    (BUILD / log).write_text(output, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {command[0]}\n{output}')
    # Only the three documented legacy-name/unused-import warnings are suppressed.
    if re.search(r'^(?:warning|error|fatal error)\s+\d+', output, re.M | re.I):
        raise RuntimeError(f'Unexpected assembler diagnostic; see {BUILD / log}\n{output}')
    return output


def symbols(map_text):
    result = {}
    for value, name in re.findall(r'^\s+0x([0-9a-f]+) ([^: ]+):', map_text, re.M):
        value = int(value, 16)
        if name in result and result[name] != value:
            # Module-local names may repeat; the build uses unique globals
            # and shared constants, whose values must agree.
            result[name] = None
        else:
            result[name] = value
    return result


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def relocation_offsets(data, image_size):
    """Decode vlink rawbin -q's bounded byte-distance relocation stream."""
    check(len(data) >= 4, 'Missing relocation table size')
    check(int.from_bytes(data[:4], 'big') == len(data)-4, 'Invalid relocation table size')
    offsets, position, offset = [], 4, 0
    while position < len(data):
        distance = data[position]
        position += 1
        if distance == 0:
            check(position + 4 <= len(data), 'Truncated extended relocation distance')
            distance = int.from_bytes(data[position:position+4], 'big')
            position += 4
        offset += distance
        check(offset % 2 == 0 and offset + 4 <= image_size, 'Relocation outside game code')
        check(not offsets or offset >= offsets[-1]+4, 'Overlapping relocations')
        offsets.append(offset)
    return offsets


def relocate_image(image, offsets, delta):
    result = bytearray(image)
    for offset in offsets:
        value = int.from_bytes(result[offset:offset+4], 'big') + delta
        check(0 <= value <= 0xffffffff, 'Relocated address overflow')
        result[offset:offset+4] = value.to_bytes(4, 'big')
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vasm', type=Path, default=TOOLS / 'vasmm68k_mot.exe')
    parser.add_argument('--vlink', type=Path, default=TOOLS / 'vlink.exe')
    parser.add_argument('options', nargs='*', metavar='OPTION',
                        help='noprotect=yes|no (default: no); commander=max|default '
                             '(default: default, max starts with 1,000,000 Cr); '
                             'laser=dualbeam|singlebeam (default: dualbeam); '
                             'aifiresound=yes|no (default: no); '
                             'scannerlogo=yes|no (default: yes)')
    args = parser.parse_intermixed_args()
    noprotect, commander, laser = False, 'default', 'dualbeam'
    aifiresound = False
    scannerlogo = True
    for option in args.options:
        if option in ('noprotect=yes', 'noprotect=no'):
            noprotect = option == 'noprotect=yes'
        elif option in ('commander=max', 'commander=default'):
            commander = option.split('=', 1)[1]
        elif option in ('laser=dualbeam', 'laser=singlebeam'):
            laser = option.split('=', 1)[1]
        elif option in ('aifiresound=yes', 'aifiresound=no'):
            aifiresound = option == 'aifiresound=yes'
        elif option in ('scannerlogo=yes', 'scannerlogo=no'):
            scannerlogo = option == 'scannerlogo=yes'
        else:
            parser.error(f'Unknown build option: {option}; expected noprotect=yes|no '
                         'or commander=max|default or laser=dualbeam|singlebeam '
                         'or aifiresound=yes|no or scannerlogo=yes|no')
    args.vasm, args.vlink = args.vasm.resolve(), args.vlink.resolve()
    for tool in (args.vasm, args.vlink):
        check(tool.is_file(), f'Tool not found: {tool}. Restore the bundled root tools folder '
              'or rebuild it with src_atari/tools/setup-toolchain.ps1.')
    for directory in (BUILD, OUTPUT, GAME):
        directory.mkdir(parents=True, exist_ok=True)
    modules = (ROOT / 'modules.txt').read_text().split()

    def assemble(name, fmt='vobj', output=None, extra=(), extension='.m68'):
        output = output or BUILD / (name + '.o')
        run([args.vasm, *FLAGS, f'-Dnoprotect={int(noprotect)}',
             f'-Dcommander_max={int(commander == "max")}', f'-Daifiresound={int(aifiresound)}',
             f'-Dscannerlogo={int(scannerlogo)}',
             f'-Dlaser_singlebeam={int(laser == "singlebeam")}', '-F' + fmt, *extra,
             '-I' + str(BUILD), '-I' + str(ROOT / 'asm'),
             '-o', output, ROOT / 'asm' / (name + extension)], name + '.log')

    def link_game(log, output=None, extra=(), script=None):
        return run([args.vlink, '-brawbin1', *extra, '-T', script or ROOT / 'elite.ld', '-M',
                    '-o', output or GAME / 'ELITE.IMG',
                    *(BUILD / (name + '.o') for name in modules + ['workspace'])], log)

    print(f'Assembling {len(modules)} game modules for MC68000...')
    print('Novella question: ' + ('disabled' if noprotect else 'enabled'))
    print('Player laser style: ' + laser)
    print('AI laser firing sound: ' + ('enabled' if aifiresound else 'disabled'))
    print('Scanner ELITE logo: ' + ('shown' if scannerlogo else 'hidden'))
    print('Default commander: ' + ('1,000,000 Cr, Deadly' if commander == 'max' else '100 Cr, Harmless'))
    for name in modules + ['workspace']:
        assemble(name)
    first_map = link_game('elite-pass1.map')
    syms = symbols(first_map)
    first_image = (GAME / 'ELITE.IMG').read_bytes()
    start, end = syms['checksum_start'] - ORIGIN, syms['checksum_end'] - ORIGIN
    check(0 <= start < end <= len(first_image), 'Invalid checksum region')
    checksum = sum(first_image[start:end]) & 0xffff
    assemble('checksum', extra=[f'-Dvalid={checksum}'])
    final_map = link_game('elite.map')
    syms = symbols(final_map)
    image = (GAME / 'ELITE.IMG').read_bytes()
    check(len(image) == len(first_image) and image[start:end] == first_image[start:end],
          'Checksum pass changed the protected region or image size')
    if syms['use_novella']:
        position = syms['checksum_expected'] - ORIGIN
        check(position >= end and image[position:position+2] == b'\x3d\x7c',
              'Unexpected instruction at checksum_expected')
        check(int.from_bytes(image[position+2:position+4], 'big') == checksum,
              'Embedded checksum does not match the linked program')

    check(syms['elite'] == ORIGIN, 'Main entry must stay at $12000')
    check(syms['textscr'] == ORIGIN + len(image), 'Workspace overlaps the program')
    check(syms['other_screen'] % 32768 == 0, 'Second screen must be aligned to 32 KB')
    check(syms['vars'] + syms['var_size'] == syms['ram_end'], 'Invalid variable area')
    check(syms['ram_end'] <= 0x78000, 'Game overlaps the default 512 KB ST screen')
    check(image[syms['initialise']-ORIGIN:syms['initialise']-ORIGIN+6] ==
          b'\x4d\xf9' + syms['vars'].to_bytes(4, 'big'), 'Incorrect workspace relocation')
    for name, size in syms.items():
        if name.endswith('_used') and name[:-5] + '_vsize' in syms:
            check(size <= syms[name[:-5] + '_vsize'] * 2, f'Variable area overflow: {name}')
    check(syms['key_fire'] == ord('A') and syms['key_1'] == ord('1'),
          'Quelo character literal conversion broke keyboard constants')

    print(f'Linked ELITE.IMG: {len(image):,} bytes; checksum ${checksum:04X}.')
    # Keep the on-disk image and its original link addresses. Only the launcher
    # applies a runtime delta, using relocation records emitted by the linker.
    reloc_output = BUILD / 'elite-reloc.bin'
    link_game('elite-reloc.map', reloc_output, extra=['-q'])
    reloc_image = reloc_output.read_bytes()
    reloc_data = reloc_image[len(image):]
    relocs = relocation_offsets(reloc_data, len(image))
    check(relocate_image(reloc_image[:len(image)], relocs, ORIGIN) == image,
          'Relocation records do not reconstruct the fixed-address image')
    (BUILD / 'game-relocations.bin').write_bytes(reloc_data[4:])
    shifted_script = BUILD / 'elite-shifted.ld'
    shifted_script.write_text((ROOT / 'elite.ld').read_text().replace(
        '. = 0x12000;', '. = 0x1a000;', 1))
    shifted_output = BUILD / 'elite-shifted.bin'
    link_game('elite-shifted.map', shifted_output, script=shifted_script)
    check(relocate_image(image, relocs, 0x8000) == shifted_output.read_bytes(),
          'Runtime relocation differs from independently linking at a higher address')

    (BUILD / 'loader-config.inc').write_text(
        f'game_size equ {len(image)}\n'
        f'title_size equ {(ROOT / "assets/TITLE.PC1").stat().st_size}\n', encoding='ascii')
    assemble('loader')
    loader_map = run([args.vlink, '-brawbin1', '-Ttext', hex(LOADER_ORIGIN), '-M',
                      '-o', GAME / 'LOADER.IMG', BUILD / 'loader.o'], 'loader.map')
    loader_size = (GAME / 'LOADER.IMG').stat().st_size
    check(symbols(loader_map)['main'] == LOADER_ORIGIN, 'Incorrect loader entry address')
    check(0 < loader_size <= ORIGIN - LOADER_ORIGIN, 'Loader overlaps main program')
    loader_shifted = BUILD / 'loader-shifted.bin'
    run([args.vlink, '-brawbin1', '-Ttext', hex(LOADER_ORIGIN + 0x8000),
         '-o', loader_shifted, BUILD / 'loader.o'], 'loader-shifted.log')
    check(loader_shifted.read_bytes() == (GAME / 'LOADER.IMG').read_bytes(),
          'Loader is not position-independent')
    (BUILD / 'boot-config.inc').write_text(
        f'loader_address equ ${LOADER_ORIGIN:x}\nloader_size equ {loader_size}\n'
        f'game_address equ ${ORIGIN:x}\ngame_size equ {len(image)}\n'
        f'required_ram equ ${syms["ram_end"]:x}\n'
        f'patch_checksum equ {int(bool(syms["use_novella"]))}\n'
        f'checksum_start_offset equ {start}\nchecksum_length equ {end-start}\n'
        f'checksum_patch_offset equ {syms.get("checksum_expected", ORIGIN)-ORIGIN+2}\n',
        encoding='ascii')
    assemble('boot', 'tos', GAME / 'ELITE.TOS', extra=['-nosym'], extension='.s')
    auto_program = BUILD / 'ELITE.PRG'
    assemble('boot', 'tos', auto_program, extra=['-nosym', '-Dauto_start=1'], extension='.s')
    tos = (GAME / 'ELITE.TOS').read_bytes()
    check(tos[:2] == b'\x60\x1a', 'Invalid TOS executable header')
    text_size, data_size, bss_size, symbol_size = struct.unpack_from('>4I', tos, 2)
    check(text_size > 0 and len(tos) >= 28 + text_size + data_size + symbol_size,
          'Truncated TOS executable')
    check(struct.unpack_from('>I', tos, 22)[0] & 2 == 0,
          'Launcher must load into ST RAM, not alternative RAM')

    assemble('objects', 'bin', GAME / 'OBJECTS.IMG')
    assemble('elitechr', 'bin', GAME / 'ELITECHR.IMG')
    for name in ASSET_NAMES:
        shutil.copyfile(ROOT / 'assets' / name, GAME / name)
    # The depth-based starfield no longer loads direction lookup files.
    for name in ('DCOS.DAT', 'DSIN.DAT'):
        (GAME / name).unlink(missing_ok=True)
    # Each buffer length follows the absolute layout in elite.ld.
    capacities = {'TEXTSCR.PC1': syms['hyper_buffer']-syms['textscr'],
                  'TEXTURE.PC1': syms['obj_data']-syms['texture'],
                  'OBJECTS.IMG': syms['logo']-syms['obj_data'],
                  'LOGO.PC1': syms['cockpit']-syms['logo'],
                  'COCKPIT.PC1': syms['vars']-syms['cockpit']}
    for name, capacity in capacities.items():
        check((GAME / name).stat().st_size <= capacity, f'{name} exceeds its reserved buffer')

    names = (*ASSET_NAMES, 'ELITE.IMG', 'LOADER.IMG', 'ELITE.TOS', 'OBJECTS.IMG', 'ELITECHR.IMG')
    files = [GAME / name for name in names]
    disk = OUTPUT / 'ELITE.ST'
    make_disk(files, disk, auto_program=auto_program)
    verify_disk(disk, files, auto_program=auto_program)
    baseline = json.loads((ROOT / 'original-sha256.json').read_text())
    report = {
        'cpu': 'MC68000', 'game_modules': len(modules), 'checksum': f'{checksum:04X}',
        'build_options': {'noprotect': noprotect, 'commander': commander, 'laser': laser, 'aifiresound': aifiresound, 'scannerlogo': scannerlogo},
        'entry': f'{ORIGIN:08X}', 'loader_entry': f'{LOADER_ORIGIN:08X}',
        'other_screen': f'{syms["other_screen"]:08X}', 'vars': f'{syms["vars"]:08X}',
        'ram_end': f'{syms["ram_end"]:08X}',
        'runtime_relocation': {'step': 32768, 'records': len(relocs),
                               'table_bytes': len(reloc_data)-4,
                               'workspace_bytes': syms['ram_end']-LOADER_ORIGIN,
                               'startup_stack_bytes': 4096},
        'byte_identical_to_original': {name: digest(GAME / name) == baseline[name]
                                       for name in ('OBJECTS.IMG', 'ELITECHR.IMG', *ASSET_NAMES)},
        'artifacts': {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
                      for path in [*files, disk]},
        'checks': ['all modules assembled', 'all symbols linked', 'checksum embedded and verified',
                   'workspace relocation and RAM limits', 'per-module variable capacities',
                   'keyboard ASCII constants', 'asset buffer capacities', 'TOS header',
                   'runtime relocation matches independent higher-address link',
                   'position-independent loader and ST-RAM executable flags',
                   'FAT12 image read back byte-for-byte, including AUTO/ELITE.PRG'],
        'autostart': {'path': 'AUTO/ELITE.PRG', 'sha256': digest(auto_program)},
        'runtime_tested': False,
    }
    (BUILD / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Validated TOS launcher, RAM layout and 720 KB FAT12 disk: {disk}')
    print('Floppy autostart: AUTO/ELITE.PRG (game data in the disk root)')
    print(f'Distribution: {GAME}')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f'Build failed: {exc}', file=sys.stderr)
        sys.exit(1)
