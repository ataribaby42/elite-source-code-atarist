# Source code and development

See the [main README in the project root](../README.md) for building and running the game. This directory contains the working sources and development tools. `src_orig` now contains an independent build of the preserved original game; enhanced Atari gameplay changes belong only under `src_atari`. The untouched historical source archive is `resources/elite_atarist_source.zip`.

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
| `src_atari/original-sha256.json` | Baseline SHA-256 hashes of all 307 files in the historical ZIP |
| `src_atari/build/` | Generated objects, logs, maps, and diagnostics |

## Editing and building

Edit files in `src_atari/asm`. `boot.s` and `workspace.m68` are new sources for the current build. The original novella questions are enabled by default. Build with `noprotect=yes` to skip the question without editing assembly definitions or changing other protection checks.

```powershell
.\build_atari.bat
.\build_atari.bat noprotect=yes
```

`noprotect=no` restores the default behavior. The same options are accepted by `python src_atari/build.py`.

`commander=max` gives the default Jameson commander **1,000,000 Cr** and the **Deadly** rating when starting or resetting a game. His score starts at the Deadly threshold (`$A0000`). `commander=default` keeps the original **100 Cr**, **Harmless** rating and zero score, and is the Python build default. Saved commanders retain their saved balances, scores and ratings.

`laser=dualbeam` is the default player laser style: two filled beams from the bottom left and right converge on the jittering crosshair tip. `laser=singlebeam` selects one narrow filled beam from the bottom centre. Both styles use the existing palette: Pulse is red, Beam orange, Military white, and Mining the same magenta as the instrument bars. They keep the same cosmetic jitter, fixed-axis targeting, damage and timing. These style options do not affect AI beams or their 10% random miss chance.

```powershell
.\build_atari.bat laser=dualbeam
.\build_atari.bat laser=singlebeam
```

`aifiresound=no` is the build default and disables AI laser firing sounds. `aifiresound=yes` enables them, subject to the game's existing Effects setting. This option controls AI laser shot sounds only; hit/impact sounds, player weapons, missile alerts and other effects keep their existing handling.

```powershell
.\build_atari.bat aifiresound=no
.\build_atari.bat aifiresound=yes
```

`scannerlogo=yes` (default) shows the ELITE caption below the scanner. Use `scannerlogo=no` to hide the caption on both cockpit buffers. The scanner, instruments and other game logos are unaffected. This is a build-time setting.

```powershell
.\build_atari.bat scannerlogo=no
```

The root `build_atari.bat` currently supplies `noprotect=yes commander=max laser=singlebeam aifiresound=no scannerlogo=yes`. Arguments passed on the command line override these defaults; the last occurrence of each option wins independently. Use `build_atari.bat commander=default` to build with the original starting balance.

The build uses the bundled `tools/vasmm68k_mot.exe` and `tools/vlink.exe` in the project root. It assembles all game modules from source, without using `src_orig` or old `.LTX` objects. It writes the game files to `output_atari/ELITE` and the floppy image to `output_atari/ELITE.ST`. Both assembler and linker run from `src_atari/build` with explicit output paths to prevent `a.out` from appearing in the root.

The floppy contains `AUTO/ELITE.PRG` for automatic startup when booting from drive A:. This variant of `boot.s` selects the current drive root before opening `LOADER.IMG`; all data and the manual `ELITE.TOS` launcher remain in the root. The directory distribution remains flat for manual startup from a hard-drive folder. The FAT12 verifier checks both the root files and the AUTO directory, including its dot entries and launcher bytes.

`src_atari/tools/convert_quelo.py` documents the one-time import of the original dialect. It now requires `--source-dir` pointing to a separately extracted copy of `resources/elite_atarist_source.zip`. **The normal build does not run it.** By default, it refuses to overwrite existing files. Its `--overwrite` option discards edits to converted files in `src_atari/asm` and is intended only for deliberately repeating the import.

The build automatically recalculates the new binary's checksum and assembles the checksum module a second time. There is no need to edit the historical `$5123` constant manually.

The link map is in `src_atari/build/elite.map`; verification results and output SHA-256 hashes are in `src_atari/build/verification.json`. See [ANALYSIS.md](ANALYSIS.md) for the memory layout, original architecture, and conversion details.


## Flight controls

`A`, left `Shift` and right `Shift` fire the player laser on Atari ST, with either mouse or joystick selected. Holding multiple fire keys does not increase the firing rate, and releasing one continues firing while another remains held. The Shift keys provide additional bindings to try with two simultaneous steering keys on the original keyboard.

Alternate retains its original hyperspace shortcut and does not fire the laser.

## Verification

Tests and original-file verification can be run independently:

```powershell
python -m unittest discover -s src_atari/tests -v
python src_atari/tools/verify_original.py
```

The build checks all external symbols, the embedded checksum, A6 relocation to the variable area, RAM and local-variable bounds, control-key ASCII values, data buffer capacities, the TOS header, and a full readback of the FAT12 floppy image. Tests also cover sensitive Quelo conversion details, including reused labels, the tenth macro argument, and OR conditions, as well as launcher placement under TOS 1.04 and error-message termination.

Viewport clearing uses three `MOVEM.L` stores per row (11 + 11 + 10 longwords), saving and restoring A2-A4 once per call. It clears the same 256 x 112 viewport and keeps the original VBL wait. Diagonal lines cache their two colour pairs in registers and preserve the caller's D7 counter. The original pixel selection, patterned colours and frame synchronization are retained.

