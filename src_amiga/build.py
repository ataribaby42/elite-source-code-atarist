"""Build the independent Elite game as a native, relocatable AmigaOS 1.3 executable."""
import argparse
import os
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
from tools.gfx_assets import compile_assets
from tools.beam_audio import generate_beam_audio
from tools.rcs_audio import generate_rcs_audio
from tools.engine_audio import generate_engine_audio
from tools.bomb_audio import generate_bomb_audio
from tools.make_adf import make_adf
from tools.amiga_hunk import verify_hunk

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
OUTPUT = ROOT.parent / 'output_amiga'
TOOLS = ROOT.parent / 'tools'
FLAGS = ['-no-opt', '-align', '-allmp', '-spaces', '-nocase', '-nowarn=40', '-nowarn=41', '-nowarn=62']
ASSET_NAMES = ('BITMAPS.IMG', 'COCKPIT.PC1', 'TEXTSCR.PC1', 'TEXTURE.PC1', 'LOGO.PC1', 'TITLE.PC1', 'ELITE.info')
# display option: the assembler switches that differ from the defaults below,
# and the line the build prints.
DISPLAY_DEFAULTS = {'ntsc': 0, 'hires': 0, 'lace': 0, 'double': 0}
DISPLAYS = {
    'pal':            ({}, 'PAL, 320 x 256'),
    'ntsc':           ({'ntsc': 1}, 'NTSC, 320 x 200'),
    'pal-hires':      ({'hires': 1}, 'PAL hires, 640 x 256'),
    'pal-hireslace':  ({'hires': 1, 'lace': 1}, 'PAL hires interlaced, 640 x 512'),
    'ntsc-hires':     ({'ntsc': 1, 'hires': 1}, 'NTSC hires, 640 x 200'),
    'ntsc-hireslace': ({'ntsc': 1, 'hires': 1, 'lace': 1}, 'NTSC hires interlaced, 640 x 400'),
    'dblpal-hires':   ({'hires': 1, 'double': 1},
                       'DblPAL, 640 x 512, AGA super-hires'),
}
DISPLAYS['hires'] = DISPLAYS['pal-hires']              # PAL spellings
DISPLAYS['hireslace'] = DISPLAYS['pal-hireslace']


def bundled_tool(name, variable):
    """The tool in tools/ for this platform, an override, or the first one on PATH."""
    override = os.environ.get(variable)
    if override:
        return Path(override)
    bundled = TOOLS / (name + '.exe' if os.name == 'nt' else name)
    if bundled.is_file():
        return bundled
    found = shutil.which(name)
    return Path(found) if found else bundled


def validate_outputname(name):
    """Require a single Windows filename so outputs stay in their target tree."""
    if (not name or name.endswith((' ', '.')) or
            re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or
            re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]|CONIN\$|CONOUT\$',
                         name.split('.', 1)[0].rstrip(), re.I)):
        raise ValueError('outputname must be a non-empty Windows filename without a path, '
                         'reserved device name, trailing space or trailing dot')
    return name


