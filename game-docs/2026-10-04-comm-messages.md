# Cockpit communications

Both enhanced platforms have independent implementations in `asm/comm.m68`.
AI ship messages use this same framework; their triggers, 50% event lottery and
seventy text variants are documented in [AI ship radio](2026-10-04-ai-radio.md).
Station messages keep their existing IDs and rules. AI and station messages have
equal queue priority, so an AI arrival can evict the oldest station message when
the queue is full.
The queue holds three messages, oldest first. A fourth arrival replaces the
oldest entry immediately, including in UI. Each record contains snapshots of
the sender and recipient registrations, a text ID, and an explicit player-recipient
flag. The queue has one shared
timer. Removing a ship or reusing its object slot cannot change a message
already received.

Messages are yellow, at the top left of the 3D viewport. In messages addressed
to the player, only the six recipient-ID characters after the colon use the
existing pulsing engine colour (`pulse`, palette index 14). The sender, colon,
comma and message body remain yellow. The recipient pulses in sync with engines;
there is no separate blink timer. This also applies to the player's `??-???` ID,
but anonymous NPC recipients remain yellow. The audience flag is captured at
receipt, so later registration or Scramble ID changes cannot retag queued messages.
Newer messages appear below older ones; removal compacts the queue upwards. Text wraps at the viewport
width (32 logical characters with the cockpit frame, 40 without it). The first
line is at logical y=8, leaving the frameless view heading visible. Existing font
routines scale text for hires, interlaced and doubled display modes. Messages
are not painted on menus or charts.

Each arrival requests its own receipt voice (`sfx_comm`), including while in a UI
screen, subject to the normal Effects setting and music priority. The sound is
the platform's hyperspace countdown beep: original Amiga effect 18, or Atari's
existing lock/countdown PSG tone. There is no separately generated radio sample.
Rapid receipts restart one receipt voice instead of stacking voices. Drawing
and expiry do not play a sound. Identification and missile locking retain their
original sounds; ordinary Amiga identification/lock requests retain duplicate
suppression.
Every seven seconds in the 3D view, only the oldest message is removed. The
remaining messages move up, and the next interval starts at a full seven
seconds. Three messages received together in UI therefore disappear after
7, 14 and 21 seconds in 3D. A delayed frame removes at most one entry rather
than clearing several messages together.

The shared timer pauses on UI screens and resumes with its remaining time on
return to 3D. New arrivals always append immediately, including in UI. Appending
to a non-full queue does not postpone the current interval. An arrival to a
full queue immediately evicts the oldest entry and starts a fresh interval for
the newly promoted head; the timer remains paused if this happens in UI.
The first arrival into an empty queue also starts a fresh interval. Timing uses
elapsed hardware flybacks counted only while the cockpit is visible:
350 ticks at 50 Hz, 420 at 60 Hz. Atari reads the active video-frequency bit;
Amiga uses the selected PAL/NTSC display family. Screen transitions settle the
elapsed time before changing the cockpit flag, so even a long UI visit cannot
be charged to the first 3D frame. Amiga receipt sounds can retrigger an ongoing
beep; ordinary repeated effects retain their previous suppression rules.

The queue is transient and is cleared on death, a new game, loading a commander,
normal or galactic hyperspace, and docking. Beginning a hyperspace countdown
does not clear it. The common system reset also clears it when launching.
No communication state is written to commander saves.
The same resets clear the station-approach notification state.

## Active Cloaking Device

An active player Cloaking Device suppresses every new radio receipt: station
messages, AI-to-player messages and AI-to-AI messages. The shared queue rejects
both enqueue entry points without changing queued records or requesting a beep.
Event producers also skip their cosmetic random draws while cloaked. Existing
received messages still display and expire normally; they are not cleared by
toggling cloaking.

AI greeting/protest opportunities and station arrival-notification latches are
not consumed while cloaked. After uncloaking, current eligible conditions can
produce messages normally; past departure/ejection events are not replayed.
Station docking permissions, bans and S-zone latch resets still follow their
existing rules. Cloaking does not bypass the Scramble ID docking restriction.
Cargo ejection is the explicit legal-status exception described below.

