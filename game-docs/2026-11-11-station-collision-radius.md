# Station collision sphere correction — 2026-11-11

## Cause and scope

The collision routine added the general 100-unit object allowance to station
model radii. This produced a substantial invisible contact shell around both
Coriolis and the Dodecahedron alien station. The issue reproduced in the real
Atari and Amiga routines: a Cobra at distance 228 from Coriolis took damage,
and an Adder at distance 249 from Dodecahedron was destroyed despite being
outside the spheres required to enclose those models.

At the user's request, collision remains spherical. No face, polygon or
per-player-hull geometry checks are introduced. Only `asm/flight.m68` changes
in each independent platform tree. Every one of the 13 player hulls uses the
same corrected station radius.

| Station | Maximum vertex distance | Previous contact radius | Corrected contact radius |
| --- | ---: | ---: | ---: |
| Coriolis | 226.27416998 | 326 | 227 |
| Dodecahedron | 247.31558786 | 347 | 248 |

The model headers contain the truncated radii 226 and 247. Station collision
now adds one unit to enclose every vertex instead of adding 100. Both Coriolis
color variants share the same geometry and radius. Rigid rotation does not
change the mathematical enclosing radius; the engine's existing integer range
calculation and fixed-point transforms retain their normal rounding.

The sphere still contains empty space around flat faces and corners. This is
the intended sphere-only approximation, not a polygon collision model.

Docking distance, docking alignment, entry bans, collision damage and mission
rules remain unchanged. Other objects retain their original 100-unit allowance.
Models, drawing, player ship parameters, bounty hunters and police are untouched.

## Validation

The new independent `tests/native_station_collision.py` suites exercise actual
range calculation and collision routines on both platforms. For every player
hull and both station types, they check the first clear axial position, 18 near
miss positions on all six sides with and without an entry ban, a 41-frame
grazing pass without cumulative damage, and contact at and just inside the
corrected boundary. They also check that ordinary ship, cargo, escape-capsule
and asteroid collision radii retain their previous allowance.

Existing suites cover manual and automatic docking gates, entry policy, real
station shield/energy damage, missile and mission-ship collisions, player
flight and station destruction. Only normal ELITE and ELITE_ALT distributions
are built; Amiga tests use PAL/MC68000 with 1 MB RAM.

Tests run in private emulator copies on verified separate hidden desktops.
Baseline failures, source snapshots and final reports are retained under each
platform's `build/station-collision-qa` directory.

## Final results

All 464 native scenarios passed on each platform: 204 in ELITE and 260 in
ELITE_ALT. Each station-collision suite includes 2,028 no-damage position/frame
checks across the 13 player hulls and both stations, plus 52 station-contact
checks and eight non-station boundary scenarios.

The pre-fix RAM captures confirm the failure independently on both platforms:
the Coriolis probe reduced the Cobra's front shield from 24 to 17 at distance
228; the Dodecahedron probe set game over for the Adder at distance 249 while
both shields and energy were still full.

`src_atari/build/station-collision-qa/verify_final.py` verifies the baseline RAM
evidence, complete model-vertex bounds, source scope, final distribution hashes,
and equality of output disk images with the private images tested. Per-platform
results are in `build/station-collision-qa/final/report.json`; the combined report
is `src_atari/build/station-collision-qa/summary.json`.

ELITE and ELITE_ALT are updated in `output_atari` and `output_amiga`. No G: files
were updated. `CHANGELOG.md`, the historical source archive and all other runtime
source files remain unchanged. No private test emulator remained running after
validation. The full Amiga display/CPU matrix was not run.
