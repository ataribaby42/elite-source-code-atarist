# Elite Atari ST

Buildable Elite sources for the **MC68000**: the enhanced Atari ST version in `src_atari`, a separate native Amiga port in `src_amiga`, and the preserved original Atari ST version in `src_orig`. All three use **vasm 2.0f and vlink 0.18a** with independent source trees and build scripts. The untouched historical sources remain in `resources/elite_atarist_source.zip`; no build uses the old `.LTX` object files.

Both enhanced versions offer 13 player hulls through **Ships / Shipyards**, with
ship-specific flight limits, cargo capacity and equipment prices. **Equip** has
Buy / Sell controls for preparing a hull exchange. See the
[shipyards rules and balance table](docs/2026-09-24-player-shipyards.md).
Status shows **Equipment** mass and **Spare** cargo capacity in tonnes, including
the space used by mounted lasers and installed devices.

During flight, double-click a cargo item on **Inventory** to jettison up to **1 t** (or the entire smaller remainder), after YES/NO confirmation. Tonne, kilogram and gram commodities qualify, including Alien Items and Medical Supplies; mission cargo remains excluded. The canister retains its original commodity and exact mass in grams for scooping. Successful dumping in the station protection zone adds 15 legal-status points, except under Anarchy. See the [jettison notes](src_atari/JETTISON.md) for details shared by both enhanced versions.

Ordinary salvaged cargo yields **1 t**, **1–10 kg**, or **1–10 g** per container, according to the commodity's market unit and available hold space, on both Atari ST and Amiga. Player-ejected containers retain their exact original contents.

Cargo canisters released by destroyed AI ships drift at a random **3–6 world units per movement step**, matching player-ejected canisters. Each canister's maximum speed is set to its initial speed, so it does not accelerate later.

Random Viper patrols check the player's legal record on first contact and when
it changes, using the existing police-response probability. A successful check
makes an Offender or Fugitive a possible target; nearer pirates and aliens
still take priority. Station-launched police retain their existing behaviour.
See [patrol police-record checks](docs/2026-09-20-patrol-police-record-checks.md).

With **Reverse dive/climb** off (the default), moving the mouse up dives and
moving it down climbs in both enhanced versions. Turn this option on to restore
the previous mouse pitch direction.

## Building on Windows

You need **Windows x64 and Python 3.10 or later**, plus the **Pillow** Python library to convert the enhanced Atari and Amiga PNG graphics into binary game assets. The preserved original build needs no additional Python packages. The **vasm 2.0f assembler** (`vasmm68k_mot.exe`, MC68000 with Motorola syntax) and **vlink 0.18a linker** (`vlink.exe`) are bundled as compiled Windows executables in [tools](tools/README.md). A normal build requires no Visual Studio installation, assembler PATH configuration, or additional tool downloads.

Install Pillow once from Windows PowerShell or Command Prompt:

```powershell
python -m pip install Pillow
```

If Python is available through the Windows Python launcher instead of the `python` command, use `py -3 -m pip install Pillow`. Install Pillow into the same Python environment that runs the build. If you pass a custom `-Python` path to the build script, use that executable to install Pillow as well; for example, in PowerShell:

```powershell
& "C:\path\python.exe" -m pip install Pillow
```

Run this from the project root:

```powershell
.\build_atari.bat
```

On Linux, `build_amiga.sh` builds the Amiga version instead. It needs Python 3.10+ and runs the bundled native Linux assembler and linker, which produce the same game files as the Windows pair. With no display named it builds PAL then NTSC; naming one builds only that. Each build is named by its `outputname` and nothing else.

```sh
./build_amiga.sh              # ELITE.ADF, named by outputname
./build_amiga.sh display=ntsc
./build_amiga.sh all          # every delivered image, one call each
```

The enhanced Atari, Amiga and preserved original builds have independent source trees and entry points. No platform option is used.

```powershell
.\build_atari.bat
.\build_amiga.bat
.\build_orig.bat
```

`build_orig.bat` builds the preserved original Atari ST game into `output_orig/ELITE` and `output_orig/ELITE.ST`. Run `ELITE.TOS` from its folder on a floppy or hard drive. It retains the original projectile weapons, starfield, controls, sounds, graphics, 100 Cr / Harmless commander and novella question. It accepts tool-path overrides, but no enhanced gameplay build options. See [original-version build notes](src_orig/README.md). The options below apply to the enhanced Atari and Amiga versions.