## Registrations and callers

The visible format is `C1-107:JS-042, Message text.`. Stations use their galaxy
and system number. Pirates, alien craft and scrambled player identities use
`??-???`; the hidden state is captured at receipt. `comm_id_player`,
`comm_id_station` and `comm_id_object` return packed identity snapshots.
`comm_enqueue` accepts the text ID in D0.W, sender in D1.L and NPC recipient in
D2.L, preserving all registers. `comm_enqueue_player` accepts the same inputs
and explicitly marks the recipient as the player. Both reject unknown text IDs
without beeping or changing a queued record. Callers must select the correct
entry point instead of comparing visible registrations, because several ships
can share `??-???`. Each transient record is 12 bytes; queue compaction copies
the audience flag together with the IDs and message. Additional callers can use
these helpers without retaining object pointers.

## First message: illegal cargo jettison

A successfully created player cargo canister triggers one station message and
the existing +15 legal-status penalty only inside the physical S-zone boundary
(`planet_range < $22500`), with an intact human station and a non-Anarchy
government. Compass/UI resets do not bypass this check. An active Cloaking Device,
witch space, a destroyed station, and the Thargoid-controlled mission station
are exempt. Cloaked ejections still create the canister and remove the exact
cargo amount, but do not change the legal record or send a radio warning.
Mission state $52 is explicitly excluded. The record still saturates at 255;
reaching that limit does not suppress further warnings. Failed, empty,
cancelled or otherwise ineligible requests do not send a message.

All five texts have equal probability:

1. Dumping cargo near this station is illegal.
2. Cargo dumping is prohibited in the station zone.
3. Illegal cargo disposal detected. This offence has been recorded.
4. Keep the station zone clear. Do not dump cargo here.
5. Unauthorized cargo dumping. Your legal record has been updated.

The cosmetic 8-bit LFSR has a 255-state cycle, with each variant occurring 51
times. It is seeded from the flyback clock and does not consume gameplay or
registration randomness. Consecutive arrivals may select the same variant.

## Station departure greeting

After a successful civilian AI launch, the station sends the departing ship
one of ten equally likely greetings. The sender is the station registration and
the recipient is the departing ship's newly assigned registration. Police
Vipers are excluded. Deep-space spawns and failed launches do not send it.
Anarchy stations also greet departing ships; this is independent of cargo law.
Alien, absent and destroyed stations remain silent, including mission state $52
and witch space. Pirate and scrambled player recipient IDs remain hidden.

The player receives a greeting from the same set after the real launch animation, system
reset and return to the cockpit, so the departure reset cannot erase it.
Pressing the launch/view shortcut while already in flight does not repeat it.
The existing queue, beep, UI pause and seven-second removal rules apply.

The ten departure texts are:

1. Have a good flight.
2. Fly safe.
3. Safe travels.
4. Good luck out there.
5. Until next time.
6. Have a safe journey.
7. Watch your six.
8. See you again soon.
9. Departure confirmed. Fly safe.
10. Have a profitable trip.

Departure text IDs 5–14 are separate from the five random cargo warnings (IDs 0–4).
`comm_jettison_count` bounds their existing cosmetic lottery independently of
the total text count. Departures use the same cosmetic LFSR but reject states
251–255 before reducing the remaining 250 states to ten choices. Each greeting
therefore occurs exactly 25 times per full cycle of accepted departure draws.
Consecutive greetings may repeat. No gameplay or registration RNG is consumed,
and excluded or failed departures do not consume a comm random draw.

## Station approach and docking permission

The station checks the existing cached `station_range`, calculated by
`get_range`/`calc_distance`; no second distance calculation is added. The
inclusive range of 2,000 is shared with the trader launch exclusion through
`station_traffic_range`. Shuttle launch range remains 6,144.

