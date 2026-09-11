# Elite Atari ST

A buildable version of the original Elite for Atari ST and the **MC68000** processor, with a separate native Amiga port under `src_amiga`. The Atari game modules are assembled from sources in `src_atari/asm` using **vasm 2.0f and vlink 0.18a**. The original sources in `src-orig` remain unchanged; the normal build does not use them or reuse the old `.LTX` object files.

## Building on Windows

You need **Windows x64 and Python 3.10 or later**, with no additional Python packages. The **vasm 2.0f assembler** (`vasmm68k_mot.exe`, MC68000 with Motorola syntax) and **vlink 0.18a linker** (`vlink.exe`) are bundled as compiled Windows executables in [tools](tools/README.md). A normal build requires no Visual Studio installation, assembler PATH configuration, or additional tool downloads.

Run this from the project root:

```powershell
.\build_atari.bat
```

The Atari and Amiga builds have independent source trees and entry points. No platform option is used.

```powershell
.\build_atari.bat
.\build_amiga.bat
```

To skip the novella protection question at startup, add `noprotect=yes`:

```powershell
.\build_atari.bat noprotect=yes
.\build_amiga.bat noprotect=yes
```

The Python builds default to `noprotect=no`, which keeps the question enabled. Each build applies the selected option to its own output files; it is not a runtime setting. Other game protection checks remain unchanged.

Use `commander=max` to give the default Jameson commander **1,000,000 Cr** at the start of a new game or after resetting the game:

```powershell
.\build_atari.bat commander=max
.\build_amiga.bat commander=max
```

`commander=default` restores the original **100 Cr** starting balance. This option changes cash only; loading a saved commander uses the balance stored in that save. The Python builds default to `commander=default`.

The root build scripts currently supply `noprotect=yes commander=max laser=singlebeam aifiresound=no scannerlogo=yes` as persistent defaults. Command-line arguments override these defaults independently: the last occurrence of each option wins. For example, `build_amiga.bat noprotect=no commander=default` enables the novella question and restores the original starting balance.

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
instrument bars. AI beam colours follow the player's rating: Harmless through
Poor is red, Average through Competent orange, and Dangerous through Elite white.
Constrictor beams are always white. AI damage and the 10% random miss chance
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

If the script cannot find Python, provide its path:

```powershell
.\build_atari.bat -Python "C:\path\python.exe"
```

[build_atari.bat](build_atari.bat) calls [src_atari/build.bat](src_atari/build.bat) and forwards all command-line arguments. Add persistent default options directly to the root script's `call` line, before `%*`. Use `-Vasm` and `-Vlink` to select custom assembler and linker executables. Unrecognized build arguments are rejected.

Alternatively, run `python src_atari/build.py` directly. The scripts resolve project paths relative to their own location, so you can also invoke the build from another working directory.

## Build output and running the game

| Path relative to the project root | Contents |
| --- | --- |
| `output_atari/ELITE.ST` | 720 KB FAT12 floppy image with AUTO-folder startup |
| `output_atari/ELITE/` | Game directory containing the `ELITE.TOS` launcher and all data files |
| `output_amiga/ELITE.ADF` | Amiga build: bootable 880 KB OFS floppy image |
| `output_amiga/ELITE/` | Amiga build: native `ELITE` executable and data files |
| `src_atari/build/` | Intermediate files, logs, link map, and verification report |
| `src_amiga/build/` | Independent Amiga intermediate files, logs, link map, and verification report |

Mount `output_atari/ELITE.ST` in drive A: and reset the Atari to boot from the floppy. TOS runs `AUTO\ELITE.PRG` automatically; the launcher selects the disk root before loading the game data. `ELITE.TOS` remains in the root for manual startup from the desktop. The disk uses the standard TOS AUTO-folder mechanism, without executable boot-sector code.

To run from C:, copy the entire contents of `output_atari/ELITE` to a directory such as `C:\ELITE`, then run `C:\ELITE\ELITE.TOS`. **All files must be in the same directory as `ELITE.TOS`, with no separate data subdirectory.** When updating, replace every file, including `LOADER.IMG`, or replace the entire floppy image.

The default target is a standard Atari ST with a colour monitor, at least 512 KB RAM, and a plain TOS desktop without resident accessories. The original novella protection questions are enabled unless built with `noprotect=yes`.

Startup from both A: and C: has been verified in Hatari 2.6.1 with TOS 1.04 DE and 1 MB RAM, as far as the novella question screen. Startup has also been confirmed in Steem SSE. Full gameplay and real hardware have not yet been tested.

## Independent Amiga version

