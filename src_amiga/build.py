"""Build the independent Elite game as a native, relocatable AmigaOS 1.3 executable."""
import argparse
import sys
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess

# Keep Python import artifacts out of the source and tools directories.
sys.dont_write_bytecode = True

from tools.amiga_assets import extract_assets
from tools.make_adf import make_adf
from tools.amiga_hunk import verify_hunk

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
OUTPUT = ROOT.parent / 'output_amiga/ELITE'
TOOLS = ROOT.parent / 'tools'
FLAGS = ['-m68000', '-no-opt', '-align', '-allmp', '-spaces', '-nocase', '-nowarn=40', '-nowarn=41', '-nowarn=62']
ASSET_NAMES = ('BITMAPS.IMG', 'COCKPIT.PC1', 'TEXTSCR.PC1', 'TEXTURE.PC1', 'DCOS.DAT', 'DSIN.DAT', 'LOGO.PC1', 'TITLE.PC1')


def build_amiga(vasm, vlink, noprotect=False):
    BUILD.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for tool in (vasm, vlink):
        if not tool.is_file():
            raise ValueError('Missing build tool: ' + str(tool))
    boot, audio = extract_assets(ROOT.parent/'resources/amiga/Elite 2.0.adf', BUILD)
    periods = [round(3546895/(32*32.70319566*2**(n/12))) for n in range(72)]
    (BUILD/'amiga-periods.inc').write_text('    dc.w '+','.join(map(str,periods))+'\n')
    def run(command, name):
        result = subprocess.run(list(map(str,command)), cwd=BUILD, capture_output=True, text=True)
        (BUILD/name).write_text(result.stdout+result.stderr)
        if result.returncode:
            raise ValueError(result.stderr[-6000:] or result.stdout[-6000:])
        if re.search(r'^(?:warning|error|fatal error)\s+\d+', result.stdout+result.stderr, re.M | re.I):
            raise ValueError('Unexpected diagnostic; see ' + str(BUILD/name))
        return result.stdout+result.stderr
    def assemble(name, fmt='vobj', output=None):
        output = output or BUILD/(name+'.o')
        run([vasm,*FLAGS,f'-Dnoprotect={int(noprotect)}','-F'+fmt,'-I'+str(BUILD),
             '-I'+str(ROOT/'asm'),'-o',output,ROOT/'asm'/(name+'.m68')], name+'.log')
    modules = (ROOT/'modules.txt').read_text().split()
    modules = ['system', 'fileio', *modules, 'workspace']
    print('Assembling independent native Amiga game modules for MC68000...')
    print('Novella question: ' + ('disabled' if noprotect else 'enabled'))
    for module in modules:
        assemble(module)
    executable = OUTPUT/'ELITE'
    # vlink applies -hunkattr while reading Hunk objects, not VOBJ inputs.
    # The intermediate object preserves section names for Chip RAM allocation.
    combined = BUILD/'linked.hunk'
    run([vlink,'-bamigahunk','-r','-o',combined,
         *(BUILD/(n+'.o') for n in modules)],'object-link.log')
    linkmap = run([vlink,'-bamigahunk','-kick1','-hunkattr','amiga_video=2',
                   '-hunkattr','amiga_copper=2','-hunkattr','amiga_audio=2',
                   '-e','amiga_entry','-M','-o',executable,
                   combined],'elite.map')
    data = executable.read_bytes()
    if data[:4] != struct.pack('>I',1011):
        raise ValueError('Invalid Amiga Hunk header')
    section_names = re.findall(r'^  [0-9a-f]+ (\S+)  \(size ', linkmap, re.M)
    hunks = verify_hunk(data, section_names)
    symbols = {name: int(value, 16) for value, name in
               re.findall(r'^  0x([0-9a-f]+) (\w+): global (?:abs|reloc),', linkmap, re.M)}
    for name, size in symbols.items():
        capacity = name.removesuffix('_used') + '_vsize'
        if name.endswith('_used') and capacity in symbols and size > symbols[capacity]*2:
            raise ValueError('Module variable area overflow: ' + name)
    if symbols['vars'] + symbols['var_size'] != symbols['ram_end']:
        raise ValueError('Invalid game workspace size')
    if (symbols['amiga_primary'] != 0 or symbols['other_screen'] != 32768 or
            hunks['amiga_video']['bytes'] != 65536):
        raise ValueError('Expected exactly two 32 KB native Chip RAM screens')
    assemble('objects','bin',OUTPUT/'OBJECTS.IMG')
    assemble('elitechr','bin',OUTPUT/'ELITECHR.IMG')
    for name in ASSET_NAMES:
        shutil.copyfile(ROOT/'assets'/name, OUTPUT/name)
    capacities = {'TEXTSCR.PC1': ('textscr', 'hyper_buffer'),
                  'TEXTURE.PC1': ('texture', 'obj_data'),
                  'OBJECTS.IMG': ('obj_data', 'logo'),
                  'LOGO.PC1': ('logo', 'dust_cos'),
                  'DCOS.DAT': ('dust_cos', 'dust_sin'),
                  'DSIN.DAT': ('dust_sin', 'cockpit'),
                  'COCKPIT.PC1': ('cockpit', 'vars')}
    for name, (start, end) in capacities.items():
        if (OUTPUT/name).stat().st_size > symbols[end]-symbols[start]:
            raise ValueError('Asset exceeds its workspace buffer: ' + name)
    if (OUTPUT/'TITLE.PC1').stat().st_size > hunks['amiga_video']['bytes']//2:
        raise ValueError('TITLE.PC1 exceeds the secondary screen loading buffer')
    files = {'ELITE': data, 's/startup-sequence': b'ELITE\n'}
    files.update({name:(OUTPUT/name).read_bytes() for name in (*ASSET_NAMES,'OBJECTS.IMG','ELITECHR.IMG')})
    disk = OUTPUT.parent/'ELITE.ADF'
    disk_report = make_adf(files, disk, boot)
    report = {'platform':'amiga','cpu':'MC68000','minimum_kickstart':'1.3',
              'build_options':{'noprotect':noprotect},
              'audio':audio,'disk':disk_report,'runtime_tested':False,
              'hunks':hunks,
              'checks':['MC68000 assembly and linking', 'Hunk relocations and Chip RAM attributes',
                        'Kickstart 1.x BSS limits', 'per-module variable capacities',
                        'asset buffer capacities', 'two native Chip RAM screens',
                        'original sample bank checksum', 'OFS checksums and byte-for-byte readback'],
              'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in (executable,disk)}}
    (BUILD/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Linked native Amiga executable: {len(data):,} bytes.')
    print(f'Validated 880 KB OFS disk: {disk}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vasm', type=Path, default=TOOLS/'vasmm68k_mot.exe')
    parser.add_argument('--vlink', type=Path, default=TOOLS/'vlink.exe')
    parser.add_argument('options', nargs='*', metavar='noprotect=yes|no',
                        help='skip the novella question with noprotect=yes (default: no)')
    args = parser.parse_intermixed_args()
    for option in args.options:
        if option not in ('noprotect=yes', 'noprotect=no'):
            parser.error(f'Unknown build option: {option}; expected noprotect=yes or noprotect=no')
    noprotect = bool(args.options and args.options[-1] == 'noprotect=yes')
    build_amiga(args.vasm.resolve(), args.vlink.resolve(), noprotect)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
