# Source code and development

See the [main README in the project root](../README.md) for building and running the game. This directory contains the working sources and development tools. `src-orig` is read-only; make source changes only under `src`.

Run all commands below from the project root. Paths in the tables and text are also relative to the root.

## Directory contents

| Path | Purpose |
| --- | --- |
| `src/asm/` | 39 converted game modules, macros, definitions, loader, font, and ship data |
| `src/assets/` | Copies of original bitmaps, images, and trigonometric tables |
| `src/modules.txt` | Game module order from the original `ELITE.LNK` |
| `src/elite.ld` | Fixed memory layout and linker symbols |
| `src/build.py` | Assembly, linking, verification, and floppy image creation |
| `src/build.bat` | Windows build entry point called by the root `build.bat`; forwards all arguments |
| `src/build.ps1` | Python discovery and argument forwarding to `src/build.py` |
| `src/tools/` | Original dialect converter, floppy image builder, original-file verification, and helper scripts |
| `src/tests/` | Regression tests for the conversion and launcher |
| `src/vendor/` | Two original vasm/vlink source archives for optional tool rebuilding |
| `src/original-sha256.json` | Baseline SHA-256 hashes of all 307 files in `src-orig` |
| `src/build/` | Generated objects, logs, maps, and diagnostics |

## Editing and building

Edit files in `src/asm`. `boot.s` and `workspace.m68` are new sources for the current build. The original novella questions are controlled by `use_novella = -1` in `src/asm/common.def`.

```powershell
.\build.bat
```

The build uses the bundled `tools/vasmm68k_mot.exe` and `tools/vlink.exe` in the project root. It assembles all game modules from source, without using `src-orig` or old `.LTX` objects. It writes the game files to `output/ELITE` and the floppy image to `output/ELITE.ST`. Both assembler and linker run from `src/build` with explicit output paths to prevent `a.out` from appearing in the root.

`src/tools/convert_quelo.py` documents the one-time import of the original dialect. **The normal build does not run it.** By default, it refuses to overwrite existing files. Its `--overwrite` option discards edits to converted files in `src/asm` and is intended only for deliberately repeating the import.

The build automatically recalculates the new binary's checksum and assembles the checksum module a second time. There is no need to edit the historical `$5123` constant manually.

The link map is in `src/build/elite.map`; verification results and output SHA-256 hashes are in `src/build/verification.json`. See [ANALYSIS.md](ANALYSIS.md) for the memory layout, original architecture, and conversion details.

## Verification

Tests and original-file verification can be run independently:

```powershell
python -m unittest discover -s src/tests -v
python src/tools/verify_original.py
```

The build checks all external symbols, the embedded checksum, A6 relocation to the variable area, RAM and local-variable bounds, control-key ASCII values, data buffer capacities, the TOS header, and a full readback of the FAT12 floppy image. Tests also cover sensitive Quelo conversion details, including reused labels, the tenth macro argument, and OR conditions, as well as launcher placement under TOS 1.04 and error-message termination.

Use `src/tools/run_hatari.py` to repeat the startup diagnostic. It requires a separately installed Windows [Hatari 2.6.1](https://www.hatari-emu.org/download.html) and your own TOS ROM. Supply their paths as arguments; the emulator is not copied into the repository:

```powershell
python src/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img'
python src/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img' --floppy
```

The script uses the game from the root `output` directory and stores screenshots and diagnostics separately in `src/build/hatari-test/harddrive` and `src/build/hatari-test/floppy`. It runs without a window, write-protects the game disks, and does not save settings to the user profile. Assess the result using the screenshots and logs; the emulator's exit code alone does not confirm that the game works. The normal build does not run the emulator (`runtime_tested: false` in its report).

## Optional assembler and linker rebuild

The normal build uses the bundled executables and does not need this step. Rebuilding the assembler and linker themselves requires Visual Studio 2022 or Build Tools with the C++ tools and Windows SDK:

```powershell
.\src\tools\setup-toolchain.ps1
```

The script verifies the SHA-256 hashes of the archives in `src/vendor`, extracts them to `src/build/toolchain`, builds the tools with MSVC and a statically linked C runtime (`/MT`), and copies the resulting executables to the root `tools` directory. If archives are missing, it downloads them from the official site. Versions and hashes are recorded in `src/tools/toolchain.json`; the script rejects changed upstream content until it has been reviewed. Extracted sources and objects therefore remain among the ignored build files.

The upstream license terms are included beside the executables: [vasm](../tools/vasm-LICENSE.txt), [vlink](../tools/vlink-LICENSE.txt). The original archives remain in `src/vendor`. See [tools/README.md](../tools/README.md) for the bundled binaries, and the [vasm](https://sun.hasenbraten.de/vasm/) and [vlink](https://sun.hasenbraten.de/vlink/) sites for official documentation.
