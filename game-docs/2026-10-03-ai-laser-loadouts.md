# Per-ship AI laser loadouts

Both enhanced platforms now assign a laser independently when a ship enters
the bubble. This replaces the global laser class previously refreshed on
station departure and completed jumps. Player weapon power and the existing
AI trigger probability, aim cones and distance miss roll are unchanged.
The subsequent [burst implementation](2026-10-03-ai-laser-bursts.md) adds
per-class cadence and continuous Beam/Military rendering.

## Selection

| Player rating when the ship is created | Pulse | Beam | Military |
| --- | ---: | ---: | ---: |
| Harmless, Mostly Harmless, Poor | 90% | 7% | 3% |
| Average, Above Average, Competent | 70% | 21% | 9% |
| Dangerous, Deadly, Elite | 50% | 35% | 15% |

These are upgrade chances of 10%, 30% and 50%, followed by a 70% Beam / 30%
Military split. The implementation uses one unbiased percentile with the
equivalent combined probabilities. `ai_laser_roll` accepts random bytes
0–199, maps them to 0–99, and retries bytes 200–255. Each percentile has
exactly two accepted byte values; modulo bias is avoided.

Police Vipers use the same roll but replace Pulse with Beam, keeping Military
unchanged. Their Beam/Military probabilities are 97/3%, 91/9% and 85/15% across
the three rating bands. This applies to station launches, encounter patrols and
copied wingmen, without an additional random draw.

Cougar always has Beam (power 9, orange). Constrictor retains Military
(power 11, white). Thargoids always have Beam (power 9), while Thargons/Tharglets
always have Pulse (power 5), regardless of player rating. Both draw light blue.
These four types do not consume the ordinary loadout roll. Their invincibility,
mission logic, ECM and other special behaviour are unchanged.

Ordinary Pulse, Beam and Military beams are red, orange and white, respectively.
Mining Lasers are not part of the AI lottery. A ship without a working gun
still cannot fire merely because it has a stored loadout.

## Lifetime and damage

`ai_laser_loadout` is one word in each live object record, before the copied
model header. It encodes the selected base power: 0 for no ship weapon, or
5/9/11 for Pulse/Beam/Military. This loadout addition grew the object stride from 184 to 186 bytes:
60 additional bytes for the 30-slot pool. The subsequent burst state adds
another eight bytes per slot, making the current stride 194 bytes. The commander save format is
unchanged.

`create_object` calls `ship_ai_init`, which resets the field and calls
`init_ship_laser` for ship types. Every copied wingman is initialized again
and rolls independently; it does not retain the parent's weapon. Non-ship
objects retain zero. Allocation, removal and clearing the bubble reset the
field. Existing ships keep their loadout when the player's rating changes;
new ships, including aliens, use the rating at their own creation.

`ai_laser_power` reads this stored word for both AI-versus-player and
AI-versus-AI damage. `ai_laser_palette` derives the beam colour from the same
field, with the blue alien exception. Rendering and accepted-hit damage do
not reroll the weapon. The `ai_laser` field still records this frame's shot
state separately (none / miss / hit).

The old `ai_laser_colour`, `ai_laser_damage` and `init_ai_laser_colour` are
removed, including calls from launch and hyperspace completion. Both source
trees implement the same rules independently. The historical source and
archive are untouched. New spawn-time draws naturally change subsequent
random sequences; they do not change the formulas for hit probability.

## Validation

`tests/native_ai_loadouts.py` executes the linked 68000 routines on each
platform. Its 71 scenarios include:

- All 100 percentiles for every ordinary hull at all nine ratings: 16,200
  selections, including both boundaries of every weapon range.
- Fixed exceptions at every rating, no loadout draws for those exceptions,
  matching beam colours and base power, and persistence after rating changes.
- Real construction, copied wingmen, the final object slot, allocation,
  removal, bubble clearing and conversion to non-ship objects.
- All 256 possible raw bytes, including rejection and retry for 200–255.
- Three nonzero game RNG seeds, 20,000 selections per seed and rating band:
  180,000 random selections on each platform.

Atari and Amiga produced identical counts for each seed. Aggregating the
three seeds gives these observed percentages (60,000 ships per band):

