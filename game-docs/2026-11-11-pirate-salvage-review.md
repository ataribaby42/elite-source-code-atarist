# Pirate salvage integration review — 2026-11-11

## Scope and result

Reviewed the independently implemented Atari ST and Amiga salvage modules and
their integration with spawning, combat, police, cargo handling, object reuse,
Scramble ID, escape pods and station-trader hyperspace. Standard `ELITE` and
`ELITE_ALT` images were rebuilt for both platforms. Amiga validation uses the
ordinary framed PAL 68000 build, not the full display/CPU release matrix.

One gameplay defect was reproduced and fixed on both platforms. No other
actionable defect was found in the reviewed paths. The verification below is
targeted integration/regression testing, not a complete mission playthrough.

## Fixed: retaliation could reactivate an abandoned pirate hull

An encounter pirate could be attacked, escape in its capsule, and leave an
abandoned hull carrying its original encounter identity. Subsequent player
theft or destruction of the group's cargo selected that hull as a surviving
group member. The retaliation hook replaced `LOG_ABANDONED` with `LOG_ATTACK`
even though its attack type was `ACT_NOTHING`.

`loot_provoke_group` now requires `ACT_ATTACK` before provoking a member. Live
collectors, waiting pirates, departing pirates and pirates already fighting
remain eligible. An escaped pilot's hull keeps its inert drift behaviour.

The added `native_pirate_loot_abandoned.py` suite executes a real Viper
interruption and real capsule launch, then tests player cargo scooping, laser
destruction and missile destruction. The active partner retaliates; the
abandoned hull and an unrelated encounter remain unaffected. The probability
stub applies only to the single escape decision; capsule direction and creation
use the actual RNG.

Before the fix, the scoop case failed with one capsule present, hull attack type
zero and hull logic 6 (`LOG_ATTACK`) instead of 40 (`LOG_ABANDONED`). The failing
RAM image and payload are retained under
`src_atari/build/pirate-loot-qa/review-20261111/abandoned-before-fix`.

## Reviewed integration boundaries

- **Police and factions:** collectors retain pirate identity. Vipers acquire
  them in pending, collecting and departing modes. Actual police hits cancel
  collection and release reservations. Collection does not disable police AI.
- **Reservations and lifetime:** both ends retain object pointers and lifetime
  serials. Destroying, removing or recycling cargo/owners cannot transfer a
  reservation to an unrelated object. Only one pirate can own a barrel.
- **Player interactions:** successful scooping and player-caused laser, missile
  or collision destruction provoke the tagged group. Failed scoops by
  themselves, nonlethal cargo hits, NPC kills and unrelated cargo do not.
  Provocation revokes the group's Scramble ID neutrality.
- **Collection and accounting:** NPC pickup has no player hold, cash, score,
  mission or equipment side effects. Deferred removal still owns object
  counters; a consumed barrel becomes non-colliding immediately, preventing a
  second pickup later in the same frame.
- **Capacity and movement:** each pirate retains its four-container lifetime
  limit. Collection uses `floor(VEL_MAX / 5)` without changing the model maximum.
  Departure and combat resume normal acceleration. The approach has a bounded
  5,120-step timeout and releases its reservation on exit.
- **Spawning:** ten possible count combinations cover 4–8 containers and 1–2
  pirates. Fewer than five free slots suppress creation; scarce capacity reduces
  cargo to four before reducing pirates to one. Other encounter weights,
  formations, mission guards and partial-spawn rules retain their existing
  behaviour. Actual groups use independent 1–2 cargo speeds and compact debris
  positions, with separated pirate approach positions.
- **Memory layout:** the 30-byte transient salvage extension precedes the model
  header. Object copies and header copies operate on bytes; pool clearing uses
  words. The even 250-byte object size therefore does not truncate these
  operations. Model header layout and commander serialization are unchanged.
- **Older gameplay:** regression suites cover trader departures, Scramble ID,
  AI systems and laser bursts, missile provocation/target loss/collisions/impacts,
  ordinary death cargo, station destruction, radio, condition and cloaked cargo.

## Verification

All emulator runs use private executable/configuration/disk copies on verified
separate hidden Windows desktops. No user emulator session is controlled, and
nothing is written to G:. WinUAE uses KS1.3, MC68000, 512 KB Chip RAM and 512 KB
slow RAM. Atari uses a private 1 MB Hatari ST instance.