def build_amiga(vasm, vlink, noprotect=False, commander='default', laser='dualbeam', aifiresound=False, scannerlogo=True, altgfx=False, outputname='ELITE', display='pal', cpu='68000', frame=True, frametime=False, fastdraw=False, shadowcopy='changes'):
    options, display_name = DISPLAYS[display]
    options = {**DISPLAY_DEFAULTS, **options}
    ntsc, hires, lace = options['ntsc'], options['hires'], options['lace']
    double = options['double']
    tall = lace+double
    game = OUTPUT / validate_outputname(outputname)
    BUILD.mkdir(parents=True, exist_ok=True)
    game.mkdir(parents=True, exist_ok=True)
    for tool in (vasm, vlink):
        if not tool.is_file():
            raise ValueError('Missing build tool: ' + str(tool))
    print(f'Assembler: {vasm}')
    print(f'Linker: {vlink}')
    graphics = compile_assets(ROOT, altgfx=altgfx, zoom_x=1+hires, zoom_y=1+tall, build=BUILD, frame=frame)
    print(f'Compiled editable PNG graphics from {"gfx_alt" if altgfx else "gfx"}/ into assets/.')
    print(f'Cockpit artwork: {"cockpit.png" if frame else "cockpit_noframe.png"}')
    boot, audio = extract_assets(ROOT.parent/'resources/amiga/Elite 2.0.adf', BUILD)
    audio['continuous_lasers'] = generate_beam_audio(BUILD)
    audio['rcs'] = generate_rcs_audio(BUILD)
    audio['engine'] = generate_engine_audio(BUILD)
    audio['energy_bomb'] = generate_bomb_audio(BUILD)
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
        run([vasm,'-m'+cpu,*FLAGS,f'-Dnoprotect={int(noprotect)}',f'-Dcpu_68020={int(cpu == "68020")}',
             f'-Dcommander_max={int(commander == "max")}', f'-Daifiresound={int(aifiresound)}',
             f'-Dscannerlogo={int(scannerlogo)}',
             *(f'-Ddisplay_{name}={value}' for name, value in options.items()),
             f'-Dframe={int(frame)}', f'-Dframetime={int(frametime)}',
             f'-Dfastdraw={int(fastdraw)}', f'-Dshadow_every={int(shadowcopy == "all")}',
             f'-Dshadow_count={int(shadowcopy == "counter")}',
             f'-Dlaser_singlebeam={int(laser == "singlebeam")}','-F'+fmt,'-I'+str(BUILD),
             '-I'+str(ROOT/'asm'),'-I'+str(ROOT/'assets'),'-o',output,ROOT/'asm'/(name+'.m68')], name+'.log')
    modules = (ROOT/'modules.txt').read_text().split()
    modules = ['system', 'fileio', *modules, 'workspace']
    print('Assembling independent native Amiga game modules for MC68000...')
    print('Novella question: ' + ('disabled' if noprotect else 'enabled'))
    print('Player laser style: ' + laser)
    print('AI laser firing sound: ' + ('enabled' if aifiresound else 'disabled'))
    print('Scanner ELITE logo: ' + ('shown' if scannerlogo else 'hidden'))
    rows = (200 if ntsc or frame else 256)*(1+tall)
    print('Display: ' + (f'{"NTSC" if ntsc else "PAL"}{" hires" if hires else ""}'
                         f'{" interlaced" if lace else ""}{" doubled" if double else ""},'
                         f' {640 if hires else 320} x {rows},'
                         f' framed {256*(1+hires)} x {112*(1+tall)} view' if frame else display_name))
    print('CPU: ' + ('MC68020 or better, native 32-bit maths only' if cpu == '68020'
                     else 'MC68000, with the native 32-bit maths patched in where it exists'))
    if frametime:
        print('Frame time: shown in the top left corner')
    if fastdraw:
        print('Flight view: Fast RAM or the blitter, whichever the machine has')
        if shadowcopy == 'all':
            print('Shadow transfer: every piece, every frame, for comparison')
        elif shadowcopy == 'counter':
            print('Shadow transfer: the changes, counted on the frame time line')
    print('Default commander: ' + ('1,000,000 Cr, Deadly' if commander == 'max' else '100 Cr, Harmless'))
    for module in modules:
        assemble(module)
    executable = game/'ELITE'
    # vlink applies -hunkattr while reading Hunk objects, not VOBJ inputs.
    # The intermediate object preserves section names for Chip RAM allocation.
    combined = BUILD/'linked.hunk'
    run([vlink,'-bamigahunk','-r','-o',combined,
         *(BUILD/(n+'.o') for n in modules)],'object-link.log')
    linkmap = run([vlink,'-bamigahunk','-kick1','-hunkattr','amiga_video=2',
                   '-hunkattr','amiga_video2=2',
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
    # The generated pictures own a complete BSS Hunk, never a borrowed UI buffer.
    if (symbols['ship_graphics_begin'] != 0 or
            symbols['ship_graphics_end'] != hunks['ship_graphics']['bytes']):
        raise ValueError('Generated ship images do not own their complete Hunk')
    for start, end, size in (('ship_yard_atlas', 'ship_yard_end', 13*1644),
                             ('ship_status_image', 'ship_status_end', 4084),
                             ('ship_planet_image', 'ship_planet_end', 904)):
        if symbols[end]-symbols[start] != size:
            raise ValueError('Invalid generated ship image capacity: ' + start)
    # A programmed-beam mode allocates its screens after checking the machine.
    if 'amiga_video' in hunks:
        screen = hunks['amiga_video']['bytes']
        if screen % 4 or hunks['amiga_video2']['bytes'] != screen:
            raise ValueError('Expected exactly two equal native Chip RAM screens')
    assemble('objects','bin',game/'OBJECTS.IMG')
    assemble('elitechr','bin',game/'ELITECHR.IMG')
    for name in ASSET_NAMES:
        shutil.copyfile(ROOT/'assets'/name, game/name)
    # The depth-based starfield no longer loads direction lookup files.
    for name in ('DCOS.DAT', 'DSIN.DAT'):
        (game / name).unlink(missing_ok=True)
    capacities = {'TEXTSCR.PC1': ('textscr', 'hyper_buffer'),
                  'TEXTURE.PC1': ('texture', 'obj_data'),
                  'OBJECTS.IMG': ('obj_data', 'logo'),
                  'LOGO.PC1': ('logo', 'cockpit'),
                  'COCKPIT.PC1': ('cockpit', 'vars')}
    for name, (start, end) in capacities.items():
        if (game/name).stat().st_size > symbols[end]-symbols[start]:
            raise ValueError('Asset exceeds its workspace buffer: ' + name)
    if (game/'TITLE.PC1').stat().st_size > symbols['bitmap_bytes']:
        raise ValueError('TITLE.PC1 exceeds the bitmap bank it is loaded into')
    # The loader expands every source column to a mask plus four planes at display scale.
    bank = (game/'BITMAPS.IMG').read_bytes()
    entries = struct.unpack('>I', bank[:4])[0]//4
    table = struct.unpack_from('>'+str(entries)+'I', bank)
    offsets = sorted(set(table)-{0})
    if entries != 125 or len(offsets) != 124 or table[54] != 0:
        raise ValueError('Bitmap table must retain 125 IDs and omit only the PNG Cobra')
    columns = sum(width*depth for width, depth in
                  (struct.unpack('>HH', bank[o:o+4]) for o in offsets))
    zoom = (1 + hires)*(1 + tall)
    if entries*4 + len(offsets)*4 + columns*10*zoom > symbols['bitmap_bytes']:
        raise ValueError('Expanded BITMAPS.IMG exceeds its bitmap bank')
    files = {'ELITE': data, 's/startup-sequence': b'ELITE\n'}
    files.update({name:(game/name).read_bytes() for name in (*ASSET_NAMES,'OBJECTS.IMG','ELITECHR.IMG')})
    disk = OUTPUT/(game.name+'.ADF')
    disk_report = make_adf(files, disk, boot)
    report = {'platform':'amiga','cpu':'MC' + cpu,'minimum_kickstart':'1.3',
              'png_graphics':graphics,
              'build_options':{'cpu':cpu,'noprotect':noprotect,'commander':commander,'laser':laser,'aifiresound':aifiresound,'scannerlogo':scannerlogo,'altgfx':altgfx,'outputname':outputname,'display':display,'frame':frame,'frametime':frametime,'fastdraw':fastdraw,'shadowcopy':shadowcopy},
              'output_paths':{'directory':str(game),'disk':str(disk)},
              'audio':audio,'disk':disk_report,'runtime_tested':False,
              'hunks':hunks,
              'checks':['MC68000 assembly and linking', 'Hunk relocations and Chip RAM attributes',
                        'Kickstart 1.x BSS limits', 'per-module variable capacities',
                        'asset buffer capacities', 'expanded bitmap bank capacity',
                        'two native Chip RAM screens',
                   'original effect and music assets; instrument loop bounds',
                   'OFS checksums and byte-for-byte readback'],
              'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in (executable,disk)}}
    (BUILD/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Linked native Amiga executable: {len(data):,} bytes.')
    print(f'Validated 880 KB OFS disk: {disk}')
    print(f'Distribution: {game}')


def read_options(parser, words):
    """The option words of one build, as keyword arguments for build_amiga."""
    settings = {'noprotect': False, 'commander': 'default', 'laser': 'dualbeam',
                'aifiresound': False, 'scannerlogo': True, 'altgfx': False,
                'outputname': 'ELITE', 'display': 'pal', 'cpu': '68000', 'frame': True,
                'frametime': False, 'fastdraw': False, 'shadowcopy': 'changes'}
    for option in words:
        if option in ('noprotect=yes', 'noprotect=no'):
            settings['noprotect'] = option == 'noprotect=yes'
        elif option in ('commander=max', 'commander=default'):
            settings['commander'] = option.split('=', 1)[1]
        elif option in ('laser=dualbeam', 'laser=singlebeam'):
            settings['laser'] = option.split('=', 1)[1]
        elif option in ('aifiresound=yes', 'aifiresound=no'):
            settings['aifiresound'] = option == 'aifiresound=yes'
        elif option in ('scannerlogo=yes', 'scannerlogo=no'):
            settings['scannerlogo'] = option == 'scannerlogo=yes'
        elif option in ('altgfx=yes', 'altgfx=no'):
            settings['altgfx'] = option == 'altgfx=yes'
        elif option.startswith('outputname='):
            settings['outputname'] = option.split('=', 1)[1]
        elif option in ('cpu=68000', 'cpu=68020'):
            settings['cpu'] = option.split('=', 1)[1]
        elif option in ('frame=yes', 'frame=no'):
            settings['frame'] = option == 'frame=yes'
        elif option in ('frametime=yes', 'frametime=no'):
            settings['frametime'] = option == 'frametime=yes'
        elif option in ('fastdraw=yes', 'fastdraw=no'):
            settings['fastdraw'] = option == 'fastdraw=yes'
        elif option in ('shadowcopy=changes', 'shadowcopy=counter', 'shadowcopy=all'):
            settings['shadowcopy'] = option.split('=', 1)[1]
        elif option.startswith('display=') and option.split('=', 1)[1] in DISPLAYS:
            settings['display'] = option.split('=', 1)[1]
        else:
            parser.error(f'Unknown build option: {option}; expected noprotect=yes|no '
                         'or commander=max|default or laser=dualbeam|singlebeam '
                         'or aifiresound=yes|no or scannerlogo=yes|no or altgfx=yes|no '
                         'or outputname=NAME or frame=yes|no or frametime=yes|no or fastdraw=yes|no '
                         'or shadowcopy=changes|counter|all '
                         'or display=' + '|'.join(DISPLAYS))
    try:
        validate_outputname(settings['outputname'])
    except ValueError as error:
        parser.error(str(error))
    return settings


def main():
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10 or later is required')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vasm', '-Vasm', type=Path,
                        default=bundled_tool('vasmm68k_mot', 'ELITE_VASM'))
    parser.add_argument('--vlink', '-Vlink', type=Path,
                        default=bundled_tool('vlink', 'ELITE_VLINK'))
    # The wrappers read -Python to choose an interpreter; it never reaches a build.
    parser.add_argument('-Python', dest='interpreter', help=argparse.SUPPRESS)
    parser.add_argument('options', nargs='*', metavar='OPTION',
                        help='noprotect=yes|no (default: no); commander=max|default '
                             '(default: default, max starts with 1,000,000 Cr); '
                             'laser=dualbeam|singlebeam (default: dualbeam); '
                             'aifiresound=yes|no (default: no); '
                             'scannerlogo=yes|no (default: yes); '
                             'altgfx=yes|no (default: no); '
                             'outputname=NAME (default: ELITE); '
                             'cpu=68000|68020 (default: 68000); '
                             'frame=yes|no (default: yes, the original cockpit frame); '
                             'frametime=yes|no (default: no, measures the game frame); '
                             'fastdraw=yes|no (default: no, Fast RAM or the blitter for the flight view); '
                             'shadowcopy=changes|counter|all (default: changes; counter shows how many pieces '
                             'cross with frametime=yes, all carries every piece); '
                             'display=' + '|'.join(DISPLAYS) + ' (default: pal, 320 x 256)')
    args = parser.parse_intermixed_args()
    build_amiga(args.vasm.resolve(), args.vlink.resolve(),
                **read_options(parser, args.options))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
