# Whole-project review — 19 November 2026

Follow-up: all four findings below have now been corrected and verified. See [Project review fixes and verification](2026-11-19-project-review-fixes.md). The findings and initial-review change list below describe the pre-fix review state.

## Scope and result

This review covers the current project from its historical source baseline, including the original-source conversion, Atari enhancements, independent Amiga port, gameplay additions, rendering, build scripts and documentation. It is a comparison of the current implementation with the preserved original, not a reconstruction of individual commits. No version-control commands were used.

Four defects remain open: an Amiga blitter synchronization failure under accelerated emulation, two unsigned-cash transaction errors shared by both enhanced versions, and argument splitting in the Amiga Linux build wrappers. Windows build-wrapper defects and inaccurate documentation were corrected during the review. No game assembly source was changed.

The regression runs passed 21,791 named native scenarios in the configurations described below. This does not invalidate the additional failing edge-case probes documented here, or establish correctness for every hardware and display configuration.

## Open findings

### P2 — Amiga can release an unfinished viewport clear

Location: `src_amiga/asm/system.m68`, `wait_clear`, lines 607–625; particularly the bounded `DBRA` at line 614 and clearing of `clear_pending` at line 622.

After 65,536 unsuccessful busy polls, execution falls through to the completion path even if the blitter is still busy. The routine clears the pending flag and releases blitter ownership, allowing CPU drawing to overlap the unfinished clear. This can erase or alter newly drawn pixels.

The unchanged ELITE_ALT build reproduced framebuffer mismatches in both `native_viewport_bounds` and `native_shield_flash` with WinUAE configured as 68000, `cpu_speed=max`, and CPU/memory cycle accuracy disabled. A second unmodified control run failed again: the line test failed at case 1 and the shield test at case 65. The changing failure position is consistent with a timing-dependent fault.

As a diagnostic, changing only the polling-loop instruction from `DBRA` to an unconditional branch in the private emulator's RAM made all 216 viewport scenarios and 72 shield scenarios pass under the same accelerated settings. The distributed executable was not patched. Both suites also pass unmodified with cycle-exact, real-speed 68000 timing. This establishes an accelerated-emulation failure; reproduction on accelerated physical Amiga hardware has not been established.

Recommended correction: retain ownership and the pending state until completion is confirmed, or implement a recovery path that actually stops/drains the outstanding operation. A timeout must not be treated as successful completion. Test the eventual change on the additional supported Amiga CPU/display modes before release.

Evidence: `src_amiga/build/project-review-2026-11-19/blitter-control/ELITE_ALT` and `blitter-probe/ELITE_ALT`. The latter contains the exact diagnostic instruction bytes and is excluded from the normal pass totals.

### P2 — Ship purchase overflows an intermediate unsigned balance

Locations: `src_atari/asm/ships.m68:194` and `src_amiga/asm/ships.m68:191`, in `ship_purchase`.

The calculation adds the old ship's trade-in value to cash before subtracting the new price. The addition can wrap even when the final, net purchase cost is affordable and the correct final balance fits in 32 bits.

Reproduction on both platforms: an otherwise eligible Cobra commander with cash `$FFFFFFFF` buys an Asp. Cobra trade-in is 600,000 internal tenths and the Asp costs 8,950,000, so the correct remaining balance is 4,286,617,295 tenths. Instead, the intermediate addition wraps and the routine returns the insufficient-cash result, leaving the purchase unapplied.

Recommended correction: calculate the net charge/refund first, or retain the carry in a wider calculation. Define overflow handling separately for refunds that genuinely exceed the cash field's capacity.

### P2 — Laser purchase uses a signed test for unsigned cash

Locations: `src_atari/asm/ships.m68:322` and `src_amiga/asm/ships.m68:319`, in `ship_equip_transaction`.