On the first close approach during a visit to the physical S zone, an intact
human station sends one message to the player. The existing `no_entry` flag,
also used by manual docking and the docking computer, selects a clearance or
a denial. A new Scramble ID permission check runs before text selection: at
2,000 units or closer, a hidden ID sets `no_entry` in Multi-Government, Communist,
Confederacy, Democracy or Corporate State. The check never changes the legal
record. It runs even if clearance was already sent, so newly qualifying hidden
IDs receive one additional denial. Existing bans retain priority. Entering S
alone does not trigger this check, and Anarchy, Feudal and Dictatorship exempt it.
Anarchy stations participate. Alien stations, including the Thargoid-controlled
mission station ($52), remain silent. There is no message while docked, in the
actual docking frame, in witch space, or without an active human station.

`comm_arrival_sent` has three transient states: 0 means no approach message,
1 means clearance sent, and 2 means denial sent. Circling the station, leaving
the 2,000-unit radius, switching UI pages and expiration of the visible message
do not reset it. It rearms at the physical S-zone exit
(`planet_range >= $22500`), independently of compass selection and the separate
cargo-scan hysteresis. Death, new/load game, hyperspace, galactic hyperspace and
docking clear it through `comm_reset`.

If a player who received clearance subsequently loses docking permission, the
station sends one additional denial during that S-zone visit, once the player
is 2,000 units away or closer. Further denials are suppressed.
A confirmed player laser hit on the station also calls `comm_station_hit`
immediately after setting `no_entry`. It uses the same station exclusions,
inclusive 2,000-unit limit and `comm_arrival_sent` state as approach checks.
A shot within that limit sends the warning during the hit handler. A shot
farther away applies the existing ban and 10-point legal-record increase
immediately (saturating at 255), but does not enqueue a warning or play its
receipt beep. The approach check sends it upon reaching 2,000 units or closer.
This also applies just after launch, when the station is 2,500 units behind the
player, and when a previous clearance has been issued. While deferred, the
sent latch and cosmetic RNG are unchanged; no additional pending-message flag
is needed. Sending the warning sets state 2, so repeated hits, UI transitions,
message expiry and later approaches cannot repeat it during that S-zone visit.
Hitting a Thargoid station remains silent.

After leaving and returning to the S zone, a still-banned player receives a new
denial on close approach, including a station hit within S and at most 2,000
units away. No permission or denial message is newly issued above that distance.
Leaving S never removes the docking ban itself.

Clearance messages (IDs 15–24, 10% each):

1. Permission to dock granted.
2. Cleared to dock.
3. Docking clearance granted.
4. Welcome. You may dock.
5. Docking permission approved.
6. Approach approved. Proceed to dock.
7. Dock when ready.
8. You may begin your docking approach.
9. Clearance confirmed. Approach safely.
10. Welcome to the station. Docking approved.

For an Offender (legal record 1..49) or Fugitive (50..255) in Multi-Government,
Communist, Confederacy, Democracy or Corporate State, an otherwise permitted
clearance selects one of these ten texts (IDs 30–39, 10% each):

1. Docking granted, but you are not welcome here.
2. You may dock, despite your criminal record.
3. Docking approved. We have checked your record.
4. Cleared to dock. Keep your visit brief.
5. Docking permitted. You are being watched.
6. You may dock, but do not cause trouble.
7. Docking granted. Your record is a concern.
8. Clearance granted. We know your reputation.
9. Docking approved. Stay out of trouble.
10. You may dock. We will be watching you.

Clean players, and all players in Anarchy, Feudal and Dictatorship, use the
ordinary clearance set when docking is allowed. Offender/Fugitive status by
itself does not impose a docking ban. Both clearance sets use the same physical
S-zone and inclusive 2,000-unit approach checks and the same sent-state latch.
Changing the record after clearance does not send a second clearance. The old
automatic Scramble ID legal-record penalty and its three short pirate warnings
remain removed. Hidden player IDs still appear as `??-???` in the prefix; this
is independent of the selected body text.

Denied-docking messages (IDs 25–29, 20% each):