| Rating band | Pulse | Beam | Military |
| --- | ---: | ---: | ---: |
| Harmless–Poor | 89.850% | 7.113% | 3.037% |
| Average–Competent | 69.930% | 20.978% | 9.092% |
| Dangerous–Elite | 50.092% | 34.765% | 15.143% |

The exhaustive tests verify the exact configured probabilities; sampling
checks the actual game RNG and permits normal sampling variation. The native
spawn suite isolates its controlled encounter RNG from the new loadout RNG,
so its forced values, including 255, still test encounter routing. The AI
systems suite explicitly equips each tested laser before checking accepted
hits against player and NPC shields.

All emulator runs use private executable, configuration and disk copies on
separate hidden Windows desktops, with desktop assignment verified before
testing. The user's emulator session is not used.

The final regression run passed 4,082 native scenarios on each platform:

| Coverage | Scenarios per platform |
| --- | ---: |
| New loadout selection and lifetime tests | 71 |
| Shared combat systems, accuracy, alien and mission behaviour | 248 |
| Spawn paths, copied objects, launch, jumps and slot reuse | 83 |
| Missile collisions and impact explosions | 30 |
| Shield flashes | 66 |
| Shieldless Worm | 32 |
| Unbound-relative durability | 124 |
| Player hulls, purchases, equipment and saves | 106 |
| Live player flight | 14 |
| Runtime ship graphics | 15 |
| Missile indicators | 148 |
| Identification indicator and controls | 49 |
| All-model rendering bounds | 3,096 |
| Total | 4,082 |

Mission coverage includes Constrictor invincibility and progression, Cougar
rewards, Thargoid child creation and deactivation, and witch-space drive
repair. Combat tests exercise accepted hits and misses against both player
and NPC victims. The Amiga shield-flash, missile-impact and player-hull suites
ran with cycle-exact 68000 emulation.

Both platforms also passed 34 ordinary tests, with one existing conditional
art-identity test skipped in each 35-test discovery run. All 20 build variants
passed: two Atari artwork variants and 18 Amiga artwork/display variants.
Native gameplay tests ran on the framed PAL 68000 builds; the other Amiga
display variants received build validation. The selected pre-test build
options were restored afterward.

`game-docs/ship-balance.html` now contains the probability table and current fixed
exceptions. Its embedded source fingerprints were checked against both source
trees, and its 110 durability counts still match the existing native results.
Reports, RNG counts, payload listings and build logs are retained under each
platform's `build/ai-loadout-qa` directory; the combined result is
`src_atari/build/ai-loadout-qa/final-audit.json`.

## Fixed alien loadouts follow-up

Thargoids now always use Beam and Thargons/Tharglets always use Pulse. Both
retain light blue at every player rating. The updated native selection tests
cover all nine ratings, creation without a loadout RNG draw, palette selection,
and persistence after a rating change.

Both selected Atari and Amiga builds passed 493 native scenarios each: 71
loadout, 91 burst/cadence, 248 combat systems and 83 spawn-path scenarios.
This includes player/NPC damage, mission progression, alien brood creation
and deactivation. Reports and build logs are in each platform's
`build/alien-laser-qa` directory. The existing build options were preserved.

## Police Viper minimum laser follow-up (4 October 2026)

Police Vipers retain the ordinary rating-based percentile draw, but a Pulse
result becomes Beam. Military results are unchanged. No extra random draw is
made, and other hulls retain their previous selection rules. Initialization
applies this to station launches, encounter patrols and copied Vipers alike.

| Player rating | Pulse | Beam | Military |
| --- | ---: | ---: | ---: |
| Harmless, Mostly Harmless, Poor | 0% | 97% | 3% |
| Average, Above Average, Competent | 0% | 91% | 9% |
| Dangerous, Deadly, Elite | 0% | 85% | 15% |

Both platforms passed 504 native scenarios: 82 loadout, 83 spawn-path, 91 burst
and 248 combat-system cases. The loadout suite exhausts all 100 percentiles at
all nine ratings for Vipers and the other 17 ordinary hulls, checks fixed alien
and mission loadouts, colours, persistence and RNG consumption, and verifies
independent Beam/Military selection for copied Vipers. Station-launch checks
include police launches and the mission's Thargoid replacement.

Tests used private emulators on verified hidden desktops. Standard and selected
ALT distributions were rebuilt; build options were preserved. Reports and logs
are under each platform's `build/police-laser-qa` directory.
