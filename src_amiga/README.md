# Independent native Amiga version

This source tree started as a copy of the corrected Atari sources before the combined Amiga build was introduced. It retains the game logic and starfield fixes, with Amiga-specific rendering, sound, input, startup and file handling developed here. It builds independently of `src_atari`; neither target uses a platform switch or imports the other target's build script.

## Build and run

Run from the project root:

```powershell
.\build_amiga.bat
.\build_amiga.bat noprotect=yes
.\build_amiga.bat -Python "C:\path\python.exe"
```

`noprotect=yes` skips the novella question at startup. The default, `noprotect=no`, keeps it enabled. Other protection checks are unaffected. The last occurrence wins if the option is repeated; `python src_amiga/build.py` accepts the same options.

Python 3.10+ and Windows x64 are required. The build uses the root `tools/vasmm68k_mot.exe` (vasm 2.0f, Motorola syntax, MC68000) and `tools/vlink.exe` (vlink 0.18a). No additional Python packages are needed. `-Vasm` and `-Vlink` select alternative tool paths. `python src_amiga/build.py` is also supported. Unknown arguments, including `platform=amiga`, are rejected.

The build reads `resources/amiga/Elite 2.0.adf` without modifying it. Its checksum is validated before extracting the original boot block and 19 PCM sound samples. It produces:

| Path from the project root | Contents |
| --- | --- |
| `output_amiga/ELITE/` | Native Amiga Hunk executable `ELITE`, font, objects and game assets |
| `output_amiga/ELITE.ADF` | Bootable 880 KB OFS disk with all game files |
| `src_amiga/build/` | Objects, generated sound tables, logs, link map and verification report |

Target: **PAL OCS, MC68000, Kickstart 1.3, 512 KB Chip RAM plus 512 KB expansion RAM**. Boot the ADF in DF0:, or copy every file from `output_amiga/ELITE` into one writable directory, change to that directory in AmigaDOS and run `ELITE`. The original novella questions are enabled unless built with `noprotect=yes`. F1 launches, F2-F4 select the other flight views, F5/F6 show the charts, F9 shows status, F10 shows inventory, and minus opens the disk menu while docked. **Ctrl+F10 exits to AmigaDOS.**

## Native implementation

The raster routines write directly to the two screens used by Amiga display DMA. The original Atari word-interleaved framebuffer and the former frame conversion wrapper are absent.

Startup displays the Atari release's `TITLE.PC1` artwork while loading the game assets. It decodes directly into the primary Amiga screen with a native OCS palette. The secondary screen temporarily holds the compressed picture, then becomes the bitmap loader's disk buffer. Display refresh runs during loading; game clock, cursor and sound updates begin only after initialization. The game continues automatically when loading finishes, without requiring a key press. A missing or unreadable title file is skipped.

Screen swapping waits for the VBL handler to accept the rendered screen before reusing the previous display buffer. It preserves that VBL acknowledgement, so the next viewport clear does not wait for an extra refresh. The existing three-VBL gameplay frame limiter remains in effect.

- **Display:** 320 x 200, four planes, 16 colours. Each row contains four consecutive 40-byte plane rows. Pixel word addresses are `screen + y*160 + (x>>4)*2`, with plane offsets 0, 40, 80 and 120. Copper uses a bitplane modulo of 120. Two 32 KB Chip RAM buffers provide double buffering; a VERTB handler publishes the completed screen.
- **Drawing:** lines, polygons, text, sprites and their saved backgrounds, radar, scrolling text, chart circles and planet shading use the native plane addresses. DEGAS RLE artwork decodes directly into this row-interleaved layout. The asset palette is imported once into native 12-bit OCS colours. Game artwork and compact sprite assets remain derived from the Atari release.
- **Input:** an `input.device` handler supplies native Amiga raw keys and mouse movement. The keyboard tables and steering bindings use Amiga key codes directly. The vertical blank handler reads the joystick port and fire button. There is no ST scancode translation or IKBD packet emulation.
- **Sound:** `sounds.m68` drives Paula DMA using the 19 original Amiga samples. Audio samples and Copper data are allocated in Chip RAM. Music uses the existing Blue Danube note sequence with a simple looped waveform; effect timing and envelopes are simplified. This is not the original Amiga music replay engine.
- **Files:** `fileio.m68` calls AmigaDOS Open, Read, Write and Close with full 32-bit BPTR handles. Directory enumeration uses Lock, Examine and ExNext and returns commander filenames directly. It does not simulate GEMDOS traps, handle numbers or a DTA. The existing 256-byte commander format is retained.
- **Lifecycle:** Exec remains running for input and disk I/O. Startup saves the OS View and installs the handlers; exit removes them, closes open files, releases the directory lock and restores the OS display and Copper list. Relocatable Hunk sections replace the fixed Atari memory map. Each BSS Hunk stays below the Kickstart 1.x clearing limit.