1. Vacate the area immediately.
2. Docking denied. Leave the station area.
3. You are not cleared to dock. Move away.
4. Keep clear of the station. Docking denied.
5. Docking access revoked. Leave immediately.

The same denial set is used for station hits, existing bans and the new hidden-ID
ban. No special additional warning set is introduced. A ban persists after
leaving S and clears through the existing system reset (death, launch and either
kind of hyperspace jump). The message latch has its own reset rules described
above. A banned station refuses docking-computer activation. Physical contact
with it applies normal station-impact damage even at perfect docking alignment
and while a previously engaged docking computer is flying the approach.
Repeated contact drains the struck shield and then energy; moving clear stops
this contact damage. Death occurs through the normal energy-depletion check,
not a special immediate kill. The existing speed-dependent collision formula
and hull resistance scaling are reused through `hit_station`.

The enhanced collision handler now checks `no_entry` again before the station
geometry branch. The historical Atari `FLIGHT.M68` routes a banned approach
through salvage checks but then returns to that geometry branch, allowing a
perfectly aligned approach in the native regression. Only the enhanced trees
are corrected; the historical archive and preserved original build are untouched.
This source finding does not assert the behaviour of every released game binary.

All three groups use only the cosmetic comm RNG. Both clearance sets use the same
unbiased ten-way draw as departure greetings; the five denials use the same
five-way draw as cargo warnings, with separate text-ID ranges. Each message
uses a snapshot of the station/player IDs, conceals a scrambled player ID,
beeps once and joins the existing queue immediately, including in flight UI.

## Verification

Native tests run the assembled game routines in private Hatari/WinUAE instances
on verified, separate hidden Windows desktops. Test code lives independently
in each platform's `tests` directory; logs and harnesses are under
`build/comm-qa`.

- `native_comm.py`: identity snapshots, hidden IDs, all 40 texts, unbiased greeting
  selection with rejection/retry, three-entry
  capacity, immediate UI overflow, shared timer, separate 7/14/21-second removal,
  exact deadlines, clock wrap, UI pause/resume, receipt-only
  sound requests, RNG distribution/isolation, successful and rejected cargo
  transactions, all governments, legal saturation, station/mission/witch-space
  exceptions, new/restored commander and system reset.
- `native_comm_render.py`: full-screen hashes against independently wrapped
  reference text, including three long messages after overflow, hidden IDs, empty queues and
  UI suppression. It also checks restoration of text cursor and colours.
- `native_comm_lifecycle.py`: real death, normal/galactic jump and docking
  entry points; only long animations and unrelated dialogs are skipped.
- `native_comm_departure.py`: real civilian and police launches, failed launches,
  deep-space spawns, player departures and mission progression, identity snapshots,
  UI delivery and exclusions for alien or missing stations. Complete 250-arrival
  cycles separately verify the exact ten-way distribution for player and AI recipients.
- `native_comm_arrival.py`: exact distance/S boundaries, the real cached-distance
  calculation, permission and denial, station-hit revocation, UI transitions,
  queue overflow, scrambled recipients, silent alien stations, gameplay RNG
  isolation, and complete clearance/denial distribution cycles.
- `native_docking_policy.py`: all 256 legal records, both identity states, all
  eight governments and distances 1,999/2,000/2,001 (12,288 combinations), plus
  station exclusions, real cached distance, existing-clearance revocation,
  legal-record preservation, notification rearming and exact text distributions.
- `native_docking_access.py`: accepted legal approaches, ordinary impact damage
  for banned contact with manual or active automatic control, and blocked
  docking-computer activation in both animated and instant modes. Real repeated
  impacts cover front/aft shields, Cobra/Anaconda resistance, four speeds,
  disengagement, shield overflow into energy and eventual energy-depletion death.
- `native_comm_audio.py`: actual PSG/Paula voices in UI and 3D, repeated
  arrivals, Effects OFF, music priority and audio shutdown.
- Existing Special Cargo input, W/V routing, mission spawn, AI systems and
  death-cargo suites cover adjacent gameplay.

