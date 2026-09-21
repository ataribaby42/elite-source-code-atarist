# Random encounter spawn range audit and fix

Date: 2026-09-21
Trees inspected: `src_atari`, `src_amiga`.
Status: confirmed issue; reduced leader radius implemented in both trees.

## Finding

Before the fix, every one of the eight encounter templates could place a ship
beyond the fixed scanner radius of 24,576 units. A ship that is still cruising is then marked
for removal on its first AI update, before it has a chance to move inward.
In some cases the entire group is lost, including a peaceful trader convoy.

This is separate from the corrected normal-flight/torus dispatch: both entries
use the same `random_encounter` placement routines and share the problem.

## Causes

The original `encounter_place` rolled a nominal leader radius from 16,384
through 24,575. It made no allowance for either of these effects:

1. `orbit` uses integer sine/cosine values scaled by 256. Rounding means that
   the actual distance need not equal the nominal radius. For example, radius
   24,575 with angles 20 and 8 degrees produces coordinates
   `(22954, 3455, 8381)`. The game's own distance routine reports **24,679**.
2. `encounter_offset` places followers 1,000 units along the leader's stored
   axes without checking their final ranges. Even a perpendicular offset from
   a leader at `(24575, 0, 0)` puts the follower at distance **24,595**. The
   fourth member uses the stored Y axis, which `build_vector` initially chooses
   randomly; it has not yet been made perpendicular to the direction of travel.
   That offset can contain a substantial outward radial component. Templates
   3, 4 and 7 can create this fourth member.

Mirroring Z to place the group in front of the player and pointing its heading
toward the player do not correct these initial distances. `game_logic` computes
`obj_range` and runs AI before moving the object. `do_cruising` reaches the
shared cleanup in `do_abandoned`, which discards distances **greater than**
24,576. Equality remains inside the boundary.

Only one object slot retargets per game turn. An out-of-range ship can therefore
remain in its initial `log_cruise` state until this cleanup runs; turning to
combat cannot be relied on to prevent the loss.

## Native boundary checks

The diagnostic calls the linked game's `random_encounter`, `get_range`,
`retarget`, `do_logic` and `remove_objects` routines. System slots are reserved
as during flight. Retarget slot 0 is used, a valid game-loop state, so newly
created ships receive their initial cruise update before any combat transition.

There are 48 boundary cases: all eight templates, minimum and maximum group
sizes, and three placements. Controlled RNG outputs select only these boundary
inputs; placement, vector construction, model creation, distance calculation
and cleanup are the real game code.

| Placement | Leader distance | Follower distances at maximum group size | Result |
| --- | ---: | --- | --- |
| Nominal radius 16,384, axis aligned | 16,384 | 16,414; 16,414; 16,980 where present | Every ship survives |
| Nominal radius 24,575, axis aligned | 24,575 | 24,595; 24,595; 25,165 where present | Only the leader survives |
| Nominal radius 24,575, angles 20/8 degrees | 24,679 | 24,698; 24,698; 25,499 where present | Entire group removed |

These are before-fix results. The third/fourth columns describe the deterministic
test orientation, not a claim that every random orientation produces the same ranges.

## Actual-RNG sample

A second test restores the unmodified game RNG and generates 4,096 successive
groups in government 7, where every template is eligible. It applies the same
first-turn cruise/range cleanup and records a reproducible seed for the first
failure in each template.

| # | Template | Groups sampled | Groups with out-of-range ships | Ships immediately removed | Maximum distance observed |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 1 Thargoid, 1-2 pirates | 227 | 1 | 2 | 24,581 |
| 2 | 1 Thargoid, 1-2 traders | 213 | 2 | 5 | 24,647 |
| 3 | 1-2 pirates, 1-2 traders | 910 | 9 | 13 | 25,408 |
| 4 | 1-2 pirates, 1-2 Vipers | 708 | 7 | 9 | 25,319 |
| 5 | 1-2 pirates, 1 Viper | 666 | 2 | 5 | 24,597 |
| 6 | 1-2 pirates, 1 bounty hunter | 479 | 1 | 2 | 24,628 |
| 7 | 1-2 pirates, 1 bounty hunter, 1 trader | 455 | 7 | 14 | 25,282 |
| 8 | 1-2 traders in formation | 438 | 2 | 3 | 24,604 |
| Total | | 4,096 | 31 | 53 | 25,408 |

These counts demonstrate the issue with real random inputs. They are not a
universal gameplay loss rate: the selected retarget slot and game state affect
whether a particular ship enters combat before receiving its cruise update.

## Validation and artifacts

Before/after validation passed in Hatari with TOS 1.04 and 2 MB RAM, and in
WinUAE A500 with Kickstart 1.3, PAL OCS, a real-speed MC68000, 512 KB Chip RAM
and 512 KB slow RAM. All emulator diagnostics used private executables and
disk/configuration copies on verified hidden Windows desktops. No user
emulator session was accessed.

Both platforms produced identical before/after placement and cleanup results:

| Check, per platform | Before | After |
| --- | ---: | ---: |
| Boundary cases | 48 checked; every template can lose ships | All 48 retain every ship |
| Actual-RNG groups checked | 4,096 | 4,096 |
| Actual-RNG groups with out-of-range ships | 31 | 0 |
| Ships immediately removed in that sample | 53 | 0 |
| Farthest ship in that sample | 25,408 | 23,385 |

The actual-RNG template counts are identical before and after: the fix neither
adds random draws nor changes template selection. Python build/data checks
also passed: Atari 32 passed and 1 skipped; Amiga 30 passed and 1 skipped.
The historical-graphics identity check skips customized source PNGs.

Each source tree's `build/encounter-range-qa` contains the test scripts and a
private compiled game. The Atari after report is `range-report.json`; the Amiga
after report is `boot/range-report.json`. The `before` directory in each test
area retains the original report and source. Reports include per-ship
coordinates, ranges, removal masks and real-RNG reproduction seeds.

The `ELITE` and `ELITE_ALT` distributions were rebuilt for both platforms; their
game executables match the privately tested executables byte for byte. The
Amiga before/after executable differs in just one byte: the high byte of the
encounter radius range immediate changes from `$20` to `$18` (8192 to 6144).

## Implemented correction

Only the first ship's radius distribution changes. `encounter_range` is now
`radar_range - rand_limit - $800`, giving a nominal radius of **16,384..22,527**.
The 2,048-unit reserve covers formation placement, rounded trigonometry and a
small safety margin. The existing `rand_range` used by ordinary ambushes and
other spawners is unchanged.

The stored-axis components cannot exceed the fixed-point unit value after
normalization. Thus even a conservative independent bound on all three
components of a 1,000-unit follower offset gives a length at most
`1000 * sqrt(3)`. The maximum squared sine/cosine norm in `orbit_trigs` is
65,825, versus the ideal 65,536. Bounding both trigonometric products gives:

```text
maximum group distance <= 22527 * 65825 / 65536 + 1000 * sqrt(3)
                       < 24358.4
scanner boundary         24576
remaining margin         > 217.6
```

This deliberately allows for imperfect stored axes as well as rounded trig
values. Exhaustively checking all 129,600 angle pairs at the new maximum
nominal radius gives a maximum measured leader distance of 22,622.

No additional random draws, per-frame work or formation corrections were
introduced. Group weights, composition, spacing, convoy speed, mission spawns,
normal-flight/torus dispatch and the existing out-of-range cleanup are retained.
