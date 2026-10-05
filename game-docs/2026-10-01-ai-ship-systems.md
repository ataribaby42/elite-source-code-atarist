# Shared player and AI ship statistics

The enhanced Atari ST and Amiga trees independently implement the same rules.
The historical ZIP and `src_orig` are unchanged.

Latest validation: [4,008 native scenarios per platform and all 20 builds](#current-regression-verification-2-october-2026).

## Hulls and defensive stores

All 13 purchasable AI hulls read the existing player `ship_profiles` table during
`create_object`. Recharge grade, maximum speed, separate roll and pitch limits,
and missile capacity therefore match the corresponding player hull. Weapon
resistance comes from the same model-indexed `ship_weapon_profiles` table for
player and AI. AI movement decisions and fire opportunities remain AI behaviours;
equal limits do not require an AI ship to fly at full speed continuously.

Every ship has 96 energy points (the player's four banks). All except Worm /
Escape Capsule have a 24-point front shield and a 24-point aft shield. For AI,
`health` now holds these energy points.
Each has its own recharge countdown and an `ai_energy_unit` value: 0 for none,
1 for Extra Energy Unit, 2 for Naval Energy Unit. Creation always resets it to
zero, including copied and reused object slots. A future equipment roll can
assign 1 or 2 after creation without changing the damage or charging code.

Stations, asteroids, cargo, missiles, fragments, title letters, launch panels,
planets and other non-ship effects retain their existing object-health system.

Ships without a player profile retain their original speed, turning rate and
missile/Thargon allowance; recharge grade is 1. Their weapon resistances use
the same Unbound-relative balance as purchasable hulls, described below.

| AI-only hull | Speed | Roll / pitch | Missile or brood allowance |
| --- | ---: | --- | ---: |
| Worm / Escape Capsule | 17 | 24 / 24 | 0 |
| Thargon | 15 | 24 / 24 | 0 |
| Viper | 22 | 28 / 28 | 0 |
| Wolf | 30 | 36 / 36 | 3 |
| Shuttle | 6 | 16 / 16 | 1 |
| Transporter | 22 | 16 / 16 | 0 |
| Thargoid | 30 | 40 / 40 | One brood release |
| Cougar | 30 | 36 / 36 | 7 |
| Constrictor | 30 | 36 / 36 | 127 (existing mission allowance) |

## Unshielded escape capsule

Worm is used as the AI Escape Capsule. It starts with zero front/rear shields,
zero shield fractions and no shield flash. Creation resets these fields even
when the slot is copied from a shielded parent or reused. Its 96 energy, weapon
resistances, movement, collection rules and collision calculations are unchanged.

The shared charge step accepts a null shield pointer for energy-only stores.
Worm uses it on every recharge event: energy replenishes at the normal rate,
including with either future Energy Unit, without ever creating a shield. Hits
therefore go directly to energy and cannot trigger a blue shield flash. A fully
charged Worm is destroyed by the sixth Pulse, third Beam, fourth Mining, third
Military or first guided-missile hit, without recharge between hits.

## Cockpit missile indicators

Both platforms show `min(hull missile capacity, 4)` square slots. Filled slots
show `min(loaded missiles, 4)`; the last filled slot takes the armed or locked
colour. A zero-capacity hull shows no slots. Boa and Anaconda retain their real
magazine capacities, with four filled slots while at least four missiles remain.
No numeric counter is displayed. Redrawing clears obsolete slots in the current
screen buffer, and the existing dirty flags update both buffers independently.

The 2 October HUD revision passed 148 native pixel/state scenarios per platform,
covering every legal inventory of all 13 player hulls, all three missile states
when loaded, both buffers and clearing stale pixels. The 14 flight and eight
missile-collision scenarios also passed on each platform, as did 34 ordinary
tests (one existing artwork-identity test skipped). Native checks used verified
private hidden desktops with 1 MB Atari ST and Kickstart 1.3 Amiga configurations.
HUD reports are under each tree's `build/missile-slots-qa` directory.

## Unbound-relative weapon balance

The balance inputs are the user's supplied comparison tables: Unbound AI Pulse
hit counts and missile counts with `realmissiledamage=yes`. Cobra Mk III remains
the local reference, taking 24 Pulse hits or two missiles. For a hull with an
Unbound Pulse count `P`, laser resistance is `14 * P`, against Cobra's 154
(`14 * 11`). This scales continuous durability by `P / 11`; the final lethal
hit count rounds upward. Wolf uses the requested estimated Pulse count of 13.

Cougar and Constrictor use the requested finite Military ratio `51 / 7`, giving
laser resistance 1122 (`154 * 51 / 7`). All four laser classes can damage them
in their vulnerable mission phase. Their previous immunity/progression flags
remain effective where the mission requires them.

Missiles have separate resistance values, `77 * M`, where `M` is the desired
number of direct impacts. They therefore match the supplied Unbound missile
counts exactly under the conditions below, without weakening the laser balance.
Wolf's three-missile value is a local estimate; its supplied table has no Unbound
counterpart. ECM and intercepted missiles are excluded from these counts.

The table gives the hit that destroys a fully charged ship, firing repeatedly
at the same side with no recharge. The other shield remains full where fitted.
Worm has no shields; its values reflect the later shield-removal revision.
Purchasable hulls have identical results for player and AI; all results apply to both
platforms. Mission hulls are measured in their vulnerable phase.

| Hull | Unbound Pulse input | Local Pulse | Local Beam | Local Mining | Local Military | Local missiles |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cobra Mk III | 11 | 24 | 14 | 18 | 11 | 2 |
| Adder | 6 | 14 | 8 | 10 | 6 | 2 |
| Gecko | 5 | 11 | 7 | 8 | 5 | 1 |
| Moray | 7 | 16 | 9 | 11 | 7 | 2 |
| Cobra Mk I | 7 | 16 | 9 | 11 | 7 | 2 |
| Fer-de-Lance | 11 | 24 | 14 | 18 | 11 | 2 |
| Python | 17 | 38 | 21 | 27 | 17 | 4 |
| Boa | 17 | 38 | 21 | 27 | 17 | 4 |
| Anaconda | 17 | 38 | 21 | 27 | 17 | 4 |
| Asp Mk II | 11 | 24 | 14 | 18 | 11 | 2 |
| Sidewinder | 5 | 11 | 7 | 8 | 5 | 1 |
| Krait | 6 | 14 | 8 | 10 | 6 | 1 |
| Mamba | 7 | 16 | 9 | 11 | 7 | 1 |
| Worm / Escape Capsule | 3 | 6 | 3 | 4 | 3 | 1 |
| Thargon / Tharglet | 2 | 5 | 3 | 4 | 2 | 1 |
| Viper | 10 | 22 | 13 | 16 | 10 | 2 |
| Wolf | 13 (estimate) | 29 | 16 | 21 | 13 | 3 |
| Shuttle | 3 | 7 | 4 | 5 | 3 | 1 |
| Transporter | 3 | 7 | 4 | 5 | 3 | 1 |
| Thargoid | 17 | 38 | 21 | 27 | 17 | 3 |
| Cougar | Military ratio 51/7 | 175 | 98 | 125 | 80 | 4 |
| Constrictor | Military ratio 51/7 | 175 | 98 | 125 | 80 | 4 |

## Damage and charging

Player and AI use the same weapon calculation. Zero power does no damage;
positive power becomes `ceil(power * 154 * 65536 / resistance)` in unsigned
16.16 fixed-point units. The resistance is selected separately for lasers and
missiles. Rounding adds less than 1/65536 energy point per hit. There is no
one-point floor: weak lasers no longer collapse to identical damage on tough
hulls, and fractional damage is retained between hits.

Each energy/shield store keeps its existing integer value plus a fractional
damage debt. Actual remaining energy is `integer - debt / 65536`; the existing
HUD displays its ceiling. Front shield, aft shield and energy have independent
debts, cleared on fresh creation, copied-slot initialization and player system
reset. Fractional overflow passes exactly from the struck shield into energy.
These transient debts do not change the commander save format.

The attacked shield absorbs damage first, with the remainder deducted from
energy. The other shield is untouched. Player shield selection retains the
attacker's front/aft position. AI selection uses the dot product of the victim's
forward vector and the vector from victim to attacker: nonnegative means front,
negative means aft. Player fire originates at world position zero; NPC fire
uses the shooter's position and a missile uses its impact position. This works
for rotated ships and for combat between two NPCs.

A missile that hits a surviving target now keeps its own slot as an explosion
until the existing explosion timer expires. This applies to player and NPC
missiles, including impacts on immune hulls. The effect cannot deal another hit,
award score or bounty, release cargo or fragments, or change mission state. It
uses no gameplay randomness and needs no free object slot. Locks and other
missiles following the surviving target remain valid; locks on the spent missile
are released. Player missile impacts play the explosion sound; NPC-versus-NPC
impacts retain their existing silence. A lethal hit retains the target's normal
destruction path, including mission rewards and Thargon dormancy.

If a target is destroyed or leaves the bubble before impact, each incoming
player or NPC missile now detonates at its current position using the same
cosmetic effect. It causes no additional damage or rewards. A bounded queue
also clears chains of missiles targeting other missiles without recursive
calls or extra object allocation. Unrelated missiles keep their targets, and
missiles already marked for removal are not revived. The existing player
"Target lost" notification and lock cancellation are retained.

Successfully launching a player missile now provokes its live, vulnerable
combat-capable target before impact. The launch clears that target's pirate
truce and sets its hostility flag. A cruising ship starts an attack on the
player immediately; normal faction target ranking resumes on its next turn.
An existing fight retains its target, laser burst and manoeuvre. A peaceful
peel-off finishes its turn before attacking rather than returning to cruise
and clearing the provocation. This launch reaction uses no additional gameplay
random numbers and does not simulate weapon damage.

Eligible traders, including the Python, use their existing protest message
set when the player successfully launches a missile at them. The existing
50% radio chance and separate radio random stream are retained. This consumes
the same one-time opportunity as their first survived weapon hit, even when
the radio roll is silent; a later impact or another launch cannot repeat it.
Player identity masking is taken from the missile's shooter snapshot. Pirate,
police and Thargoid threats continue to follow their normal target-selection
observer, which can now see the attack prompted by the launch before impact.

The Python, Shuttle, Transporter and other fleeing or passive hulls retain
their existing behaviour. In particular, the Python still uses ECM and its
existing low-energy defensive missile logic. Stations, mission-only hulls
(Constrictor and Cougar), dormant Thargons, protected or disappearing objects,
and launch/docking scripts are excluded from the new reaction. Missile ECM
checks, damage, station penalties and mission progression remain on their
existing paths. A failed launch, including a full object bubble, cannot
provoke the target.

Zero remaining energy is lethal, including an exact-zero hit. Recharge cannot
revive a ship after a lethal hit. Existing destruction, cargo, score, bounty and
mission routines still process the death.

Both sides call the same charging step once their individual countdown expires.
Each tick restores one energy point, up to 96. Recharge grade 1 charges shields
only when actual energy has reached 96, including its fractional part; higher
grades charge energy and both shields together, each shield gaining one point
up to 24. Shields do not consume energy
while charging, matching the existing player system. Charging preserves any
remaining fractional deficit and clamps each store to its exact maximum.

| Hull | No unit | Extra unit | Naval unit |
| --- | ---: | ---: | ---: |
| Ordinary hull | 24 frames | 15 frames | 9 frames |
| Fer-de-Lance | 15 frames | 9 frames | 7 frames |

The player's laser cooling remains on the same charging ticks. AI charging is
processed at the same point at the end of the flight frame. Exploding, removed
and unused records do not recharge.

## Shield-hit appearance

Each object slot has a `shield_flash` frame counter. Allocation and removal
explicitly clear it; creation also resets it after any parent record is copied,
and clearing the whole bubble zeros every slot. A positive laser or missile hit
sets it to one if the struck front or
aft shield was above zero before damage. This includes shield-breaking hits,
player fire and AI-versus-AI combat, including damage below one energy point.
Hull-only damage, zero-power hits and
immune targets do not start a flash.

While the counter is positive, all mesh panels and lines use solid orange for
Thargoids and Thargons/Tharglets, and solid light blue for other ships,
including engine details. A distant grey sphere uses the same flash colour, but its smaller
single-pixel and cross representations retain their normal grey. Materials and
object colour overrides are never modified. The counter decreases once at the
end of every flight frame, after drawing, including off-screen/cloaked ships
and flight menus. It cannot wait for a ship to re-enter the view.

Collision classes, damage and destruction rules remain unchanged. A surviving
AI ship can flash at the contact side. An AI ship destroyed by ramming has its
pending flash cleared and goes directly to the normal explosion. A lethal
laser or missile hit against an active shield can show one coloured hull frame
before its already-started explosion becomes visible.

## AI laser hit calculation

The existing hit decision is retained:

1. Existing targeting, station-space behaviour, cloaking and locked-control
   checks apply. A target must be within 12,288 world units.
2. An existing random byte `r` permits a shot when `r <= mood`.
3. The forward-direction dot product is compared with distance times the Q14
   cosine threshold. Below `14563 / 16384` (approximately 32/36), no beam is
   fired. From that threshold up to `15928 / 16384` (approximately 35/36), a
   visible miss is fired. At or above the second threshold, it can hit.
4. A candidate hit receives the existing additional distance miss roll. Values
   200..255 are rejected, producing a uniform roll 0..199. A roll below the
   threshold misses; otherwise it hits. Interpolation is linear between the
   anchors, rounded down to half-percentage-point steps.

| Distance | Additional miss chance | Candidate-hit success chance |
| --- | ---: | ---: |
| Up to 1,000 | 10% | 90% |
| 3,000 | 20% | 80% |
| 5,000 | 30% | 70% |
| 7,000 through 12,288 | 50% | 50% |

These are conditional chances after the fire opportunity and aim checks, not
the probability of taking damage on every frame.

Only the damage after an accepted hit changes. The former random damage and
2-or-3 multiplier are replaced by the player's base damage for that laser
class. Ordinary AI selects a separate persistent loadout for each new ship:

| Player rating when the ship is created | Pulse (5) | Beam (9) | Military (11) |
| --- | ---: | ---: | ---: |
| Harmless, Mostly Harmless, Poor | 90% | 7% | 3% |
| Average, Above Average, Competent | 70% | 21% | 9% |
| Dangerous, Deadly, Elite | 50% | 35% | 15% |

The player's Mining Laser remains 7. Cougar always uses Beam and Constrictor
Military. Thargoids always use Beam (9) and Thargons/Tharglets always use
Pulse (5), regardless of player rating; both remain light blue. NPC versus NPC combat
uses the shooter's same stored power; it has no separate weaker damage roll.
Aim and distance accuracy are unchanged. Pulse now has a minimum 10-step
interval; Beam/Military use continuous 6–18-step bursts with checks every
6/3 steps. See [burst timing and impact audio](2026-10-03-ai-laser-bursts.md). There is no global
laser cache refreshed on departure or hyperspace. See
[per-ship loadouts and validation](2026-10-03-ai-laser-loadouts.md).

All guided missiles now use the player's existing base power of 60, scaled by
the victim's missile resistance and absorbed by the struck shield and then
energy. The old 48-point exception for incoming player hits is removed. ECM, missile guidance,
impact range, station immunity and invincibility are preserved.

For example, a full Cobra Mk III takes 24 Pulse hits, 14 Beam hits, 11 Military
hits, or two missiles to destroy from the same side without intervening
recharge, whether it belongs to the player or AI. Changing side, equipment or
time between hits can change the total.

## Collisions and special behaviour

Collision size classes and their fatal-size-mismatch rule remain unchanged.
Before the existing `8 + floor(health / 32)` calculation, an AI hull using the
shared energy system has its energy converted back to the legacy scale with
`floor(health * original energy_max / 96)`. A full Cobra still contributes 72,
and a full Cougar 1024, preserving their previous collision damage. The class
adjustment and legacy player hull resistance are then applied as before. The
new laser/missile resistance table does not alter collision classes, legacy
model energy or the collision-resistance field in `ship_profiles`.

Constrictor ramming protection, mission invincibility, station destruction
progression, Cougar reward cargo, ECM and energy-bomb exceptions are retained.
Thargoids retain brood release; every child gets fresh systems. Killing a
mother still makes only its own Thargons dormant, including NPC laser and
missile kills. Witch-space drive repair still counts the appropriate mother
ship removals. NPC kills do not credit the player.

## Verification

`tests/native_ai_systems.py` in each tree runs the linked 68000 routines. It
checks every hit through death for all 13 hulls, all four player laser powers
and missile power, from both shield sides; 720-frame recharge traces with all
three unit states; independent counters; object reuse; axis-oriented shields;
rating tiers; the original aim and distance thresholds; separate pitch and roll
limits; exact-zero death; mission progression and invincibility; Thargon launch
and dormancy; energy bombs; and witch-space removal.

The existing player hull and missile/collision suites now initialize real ship
records and expect the new defensive stores. Additional regression suites cover
live flight, runtime ship images, station-impact death, death cargo and guarded
mesh rendering. Native emulator runs use private executable/configuration/disk
copies on verified hidden Windows desktops, with 1 MB RAM. Logs and reports are
under each tree's `build/ai-systems-qa` directory.

Completed verification on 2026-10-01:

| Native suite | Atari ST | Amiga |
| --- | ---: | ---: |
| Shared systems, weapon parity, aim, missions and aliens | 257 | 257 |
| Missile impacts, Cougar reward and collision protection | 8 | 8 |
| Player hull purchases, equipment and commander state | 106 | 106 |
| Live flight across all player hulls | 14 | 14 |
| Runtime ship images and cache guards | 15 | 15 |
| Station-impact death | 2 | 2 |
| Death cargo | 35 | 35 |
| All meshes, rotations and near-camera poses | 3096 | 3096 |
| Mission spawns, encounter routing, missiles, brood and slot reuse | 83 | 83 |
| **Total passed** | **3616** | **3616** |

Both targets also passed 34 ordinary tests each. One historical PNG byte-identity
check per target was intentionally skipped because the editable artwork is
customized. All 20 distribution builds passed: two Atari artwork variants and
18 Amiga artwork/display/CPU combinations. Native runtime coverage used the
standard Atari and PAL Amiga builds; the other display variants received build
and format verification. Amiga boot and core checks included cycle-exact 68000
execution on Kickstart 1.3 with 512 KB Chip plus 512 KB Slow RAM; bulk functional
and rendering regressions used accelerated 68000 execution with the same RAM.

The source audit confirms that both aim-cone and distance-miss routines, the
fire-decision block up to the accepted-hit branch, and the collision-class
table match their pre-change copies. `summary.json` in each QA directory records
the totals and the final default build verification.

The subsequent shield-flash change adds `tests/native_shield_flash.py` to each
tree. Its 62 native scenarios cover both shield sides through the actual player
laser, NPC laser and missile paths; zero/immune/hull-only hits; copied slots;
frame expiry off-screen and in flight menus; collision survivors and destroyed
colliders; and pixel-level checks for all 22 ship types. The rendered model must
contain only light-blue pixels, then return exactly to its normal materials.
Grey dots and crosses and the larger distant sphere are tested separately.
The Amiga pixel comparison starts with a blank viewport after waiting for the
asynchronous clear, avoiding residual cockpit corners in the test canvas.

All 3,616 prior native cases and the 62 new cases passed again on each platform
(3,678 per platform), as did the 34 ordinary tests with the same historical
artwork check skipped. These later results and private-emulator diagnostics are
under each tree's `build/shield-flash-qa` directory. Runtime coverage for this
change uses the standard Atari ST and PAL Amiga builds with 1 MB RAM; Amiga
uses accelerated 68000 execution on Kickstart 1.3. All 20 distribution variants
also rebuilt and passed their format/layout verification after this change.

The slot-lifecycle follow-up adds five native cases (67 shield-flash cases in
total) for immediate/deferred removal, fresh allocation, copying a flashing
parent and clearing every slot in the bubble. The updated flash suite plus
the shared-systems and spawn suites passed on both platforms: 407 native cases
per platform. `build/shield-flash-qa/lifecycle-verification.json` records these
targeted reruns. Creation continues to clear the counter after copying a parent;
allocation and removal now explicitly clear it as well.

The nonlethal missile-impact fix adds `tests/native_missile_impacts.py` in both
trees. Its 22 scenarios execute player and NPC impacts from both shield sides,
with active and depleted shields; immune targets; the complete explosion
lifetime without repeated damage or false rewards; a full object bubble;
independent target locks; gameplay RNG preservation; and actual pixels showing
the missile explosion alongside a blue surviving hull. The visual fixture
explicitly reselects the missile after cockpit initialization, whose routines
may change A5.

Amiga verification of the impact and shield-pixel suites passed with cycle-exact
68000 timing. Accelerated WinUAE runs intermittently failed the older shield
suite's exact before/after pixel hash at different models; these were retained
as diagnostic failures, and the final rendering checks use cycle-exact timing.
No renderer change was made for this missile fix.

Final targeted verification after this fix passed 437 native scenarios per
platform: 22 impact cases, 8 missile/collision cases, 257 shared-systems cases,
67 shield-flash cases and 83 spawn/mission/alien cases. Both targets also passed
34 ordinary tests, with the existing customized-artwork identity check skipped.
All 20 distribution variants rebuilt successfully. Final default executables
match the binaries used in the native tests exactly. Reports, timing settings,
source hashes and build verification are in each tree's
`build/missile-impact-qa/summary.json`. All emulator runs used verified private
hidden desktops; Amiga impact, shield and spawn checks used cycle-exact 68000
execution with Kickstart 1.3, 512 KB Chip RAM and 512 KB Slow RAM.

## Unbound-relative balance verification

The later balance revision adds `tests/native_unbound_balance.py` independently
to each tree. Its 124 linked-68000 scenarios verify all 22 hulls through the
lethal hit for all four lasers and missiles, including the actual missile
damage entry. They also cover damage below one displayed point, independent
front/aft fractions, exact shield-to-energy overflow, mixed laser/missile
damage, slow and fast recharge at fractional boundaries, copied/reused slots,
immunity, zero damage and player hull/system resets. The updated shared-systems
suite compares the full integer and fractional player/AI state after every
hit on both sides for all purchasable hulls.

All native suites passed after the balance revision on both platforms:

| Native suite | Atari ST | Amiga |
| --- | ---: | ---: |
| Shared systems, weapon parity, aim, missions and aliens | 257 | 257 |
| Unbound-relative counts and fractional damage | 124 | 124 |
| Missile impacts, Cougar reward and collision protection | 8 | 8 |
| Player hull purchases, equipment and commander state | 106 | 106 |
| Live flight across all player hulls | 14 | 14 |
| Runtime ship images and cache guards | 15 | 15 |
| Station-impact death | 2 | 2 |
| Death cargo | 35 | 35 |
| All meshes, rotations and near-camera poses | 3096 | 3096 |
| Mission spawns, encounter routing, missiles, brood and slot reuse | 83 | 83 |
| Shield flashes and slot lifecycle | 67 | 67 |
| Nonlethal missile explosions and target locks | 22 | 22 |
| **Total passed** | **3829** | **3829** |

Both targets also passed 34 ordinary tests, with the existing customized-artwork
identity check skipped. The Amiga hull-purchase, shield-flash and missile-impact
runs used cycle-exact 68000 execution; bulk functional and mesh tests used
accelerated 68000 execution. All native runs used the standard display/artwork
build, 1 MB RAM and verified private hidden desktops. Amiga used Kickstart 1.3
with 512 KB Chip and 512 KB Slow RAM.

Two preliminary Amiga attempts are retained as diagnostics: an accelerated
player-hull run timed out, and a cycle-exact attempt failed in the scratch-memory
bootstrap before the scenarios began. The test harness now parks its entry
before installing the test jump, avoiding replacement of an instruction that
could still be executing. The final hull run and rendering runs completed with
cycle-exact timing. No game change was made for these harness failures.

The source audit checks unchanged AI aim, distance accuracy and fire-decision
instructions, legacy collision scaling and classes, original player profile
values, and the nonlethal missile-impact effect. Results and source hashes are
under `build/unbound-balance-qa` in each tree. Additional Amiga functional-run
diagnostics are under `build/unbound-balance-functional-qa`.

All 20 distribution variants also rebuilt successfully: two Atari artwork
variants and 18 Amiga artwork/display/CPU combinations. Other display variants
received build and format/layout verification; native coverage is specified
above. Final default executables match the binaries used in the native tests
exactly. Each tree's `build/unbound-balance-qa/summary.json` records the complete
counts, source audit, durability table and final build verification.

## Worm shield-removal verification (2 October 2026)

The subsequent shield-removal change passed 754 native scenarios on each
platform: 32 dedicated Worm lifecycle/damage/recharge cases, 257 shared-system
and mission cases, 124 weapon-balance cases, 83 spawn cases, 66 shield-effect
cases, 22 missile-impact cases, eight missile-collision cases, 14 flight cases,
and 148 missile-display cases. These runs used the current standard Atari and
PAL Amiga binaries on verified private hidden desktops, with 1 MB RAM and an
accelerated 68000. Both platforms also passed 34 ordinary tests; the existing
artwork-identity test was skipped. The remaining 3D mesh suite was not repeated
for this change, which does not modify geometry or drawing.

All 20 distribution variants rebuilt with their normal format/layout checks.
The final default disks match the disks exercised by these native tests. Reports,
source snapshots, durability counts and final hashes are retained under
`build/worm-shields-qa` in each source tree. The standalone `ship-balance.html`
reference and inspector now start Worm with zero shields; browser checks verify
all 110 weapon counts and its six-Pulse-hit result from either side or alternating
sides, plus player/AI parity for purchasable hulls, mobile layout and offline use.

## Current regression verification (2 October 2026)

This full rerun verifies the current source after the weapon rebalance, missile
HUD change and removal of Worm shields. It supersedes the earlier verification
counts above. All scenarios below passed on both platforms; retries are counted
only once.

| Native suite | Atari ST | Amiga |
| --- | ---: | ---: |
| Shared systems, weapon parity, aim, mission protection and aliens | 257 | 257 |
| Mission encounters, station launches, witch-space, brood and slot reuse | 83 | 83 |
| Cougar reward, missile immunity and collision protection | 8 | 8 |
| Unshielded Worm: damage, energy-only recharge and lifecycle | 32 | 32 |
| Weapon hit counts and fractional damage | 124 | 124 |
| Nonlethal missile explosions and target locks | 22 | 22 |
| Shield effects, frame expiry and slot reuse | 66 | 66 |
| Missile HUD capacity, clipping and both screen buffers | 148 | 148 |
| Flight across all purchasable hulls | 14 | 14 |
| Station collision and player death | 2 | 2 |
| Death cargo and rewards | 35 | 35 |
| Runtime ship portraits, caches and screen transitions | 15 | 15 |
| Every mesh, rotations and near-camera/off-screen poses | 3096 | 3096 |
| Purchases, equipment, cargo, missiles and saved commanders | 106 | 106 |
| **Total passed** | **4008** | **4008** |

Each platform also passed 34 ordinary tests. The existing customized-artwork
byte-identity check was skipped (35 discovered, one skipped). All 20 distribution
variants rebuilt and passed format/layout checks: two Atari artwork variants and
18 Amiga artwork/display/CPU combinations.

Mission checks include Constrictor protection and progression, alien-station
progression, Cougar creation and Cloaking Device rewards, laser/missile kills
versus ramming, mission encounter and torus routes, Thargoid brood ownership and
dormancy after mother kills, witch-space spawns and drive repair, and energy-bomb
exceptions. The same runs cover player/AI damage and recharge parity, live flight,
all player hull purchases and saved state, slot reuse and the revised missile HUD.

Native runs used standard Atari ST and framed PAL Amiga builds with 1 MB RAM.
WinUAE used Kickstart 1.3, 512 KB Chip plus 512 KB Slow RAM. Amiga player-hull,
shield-effect and missile-impact suites used cycle-exact 68000 timing; the other
Amiga suites used accelerated 68000 execution. Other Amiga display modes received
build/layout validation. All emulator processes, configurations and disk copies
were private and ran on verified hidden desktops.

One preliminary Atari image-suite launch could not confirm the private desktop
window and was discarded. The suite subsequently passed with verified isolation;
its startup diagnostics and successful rerun are retained. No gameplay change
was needed. Source fingerprints confirm that both game trees, the original source
and the historical ZIP stayed unchanged during this verification. The final
default disks match the disks exercised by the native tests.

Reports, build logs, per-suite results, source audit and disk hashes are in each
tree's `build/balance-regression-qa`. `summary.json` records the exact scope and
counts. The standalone balance page was refreshed from both source trees and all
110 weapon counts were checked against this fresh native run. Browser checks
cover player/AI parity, the zero-shield Worm from either side and alternating
sides, controls, filtering, local links, desktop/mobile layout, print and no-JavaScript
use. Worm survives five full-energy Pulse hits and is destroyed by the sixth,
without intervening recharge.
