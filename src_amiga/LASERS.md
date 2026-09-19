# Instant-hit lasers

Player and AI weapons use instant-hit beams instead of travelling projectiles.
Each target keeps its own implementation in its source tree.

## Player weapons

An accepted shot is evaluated in the same game frame, on the fixed axis through
the centre of the current view's crosshair. The small random movement of the
drawn beam tip is cosmetic and never changes this hit axis. The target test uses
`this_xpos^2 + this_ypos^2 <= hits_rad^2`, with the existing visibility,
invincibility and destruction checks. Only one eligible object can take damage
per shot; the original object traversal order is retained. Missile locking keeps
its existing targeting test.

The build option `laser=dualbeam` (default) draws two filled triangular
beams from the bottom left and right, converging on one shared jittering tip.
`laser=singlebeam` draws one narrow filled triangle from the bottom centre
to the same tip. In the 256 x 112 viewport, dual bases span x=-92..-80 and
x=80..92; the single base spans x=-3..3. All bases lie at y=-56. Both styles
retain the existing tip jitter (x=-4..3, y=-2..1), consuming the same two random
calls per drawn frame. The native solid polygon raster fills both even and odd
rows in the weapon colour, using temporary stack vertices without changing code
or the world node list. All four flight views use their own equipped laser.
The option changes player beam appearance only; AI beam drawing is unchanged.

| Laser | Colour (existing palette index) | Damage per accepted hit | Original cooldown | Visual behaviour |
| --- | --- | ---: | ---: | --- |
| Pulse | Red (6) | 5 | 10 game frames | Short pulse at each accepted shot |
| Mining | Magenta (4) | 7 | 8 game frames | Short pulse at each accepted shot |
| Beam | Orange (3) | 9 | 6 game frames | Continuous while fire is held and heat permits |
| Military | White (15) | 11 | 3 game frames | Continuous while fire is held and heat permits |

Mining uses the same magenta as the shield and energy instrument bars. No
palette entries are changed. Colour selection follows the laser fitted to the
current view and applies to both beam styles. AI colours follow the player's
rating bands described below.

The shot cooldown uses the original Atari game-frame counter, decremented in
the same place in the cockpit renderer as before the laser conversion. It
continues counting down after trigger release. Returning to fire before it
expires does not bypass it. Unlike the first instant-laser implementation,
Pulse does not use a 50 Hz clock for its firing interval, and visible Beam or
Military frames do not automatically produce damage.

Each accepted shot immediately evaluates one hit and adds one unit of heat.
Pulse and Mining trigger the original firing sound; Beam and Military use
continuous audio independent of the damage interval. The original per-hit damage, heat limit,
cooling and energy handling are retained. Thus shot intervals and the entire
heat progression match the travelling-projectile version; only its initial
eight-game-frame hit delay is removed.

A separate per-frame visual request keeps Beam and Military visible between
damage ticks. Cosmetic tip jitter updates on every drawn frame, independently
of damage and heat. Releasing the trigger removes the continuous beam on the
next frame. Overheating prevents both new shots and the held-beam request.
Pulse flashes are visible on their firing frame and may persist until three
vertical blanks have elapsed; this short visual lifetime does not control
shot cadence and never repeats damage. View/system resets clear the cooldown,
pending hit, held-beam request and pulse flash.

At PAL 50 Hz with three vertical blanks per game frame, the nominal shot
intervals are 0.60 s (Pulse), 0.48 s (Mining), 0.36 s (Beam), and 0.18 s
(Military). Actual intervals increase if the game frame takes longer. This is
the original frame-based pacing rather than BBC's 50 Hz shot timer; the BBC
references below describe the visual style and fixed-axis aiming.

## Continuous player laser audio

The input frame publishes a stable audio request independently of the
visual beam flag. Holding Beam or Military sustains the sound between
accepted hits without restarting it or consuming random numbers. Release,
overheating, pause, docking, hidden cockpit, locked controls, game over
and disabled Effects end the sound with a short release. View/system
changes clear the request; music startup and shutdown also clear it.

The native Amiga driver loops two newly synthesized 4,096-byte signed PCM
waveforms at Paula period 214. Beam is lower and softer; Military is brighter
and richer in harmonics. Both are original sounds generated at build time
by `tools/beam_audio.py`, with no Frontier samples or additional build
dependencies. Channel 3 is reserved only while the sound is active or fading,
leaving three channels for effects. Volume ramps to 48/64 and releases in
three PAL VBLs (60 ms); the existing muted-DAC delay precedes DMA shutdown.

Successful player hits still trigger the original target-impact effect. It plays
on another effect channel alongside the continuous beam; `aifiresound=no`
does not disable this feedback.

## AI weapons

AI beam colours follow the same player-rating bands as base damage, using
existing palette entries: Harmless through Poor is red (6), Average through
Competent is orange (3), and Dangerous through Elite is white (15). The
Constrictor always uses white regardless of player rating. Thargoids and
Thargons (Tharglets) always use light blue (10). The colour applies
to both hits and misses; it does not assign a player weapon type or change
damage, firing opportunities, accuracy or sound.

An enemy's current position and forward orientation determine whether it can
fire and hit. The firing cone uses the BBC ratio 32/36; the narrower hit cone
uses 35/36. A ship aimed between those limits fires a visible beam but misses.
Within the narrower hit cone, each shot also makes a separate accuracy roll:
the additional miss chance increases with the shooter's distance from the player.
This is a project-specific change, not a rule from BBC Elite.

