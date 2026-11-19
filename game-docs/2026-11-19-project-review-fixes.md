# Project review fixes and verification — 19 November 2026

All four findings from the [whole-project review](2026-11-19-project-review.md) have been corrected. The standard Atari and Amiga ELITE and ELITE_ALT distributions were rebuilt and tested. No files on G: were updated.

## Changes

### Amiga rendering synchronization

`src_amiga/asm/system.m68`, `wait_clear`, now retains blitter ownership and the pending-clear state until the hardware reports completion. The fixed CPU-iteration timeout has been removed. Both busy-register reads remain, including the check for a late busy indication.

This prevents a still-running clear from erasing subsequent CPU drawing in accelerated emulation. The change preserves the existing register contract and frame-time accounting. It does not alter planet geometry, colors or other drawing content.

### Unsigned cash on both platforms

Each independent `ships.m68` now contains the same local `ship_cash_delta` routine. Hull purchase first calculates the net price after trade-in, avoiding an overflowing intermediate `cash + trade-in` sum. Positive charges use an unsigned affordability check; negative charges are refunds and do not use the sign of the resulting balance as an error condition.

Hull trade-in refunds, laser replacements and equipment sales now saturate at the existing 32-bit cash maximum, 429,496,729.5 credits, if a refund would exceed it. They cannot wrap the balance towards zero. Ordinary prices, resale percentages and equipment/hull eligibility rules are unchanged. Failed purchases retain the original balance and equipment. The save format is unchanged.

The transaction implementation matches between Atari and Amiga without introducing shared source imports or platform switches.

### POSIX build argument handling

`src_amiga/build.sh` preserves arguments as an argument vector, including tool paths, spaces, quotes, wildcard characters and empty values. Interpreter/tool options consume their values explicitly; missing values produce an error. Display selection retains the last supplied value and forwards it as one argument.

The root release wrapper also preserves the user argument vector. Each release entry retains its own output name and display, and the double-scan entries still select 68020. The test wrapper passes its defaults as separate arguments, preserving user overrides. Default two-image and 18-entry release dispatch behavior is covered using stubs, without building the full release matrix.

## Verification

### Regression results

| Configuration | Suites passed | Named scenarios passed |
| --- | ---: | ---: |
| Atari ELITE_ALT, complete applicable suite set | 85 | 13,577 |
| Atari ELITE, focused regressions | 11 | 4,790 |
| Amiga ELITE_ALT, complete applicable suite set | 86 | 13,610 |
| Amiga ELITE, focused regressions | 11 | 4,846 |
| Amiga ELITE_ALT, additional real-speed/cycle-exact 68000 graphics checks | 2 | 288 |
| Amiga ELITE_ALT, additional 68020 runtime checks | 7 | 4,377 |
| Total | 202 | 41,488 |

The total counts suite/configuration runs. Initial failed attempts, duplicate pilot runs and pre-fix probes are excluded. No remaining failure was found in the applicable final runs.

Both graphics asset sets passed the 3,584-case cash boundary suite and the four exact reproduction/save cases on each platform. The additional 68020 run also passed the cash boundary suite. Coverage includes every ordered exchange between distinct player hulls, all four laser types on every hull, and buying/selling equipment across every price category. Cases cover insufficient funds, exact affordability, signed-boundary crossings, zero-cost replacements and refund saturation.

The original reproductions now produce the expected results:

- Cobra to Asp at cash `$FFFFFFFF`: succeeds with 4,286,617,295 internal tenths remaining.
- Pulse purchase at `$80010000`: succeeds with 2,147,545,184 internal tenths remaining.
- Military-to-Pulse replacement at `$7FFFFFFF`: succeeds with 2,147,509,647 internal tenths remaining.
- Maximum unsigned cash and a purchased laser survive the existing save/restore routines.

The full suites also exercise police and bounty-hunter targeting, pirate cargo collection and provocation, trader hyperspace, planet rendering and rotation, missiles, station collisions, docking, radio, cargo missions, ship graphics and UI transitions. The focused ELITE suites cover cash, player ships, planets/cursor, stations, bounty-hunter interactions, radio rendering, viewport bounds, shield flashes and return from menus.

All 30 post-click shipyard cursor captures on each platform matched their corresponding base image byte-for-byte. The two base captures per platform are retained alongside these comparisons.

### Amiga timing and rendering paths

The formerly failing viewport and shield-flash suites pass in maximum-speed WinUAE without cycle accuracy, using the actual rebuilt game with no diagnostic instruction patch. They also pass with real-speed, cycle-exact 68000 timing.

The standard 68000 executable was additionally tested on an emulated 68020. Runtime inspection confirmed CPU level 2 and the CPU clearing path (`clear_blit=0`). These checks cover cash, player ships, viewport bounds, planet surfaces, shield flashes, UI return and radio rendering. The real-speed 68000 run used the blitter path.

The F7 cursor and Pulse-audio hardware-timing tests use cycle-exact timing. An initial Pulse-audio run used the unrestricted-speed configuration despite its explicit cycle-exact requirement; its unchanged assertions passed when rerun with the required configuration. No audio production code was changed.

### Build and unit verification

- Atari: 36 unit tests passed, one optional custom-PNG identity test skipped.
- Amiga: 43 unit tests passed, one optional custom-PNG identity test skipped. The five shell-wrapper tests were rerun after the final shell edit and passed.
- Preserved original: all 12 unit tests passed, including all 307 archive members and 48 converted sources.
- Total: 91 unit tests passed and two optional tests skipped.
- A real root shell build, using assembler and linker executable paths containing spaces, successfully produced both standard Amiga distributions. This exercised the shell wrappers with the Windows toolchain; it was not a Linux-native toolchain run.
- Final disk-image bytes match the frozen build copies used for native testing.

All emulator runs used agent-owned executable/configuration/disk copies on verified separate hidden Windows desktops. Test processes were closed after completion. One Atari emulator initially failed to create its private window within the startup deadline; its debris regression passed on a separate rerun. The long Atari cash suite required a larger execution budget because it repeatedly regenerates ship portraits; both graphics builds then completed successfully without bypassing rendering or weakening assertions.

## Outputs and evidence

Updated distribution images:

- `output_atari/ELITE.ST`
- `output_atari/ELITE_ALT.ST`
- `output_amiga/ELITE.ADF`
- `output_amiga/ELITE_ALT.ADF`

Their corresponding distribution directories were updated as well. Other Amiga graphics variants were not rebuilt. No Git operations were performed, and the changelog and preserved original gameplay were not changed.

Detailed logs, initial failures, reruns and private test configurations are retained under each enhanced tree's `build/project-review-fixes-2026-11-19` directory. The consolidated scenario index and image hashes are in `src_atari/build/project-review-fixes-2026-11-19/consolidated-results.json`.

The historical archive remains byte-identical, with SHA-256 `19496256fb315c5db71c92385783acf4590a682ee3aae0c6a3435d0ea5faa1e2`.

The full 18-image Amiga release matrix, specialized wide/Fast-RAM shadow-buffer configurations, physical hardware and complete mission playthroughs were not rerun. The results above apply to the explicitly tested configurations.