The viewport uses inclusive logical coordinates `x=-128..127`, `y=-56..55`, matching the full cleared screen area `x=32..287`, `y=8..119` (256 x 112 pixels). Clipped lines and filled polygons reach both edge columns. Planets and other solid circles use the same bounds; sun flares are added before final clipping, so they cannot overwrite the cockpit border.

The starfield uses a native adaptation of the BBC/C64 Elite depth and recycling model. Each star is always one pixel, with nearby particles moving faster than distant ones. Front, rear and side views have their original distinct replacement rules; steering follows this game's 512-pixel object projection. The old direction lookup files are no longer loaded or distributed. See [STARFIELD.md](STARFIELD.md) for the original source references, scaling and validation.

Player and AI lasers use instant-hit beams. Player Beam and Military lasers now have distinct continuous firing sounds with short attack and release ramps; Pulse and Mining retain their original firing effects. Player colours depend on the weapon: Pulse red, Beam orange, Military white, and Mining instrument-bar magenta. AI beam colours follow player rating: Harmless through Poor is red, Average through Competent orange, and Dangerous through Elite white; Constrictor beams are always white; Thargoid and Thargon (Tharglet) beams are always light blue. Player damage per hit is unchanged; successful AI hits multiply the original base damage by a random 2, 3 or 4 to approximate repeated projectile damage. Player beam jitter is cosmetic: targeting stays at the crosshair centre. AI beams originate at each model's `gun_node`, with centred bow muzzles for Sidewinder, Gecko, Adder and Moray; even correctly aimed shots have a 10% chance to miss, preserving the beam and optional firing sound without causing damage. See [LASERS.md](LASERS.md) for weapon timing, targeting and CPU validation.

Sprite and bitmap drawing uses fixed left/right rotation loops from `asm/sprite_rows.inc`, including clipped sprites. It never patches executable instructions, avoiding stale rotation opcodes in the instruction cache of 68020 and later CPUs. Each rotation still uses at most eight steps on the 68000. This change concerns sprite rendering; compatibility with other Atari display hardware and operating systems requires separate testing.

The optional `tests/test_sprites.py` suite uses `unicorn==2.1.4`. It executes the actual Atari sprite routines on MC68000 and MC68020 CPU models with executable memory write-protected. Tests cover the original options icons and missile indicators, all sixteen horizontal shifts, clipped edges, both screen buffers and background restoration. Unicorn does not emulate instruction-cache coherency; write protection verifies that drawing no longer modifies code.

The optional `tests/test_raster.py` checks require `unicorn==2.1.4` (`python -m pip install unicorn==2.1.4`); they are skipped when it is absent. They assemble and execute the actual MC68000 raster routines and compare guarded buffers against a pixel reference, covering viewport clearing, the flyback wait, preserved registers, all line directions, 120 panel colour patterns, 16 solid colours, word boundaries and both screens. These checks do not measure gameplay frame rate. The normal game build has no new package dependency.

The optional CPU tests in `tests/test_viewport.py` also require `unicorn==2.1.4`. They check full-width clipped lines and polygons, planets and sun flares at viewport boundaries, and large unclipped circle spans. Entire guarded screen buffers are compared with a pixel reference. `tests/test_starfield.py` verifies depth-based motion, all four views, retro rockets, rotation, recycling, and one-pixel stars on MC68000 and MC68020 CPU models.

Use `src_atari/tools/run_hatari.py` to repeat the startup diagnostic. It requires a separately installed Windows [Hatari 2.6.1](https://www.hatari-emu.org/download.html) and your own TOS ROM. Supply their paths as arguments; the emulator is not copied into the repository:

```powershell
python src_atari/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img'
python src_atari/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img' --floppy
```

The script uses the game from the root `output_atari` directory and stores screenshots and diagnostics separately in `src_atari/build/hatari-test/harddrive` and `src_atari/build/hatari-test/floppy`. The floppy diagnostic uses the real TOS AUTO scan; only the hard-drive diagnostic uses desktop autorun. It runs without a window, write-protects the game disks, and does not save settings to the user profile. Assess the result using the screenshots and logs; the emulator's exit code alone does not confirm that the game works. The normal build does not run the emulator (`runtime_tested: false` in its report).

## Optional assembler and linker rebuild

The normal build uses the bundled executables and does not need this step. Rebuilding the assembler and linker themselves requires Visual Studio 2022 or Build Tools with the C++ tools and Windows SDK:

```powershell
.\src_atari\tools\setup-toolchain.ps1
```

The script verifies the SHA-256 hashes of the archives in `src_atari/vendor`, extracts them to `src_atari/build/toolchain`, builds the tools with MSVC and a statically linked C runtime (`/MT`), and copies the resulting executables to the root `tools` directory. If archives are missing, it downloads them from the official site. Versions and hashes are recorded in `src_atari/tools/toolchain.json`; the script rejects changed upstream content until it has been reviewed. Extracted sources and objects therefore remain among the ignored build files.

The upstream license terms are included beside the executables: [vasm](../tools/vasm-LICENSE.txt), [vlink](../tools/vlink-LICENSE.txt). The original archives remain in `src_atari/vendor`. See [tools/README.md](../tools/README.md) for the bundled binaries, and the [vasm](https://sun.hasenbraten.de/vasm/) and [vlink](https://sun.hasenbraten.de/vlink/) sites for official documentation.
