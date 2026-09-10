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

The default is `noprotect=no`, which keeps the question enabled. Each build applies the selected option to its own output files; it is not a runtime setting. If repeated, the last `noprotect` option wins. Other game protection checks remain unchanged.

If the script cannot find Python, provide its path:

```powershell
.\build_atari.bat -Python "C:\path\python.exe"
```

[build_atari.bat](build_atari.bat) calls [src_atari/build.bat](src_atari/build.bat) and forwards all command-line arguments. Add persistent default options directly to the root script's `call` line, before `%*`. Use `-Vasm` and `-Vlink` to select custom assembler and linker executables. Unrecognized build arguments are rejected.

Alternatively, run `python src_atari/build.py` directly. The scripts resolve project paths relative to their own location, so you can also invoke the build from another working directory.

## Build output and running the game

| Path relative to the project root | Contents |
| --- | --- |
| `output_atari/ELITE.ST` | 720 KB FAT12 floppy image containing all game files |
| `output_atari/ELITE/` | Game directory containing the `ELITE.TOS` launcher and all data files |
| `output_amiga/ELITE.ADF` | Amiga build: bootable 880 KB OFS floppy image |
| `output_amiga/ELITE/` | Amiga build: native `ELITE` executable and data files |
| `src_atari/build/` | Intermediate files, logs, link map, and verification report |
| `src_amiga/build/` | Independent Amiga intermediate files, logs, link map, and verification report |

Mount `output_atari/ELITE.ST` in your emulator, open drive A:, and run `ELITE.TOS`. The floppy does not boot automatically.

To run from C:, copy the entire contents of `output_atari/ELITE` to a directory such as `C:\ELITE`, then run `C:\ELITE\ELITE.TOS`. **All files must be in the same directory as `ELITE.TOS`, with no separate data subdirectory.** When updating, replace every file, including `LOADER.IMG`, or replace the entire floppy image.

The default target is a standard Atari ST with a colour monitor, at least 512 KB RAM, and a plain TOS desktop without resident accessories. The original novella protection questions are enabled unless built with `noprotect=yes`.

Startup from both A: and C: has been verified in Hatari 2.6.1 with TOS 1.04 DE and 1 MB RAM, as far as the novella question screen. Startup has also been confirmed in Steem SSE. Full gameplay and real hardware have not yet been tested.

## Independent Amiga version

The Amiga game is developed in [src_amiga](src_amiga/README.md), separately from the Atari sources in `src_atari`. Both started from the corrected Atari game, including the starfield fixes. Amiga changes no longer require platform conditionals in the Atari tree.

Run `build_amiga.bat` to create `output_amiga/ELITE.ADF` and the game files in `output_amiga/ELITE`. The target is **PAL OCS, MC68000, Kickstart 1.3, 512 KB Chip RAM plus 512 KB expansion RAM**. Boot the ADF in DF0:. The novella questions are enabled unless built with `noprotect=yes`. Ctrl+F10 returns to AmigaDOS; F10 opens the inventory.

The renderer writes directly into two Chip RAM screens using native Amiga bitplanes. Copper selects the visible screen; there is no ST framebuffer or per-frame screen conversion. The game consumes native Amiga raw-key events, reads the joystick port, and uses AmigaDOS calls with 32-bit file handles. Its sound code drives Paula with 19 original samples extracted from `resources/amiga/Elite 2.0.adf`. Music and effect envelopes remain simplified compared with the original Amiga release.

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

The experimental Amiga port reuses sound samples from the supplied Amiga release, whose music and sound are credited to **Wally Beben**. This port derives its artwork and game logic from the Atari source tree; it is not a source reconstruction of the original Amiga executable.

This repository maintains a buildable version of the Atari ST sources with fixes and modern build tooling. It does not claim ownership of the original game, code, graphics, or other assets. Their copyrights remain with their respective rights holders; inclusion in this repository does not place them in the public domain or grant additional rights to use or redistribute them.

The build uses the bundled **vasm 2.0f assembler** and **vlink 0.18a linker**. These tools have separate license terms: [vasm license](tools/vasm-LICENSE.txt) and [vlink license](tools/vlink-LICENSE.txt).
