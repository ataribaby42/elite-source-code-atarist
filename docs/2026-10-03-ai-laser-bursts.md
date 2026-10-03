# AI laser bursts and incoming impact audio

Both enhanced versions give each AI ship its own firing timers. Pulse fires
single shots; Beam and Military draw a continuous beam for a randomly chosen
burst. Player weapon timing, base damage, hull resistance and loadout selection
remain unchanged. There is no random damage multiplier.

## Timing and appearance

| AI laser | Visible duration | Minimum interval between damage checks | Checks in a complete burst |
| --- | --- | ---: | ---: |
| Pulse | One game step | 10 game steps | 1 |
| Beam | 6–18 game steps | 6 game steps | 1–3 |
| Military | 6–18 game steps | 3 game steps | 2–6 |

The first damage check happens on the first visible step. For example, a
12-step Beam burst checks on steps 0 and 6 and remains visible on steps 0–11.
A 12-step Military burst checks on steps 0, 3, 6 and 9. The normal AI trigger
chance can start another shot or burst once the previous burst has ended and
the last damage check's cooldown has expired. It does not interrupt an active
burst. Consecutive successful triggers can therefore produce adjacent bursts.

At full PAL speed, one game step takes three vertical blanks (0.06 seconds):
a complete burst lasts 0.36–1.08 seconds. Slower rendering lengthens real time.
Beam damage checks are at least 0.36 seconds apart, Military checks at least
0.18 seconds apart, and Pulse shots at least 0.60 seconds apart at that rate.

The burst remains visible between damage checks and on a miss. Its position
is recalculated from the moving shooter and target each step. A visible line
is not itself evidence of damage: the existing aim cone and distance miss
roll still determine each scheduled hit. Damage remains Pulse 5, Beam 9 and
Military 11 before the victim's existing resistance calculation, for both
AI-versus-player and AI-versus-AI fire.

Target removal, explosion, a target change, lost firing aim, leaving attack
logic, or exceeding firing range cancels the burst. Player cloak and locked
controls also stop fire at the player; they do not stop combat between NPCs.
The remaining cooldown is retained after cancellation. A ship outside the
screen still advances both timers.

Laser classes and colours follow the [per-ship loadout rules](2026-10-03-ai-laser-loadouts.md).
Cougar always uses Beam, Constrictor uses Military, and Thargoid/Thargon retain
their rating-selected base power and blue colour. Their cadence follows that
stored power. Mission immunity, rewards, child creation and deactivation are
not changed by the burst code.

## Object state and random selection

Each live object gains two words and one longword:

- `ai_laser_cooldown`: remaining game steps until another damage check.
- `ai_laser_burst`: visible steps remaining, including the current step.
- `ai_laser_target`: target captured at burst start.

The object stride grows from 186 to 194 bytes: 240 additional bytes across
the 30-slot pool. The copied model header and commander save format do not
change. Allocation, creation (including copied ships), removal and clearing
the bubble reset the transient state.

`ai_laser_tick` runs before each object's normal flight processing. A counter
set on a firing step is first decremented on the following step. `ai_fire_laser`
handles trigger eligibility, held-beam rendering and scheduled damage checks.
The existing per-frame `ai_laser` value means no beam (0), visible without an
accepted damage hit (1), or an accepted hit on this step (2).

`ai_burst_length` accepts random bytes 0–246, rejects 247–255, then maps the
accepted byte modulo 13 to lengths 6–18. Every length has exactly 19 accepted
byte values. This avoids modulo bias. Burst length is chosen once, independently
for every new burst; the additional random draws change later RNG sequences
without changing the existing formulas for aim and distance accuracy.

## Incoming hit sounds

Each accepted incoming laser hit requests a fresh shield-impact sound even
when the previous impact is still playing. The current shield voice is reused
and its sound restarts from its attack; effects do not stack into multiple
shield voices. Misses and visual-only steps request no impact sound. Effects
OFF and music retain their previous suppression, and ordinary missile and
collision impact requests retain their existing duplicate handling.

Atari replaces the existing PSG shield effect under the audio update guard.
Amiga publishes one atomic pending flag, consumed by the VBL audio service,
which restarts the Paula sample and envelope. The producer does not publish
two separately interruptible request fields. `quiet` clears pending as well
as active impacts. As with other Amiga effect requests, hits arriving before
the same audio update can coalesce; successive damage checks within one burst
are separated by several game steps and therefore have separate audio starts.

## Validation

`tests/native_ai_bursts.py` executes the linked game routines in 91 scenarios
per platform. It covers every length 6–18, both beam classes, player and NPC
victims, exact firing intervals, continuous rasterized pixels, misses,
cancellation, off-screen timers, slot reuse and copied objects. It checks all
256 raw RNG inputs, including rejection, and samples 39,000 burst lengths
using three real game RNG seeds on each platform.

`tests/native_ai_impact_audio.py` checks the actual sound driver in six
scenarios per platform: initial playback, twelve consecutive overlapping
restarts of the same voice, Effects OFF, music suppression, ordinary duplicate
handling and clearing pending sounds. These are native voice/envelope checks,
not a listening test.

The final regression run passed 4,041 native scenarios on each platform:

| Coverage | Scenarios per platform |
| --- | ---: |
| Burst duration, cadence, visuals and state lifetime | 91 |
| Actual impact sound driver | 6 |
| Shared combat systems, accuracy, aliens and missions | 248 |
| Spawn paths and copied objects | 83 |
| Per-ship laser loadouts | 71 |
| Missile collisions and explosions | 30 |
| Shield flashes | 66 |
| Unbound-relative durability | 124 |
| Live player flight and runtime ship graphics | 29 |
| Missile and identification indicators | 197 |
| All-model rendering bounds | 3,096 |
| Total | 4,041 |

Mission checks include Constrictor protection and progression, Cougar rewards,
Thargoid child creation and deactivation, and witch-space repair. The Amiga
audio, identification-indicator, shield-flash and missile-impact suites used
cycle-exact 68000 timing. The accelerated identification test was replaced
with the cycle-exact run after a pixel mismatch; the final 49 scenarios pass.
All-model rendering used accelerated execution; its slower cycle-exact trial
was stopped before completion. Other native suites also used accelerated
execution. No gameplay change was made to the identification renderer.

Both platforms passed 34 ordinary tests, with one existing conditional
artwork-identity check skipped in each 35-test discovery run. All 20 builds
passed: two Atari artwork variants and 18 Amiga artwork/display variants.
Native tests used the framed PAL 68000 builds; other Amiga display variants
received build validation. The user's pre-test build options were restored.
The final audit verifies distribution hashes, matching cadence implementation
in both trees, the 194-byte object stride and current HTML source fingerprints.

Build logs, native payloads and regression reports are retained in each
platform's `build/ai-burst-qa` directory. Emulator runs use private executable,
configuration and disk copies on verified separate hidden Windows desktops.
The user's emulator session is not used. `docs/ship-balance.html` includes
the cadence table and incoming-hit sound behaviour; this change does not
alter its 110 hull durability counts.