The current native suites contain 126 comm scenarios, 232 full-screen rendering
comparisons, 73 approach cases, 32 policy cases, 40 docking-access cases, 45 departure cases, nine transition cases and
seven audio cases on Atari and eight on Amiga. The
standard Python tooling suites also pass (35 tests per tree, one skipped).
The initial renderer passed all 16 combinations of framed/wide view and PAL, NTSC,
PAL/NTSC hires, PAL/NTSC hires interlaced, and DblPAL/DblNTSC hires. These mode
checks use a private 68020/AGA emulator with 2 MB Chip RAM and 4 MB Fast RAM;
the normal framed PAL build is also tested as a 68000 with 1 MB total RAM.
The selected build options are restored after the mode matrix.

The subsequent reduction to three queued messages was rechecked with the 82
comm, 16 rendering and five transition scenarios on both platforms, including
replacement of the oldest message on the fourth arrival and overflow while UI
timers are paused.

The shared-timer correction passed 84 comm, 16 rendering and five transition
scenarios on each platform (105 per platform). These include checking queue
order immediately after every UI arrival and removing three queued messages
at separate 5/10/15-second deadlines after returning to 3D (the former interval). Standard and selected
ALT distributions were rebuilt with the correction.

The historical source archive and `src_orig` are unchanged.

The departure greeting passed 240 native scenarios per platform: 43 departure,
85 comm, 24 rendering, five lifecycle and 83 spawn-path cases. This includes
UI/3D delivery, civilian ship IDs, silent police launches, Anarchy departures,
alien-station exclusions, failed launches, scrambled player IDs, repeated
in-flight launch shortcuts and mission progression after player departure.
Standard and selected ALT distributions were rebuilt with the original options.
Reports and logs are under each platform's `build/comm-departure-qa` directory.

The ten-variant follow-up passed 288 native scenarios per platform: 45 departure,
95 comm, 60 rendering, five lifecycle and 83 spawn-path cases. Every greeting
appeared exactly 25 times in each 250-arrival player/AI test. Tests also cover
rejection of random states 251–255, unchanged cargo-warning selection, text
formatting and wrapping, hidden identities, and excluded departures consuming
no comm randomness. Standard and selected ALT distributions were rebuilt with
preserved build options. Reports and logs are under each platform's
`build/comm-departure-variants-qa` directory.

The initial approach/denial implementation passed 548 native scenarios per platform:
47 approach, 111 comm, 128 rendering, five lifecycle, 45 departure, 83 spawn-path
and 129 Scramble ID cases. Coverage includes actual station-hit permission
revocation, denial after earlier clearance both inside and outside the close
radius, exact physical S-zone rearming, mission-station silence, and reset on
death, both jump types, docking and commander restoration. The ten clearance
texts each appeared 25 times per 250 accepted draws; the five denial texts each
appeared 51 times per 255 draws. Standard and selected ALT distributions were
rebuilt with the preserved options. Reports and logs are in each platform's
`build/comm-arrival-qa` directory.
Its outside-radius revocation behaviour is superseded by the shared distance
gate described above.

The earlier station-hit follow-up reproduced the post-launch bug against the preceding
Atari executable, then passed 441 native scenarios on each corrected platform:
62 approach/hit, 113 comm, nine lifecycle, 45 departure, 83 spawn-path and 129
Scramble ID cases. The new regression performs a real launch, calculates the
2,500-unit station distance, and calls the actual station-hit handler (only aim
acceptance is stubbed). It checks immediate warning delivery before the next
approach check, repeated shots, hidden IDs, UI/3D, message expiry, S-zone rearming
and silent excluded stations. Reset tests now exercise both sent states 1 and 2.
Both standard and selected ALT distributions were rebuilt with preserved options.
Reports and the original failing reproduction are under `build/comm-station-hit-qa`
in the corresponding platform tree; the pre-fix reproduction is in the Atari tree.
The immediate 2,500-unit warning in that historical test is superseded: current
tests require a ban immediately and a warning only upon reaching 2,000 units.