The laser branch subtracts the signed net price and uses `BMI` to decide whether funds are insufficient. Cash is an unsigned 32-bit quantity, so a valid result with bit 31 set is incorrectly rejected.

Two reproductions returned the insufficient-cash result on both platforms:

- Buying a Pulse laser for 4,000 internal tenths with cash `$80010000`.
- Replacing a Military laser with a Pulse laser at cash `$7FFFFFFF`; the 26,000-tenth refund crosses the signed boundary but remains within the unsigned cash range.

Recommended correction: separate charges from refunds, use an unsigned affordability comparison for charges, and handle genuine refund overflow explicitly. These balances exceed approximately 214.7 million credits; ordinary balances are unaffected by the reproduced cases.

Evidence for both cash findings: `qa_cash_review.py` in each platform's review build directory, with results under `recheck/ELITE_ALT/cash-review`. These are observation probes recording actual return values and state, not successful correctness tests, and are excluded from the pass totals.

### P2 — Amiga Linux wrappers split quoted arguments

Locations: `src_amiga/build.sh:26`, `:29`, `:43`; also `build_amiga.sh:19` for the release path.

The scripts concatenate arguments into strings and expand them without quotes. This loses the original argument boundaries and permits wildcard expansion. A quoted `"outputname=Elite Review"` reaches Python as `outputname=Elite` followed by an invalid `Review` option. Explicit assembler/linker paths containing spaces have the same problem.

A private shell fixture reproduced the split using the actual wrapper scripts and an argument-recording interpreter stub. The Python filename validator accepts embedded spaces, so this is not an intentionally rejected output name. No Linux-native assembler run was performed on this Windows host.

Recommended correction: preserve the argument vector throughout the wrappers instead of serializing it into a shell string. Retain explicit display/default overrides without splitting user-supplied paths or values.

Evidence: `src_amiga/build/project-review-2026-11-19/shell-fixture/arguments.log`.

## Corrections made during this review

- The four root Windows build wrappers now stop and return a failed child build's exit code immediately. Previously, a later successful build could hide an earlier failure. Regression tests cover the ordinary two-build path and early, middle and final failures in the 18-entry release dispatch using stubs; the release matrix itself was not rebuilt.
- `src_amiga/build.bat` now finds `-Python` after prepended defaults, quotes the interpreter path, preserves the script location while scanning arguments, and handles the Python launcher argument separately. Both argument orders and paths containing spaces are tested. An actual root build using an explicit Python interpreter succeeded.
- README/build instructions and the jettison note now describe the current cargo speeds, cloaked-jettison behavior, default Linux root builds and supported display-name count. Existing text-encoding damage in the edited prose was corrected.
- Added `src_atari/tests/test_build_wrappers.py` and `src_amiga/tests/test_build_wrappers.py`.

No game assembly source, historical archive, preserved original gameplay, changelog or files on G: were changed. All test instrumentation and diagnostic patches remain under the appropriate `build` directories.

## Coverage

### Baseline and source review

The archive SHA-256 remains:

`19496256fb315c5db71c92385783acf4590a682ee3aae0c6a3435d0ea5faa1e2`

Original-version tests verified all 307 archive members and all 48 converted source files against the preserved archive and conversion rules. The original game built successfully and booted in an isolated Atari emulator to its original novella-protection question.

The source comparison identified 61 differing assembly-tree files between `src_orig` and `src_atari`, and 54 between Atari and Amiga. Review covered the differing platform startup, memory and display ownership, file/save handling, model/rendering routines, shared gameplay policies and build tooling. Gameplay parity checks distinguished platform-specific drawing/input/timing code from AI, cargo, courier and registration behavior.

Areas reviewed and exercised include:

- Planet optimizations, procedural geography, horizon/span clipping, F7 cursor handling, UI-to-flight presentation and rotation using the status-screen clock.
- Player hulls, equipment transactions, flight limits, shields, model bounds, colors, cockpit and scanner presentation.
- Pirates, cargo reservations, scavenging encounters, drift/speed limits, player provocation, cloak/scrambled-ID interactions and reservation cleanup.
- Bounty hunters, station departures, police patrol/target relations, docking restrictions, trader hyperspace selection and cloud lifecycle.
- Missile guidance, collisions, target loss, death/cargo cleanup, station clipping and both station collision spheres across the player hulls.
- Radio transitions/rendering/audio, navigation locks, status conditions, special cargo/courier lifecycle, save extensions and original-commander compatibility.

### Builds and unit tests

Actual builds completed for Atari ELITE and ELITE_ALT, Amiga ELITE and ELITE_ALT in standard framed PAL/68000 configuration, and preserved original ELITE. The final four enhanced disk images are byte-for-byte identical to the initially built images used for native testing; the review fixes affect build control and documentation, not game binaries.

| Tree | Unit tests passed | Skipped |
| --- | ---: | ---: |
| Atari | 36 | 1 |
| Amiga | 38 | 1 |
| Preserved original | 12 | 0 |
| Total | 86 | 2 |

The two skips concern the optional custom-PNG identity fixture. The original source-fidelity checks ran and passed.

### Native emulator regression

| Platform/build | Suites passed | Named scenarios passed |
| --- | ---: | ---: |
| Atari ELITE_ALT | 83 | 9,989 |
| Atari ELITE | 6 | 866 |
| Amiga ELITE_ALT | 84 | 10,022 |
| Amiga ELITE | 6 | 914 |
| Total | 179 | 21,791 |

These are assembly test payloads executing the linked game routines after a real game boot, not a complete manual playthrough. ELITE_ALT received the broad suite set. ELITE received representative planet surface/cursor, player-ship, station-collision, radio-render and bounty-hunter regressions. Shared routines and the two graphics asset sets were also inspected in source.

The shipyard cursor suites additionally produced 32 snapshots per platform: both base images and all 30 subsequent images matched byte-for-byte after cursor removal. These snapshot comparisons are separate from the named-scenario count.

Emulators used private executable/configuration/disk copies and verified separate hidden Windows desktops. No user emulator session was controlled. Test processes were closed after execution.

Early failures caused by test infrastructure were investigated and rerun: insufficient execution budgets, debugger-pipe startup, missing relocated-Hunk/display-buffer addresses, breakpoint limits and capture progress accounting. The F7 cursor timing check was rerun with real-speed, cycle-exact 68000 timing because unlimited-speed rendering does not guarantee an intervening VBL. The viewport/shield accelerated failures were separately reproduced and retained as an open defect above; they were not dismissed as infrastructure failures.

Consolidated results, including the selected successful run for each suite, are in `src_atari/build/project-review-2026-11-19/consolidated-native-results.json`. Initial failure logs and subsequent reruns remain available in each platform's review directory.

## Limits and remaining work

- The full 18-image Amiga release matrix was not rebuilt or rerun. NTSC, wide, high-resolution/interlaced, double-scan and accelerated-CPU/Fast-RAM combinations therefore have source-review coverage, not new comprehensive runtime coverage here.
- `native_shadow_viewport` is not applicable to the standard framed 68000 configuration tested. Its specialized shadow-buffer/Fast-RAM setup was not executed and is not included in the pass totals.
- Physical Atari/Amiga hardware, extended soak testing and complete mission playthroughs were not tested.
- The preserved original boot check stops at the protection question; it is not an original-game playthrough.
- No end-to-end Linux build was run. The shell argument defect was reproduced independently of compilation.
- The four open findings above still require production fixes and focused follow-up validation. Passing ordinary regressions does not cover those additional failing cases.

Review evidence is retained under `src_atari/build/project-review-2026-11-19`, `src_amiga/build/project-review-2026-11-19` and `src_orig/build/project-review-2026-11-19`. The baseline inventory and final change audit identify exactly which existing project files changed during this review.
