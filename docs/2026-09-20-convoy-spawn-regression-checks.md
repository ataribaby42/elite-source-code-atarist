# Spawn regression checks after trader convoys

Date: 2026-09-20
Trees: `src_atari`, `src_amiga`.

## Result

No regression was found in the tested existing spawn paths. No gameplay code
was changed during this verification. Both default distributions were rebuilt.

The native checks executed the linked game's MC68000 routines in Hatari and
WinUAE A500 (Kickstart 1.3, 512 KB Chip RAM, 512 KB slow RAM). Every emulator
ran on a verified separate hidden Windows desktop with private disk copies;
the user's emulator sessions were not accessed.

| Suite | Atari | Amiga |
| --- | ---: | ---: |
| Existing spawns and object lifecycle | 49 passed | 49 passed |
| Cargo drift and mining | 5 passed | 5 passed |
| Salvage and exact-quantity recovery | 34 passed | 34 passed |
| Python build/data tests | 32 passed, 1 skipped | 30 passed, 1 skipped |

The skipped test checks historical binary graphics identity. It intentionally
skips when source PNG artwork has been customized.

## Existing paths covered

- Ordinary wave routing: all 256 coin values in all eight governments retain
  the 50/50 ambush/encounter split and the original timer reload.
- Mission guards `$15`, `$21`, `$41` and `$52`: all 256 coin values still take
  the original ambush path. Actual spawns produce the Constrictor, Cougar with
  two Asps, or Thargoid groups. Existing mission ships are not duplicated;
  the Constrictor still bypasses ordinary wave gates.
- Original pirate ambushes: minimum and maximum group sizes at ratings 0, 4
  and 8, full model speeds and immediate player targets. The direct
  post-hyperspace/torus ambush entry still calls `pirate_attack`.
- Witch space: only Thargoids spawn, the population cap is respected and the
  ordinary spawn timers and pending police launches remain untouched.
- Station launches: Vipers retain their arrest/scramble distinction and stay
  outside the random-patrol record checks. Mission `$52` launches Thargoids.
- Both shuttle models and their existing suppression gates; all five ordinary
  trader models both in deep space and from the station; asteroid creation.
- Player missiles, AI missiles aimed at the player, and AI missiles aimed at
  another ship retain targets, full missile speed and ammunition accounting.
- Thargon releases retain the mother slot and their distinct player-hit and
  AI-hit group sizes. Escape capsules and released cargo do not inherit a
  parent's convoy speed or exact cargo payload.
- Exhausted object pools reject spawns safely; one free slot permits a partial
  pirate squadron. Removing the last slot updates counters once, and reuse
  clears convoy state without disturbing the new object's model header.
- System creation after hyperspace and station departure still places planet,
  station and sun records correctly with the enlarged object stride. The
  alien station is retained for mission `$52`.
- Cargo checks include 4,608 salvage collections per platform, exact jettison
  and recovery, full holds, mining fragments, and drift speeds that remain
  stable through repeated cruise updates.

## Method and limits

The new spawn suite writes nonzero convoy and payload data into free slots
before calling the real spawn routines. This verifies that slot reuse and
record copying cannot accidentally apply the convoy's speed to another ship,
a missile, cargo or an escape capsule. It also checks spawned model headers
against the loaded model data.

Deterministic random inputs force routing and group-size boundaries; direction
vectors vary so the original orientation rejection loop can terminate. The
routing-only checks temporarily replace the two spawn destinations with
markers. Subsequent spawn checks restore and execute both real destinations.
System creation and the existing cargo suites use the real random generator.
Amiga model checks resolve the separate data hunk's relocated address.

Source comparison against the local pre-convoy backups confirms that the
existing spawn and station-police routines are unchanged. The only changes
to `main.m68` and `common.def` are clearing and allocating `convoy_speed`.

This is targeted regression coverage, not a complete mission playthrough or
proof against every possible interaction. The intended new encounter weight
and corrected government filtering are covered by the separate convoy suite.

## Artifacts

Each tree's `build/spawn-regression-qa` contains the native spawn suite, build
and Python logs, and logs from the cargo suites. The Atari native report is
`report.json`; the Amiga native report is `boot/report.json`.

The source audit is in `src_atari/build/spawn-regression-qa/source-audit.json`.
Detailed cargo reports remain in each tree's `build/cargo-drift-qa` and
`build/salvage-limits-qa` directories.
