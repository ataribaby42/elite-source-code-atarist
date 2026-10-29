# Station trader hyperspace departures

Both enhanced platform trees give ordinary station-launched traders a single
hyperspace decision after their existing model-dependent departure turn.
Shuttle, Transporter, police Vipers and traders created in deep space retain
their existing routes. The departure distance remains 3,600 units; nearby-player
avoidance may still trigger the turn earlier.

## Selection and timing

`departure_jump_percent` in each tree's `asm/logic.m68` is set to **50** for
normal use. The temporary 100% test setting has been removed. Each eligible
trader draws one value from 0 through 99. A rejected selection enters the
original cruise logic and never retries.

A selected trader draws a whole-second delay from 5 through 10, inclusive,
starting when the departure turn finishes. It continues flying during this
delay. Combat or evasion does not cancel an already selected jump; destruction
or ordinary removal from the local bubble does. Faction retargeting does not
prematurely terminate the initial station departure turn.

A transient VBL counter advances only while the game is not paused. Delays and
animation use the platform's PAL/NTSC field rate rather than rendered frames.
Unpaused flight menus continue to advance the simulation. Deadline subtraction
also works across the counter's 32-bit wrap. No commander-save fields are added.

## Cloud appearance and size

At jump start the ship's velocity becomes zero. Its model is replaced by two
solid concentric circles using the existing dark-blue and mid-blue palette
entries (12 and 11). The inner radius is half the outer radius. The cloud
remains at the ship's world position; normal camera movement and perspective
still apply.

The initial world radius is calculated from the installed model headers of the
five equally likely departing trader models:

| Model | Bounding radius |
| --- | ---: |
| Cobra Mk III | 94 |
| Python | 100 |
| Fer-de-Lance | 55 |
| Anaconda | 90 |
| Cobra Mk I | 73 |

The mean is 82.4, rounded to **82** world units: an initial diameter of 164.
The radius grows linearly to 164 over one second, then shrinks to zero over
one further second. Projected pixel sizes follow the existing integer rounding.
The same calculation is used for either graphics set, without changing its
palette or model data.

The cloud cannot be targeted, hit, collided with or selected as an AI combat
ship. Existing missile locks and pursuit references are cleared, and the
departing ship's pending laser burst and shield flash are stopped. Its original
model and faction identifiers remain until normal deferred removal, so object
and trader counters are decremented exactly once. Departure awards no kill,
bounty or cargo. Reused object records start with cleared departure state.

The Amiga build also uses an absolute tail call in `cancel_targeting` where
the larger code layout exceeded a 68000 relative branch's 16-bit reach. This
preserves the existing identification/missile cancellation behaviour.

## Verification

Only standard `ELITE` and `ELITE_ALT` distributions are built for each platform.
Native tests in `tests/native_trader_departure.py` cover all five models, turn
completion, 5..10-second endpoints, clock wrap, pause, preserved world position,
camera movement, target cleanup, combat/evasion, destruction, excluded types,
record reuse and balanced removal counters. Exhaustive selection checks cover
all 100 rolls at 0%, 50% and 100%, including no retry after rejection.

The independent existing spawn suite checks police and shuttle launches,
station/deep-space trader routes and other spawn paths. Cloud framebuffer
captures compare the standard and alternate graphics sets on both platforms,
including exact colour indices, circular bounds, growth, shrinkage and zero
size. Private test binaries, logs and captures are kept under each platform's
`build/trader-hyperspace-qa`. GUI emulator runs use verified private hidden
desktops and private executables, configurations and disk images.

Distribution outputs remain in `output_atari` and `output_amiga`. No files on
the user's G: drive are updated, and the historical original remains untouched.

Final verification passed 33 departure scenarios in each of the four standard
distributions, plus 83 existing spawn scenarios on each platform. Captured cloud
pixels match across all four builds. Python suites passed 35 Atari and 36 Amiga
tests, with one existing skip per tree. All four distributed disk images match
their tested private copies. The preserved historical source archive's SHA-256
remains unchanged.