| Distance (world units) | Additional miss chance |
| ---: | ---: |
| 1,000 or less | 10% |
| 3,000 | 20% |
| 5,000 | 30% |
| 7,000 | 50% |

A 16-byte table stores these four anchors. Each otherwise well-aimed shot
interpolates between neighbouring anchors, rounding down to 0.5 percentage points;
for example, 2,000 gives 15%, 4,000 gives 25%, and 6,000 gives 40%.
There is no additional calculation on frames without an eligible shot. The
distance is the existing world-space range, independent of scanner zoom or view.
Random bytes 200..255 are retried; accepted values 0..199 are compared with
twice the miss percentage. The anchor probabilities are therefore exact.
Geometric misses do not make this extra roll and can never become hits.

AI lasers can fire at up to 12,288 world units, exactly half the scanner's
24,576-unit range at x1. Scanner zoom does not change the firing range.
The accuracy table is unchanged: its existing cap keeps the additional
miss chance at 50% from 7,000 through 12,288 units. Firing does not require a
full ship model; point-sized and subpixel ships can also fire.
The original random firing opportunity, cloaking check and control
lock remain in effect. A hit is applied immediately to the front or aft shield
according to the shooter's position. Every shot still draws its beam, including
both kinds of miss. The build option `aifiresound=no` (default) disables only the
AI laser firing sound. `aifiresound=yes` requests the existing firing sound on
hits and misses, subject to the game's Effects setting. Impact sounds remain
active on hits according to their existing rules. Misses do not update
shields/energy or request an impact sound. Player firing sounds, missile alerts
and other effects keep their existing handling. The option does not change
accuracy, damage, firing opportunities or random-number consumption.

Base damage retains the original random 1..3, 1..5 or 1..7 according to player
rating; the Constrictor's base damage remains 6. Each successful hit makes a
separate random choice of multiplier 2, 3 or 4, with equal selection weights,
and applies base damage times that multiplier in one shield/energy update.
The fourth two-bit random value is rejected to avoid favouring any multiplier.
Misses cause no damage and do not roll a multiplier. Final ordinary damage is
2..12, 2..20 or 2..28 (only products of the base and multiplier are possible);
Constrictor hits deal 12, 18 or 24.

This approximates the repeated damage that one old travelling projectile could
apply on consecutive frames within collision range. It does not reproduce
projectile travel, collision duration or exact encounter outcomes. AI shots no
longer allocate projectile objects. The former photon logic index remains
reserved and inert, preserving the other logic indices.

The beam starts at the model's transformed `gun_node`. All 22 ship models have
a valid muzzle node. Projection uses the same cached view position as the
rendered model. Following BBC Elite, the other endpoint lies at the opposite
side of the viewport, with a visual height derived from depth; this endpoint
does not determine damage. Invalid or extreme projections are rejected before
the native line clipper. Ships outside the viewport can still show the clipped
portion of their beam. After an off-screen ship's AI fires, a laser-only record
is inserted at its cached view depth in the same sorted queue as visible ships.
The off-screen model is skipped; nearer ships still cover the beam, and sights
and text remain above it. Hidden Cougars, emitters behind the current view and
exploding ships do not gain visible beams. Shots, damage and accuracy are
unchanged. There is at most one draw record per object, including laser-only
records; no extra object slots are allocated. The vector workspace reserves
80 additional bytes, without changing the object or commander-save layout.

The working ship data centres the muzzle across the bow for four models:

| Ship | Gun node (zero-based) | Local position (X, Y, Z) |
| --- | ---: | --- |
| Sidewinder | 10 | (0, 0, 36) |
| Gecko | 12 | (0, -4, 47) |
| Adder | 18 | (0, 0, 53) |
| Moray Star Boat | 14 | (0, 0, 65) |

Sidewinder and Gecko use existing centre nodes. Adder and Moray each append
one muzzle-only node; their original mesh vertices, faces and visible barrels
are retained. The Gecko muzzle keeps the bow's original height of Y=-4.
Transporter, Escape Capsule and all other models retain their original muzzle
data. Both targets reserve 20,172 bytes for `OBJECTS.IMG`, accommodating the two
additional eight-byte nodes. Original sources remain unchanged.

AI beams are drawn with their ships in the existing depth layers, allowing
nearer objects to cover them. Player beams are drawn after the world; sights
and viewport text remain above the beams. AI beams use the rating colours
described above; player beams use their weapon colours.

## Validation

The former CPU-emulation test suite has been removed. Build and file-format
checks remain available through the normal build and `tests/` discovery.
Gameplay validation requires WinUAE or original hardware.

Check both beam styles, all four flight views, player and AI beam colours, hits and misses, shielding, clipping and firing sounds.

## BBC source references

- [LASLI: player beam drawing](https://elite.bbcelite.com/disc/flight/subroutine/lasli.html)
- [Flight loop part 3: weapon firing](https://elite.bbcelite.com/disc/flight/subroutine/main_flight_loop_part_3_of_16.html)
- [Flight loop part 16: pulse timing](https://elite.bbcelite.com/disc/flight/subroutine/main_flight_loop_part_16_of_16.html)
- [HITCH: fixed-axis targeting](https://elite.bbcelite.com/disc/flight/subroutine/hitch.html)
- [TACTICS part 6: firing and hit cones](https://elite.bbcelite.com/disc/flight/subroutine/tactics_part_6_of_7.html)
- [LL9 part 9: AI muzzle and beam](https://elite.bbcelite.com/disc/flight/subroutine/ll9_part_9_of_12.html)
