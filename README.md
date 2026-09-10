# Elite Atari ST

A buildable version of the original Elite for Atari ST and the **MC68000** processor. All 39 game modules are assembled from sources in `src/asm` using **vasm 2.0f and vlink 0.18a**. The original sources in `src-orig` remain unchanged; the normal build does not use them or reuse the old `.LTX` object files.

## Building on Windows

You need **Windows x64 and Python 3.10 or later**, with no additional Python packages. The **vasm 2.0f assembler** (`vasmm68k_mot.exe`, MC68000 with Motorola syntax) and **vlink 0.18a linker** (`vlink.exe`) are bundled as compiled Windows executables in [tools](tools/README.md). A normal build requires no Visual Studio installation, assembler PATH configuration, or additional tool downloads.

Run this from the project root:

```powershell
.\build.bat
```

If the script cannot find Python, provide its path:

```powershell
.\build.bat -Python "C:\path\python.exe"
```

[build.bat](build.bat) calls [src/build.bat](src/build.bat) and forwards all command-line arguments. Add persistent default options directly to the root script's `call` line, before `%*`. Use `-Vasm` and `-Vlink` to select custom assembler and linker executables. The wrappers also pass through arguments such as `option1=yes`; each such option needs corresponding support in `src/build.py`.

Alternatively, run `python src/build.py` directly. The scripts resolve project paths relative to their own location, so you can also invoke the build from another working directory.

## Build output and running the game

| Path relative to the project root | Contents |
| --- | --- |
| `output/ELITE.ST` | 720 KB FAT12 floppy image containing all game files |
| `output/ELITE/` | Game directory containing the `ELITE.TOS` launcher and all data files |
| `src/build/` | Intermediate files, logs, link map, and verification report |

Mount `output/ELITE.ST` in your emulator, open drive A:, and run `ELITE.TOS`. The floppy does not boot automatically.

To run from C:, copy the entire contents of `output/ELITE` to a directory such as `C:\ELITE`, then run `C:\ELITE\ELITE.TOS`. **All files must be in the same directory as `ELITE.TOS`, with no separate data subdirectory.** When updating, replace every file, including `LOADER.IMG`, or replace the entire floppy image.

The default target is a standard Atari ST with a colour monitor, at least 512 KB RAM, and a plain TOS desktop without resident accessories. The original novella protection questions remain enabled.

Startup from both A: and C: has been verified in Hatari 2.6.1 with TOS 1.04 DE and 1 MB RAM, as far as the novella question screen. Startup has also been confirmed in Steem SSE. Full gameplay and real hardware have not yet been tested.

## Project structure

| Path | Purpose |
| --- | --- |
| `src-orig/` | Original source code, read-only |
| [src/](src/README.md) | Working sources, assets, build scripts, and tests |
| [tools/](tools/README.md) | Bundled Windows assembler and linker executables and license information |
| `output/` | Built game and floppy image |
| [build.bat](build.bat) | Main build entry point and place for default parameters |

All game source changes belong in `src`. Project rules are in [AGENTS.md](AGENTS.md).

Sources, documentation, and bundled tools belong in Git. `output`, `src/build`, and Python caches are ignored. The emulator and TOS ROM are not included in the repository. Original sources retain their exact encoding and line endings; run `python src/tools/verify_original.py` to verify all 307 files.

See [src/README.md](src/README.md) for development, testing, and optional tool rebuilding. [src/ANALYSIS.md](src/ANALYSIS.md) describes the original architecture and dialect conversion.

## Legal information and credits

**Elite** was originally created by **Ian Bell and David Braben** for the BBC Micro in 1984. See [Ian Bell's Elite website](https://www.elitehomepage.org/) for the original authors' credits and historical material.

The Atari ST version credits the following contributors in its [in-game credits](src/asm/action.m68):

- **Rob Nicholson of Mr. Micro Ltd.** — Atari ST conversion and programming.
- **Gary Patchen** — assistance with the conversion.
- **James McDermott** — graphics.

The [original source header](src/asm/elite.m68) identifies the Atari ST conversion as derived from the MSX version and carries **Copyright (c) 1988 Mr. Micro and Firebird Software**. The [title-screen code](src/asm/attract.m68) also credits **Bell & Braben**.

This repository maintains a buildable version of the Atari ST sources with fixes and modern build tooling. It does not claim ownership of the original game, code, graphics, or other assets. Their copyrights remain with their respective rights holders; inclusion in this repository does not place them in the public domain or grant additional rights to use or redistribute them.

The build uses the bundled **vasm 2.0f assembler** and **vlink 0.18a linker**. These tools have separate license terms: [vasm license](tools/vasm-LICENSE.txt) and [vlink license](tools/vlink-LICENSE.txt).