The pulsing recipient-ID change passed 383 native scenarios per platform:
152 full-screen render comparisons, 115 comm, 45 departure, 62 approach/hit and
nine lifecycle cases. Rendering references independently colour only the six
player recipient glyphs with palette index 14. Cases include anonymous player
and NPC recipients, mixed queues, overflow, UI suppression, wrapping, changed
registrations after receipt, and restoration of the caller's text state. Actual
jettison, player/NPC departure and station-approach paths verify the audience flag.

Amiga also passed all 152 render comparisons in eight additional configurations:
wide PAL, framed NTSC, framed and wide PAL hires, framed PAL hires interlaced,
wide NTSC hires interlaced, framed DblPAL hires and wide DblNTSC hires. These use
the private 68020/AGA harness; the normal framed PAL build passed on 68000 with
1 MB RAM. Standard and selected ALT distributions were rebuilt and the original
build options restored. Reports are under `build/comm-recipient-qa` in each tree.

The earlier Scramble ID clearance-text substitution passed 737 native scenarios per
platform: 113 approach/hit, 129 Scramble ID, 126 comm, 232 full-screen rendering,
45 departure, nine lifecycle and 83 spawn-path cases. The approach matrix checks
all eight governments with visible and scrambled IDs at 2,000 and 2,001 units:
only the text changes, never the trigger distance. Further checks cover legal
records 0..255 at relevant thresholds, unchanged ordinary police inputs, removal
of the old penalty warning, denial priority, mission-station silence and shared
notification resets. Each alternative text appears exactly 25 times in 250
accepted draws. Pirate neutrality, mission spawns and save compatibility remain
covered by the unchanged gameplay regression paths.

The standard Python suites pass 35 tests per platform (one artwork-related skip).
Both standard and selected ALT distributions were rebuilt, preserving the user's
build options. All native checks use verified hidden desktops and private
emulator files. Reports are under `build/comm-scrambled-arrival-qa` in each tree.

The later docking-policy change passed **1,076 native scenarios per platform**:
32 policy, 62 approach/hit, 126 comm, 232 full-screen rendering, 45 departure,
nine lifecycle, 129 Scramble ID, 83 spawn-path, eight docking-access, eight
missile-collision, 22 missile-impact, 72 shield-flash and 248 AI-system cases.
The 32 policy scenarios include 12,288 combinations of every legal record,
identity state, government and the 1,999/2,000/2,001 distance boundary. Tests verify
that Clean/Offender/Fugitive text selection never changes the record, hidden IDs
produce the existing denial set and ban, prior clearance can be revoked only
when the approach qualifies, and excluded stations remain silent. Both cosmetic
text lotteries retain their exact uniform distributions.

The manual-docking regression first reproduced acceptance of a perfectly aligned
banned ship, then passed after the initial enhanced collision fix. That stage verified fatal
contact for both existing bans and hidden-ID bans with manual or already active
automatic control, successful allowed docking, and rejected docking-computer
activation in normal and instant modes. Death and both jump paths also verify
that the ordinary system reset clears the ban.

Both standard and selected ALT distributions were rebuilt with preserved options.
The Python suites pass 35 tests per tree (one existing artwork skip). Private
emulator reports, source snapshots, the original failing manual-docking case
and a historical-source excerpt are under `build/comm-docking-policy-qa`.

The contact-damage follow-up replaces the initial immediate death with the
existing `hit_station` damage path. It passed **223 native scenarios per
platform**: 40 docking-access, 32 station-policy, 62 approach/hit, eight
missile-collision, nine lifecycle and 72 shield-flash cases. The expanded access
suite executes real shield and energy loss for both existing and hidden-ID bans,
front and rear impacts, Cobra and Anaconda resistance, and speeds 0, 1, 10 and 22.
It checks survival of the first impact, no damage after moving clear, separate
shield and energy depletion, and normal death only once energy runs out during
repeated impacts without intervening recharge. Allowed docking and blocked
computer activation still pass. Both standard and selected ALT distributions
were rebuilt with preserved options; reports are in `build/station-ban-impact-qa`.

