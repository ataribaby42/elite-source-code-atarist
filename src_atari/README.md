# Source code and development

See the [main README in the project root](../README.md) for building and running the game. This directory contains the working sources and development tools. `src-orig` is read-only; make source changes only under `src_atari`.

Run all commands below from the project root. Paths in the tables and text are also relative to the root.

## Directory contents

| Path | Purpose |
| --- | --- |
| `src_atari/asm/` | 39 converted game modules, macros, definitions, loader, font, and ship data |
| `src_atari/assets/` | Copies of original bitmaps, images, and trigonometric tables |
| `src_atari/modules.txt` | Game module order from the original `ELITE.LNK` |
| `src_atari/elite.ld` | Fixed memory layout and linker symbols |
| `src_atari/build.py` | Assembly, linking, verification, and floppy image creation |
| `src_atari/build.bat` | Windows build entry point called by the root `build_atari.bat`; forwards all arguments |
| `src_atari/build.ps1` | Python discovery and argument forwarding to `src_atari/build.py` |
| `src_atari/tools/` | Original dialect converter, floppy image builder, original-file verification, and helper scripts |
| `src_atari/tests/` | Regression tests for the conversion, launcher and raster routines |
| `src_atari/vendor/` | Two original vasm/vlink source archives for optional tool rebuilding |
| `src_atari/original-sha256.json` | Baseline SHA-256 hashes of all 307 files in `src-orig` |
| `src_atari/build/` | Generated objects, logs, maps, and diagnostics |

## Editing and building

Edit files in `src_atari/asm`. `boot.s` and `workspace.m68` are new sources for the current build. The original novella questions are enabled by default. Build with `noprotect=yes` to skip the question without editing assembly definitions or changing other protection checks.

```powershell
.\build_atari.bat
.\build_atari.bat noprotect=yes
```

`noprotect=no` restores the default behavior. The last occurrence wins when the option is repeated. The same options are accepted by `python src_atari/build.py`.

The build uses the bundled `tools/vasmm68k_mot.exe` and `tools/vlink.exe` in the project root. It assembles all game modules from source, without using `src-orig` or old `.LTX` objects. It writes the game files to `output_atari/ELITE` and the floppy image to `output_atari/ELITE.ST`. Both assembler and linker run from `src_atari/build` with explicit output paths to prevent `a.out` from appearing in the root.

`src_atari/tools/convert_quelo.py` documents the one-time import of the original dialect. **The normal build does not run it.** By default, it refuses to overwrite existing files. Its `--overwrite` option discards edits to converted files in `src_atari/asm` and is intended only for deliberately repeating the import.

The build automatically recalculates the new binary's checksum and assembles the checksum module a second time. There is no need to edit the historical `$5123` constant manually.

The link map is in `src_atari/build/elite.map`; verification results and output SHA-256 hashes are in `src_atari/build/verification.json`. See [ANALYSIS.md](ANALYSIS.md) for the memory layout, original architecture, and conversion details.


## Verification

Tests and original-file verification can be run independently:

```powershell
python -m unittest discover -s src_atari/tests -v
python src_atari/tools/verify_original.py
```

The build checks all external symbols, the embedded checksum, A6 relocation to the variable area, RAM and local-variable bounds, control-key ASCII values, data buffer capacities, the TOS header, and a full readback of the FAT12 floppy image. Tests also cover sensitive Quelo conversion details, including reused labels, the tenth macro argument, and OR conditions, as well as launcher placement under TOS 1.04 and error-message termination.

Viewport clearing uses three `MOVEM.L` stores per row (11 + 11 + 10 longwords), saving and restoring A2-A4 once per call. It clears the same 256 x 112 viewport and keeps the original VBL wait. Diagonal lines cache their two colour pairs in registers and preserve the caller's D7 counter. The original pixel selection, patterned colours and frame synchronization are retained.

The optional `tests/test_raster.py` checks require `unicorn==2.1.4` (`python -m pip install unicorn==2.1.4`); they are skipped when it is absent. They assemble and execute the actual MC68000 raster routines and compare guarded buffers against a pixel reference, covering viewport clearing, the flyback wait, preserved registers, all line directions, 120 panel colour patterns, 16 solid colours, word boundaries and both screens. These checks do not measure gameplay frame rate. The normal game build has no new package dependency.

Use `src_atari/tools/run_hatari.py` to repeat the startup diagnostic. It requires a separately installed Windows [Hatari 2.6.1](https://www.hatari-emu.org/download.html) and your own TOS ROM. Supply their paths as arguments; the emulator is not copied into the repository:

```powershell
python src_atari/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img'
python src_atari/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img' --floppy
```

The script uses the game from the root `output_atari` directory and stores screenshots and diagnostics separately in `src_atari/build/hatari-test/harddrive` and `src_atari/build/hatari-test/floppy`. It runs without a window, write-protects the game disks, and does not save settings to the user profile. Assess the result using the screenshots and logs; the emulator's exit code alone does not confirm that the game works. The normal build does not run the emulator (`runtime_tested: false` in its report).

## Optional assembler and linker rebuild

The normal build uses the bundled executables and does not need this step. Rebuilding the assembler and linker themselves requires Visual Studio 2022 or Build Tools with the C++ tools and Windows SDK:

```powershell
.\src_atari\tools\setup-toolchain.ps1
```

The script verifies the SHA-256 hashes of the archives in `src_atari/vendor`, extracts them to `src_atari/build/toolchain`, builds the tools with MSVC and a statically linked C runtime (`/MT`), and copies the resulting executables to the root `tools` directory. If archives are missing, it downloads them from the official site. Versions and hashes are recorded in `src_atari/tools/toolchain.json`; the script rejects changed upstream content until it has been reviewed. Extracted sources and objects therefore remain among the ignored build files.

The upstream license terms are included beside the executables: [vasm](../tools/vasm-LICENSE.txt), [vlink](../tools/vlink-LICENSE.txt). The original archives remain in `src_atari/vendor`. See [tools/README.md](../tools/README.md) for the bundled binaries, and the [vasm](https://sun.hasenbraten.de/vasm/) and [vlink](https://sun.hasenbraten.de/vlink/) sites for official documentation.