The Amiga game is developed in [src_amiga](src_amiga/README.md), separately from the Atari sources in `src_atari`. Both started from the corrected Atari game, including the starfield fixes. Amiga changes no longer require platform conditionals in the Atari tree.

Run `build_amiga.bat` to create `output_amiga/ELITE.ADF` and the game files in `output_amiga/ELITE`. The target is **PAL OCS, MC68000, Kickstart 1.3, 512 KB Chip RAM plus 512 KB expansion RAM**. Boot the ADF in DF0:. The novella questions are enabled unless built with `noprotect=yes`. Ctrl+F10 returns to AmigaDOS; F10 opens the inventory.

The renderer writes directly into two Chip RAM screens using native Amiga bitplanes. Copper selects the visible screen; there is no ST framebuffer or per-frame screen conversion. The game consumes native Amiga raw-key events, reads the joystick port, and uses AmigaDOS calls with 32-bit file handles. Its sound code drives Paula with 19 original effect samples extracted from `resources/amiga/Elite 2.0.adf`. Music uses the original four-channel Amiga arrangement of Blue Danube, with its seven sampled instruments and native replay, for the title, docking computer and Elite congratulations screen. Effect timing and envelopes remain simplified. See [Amiga music notes](src_amiga/MUSIC.md) for extraction and validation details.

The independent version has been checked in WinUAE 6.0.3 through startup, launch, all flight views, pitch controls, charts, commander save/load and catalog, and return to AmigaDOS. Audio register setup was inspected; audible sound quality, physical input devices, extended gameplay and real hardware remain untested.

See [Amiga development and testing notes](src_amiga/README.md) for the current validation scope and limitations. The independent build does not modify Atari sources or outputs.

## Project structure

| Path | Purpose |
| --- | --- |
| `src-orig/` | Original source code, read-only |
| [src_atari/](src_atari/README.md) | Working sources, assets, build scripts, and tests |
| [tools/](tools/README.md) | Bundled Windows assembler and linker executables and license information |
| `output_atari/` | Atari game and floppy image |
| [src_amiga/](src_amiga/README.md) | Independent Amiga sources, assets, build and tests |
| `output_amiga/` | Amiga game and bootable ADF |
| [build_amiga.bat](build_amiga.bat) | Amiga build entry point |
| [build_atari.bat](build_atari.bat) | Atari build entry point and place for default parameters |

Atari source changes belong in `src_atari`; Amiga source changes belong in `src_amiga`. Project rules are in [AGENTS.md](AGENTS.md).

Sources, documentation, and bundled tools belong in Git. Generated files stay in `output_atari`, `output_amiga`, `src_atari/build`, and `src_amiga/build`. The emulator and TOS ROM are not included in the repository. Original sources retain their exact encoding and line endings; run `python src_atari/tools/verify_original.py` to verify all 307 files.

See [src_atari/README.md](src_atari/README.md) for development, testing, and optional tool rebuilding. [src_atari/ANALYSIS.md](src_atari/ANALYSIS.md) describes the original architecture and dialect conversion.

## Legal information and credits

**Elite** was originally created by **Ian Bell and David Braben** for the BBC Micro in 1984. See [Ian Bell's Elite website](https://www.elitehomepage.org/) for the original authors' credits and historical material.

The Atari ST version credits the following contributors in its [in-game credits](src_atari/asm/action.m68):

- **Rob Nicholson of Mr. Micro Ltd.** — Atari ST conversion and programming.
- **Gary Patchen** — assistance with the conversion.
- **James McDermott** — graphics.

The [original source header](src_atari/asm/elite.m68) identifies the Atari ST conversion as derived from the MSX version and carries **Copyright (c) 1988 Mr. Micro and Firebird Software**. The [title-screen code](src_atari/asm/attract.m68) also credits **Bell & Braben**.

The experimental Amiga port reuses the music, instruments and sound samples from the supplied Amiga release, whose music and sound are credited to **Wally Beben**. Its native music replay is adapted from that release's replay code. Blue Danube was composed by **Johann Strauss II**. The port's artwork and game logic derive from the Atari source tree; the full original Amiga game executable is not reconstructed.

This repository maintains a buildable version of the Atari ST sources with fixes and modern build tooling. It does not claim ownership of the original game, code, graphics, or other assets. Their copyrights remain with their respective rights holders; inclusion in this repository does not place them in the public domain or grant additional rights to use or redistribute them.

The build uses the bundled **vasm 2.0f assembler** and **vlink 0.18a linker**. These tools have separate license terms: [vasm license](tools/vasm-LICENSE.txt) and [vlink license](tools/vlink-LICENSE.txt).