| Final-build verification | Atari ST | Amiga |
| --- | ---: | ---: |
| Salvage feature suites, standard artwork | 286 passed | 286 passed |
| Salvage feature suites, alternate artwork | 286 passed | 286 passed |
| Existing integration regressions, alternate artwork | 1,018 passed | 1,018 passed |
| Native scenario total | **1,590 passed** | **1,590 passed** |
| Python checks | 34 passed, 1 skipped | 35 passed, 1 skipped |

Feature totals include real movement/rendering scenes, all 100 salvage decision
outcomes, 128 actual RNG groups, slot-boundary cases, real pursuit from multiple
directions, speed transitions and the new abandoned-hull regression. Repeated
vectors within a scenario are not counted as additional scenarios. The Python
skip is the existing historical-artwork identity check for customized assets.

Final per-suite reports, source hashes, image hashes and build logs are under
each platform's `build/pirate-loot-qa/review-final`. The aggregate checker is
`src_atari/build/pirate-loot-qa/report_review.py`. It verifies that distributed
images match the tested images and that all recorded source hashes still match.
All checks passed on the final distributed bytes. The maximum-group scene
comparison was visually inspected and is retained at
`src_atari/build/pirate-loot-qa/review-final/large-scene-comparison.png`.
The historical source archive retains SHA-256
`19496256fb315c5db71c92385783acf4590a682ee3aae0c6a3435d0ea5faa1e2`.

A full host disk interrupted several diagnostic runs. These are infrastructure
failures, not passed gameplay tests. After the user freed space, final-image
verification completed successfully, including every interrupted scenario.
The WinUAE harness cleanup now closes its owned emulator
even when writing the diagnostic transcript fails. Three interrupted owned
instances were explicitly closed using their verified private executable paths.
Working Amiga QA files were compressed losslessly to reduce their disk usage.
The revised cleanup path also passed three injected checks: normal exit, a
transcript write failing with disk-full, and a handle-close failure.

## Existing design limits

- Ordinary destruction cargo still drifts at 3–6. A slow pirate under the 20%
  collection cap can fail to catch a fast ordinary barrel and eventually stop
  trying. The new encounter uses the agreed 1–2 range and passes moving-cargo
  pursuit tests. Ordinary destruction-drop speeds were not changed.
- A single pirate can leave cargo behind in a group larger than four containers;
  this follows its existing four-container capacity.
- Collected cargo is counted, not stored as an NPC commodity inventory. Destroying
  the collector uses the original model's cargo-drop rules.

## Encounter frequency

The new template has weight 1. Eligible custom-template weights total 13 in
Anarchy, 16 in Feudal systems and 19 in other governments. Including the 50%
ordinary-wave substitution gives approximately:

| Government | Chance per eligible ordinary pirate wave |
| --- | ---: |
| Anarchy | 3.85% (about 1 in 26) |
| Feudal | 3.13% (about 1 in 32) |
| Other governments | 2.63% (about 1 in 38) |

This is not a fixed elapsed-time schedule. Station proximity, existing pirates,
free slots and named-mission routing constrain actual creation. Timed waves and
torus interruptions use the same ordinary-wave selector.

## Retired forced-encounter disk and manual cleanup

The temporary distribution
`output_amiga/ELITE_LOOT_TEST.ALT.FRAMED_PAL.68000.ADF` and its matching output
directory were already absent when cleanup began. Normal production sources
retain random selection. Historical report/render helpers no longer require the
forced disk; image renderers use normal-build captures instead.

Automatic approval review rejected deletion of the private test tree, including
an exact-path attempt, reporting only `blocked by policy`. The user subsequently
removed that tree; its absence was verified during the review. These remaining
obsolete scripts are safe for the user to delete:

```text
E:\Development\github\elite-source-code-atarist\src_atari\build\pirate-loot-qa\update_count_tests.py
E:\Development\github\elite-source-code-atarist\src_atari\build\pirate-loot-qa\implement_debris.py
E:\Development\github\elite-source-code-atarist\src_atari\build\pirate-loot-qa\update_slow_cargo.py
```

The removed directory contained the private forced source/build, bootable disk
copies, emulator copies and forced-routing tests. The three remaining files are
obsolete one-time patch generators with dependencies on that private tree. Keep the ordinary
`pirate-loot-qa` directories and `src_*/tests/native_pirate_loot*.py`: they provide
the reusable normal-build regression tests and retained review evidence.