Viewport clearing writes each 32-byte plane span with one MC68000 `MOVEM.L`. Vertical lines cache their masked plane colours; horizontal spans and block fills cache all four plane words. Diagonal lines cache both colour pairs and preserve the caller's D7 counter. These CPU optimizations retain patterned colours, inclusive line endpoints, viewport borders and the existing frame limiter.

Sprite and bitmap drawing uses fixed left/right rotation loops from `asm/sprite_rows.inc`, including clipped sprites. It never patches executable instructions, avoiding stale rotation opcodes in the instruction cache of 68020 and later CPUs. Each rotation still uses at most eight steps on the 68000. This addresses the CPU-side corruption of missile indicators and options icons; it does not establish full A1200/AGA hardware compatibility.

## Source layout

| Path within this directory | Purpose |
| --- | --- |
| `asm/system.m68` | Amiga startup, shutdown, Copper, frame presentation and input |
| `asm/fileio.m68` | Native AmigaDOS file and directory operations |
| `asm/raster.inc` | Native bitplane drawing and background save/restore primitives |
| `asm/graphics.m68`, `asm/bios.m68`, `asm/sprites.m68` | Raster geometry, text, sprites and cursor |
| `asm/sounds.m68`, `asm/workspace.m68` | Paula playback and relocatable game/Chip RAM storage |
| `asm/` | Independent game modules, definitions, font and ship data |
| `assets/` | Game artwork and lookup tables |
| `build.py`, `build.ps1`, `build.bat` | Build owned by this target |
| `tools/` | Original sound extraction, Hunk validation and OFS disk creation |
| `tests/` | Asset, Hunk and OFS regression tests |

The root `build_amiga.bat` forwards arguments here. Atari development and optional assembler/linker rebuilding remain under `src_atari`; normal Amiga builds only use the bundled executables in the root `tools` directory.

## Validation

The optional `tests/test_sprites.py` suite also uses `unicorn==2.1.4`. It executes the actual sprite routines on MC68000 and MC68020 CPU models with executable memory write-protected. Tests cover the original options icons and missile indicators, all sixteen horizontal shifts, clipped edges, both screen buffers and background restoration. Unicorn does not emulate instruction-cache coherency; write protection verifies that drawing no longer modifies code.

The build checks assembly/link diagnostics, relocations, required Chip RAM allocations, BSS sizes, module variable capacities, asset buffer capacities, the two-screen layout, original PCM checksums, and OFS disk contents read back byte for byte. Run the automated tests after building:

```powershell
python -B -m unittest discover -s src_amiga/tests -v
```

The optional `tests/test_raster.py` and `tests/test_startup.py` checks require `unicorn==2.1.4` (`python -m pip install unicorn==2.1.4`); they are skipped when it is absent. They assemble and execute the actual MC68000 routines. Drawing tests compare entire guarded screen buffers with a pixel reference, covering all line directions, the 120 panel colour patterns, all 16 solid colours, horizontal word boundaries, both buffers, viewport clearing, block fills and preserved registers. Startup tests check the title pixels and palette, disk-buffer reuse, display-only refresh during loading, transition to game refresh, and startup without a readable title. OS services are stubbed in the startup tests. This is CPU-level correctness coverage, not a WinUAE gameplay or frame-rate measurement. The normal game build has no new package dependency.

Runtime checks use an isolated WinUAE 6.0.3 instance with Kickstart 1.3, PAL OCS, a real-speed MC68000, 512 KB Chip RAM and 512 KB slow RAM. Evidence and the exact executable hash are recorded locally in `build/qa/runtime-verification.json`; screenshots are in the same generated directory. `build/verification.json` reports structural checks only and does not claim emulator coverage automatically.

The new native renderer has been exercised through the novella screen, title animation, commander status, launch, all four flight views, cockpit/radar, both charts and planet data. Native keyboard pitch controls and firing were exercised, and Paula sample addresses, lengths, periods and volumes were inspected. An existing commander loaded successfully; a new commander was saved, read back from the ADF as a valid 256-byte OFS file, listed in the catalog and reloaded. Ctrl+F10 restored the AmigaDOS screen and keyboard, with the game no longer present in the CLI task. Further runtime results are listed in the local verification record.

The audio shutdown fix was separately checked with WinUAE PCM recording at 48 kHz, stereo, 16-bit. Keyclick, laser, error and alert effects returned every channel to zero volume with audio DMA disabled; the following 14.69 seconds of recorded output contained only zero samples. Music fade and exit also produced a silent recorded tail. Evidence and the tested executable hash are in `build/audio-qa/audio-verification.json`. Playback mutes a channel and allows its sample clock to latch the change before disabling DMA. The delay observes the vertical byte of VHPOSR; comparing the complete register would count horizontal positions and end the wait too soon. Music rests remain muted during a fade.

Real hardware, extended gameplay, audible sound quality and the original Amiga music arrangements are not validated. The test configuration disables host audio, so Paula playback setup is distinct from a listening test. Mouse/joystick bindings need a physical-device play test.

Original game and asset credits and bundled tool licences are documented in the [main README](../README.md#legal-information-and-credits).
