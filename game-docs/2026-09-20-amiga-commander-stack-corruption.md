# Amiga commander loading: stack corruption

## Report and snapshot

After answering Y at the title screen, a failed commander load followed by a
successful retry could leave the launched game without stars. An earlier
occurrence also displayed `Drive malfunction` and unexpected scanner contacts.
Returning to the title screen and entering the game again cleared the symptom.

The supplied `nostars.uss` has SHA-256
`b46d3307eb237ff2e453e31bc1b622c95b37e30bde9682f52c68c7bafdd4f90b`.
Its compressed Chip and slow RAM chunks were examined as a memory dump.
The relocated executable matches the pre-fix build; the differences outside
relocation operands are the OS-maintained port and interrupt structures.

- `A6` / game variables: `$00C3F366`.
- `witch_space`, at `A6+$1614`: `$001B` (27).
- Adjacent `tharg_count`: 49; `witch_x`: 563; `tharg_max`: 0.
- The normal planet, station and sun are present. This is not a real misjump.
- The saved Stars option is enabled and `sky_enabled` is 1.
- The loaded commander is TOM, galaxy 0, system 129 (Zaonce). The loaded state
  and input buffer agree; this investigation found no damaged commander data.

Both sky and moving-star rendering skip nonzero `witch_space`. The same flag
selects Thargoid encounters and drive-malfunction logic. The title exit clears
it, explaining why re-entering the game repairs the visible symptom.

## Cause

The Amiga port retained `stack_size = 256`, allocated with `rs.l`: only 1024
bytes. The stack is immediately after object records and transient game state.
Unlike Atari's GEMDOS trap interface, this port calls AmigaDOS on the game's
execution stack.

The Kickstart 1.3 DOS bridge in the snapshot, at `$00C04CC4`, copies SP to D5,
subtracts `$05DC` (1500), aligns the result and uses it as the BCPL frame pointer.
That frame already starts below a 1 KB stack, before nested DOS work is counted.
The [Amiga ROM Kernel Reference Manual, Exec Tasks](https://www.theflatnet.de/pub/cbm/amiga/AmigaDevDocs/lib_21.html)
also specifies an additional 1500 bytes for DOS calls.

A private A500/KS1.3 WinUAE run reproduced an out-of-stack write while opening
the missing `DF0:TOM.CDR` from the title's load prompt. Comparing the last four
object slots before and during Open found 174 changed bytes, spanning offsets
`$13E3..$15F1` from the game-variable base. They include DOS return addresses,
the Open mode `$03ED`, and the commander pathname. These are not game objects.
The affected addresses are below the stack's `$1656` lower bound.

The exact value 27 in `witch_space` was not reproduced in that run. The native
test establishes the underlying stack overrun; which nearby words are damaged
depends on the DOS path and call depth. Later object clearing can erase most
evidence while leaving adjacent transient fields damaged. Checking only SP or
the unused middle of the stack misses the separate BCPL frame.

## Fix

`src_amiga/asm/common.def` now reserves 1024 longwords, or 4096 bytes, for the
game stack. This adds 3072 bytes to the ordinary workspace without increasing
DMA/Chip-only allocations. It covers game calls, the BCPL frame and OS context
saves. The existing workspace-size and Kickstart Hunk checks still apply.

No unconditional witchspace reset is added: legitimate misjumps retain their
existing behavior. The commander format, AI routines, Atari tree and preserved
original tree are unchanged.

## Validation

Diagnostic scripts, memory captures and emulator transcripts are local build
artifacts under `src_amiga/build/nostars-qa`. Every emulator run uses a verified
private hidden Windows desktop, private WinUAE executable/configuration and disk
copies. The user's emulator and original save disk are not controlled or changed.

The Amiga Python suite passes: 31 tests, one existing skip for edited graphics.

Both `altgfx=no` (`output_amiga/ELITE.ADF`) and `altgfx=yes`
(`output_amiga/ELITE_ALT.ADF`) build and pass the Hunk, workspace, asset and OFS
readback checks. The minimum-memory A500 configuration boots with the extra
3 KB workspace.

The fixed default build was exercised in WinUAE with Kickstart 1.3, a real-speed
68000, PAL OCS, 512 KB Chip plus 512 KB slow RAM, and normal floppy speed (100).
The test answers Y at the title, attempts TOM on the game disk, dismisses the
missing-file error, inserts a private copy of the commander disk, loads TOM
through the single-click input path, and launches with F1. The monitored object
tail and witchspace fields remain byte-for-byte unchanged across both disk
operations. After launch, `docked=0`, `witch_space=0`, `sky_enabled=1`, and the
sky contains nine visible stars. The test process and hidden desktop are closed
afterward. Exact hashes and results are in `build/nostars-qa/runtime-verification.json`.