To skip the novella protection question at startup, add `noprotect=yes`:

```powershell
.\build_atari.bat noprotect=yes
.\build_amiga.bat noprotect=yes
```

The Python builds default to `noprotect=no`, which keeps the question enabled. Each build applies the selected option to its own output files; it is not a runtime setting. Other game protection checks remain unchanged.

Use `commander=max` to give the default Jameson commander **1,000,000 Cr** and the **Deadly** rating at the start of a new game or after resetting the game. His score starts at the Deadly threshold (`$A0000`):

```powershell
.\build_atari.bat commander=max
.\build_amiga.bat commander=max
```

`commander=default` restores the original **100 Cr**, **Harmless** rating and zero score. Loading a saved commander uses the balance, score and rating stored in that save. The Python builds default to `commander=default`.

The root build scripts currently supply `noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no altgfx=yes` as persistent defaults. `display=` selects one of six Amiga screens and `frame=yes` keeps the cockpit frame. Command-line arguments override these defaults independently: the last occurrence of each option wins. For example, `build_amiga.bat noprotect=no commander=default` enables the novella question and restores the original starting balance.

Player lasers default to `laser=dualbeam`: two filled beams converge
from the lower left and right on the jittering crosshair tip. Use
`laser=singlebeam` for one narrow filled beam from the bottom centre:

```powershell
.\build_atari.bat laser=singlebeam
.\build_amiga.bat laser=singlebeam
```

`laser=dualbeam` explicitly restores the default style. Both options preserve
cosmetic jitter, fixed crosshair targeting, shot timing and damage. They change
player laser graphics only. Player colours come from the existing palette:
Pulse red, Beam orange, Military white, and Mining the same magenta as the
instrument bars. Normal AI beam colours use the player's rating recorded on
station launch or completion of a hyperspace or galactic jump: Harmless through
Poor is red, Average through Competent orange, and Dangerous through Elite white.
That colour stays fixed throughout the flight, even if the player's rating rises;
it is refreshed on the next launch or jump, including entry into witch space.
Constrictor beams are always white; Thargoid and Thargon (Tharglet) beams
are always light blue. AI damage and the distance-dependent random miss chance
remain unchanged.

Player Beam and Military lasers have distinct continuous sounds while firing,
with short attack and release ramps. Amiga uses new synthesized sample loops;
Atari ST uses its native PSG. Pulse and Mining keep their original firing sounds.

AI laser firing sounds are disabled by default (`aifiresound=no`). Enable them
with:

```powershell
.\build_atari.bat aifiresound=yes
.\build_amiga.bat aifiresound=yes
```

`aifiresound=no` explicitly disables them again. This option controls AI laser
shot sounds only. Impact sounds, player firing sounds, missile alerts and other
effects retain their existing handling. Enabled AI firing sounds still follow
the game's Effects setting.

The ELITE caption below the scanner is shown by default (`scannerlogo=yes`).
Hide it in either build with:

```powershell
.\build_atari.bat scannerlogo=no
.\build_amiga.bat scannerlogo=no
```

`scannerlogo=yes` shows it again. This build option changes only the caption
below the scanner; it leaves the scanner, instruments and other logos intact.

Use `outputname=NAME` to name the distribution directory and floppy image.
The default is `outputname=ELITE`. For example:

```powershell
.\build_atari.bat outputname=ELITE_ALT altgfx=yes
.\build_amiga.bat outputname=ELITE_ALT altgfx=yes
```

These commands create `output_atari/ELITE_ALT/` and `output_atari/ELITE_ALT.ST`,
or `output_amiga/ELITE_ALT/` and `output_amiga/ELITE_ALT.ADF`. Each name keeps its
own distribution; rebuilding a name updates that distribution. On the Amiga the
name is the whole name: nothing is appended to it, so two builds that share an
`outputname` overwrite each other, so `all` gives every call a name of its own.
Executable and
data filenames inside it stay unchanged, including `ELITE.TOS`, `ELITE`,
`ELITE.info` and the disk startup files. Build intermediates, generated `assets/`
and `build/verification.json` remain shared within each platform's source tree.
The report records `build_options.outputname` and both selected `output_paths`.

Supply a valid Windows filename without a directory path or disk-image suffix;
the build adds `.ST` or `.ADF`. Quote an argument containing spaces, for example
`"outputname=Elite Alternate"`. Empty names, path separators, reserved device
names and names ending in a dot or space are rejected before building.

