# Guided missile speed during turns

## Behaviour

Both enhanced builds now keep a guided missile at its model's maximum speed
while steering: 42 world units per completed flight update. Player missiles,
NPC missiles aimed at the player and NPC missiles aimed at other ships all use
this rule.

Previously, `do_locked` and `do_missile` used the ordinary ship `speed_control`.
While `auto_pilot` reported the missile off course, it lost two speed units per
update down to six. Once aligned, it gained two units per update. A sufficiently
long turn therefore reduced speed sevenfold and required another 18 updates to
regain maximum speed. Native measurements reproduced this on both platforms.

The two missile handlers now copy `vel_max` to `velocity` immediately after
steering, before their existing ECM and impact checks. The shared ship speed
controller is unchanged. Missile turn limits, alignment tolerance, course-check
interval, launch behaviour, hit radii, damage, ECM, target-loss handling and
scanner-range cleanup retain their existing rules. Exploded missiles still stop
through the normal explosion logic.

The change removes braking; it does not guarantee that every interception is
shorter. Maintaining speed increases the turning radius, so a very close
crossing target can require a longer arc. Steering was deliberately left intact
after comparing full speed with an additional every-update course check; the
latter did not consistently improve interceptions.

## Verification

Each source tree has its own `tests/native_missile_guidance.py`. It executes the
linked 68000 guidance, movement and impact routines, checking speed and motion on
every update until an actual damaging hit. A missing impact within 1,200 updates
fails the test. The original implementation fails the first 90-degree turn
case because it reduces speed.

The 99 scenarios per platform cover all three missile ownership/target paths;
Cobra and small Thargon victims for object targets; stationary victims and
speeds 22 and 32; straight pursuit, pitch, roll followed by pitch, 180-degree
turns, close crossings and diagonal crossings; and zigzag, two-axis evasion and
mid-flight reversal. The moving-victim fixtures use a reference frame following
the victim, preserving the ordinary scanner boundary during prolonged pursuit.
All tested paths must hit rather than circulate indefinitely.

The existing missile-collision, missile-impact, mission/spawn, player-flight and
AI-system suites also passed against the updated builds: 99 guidance, eight
missile-collision, 22 missile-impact, 83 mission/spawn, 14 player-flight and 248
AI-system scenarios, for 474 per platform. Both standard `ELITE` and selected
`ELITE_ALT` distributions were rebuilt for Atari and Amiga. Diagnostics, native
reports and build logs are stored in each tree's `build/missile-guidance-fix-qa`.
Emulators use verified private hidden desktops and private executable and disk
copies. The historical `src_orig` gameplay is untouched.
