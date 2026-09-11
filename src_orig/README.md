# Preserved original Atari ST Elite

This independent source tree reconstructs the original Atari ST version from
`resources/elite_atarist_source.zip`. It replaces the former raw
extraction. All 307 extracted files were checked against both the ZIP CRCs and
the original SHA-256 manifest before conversion. The untouched ZIP remains the
archival copy, including historic tools, objects, source encodings and line endings.

## Build and run

From the project root on Windows x64 with Python 3.10 or later:

```powershell
.\build_orig.bat
```

The build uses the bundled root `tools/vasmm68k_mot.exe` (vasm 2.0f) and
`tools/vlink.exe` (vlink 0.18a). It needs no extra Python packages, ZIP extractor,
historical assembler, or sibling game sources. It always assembles `asm` directly;
it neither regenerates those files nor links the old `.LTX` objects.

| Path | Contents |
| --- | --- |
| `asm/` | 39 converted original game modules, shared definitions, macros, loader, font and ship data |
| `assets/` | Eight byte-identical original assets, including `DCOS.DAT` and `DSIN.DAT` |
| `modules.txt` / `elite.ld` | Original module order and translated memory layout |
| `build.py`, `build.bat`, `build.ps1` | Independent build and Windows entry points |
| `tools/` / `tests/` | Converter, archive verifier, disk builder and regression checks |
| `original-sha256.json` / `original-archive.json` | Historical file hashes and import provenance |
| `build/` | Ignored objects, maps, logs and verification results |
| `../output_orig/ELITE/` | Runnable game distribution |
| `../output_orig/ELITE.ST` | 720 KB FAT12 floppy image |

Start `ELITE.TOS` from the distribution folder, or mount `output_orig/ELITE.ST`
in an Atari ST emulator and start `ELITE.TOS` from drive A:. Keep the game files
together. Manual startup also works from a hard-drive folder; commander files
use the current directory. The original-version disk does not add an AUTO launcher.

Optional tool overrides are supported:

```powershell
.\build_orig.bat -Python C:\Python\python.exe
.\build_orig.bat -Vasm C:\Tools\vasmm68k_mot.exe -Vlink C:\Tools\vlink.exe
python src_orig/build.py --vasm C:\Tools\vasmm68k_mot.exe --vlink C:\Tools\vlink.exe
```

There are no gameplay options such as `commander=max`, `noprotect=yes`, `laser=`,
`aifiresound=` or `scannerlogo=` in this preserved build. The default commander
has 100 Cr and is Harmless; the novella question and integrity check remain enabled.
The original projectile weapons, AI, starfield, speed changes, control damping,
sound, raster routines and ship models are retained. In particular, the original
self-modifying sprite code remains: the target is MC68000, not CPUs with caches.

## Conversion scope

The 48 converted source/data files come directly from the archive. Quelo
structured conditions, macros, structure offsets, character literals and exports
are translated into vasm syntax while preserving the source algorithms. No
enhanced gameplay code is copied from `src_atari` or `src_amiga`.

Two build adapters are added: `workspace.m68` anchors vlink's BSS relocations,
and `boot.s` creates a valid TOS launcher. The launcher uses `$11E00` from the
original `LOADER.LNK`, resolving its inconsistency with the old `ELITE.S` file.
`elite.ld` preserves the old workspace, including the two dust lookup buffers.
The checksum is recalculated after linking; no protection logic is bypassed.

This is a source reconstruction, not a promise of byte-identical executable code:
the assembler, branch encoding and launcher differ from the historic toolchain.
The rebuilt `OBJECTS.IMG` and `ELITECHR.IMG`, and all eight copied assets, must
match the historical SHA-256 hashes or the build fails.

## Verification

```powershell
python -m unittest discover -s src_orig/tests -v
python src_orig/tools/verify_original.py
```

The build verifies module linking, the embedded checksum, A6 workspace relocation,
RAM and module-variable limits, keyboard ASCII constants, asset sizes, the TOS
header and every file in the FAT12 disk. Tests cover conversion details, launcher
execution when optional `unicorn==2.1.4` is installed, and original source fidelity.
They do not establish full gameplay or real-hardware compatibility.

The initial preserved build is 84,514 bytes with checksum `$B02D`, entry `$12000`,
and all original game data intact. Current results are in `build/verification.json`.

To deliberately repeat the import, extract the ZIP with an extractor that supports
its legacy Shrink/Implode compression into an ignored build subdirectory, then use
`tools/convert_quelo.py --source-dir <extracted-directory> --overwrite`. This
explicit operation replaces converted files; ordinary builds never do so.

Original author credits and legal information are in the [main README](../README.md#legal-information-and-credits).