If the script cannot find Python, provide its path:

```powershell
.\build_atari.bat -Python "C:\path\python.exe"
```

[build_atari.bat](build_atari.bat) calls [src_atari/build.bat](src_atari/build.bat) and forwards all command-line arguments. Add persistent default options directly to the root script's `call` line, before `%*`. Use `-Vasm` and `-Vlink` to select custom assembler and linker executables. Unrecognized build arguments are rejected.

Alternatively, run `python src_atari/build.py` directly. The scripts resolve project paths relative to their own location, so you can also invoke the build from another working directory.

## Editing PNG graphics

Edit the source PNGs in `src_atari/gfx/` or `src_amiga/gfx/`. Each normal
build uses Pillow to convert its own PNGs into binary files in its `assets/`
directory before assembly. Keep the original canvas dimensions.

The build option `altgfx=yes|no` selects the source set. The Python builds default
to `altgfx=no`, which uses `gfx/`; the root script defaults above also apply.
To use `src_atari/gfx_alt/` or
`src_amiga/gfx_alt/` instead, run:

```powershell
.\build_atari.bat altgfx=yes
.\build_amiga.bat altgfx=yes
```

Each `gfx_alt/` directory must contain the PNGs required by its platform and
selected cockpit mode, plus `layout.json`; missing files cause a build error.
Amiga also uses `font16.png` for its wider font and `cockpit_noframe.png` for
`frame=no`. Use `altgfx=no` to switch back. Both choices
generate the same asset filenames and distribution paths, so the next build
replaces the previous selection's outputs.

**RGB, RGBA and indexed PNGs are supported. Colours are matched by their exact
RGB values, regardless of PNG palette order or storage indices.** `cockpit.png`
uses the cockpit palette. `textscr.png`, `cargo.png`, `equipment.png`,
`gadgets.png`, `panels.png`, `characters.png` and `font.png` use the UI base
palette. Selection is automatic in both `gfx/` and `gfx_alt/`:

| Game index | UI PNG colour | Cockpit PNG colour | Meaning |
| --- | --- | --- | --- |
| 0 | `#00FFFF` | `#00FFFF` | Transparent in ordinary sprites |
| 6 | `#FF0000` | `#DB0000` | Red |
| 8 | `#6DB600` | `#6DB600` | Original ST green |
| 13 | `#000000` | `#000000` | Opaque black |
| 14 | `#6D4900` | `#FF0000` | UI base brown / cockpit pulse marker |

Compared with the former shared editing palette, UI indices 6, 8 and 14 change
from `#DB0000`, `#66AA00` and `#FF0000` to `#FF0000`, `#6DB600` and `#6D4900`.
Only index 8 changes in cockpit PNGs. In particular, `#FF0000` maps to index 6
in UI PNGs and index 14 in `cockpit.png`.

The original hardware palettes and game pixel indices remain unchanged. Cyan 0
and the cockpit pulse marker distinguish otherwise ambiguous black entries;
index 0 displays black in full-screen images. Shared sprites use the active
screen palette, and runtime colour cycling still applies. Fully transparent
PNG pixels also map to 0. Partial alpha and colours outside the selected palette
are rejected with the offending pixel's coordinates; colours are never rounded
to the nearest match. The font uses only index 0 and white index 15.

PNG palette migration preserved the original pixel indices. The general bitmap
bank now omits the unused Cobra from `panels.png`, retaining all other IDs and
artwork. Edited PNGs are not required to match default hashes. See the
[PNG editing guide](docs/2026-09-19-editable-png-graphics.md) for
the complete 16-colour palette, sheet layouts and verification commands.

## Ship images

Both enhanced games render ship pictures directly from their existing 3D models
into reserved memory. Startup creates the full Shipyards atlas: 13 tiles of
64 x 41 pixels, viewed from above with the nose pointing up. Only the current
player ship is kept for Status and the laser mount dialog (128 x 51, rear/above)
and Planet Data (32 x 45, nose right). These two images are regenerated on a new
game, commander load or successful hull purchase.

The cached dimensions stay fixed in WIDE, HIRES and HIRES-LACED. Amiga scales the
images when drawing to match the rest of the UI, without allocating larger
atlases. The image buffers are separate from screens and drawing workspaces.

