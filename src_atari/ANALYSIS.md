# Analysis of the original code and port

## Original build

`ELITE.M68` credits the conversion to Rob Nicholson / Mr. Micro, with a 1988 base and version 1.1 changes from March 1990. `ASM.BAT` uses the `m68k` preprocessor and `a68k` assembler; `LINKIT.BAT` invokes `qlink`. `HEADER.M68` includes shared definitions and the intermediate `TEMP.A68` file. The surviving `.LTX` files are old binary objects, not additional source text.

`ELITE.LNK` specifies 39 modules and an absolute address of `$12000`. Code is followed by image and working buffers, a second screen aligned to 32 KB, bitmaps, ship geometry, tables, and the variable area. Register A6 is the base for shared and module-local variables. Parts of the renderer modify their own instructions, so the build targets the 68000 and disables assembler optimizations.

| Area | Main modules |
| --- | --- |
| Startup and system handling | ELITE, INIT, BIOS, EXCEPT, DEBUG |
| 3D world and rendering | VECTOR, ROTATE, GRAPHICS, SPRITES, PDATA, DUST, SPECIAL |
| Flight and combat | MAIN, FLIGHT, LOGIC, AUTO, ORBIT, COMBAT, RADAR |
| User screens and trading | ATTRACT, COCKPIT, GALAXY, ACTION, CARGO, EQUIP, OPTIONS, DISK |
| Content and effects | DATA, FUNNY, MISSIONS, MUSIC, SOUNDS, EFFECTS |
| Program integrity checks | CHKSTART, CHKEND, CHECKSUM, NOVELLA, empty TWEAK |

## Dialect conversion

- `if / else / endi`, `repeat / until / endr`, `while / endw`, and `break` become ordinary conditional branches with unique labels. OR preserves evaluation order. Labels inside macros use `\@`.
- Original shared macros use the `q_` prefix to avoid collisions with vasm directives. `subr` creates a label and exports it when requested. Vasm `NARG` replaces `nargs`, and `mexit` replaces `exitm`.
- `offset / ds` definitions for structures and variables use `rsset / rs` and the `__RS` counter. Standalone labels in structures are absolute offsets. Words and longwords are aligned to even addresses, not four-byte boundaries.
- `db` becomes `dc.b`, and `dz <text>` becomes a NUL-terminated string. Spaces within strings and comma-separated data lists are preserved. Comments following operands receive an explicit semicolon.
- Quelo expressions such as `'A'>>8` and `'7'/256` become direct ASCII literals. Without this change, some keys and numeric input would evaluate to zero.
- `-allmp` enables the tenth macro parameter used by the vector cross product. Negation of a negative argument is parenthesized. Exported names are normalized because the linker is case-sensitive.

## Linking and loader

`elite.ld` translates the memory layout from `ELITE.LNK`. The helper `workspace.m68` creates an actual BSS section: without it, vlink would not correctly relocate symbols reserved only by the linker script. Buffers are not written into `ELITE.IMG`.

The original `ELITE.S` loads and starts the loader at `$F000`, while the surviving `LOADER.LNK` specifies `$11E00`. The build uses `$11E00` from the linker file. The loader is 390 bytes long and fits in the 512-byte gap before the game at `$12000`. The new `boot.s` creates a valid TOS program and checks both memory availability and loader reads. The game loader itself remains derived from `LOADER.M68`.

The first build incorrectly used `$F000`. When reproduced in Hatari with TOS 1.04 DE, the process basepage was at `$F0F8` and launcher code started at `$F1F8`, so the guard rejected startup before opening `LOADER.IMG`. The corrected launcher ends at `$F368`, safely below `$11E00`. Error strings are NUL-terminated as required by GEMDOS `Cconws` and split for a 40-column display; the earlier incorrect dollar-sign terminator caused two messages to run together.

The checksum module is outside the region between CHKSTART and CHKEND. The build first links the whole game, sums the bytes in that region modulo 65536, assembles CHECKSUM with the new constant, and links again. It verifies that the second pass did not change the protected region and that the constant was actually embedded in the instruction.

## Verified results

- Game code: 84,514 bytes, entry point `$12000`, checksum `$B02D` with the default sources.
- Second screen: `$28000`; variable base: `$6F16E`; end of used variables: `$72C76`, below the standard 512 KB ST screen at `$78000`.
- The initial rebuild of `OBJECTS.IMG` and `ELITECHR.IMG` matched the surviving originals. `ELITECHR.IMG` still matches. The working `OBJECTS.IMG` now contains centred muzzle definitions for Sidewinder, Gecko, Adder and Moray, including two additional nodes; its reserved buffer is 20,172 bytes.
- Eight ready-made data files are taken from copies in `assets`; their contents match the originals. The bitmap package is not currently regenerated using the helper C tools.
- The output floppy contains all files; its directory and FAT chains have been read back and compared byte for byte.
- The corrected build, started from both A: and C: in Hatari 2.6.1 with TOS 1.04 DE and 1 MB RAM, loaded game data and displayed the novella question. The `tools/run_hatari.py` diagnostic script can repeat this check and stores screenshots and GEMDOS traces in the ignored `build/hatari-test/{floppy,harddrive}` directories. This verifies startup and data loading, not full gameplay or compatibility with every TOS version.
- `ELITE.IMG` is not expected to be byte-identical to the historical binary: the build process and some branch lengths have changed. Remaining game behaviour still needs verification in an emulator or on real hardware. The original novella protection and program integrity check remain enabled.

Current values for each subsequent build are recorded in `build/verification.json`. The initial SHA-256 snapshot of all 307 historical files is in `original-sha256.json`. The raw files are preserved in `resources/elite_atarist_source.zip`; the verification script now verifies that archive because `src_orig` contains an independently buildable conversion.