The shared 2,000-unit notification gate passed **325 native scenarios per
platform**: 73 approach/hit, 32 policy, 40 docking-access, 126 comm, 45 departure
and nine lifecycle cases. The previous build fails the new post-launch test:
it warns at 2,500 units instead of deferring until 2,000. Updated tests cover
immediate warnings at 0/1,999/2,000; silence at 2,001/2,500/5,000; deferred
revocation after earlier clearance; unchanged pending latches and cosmetic RNG;
immediate legal penalties capped at 255; UI/3D and hidden IDs; and S-zone
rearming without duplicate warnings. Alien-station exclusions are tested within
the close radius so the range gate cannot mask them. Existing queue, departure,
permission, collision and reset checks also passed. Standard and selected ALT
distributions were rebuilt; reports, source hashes and the failing reproduction
are in each platform's `build/comm-distance-gate-qa`.

The queue interval was subsequently extended from five to seven seconds:
350 flybacks at 50 Hz or 420 at 60 Hz. All 126 comm and nine lifecycle scenarios
passed per platform, covering exact expiry, separate 7/14/21-second removals,
UI pause/resume, overflow, new arrivals, clock wrap and reset paths. Both standard
and selected ALT distributions were rebuilt. Reports and source hashes are in
`build/comm-seven-seconds-qa` in the corresponding tree.

Receipt audio initially reused the identification/lock confirmation instead of the
error beep. At that stage the Atari entry requested `sfx_locked`; the Amiga VBL
consumer and receipt-specific restart exception selected that same effect.
Existing sample data, PSG tone settings and the identification path were reused.
Native checks passed 139 scenarios on Atari and 140 on Amiga: seven/eight
receipt-audio cases, six laser-impact audio cases and 126 comm cases. They cover
the original identification effect, receipt playback in UI/3D, twelve rapid
receipts, Effects OFF, music priority and audio shutdown. Amiga additionally
checks that ordinary repeated lock requests retain duplicate suppression.
Standard and selected ALT distributions were rebuilt; reports and source hashes
are in `build/comm-identification-audio-qa` in each tree.

Receipt audio was then separated into `sfx_comm`, a single approximately 100 ms
beep. Atari uses tone period 56, volume 11 and five PAL or six NTSC ticks. Its
dedicated service identity lets later receipts reclaim only the receipt voice.
Amiga builds a 1,582-byte sample locally with `tools/comm_audio.py`: a 740 Hz tone,
4 ms attack, 12 ms release and silent padding. The voice stops after six PAL or
eight NTSC VBLs, before DMA can repeat the sample. The ordinary Amiga effect
request table remains unchanged; comm receipts use their dedicated VBL request.

Verification of the dedicated beep passed 144 native scenarios on Atari and
143 on PAL Amiga, plus all 11 receipt-audio scenarios on NTSC Amiga. These cover
independent identification voices, one voice for rapid receipts, bounded tone
duration, UI/3D, Effects OFF, music priority, shutdown, shield-impact audio and
the 126-case communications suite. The ten Amiga asset/build tests also pass,
including the new waveform, pitch, single-pulse and PAL/NTSC DMA-tail check.
Existing Amiga sound and music asset metadata is unchanged. Evidence is under
`build/comm-beep-qa`; both standard and selected ALT distributions were rebuilt.


## Countdown beep reuse (2026-10-05)

Receipts now reuse each platform's countdown beep. Amiga uses original effect
18 from `Elite 2.0.adf`, also selected by the newly independent countdown event.
The generated communication PCM and its generator have been removed. Atari
receipts call the existing lock/countdown sound setup (tone period 50, volume
12, ten sound services). They keep their own service identity solely to reclaim
an existing receipt voice. Neither platform changes identification or missile
lock audio. The receipt still sounds in UI, honours Effects/music gates, and
restarts one receipt voice when another message arrives.

See [countdown fix and original sound review](2026-10-05-countdown-audio-review.md)
for validation and differences deliberately left unchanged.