The former `ships.png`, `shipsplanetinfo.png`, `shipyards.png` and extraction
metadata are archived in [`resources/gfx_assets`](resources/gfx_assets).
They are no longer build inputs or distributed ship assets; editing them does
not change the game. See [runtime ship images](docs/2026-09-24-runtime-ship-images.md)
for buffer sizes, rendering details, measured savings and validation.

The original Cobra in `panels.png` is not used by either enhanced game. It remains
in the PNG as reference artwork only and generates no game bitmap.
Its former ID is reserved and its file and RAM
storage have been removed on both platforms; the runtime ship view replaces it.

## Planet colours

In both enhanced versions, planets in flight use a saved table of dominant
colours from their normal Planet Data images. Each table contains exactly 2,048
bytes: one per planet in each of the eight galaxies. Normal builds embed the
table without recalculating it. Transparent and black source pixels are excluded;
black or dark grey results use light grey. Yellow results use orange (index 3),
reserving yellow for the sun. Dominant UI brown (index 14) uses steady red
(index 6) in flight, never the pulsing cockpit slot. Flight colours remain stable
across missions.

Only after changing the planet texture or palettes, regenerate the tables
explicitly with `python src_atari/tools/planet_colours.py` and
`python src_amiga/tools/planet_colours.py`, then rebuild the games.

## Ship registrations

In both enhanced versions, press **I** and centre a ship or station in the
crosshair to identify its type and registration, for example `Viper AB-123`.
Identification also works in a view without a fitted laser. Pirates conceal
their registration as `??-???`; a hostile police ship still displays its ID.
Thargoids and Thargons (Tharglets) also conceal their registration.
The Constrictor displays its ID, as in the companion C64 version.
Debris and missiles retain their original type-only identification.

Each AI ship keeps its ID for its lifetime. Coriolis stations use their galaxy
and system number: Lave's station is `Space Station C1-007`. Alien Dodecahedron
stations conceal their registration as `Alien Space Station ??-???`.
The player's registration appears below Cash on the
Status screen and is saved with the commander. New and legacy commanders
start with `JS-042`; a successful escape capsule launch assigns the replacement
ship a new registration. The commander file remains 256 bytes, and existing
saved commanders can still be loaded.

See the [Atari registration notes](src_atari/REGISTRATION.md) and
[Amiga registration notes](src_amiga/REGISTRATION.md) for implementation and tests.

## Build output and running the game

The paths below use the default `outputname=ELITE`. With a custom output name,
substitute that name for the distribution directory and disk-image basename.

| Path relative to the project root | Contents |
| --- | --- |
| `output_atari/ELITE.ST` | 720 KB FAT12 floppy image with AUTO-folder startup |
| `output_atari/ELITE/` | Game directory containing the `ELITE.TOS` launcher and all data files |
| `output_amiga/ELITE.ADF` | Amiga build: bootable 880 KB OFS floppy image |
| `output_amiga/ELITE/` | Amiga build: native `ELITE` executable, Workbench icon and data files |
| `src_atari/build/` | Intermediate files, logs, link map, and verification report |
| `src_amiga/build/` | Independent Amiga intermediate files, logs, link map, and verification report |

Mount `output_atari/ELITE.ST` in drive A: and reset the Atari to boot from the floppy. TOS runs `AUTO\ELITE.PRG` automatically; the launcher selects the disk root before loading the game data. `ELITE.TOS` remains in the root for manual startup from the desktop. The disk uses the standard TOS AUTO-folder mechanism, without executable boot-sector code.

To run from C:, copy the entire contents of `output_atari/ELITE` to a directory such as `C:\ELITE`, then run `C:\ELITE\ELITE.TOS`. **All files must be in the same directory as `ELITE.TOS`, with no separate data subdirectory.** When updating, replace every file, including `LOADER.IMG`, or replace the entire floppy image.

The enhanced game targets an Atari ST with a colour monitor and **1 MB RAM**. Ship pictures are rendered into memory from the game's models: the full Shipyards atlas and two views of the current player ship. For hard-drive setups, the launcher places the game above resident software inside the free ST-RAM block assigned by TOS, rather than requiring fixed low addresses. Enough contiguous free ST RAM is still required; the launcher checks the game workspace, screen placement and startup stack before loading. The original novella protection questions are enabled unless built with `noprotect=yes`.

Before the player ship feature, the relocated startup was verified in Hatari 2.6.1 with TOS 1.04 DE on 512 KB and 1 MB configurations, including C: startup with a 128 KB resident program occupying low memory. The current shipyard build is tested with 1 MB. Compatibility with PP HDD Driver on physical hardware still needs confirmation.

## Independent Amiga version

The Amiga game is developed in [src_amiga](src_amiga/README.md), separately from the Atari sources in `src_atari`. Both started from the corrected Atari game, including the starfield fixes. Amiga changes no longer require platform conditionals in the Atari tree.

Run `build_amiga.bat` to create `output_amiga/ELITE.ADF` and the game files in `output_amiga/ELITE`. `outputname=NAME` names the image and its directory, and nothing is appended, so `build_amiga.bat all` gives every variant a name of its own. The target is **PAL OCS, MC68000, Kickstart 1.3, 512 KB Chip RAM plus 512 KB expansion RAM**. The default screen is the original 320 x 200 with its framed 256 x 112 view; `frame=no` gives the flight view the whole screen, 320 x 256 on PAL, and `display=` offers six screens up to 640 x 512. Boot the ADF in DF0:. The novella questions are enabled unless built with `noprotect=yes`. Ctrl+F10 returns to AmigaDOS; F10 opens the inventory.

To launch from Workbench, open the game disk or copy the complete `output_amiga/ELITE` directory to a hard drive, then double-click the `ELITE` icon. The classic four-colour, dual-image icon comes from `src_amiga/assets/ELITE.info` and is included in both outputs. Keep the executable, icon and data files together. Workbench launches use the executable's directory for assets and HDD commander files, and Ctrl+F10 returns to Workbench. The icon uses the current Workbench palette, so its colours differ between the default Workbench 1.3 and 3.0 screens.

The renderer writes directly into two Chip RAM screens using native Amiga bitplanes. Copper selects the visible screen; there is no ST framebuffer or per-frame screen conversion. The game consumes native Amiga raw-key events, reads the joystick port, and uses AmigaDOS calls with 32-bit file handles. Its sound code drives Paula with 19 original effect samples extracted from `resources/amiga/Elite 2.0.adf`. Music uses the original four-channel Amiga arrangement of Blue Danube, with its seven sampled instruments and native replay, for the title, docking computer and Elite congratulations screen. Effect timing and envelopes remain simplified. See [Amiga music notes](src_amiga/MUSIC.md) for extraction and validation details.

The independent version has been checked in WinUAE 6.0.3 through startup, launch, all flight views, pitch controls, charts, commander save/load and catalog, and return to AmigaDOS. Audio register setup was inspected; audible sound quality, physical input devices, extended gameplay and real hardware remain untested.

See [Amiga development and testing notes](src_amiga/README.md) for the current validation scope and limitations. The independent build does not modify Atari sources or outputs.

### What new in the Amiga version

Wide flight view on PAL or NTSC, each in lores, hires and hires interlaced, and on DblPAL, 640 x 512 without interlace on AGA.

The game picks the fastest drawing path for the machine it finds. A 68020 or better with Fast RAM draws the view in Fast RAM and carries it to the screen once a frame. On a 68000 the blitter clears the view while the processor keeps drawing. A 68040 or 68060 clears with MOVE16.

Every wide image prints the frame time in the top left: three numbers in milliseconds, the whole frame's work, the rasterising inside it, and the clear. Four characters sit at the right. The first is the processor family (0, 2, 4, 6), then `M` when the clear uses MOVE16 and `L` when the maths is 32-bit, a dot otherwise. The last one says how the frame was drawn: `C` straight into Chip RAM, `B` cleared by the blitter, `F` through Fast RAM.

### Screens

| image | screen | flight view |
| --- | --- | --- |
| `ELITE` | 320 x 200 | 256 x 112, framed |
| `ELITE.WIDE.NTSC` | 320 x 200 | 320 x 120 |
| `ELITE.WIDE.PAL` | 320 x 256 | 320 x 176 |
| `ELITE.WIDE.NTSC-HIRES` | 640 x 200 | 640 x 120 |
| `ELITE.WIDE.PAL-HIRES` | 640 x 256 | 640 x 176 |
| `ELITE.WIDE.NTSC-HIRESLACE` | 640 x 400 | 640 x 240 |
| `ELITE.WIDE.PAL-HIRESLACE` | 640 x 512 | 640 x 352 |
| `ELITE.WIDE.DBLPAL-HIRES` | 640 x 512 | 640 x 352 |

### Recommended configurations

| machine | image |
| --- | --- |
| 68000 at 7 MHz, no Fast RAM (A500, A600) | `ELITE`, `ELITE.NTSC` |
| 68020 at 14 MHz, no Fast RAM (A1200) | `ELITE.WIDE.NTSC` |
| 68020 at 14 MHz with Fast RAM (A1200) | `ELITE.WIDE.NTSC`, `ELITE.WIDE.PAL` |
| 68030 with Fast RAM, from 33 MHz | `ELITE.WIDE.NTSC-HIRES` |
| 68030 with Fast RAM, 50 MHz | `ELITE.WIDE.PAL-HIRES` |
| 68040+ with Fast RAM, from 33 MHz | `ELITE.WIDE.NTSC-HIRESLACE` |
| 68040+ with Fast RAM, from 50 MHz | `ELITE.WIDE.PAL-HIRESLACE` |
| AGA, 68040+ with Fast RAM, from 33 MHz, 27 kHz monitor | `ELITE.WIDE.DBLPAL-HIRES` |
​
## Project structure

| Path | Purpose |
| --- | --- |
| [src_orig/](src_orig/README.md) | Independently buildable original Atari ST version |
| `resources/elite_atarist_source.zip` | Untouched historical archive (307 files) |
| `output_orig/` | Preserved original game and floppy image |
| [build_orig.bat](build_orig.bat) | Original-version build entry point |
| [src_atari/](src_atari/README.md) | Working sources, assets, build scripts, and tests |
| [tools/](tools/README.md) | Bundled Windows assembler and linker executables and license information |
| `output_atari/` | Atari game and floppy image |
| [src_amiga/](src_amiga/README.md) | Independent Amiga sources, assets, build and tests |
| `output_amiga/` | Amiga game and bootable ADF |
| [build_amiga.bat](build_amiga.bat) | Amiga build entry point |
| [build_atari.bat](build_atari.bat) | Atari build entry point and place for default parameters |

Atari source changes belong in `src_atari`; Amiga source changes belong in `src_amiga`. Project rules are in [AGENTS.md](AGENTS.md).

Sources, documentation, and bundled tools belong in Git. Generated files stay in `output_atari`, `output_amiga`, `output_orig`, and each source tree's `build` directory. The emulator and TOS ROM are not included in the repository. The historical ZIP retains the original files, encodings and line endings; run `python src_orig/tools/verify_original.py` to verify that archive. Converted assembly is stored as text; assets and the ZIP are kept binary.

See [src_atari/README.md](src_atari/README.md) for development, testing, and optional tool rebuilding. [src_atari/ANALYSIS.md](src_atari/ANALYSIS.md) describes the original architecture and dialect conversion.

## Legal information and credits

**Elite** was originally created by **Ian Bell and David Braben** for the BBC Micro in 1984. See [Ian Bell's Elite website](https://www.elitehomepage.org/) for the original authors' credits and historical material.

The Atari ST version credits the following contributors in its [in-game credits](src_atari/asm/action.m68):

- **Rob Nicholson of Mr. Micro Ltd.** — Atari ST conversion and programming.
- **Gary Patchen** — assistance with the conversion.
- **James McDermott** — graphics.

The [original source header](src_atari/asm/elite.m68) identifies the Atari ST conversion as derived from the MSX version and carries **Copyright (c) 1988 Mr. Micro and Firebird Software**. The [title-screen code](src_atari/asm/attract.m68) also credits **Bell & Braben**.

The experimental Amiga port reuses the music, instruments and sound samples from the supplied Amiga release, whose music and sound are credited to **Wally Beben**. Its native music replay is adapted from that release's replay code. Blue Danube was composed by **Johann Strauss II**. The port's artwork and game logic derive from the Atari source tree; the full original Amiga game executable is not reconstructed.

Project contributor: **Jaroslav Pulchart**.

This repository maintains a buildable version of the Atari ST sources with fixes and modern build tooling. It does not claim ownership of the original game, code, graphics, or other assets. Their copyrights remain with their respective rights holders; inclusion in this repository does not place them in the public domain or grant additional rights to use or redistribute them.

The build uses the bundled **vasm 2.0f assembler** and **vlink 0.18a linker**. These tools have separate license terms: [vasm license](tools/vasm-LICENSE.txt) and [vlink license](tools/vlink-LICENSE.txt).
