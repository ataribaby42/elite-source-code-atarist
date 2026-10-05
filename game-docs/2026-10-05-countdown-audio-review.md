# Countdown and radio audio; original Amiga sound review

## Changes

The Amiga hyperspace and galactic countdowns now request a separate
`sfx_countdown` event, mapped to original Amiga effect 18. Existing event numbers
are unchanged. Missile lock still requests `sfx_locked`. The subsequent
[original-effect replay repair](2026-10-05-amiga-original-effect-replay.md) gives
identification its own `sfx_identify` event and original effect 9.
The countdown interval and jump timing are unchanged.

Radio receipts reuse the countdown sound on both platforms:

- Amiga: original effect 18, period 428, two VBL services. The 598-byte sample
  does not complete a DMA loop before playback stops, at either 50 or 60 Hz.
  The custom radio PCM, descriptor, include and Python generator were removed.
- Atari: `fx_comm` calls the existing `fx_locked` setup, retaining tone period
  50, volume 12 and ten services. Only the service tag remains separate so a
  rapid receipt reclaims its own voice without replacing identification.

Radio still works in UI and 3D, honours Effects OFF and music priority, and
restarts one receipt voice rather than stacking receipts. Queue behaviour,
mission rules and the existing shield-impact retrigger path are unchanged.

## Original disk evidence

The comparison reads `resources/amiga/Elite 2.0.adf` without modifying it.
Its SHA-256 is
`3ef395dc1d73c86f7a8486329a24d2ced29b5c6b108df3da6cae1380b5666ee3`.
The OFS Game file is extracted from header block 887. For game code, file
offsets equal original runtime addresses plus `0x1cc`.

At original address `$76c0`, the countdown reloads its interval to 50, sets
`D0 = $12` (effect 18), calls `$58de`, then decrements the countdown. The second
code copy at `$1ecc0` agrees. Original Elite 1.0 also selects effect 18 and has
identical effect descriptors and PCM. The current extracted 53,908-byte PCM
bank is byte-for-byte identical to Elite 2.0.

## Original review and subsequent repairs

This is a code, descriptor and sample-data comparison, not a listening test of
every sound. The table includes the subsequent repair of identification,
torus lifetime and original-effect playback. The ambush sound remains deferred.

| Event | Elite 2.0 effect | Current enhanced Amiga |
| --- | --- | --- |
| Key click | 0 | 0 |
| Missile lock | 1 | 1 |
| Pirate ambush interrupting torus travel | 2 | The dedicated effect is absent from `flight.attack` |
| Player pulse/mining laser shot | 3 | 3 |
| Error beep | 4 | 4 |
| AI laser fire | 5 | Silent; accepted hits retain their shield-impact audio |
| Alert | 6 | 6, sustained while condition is red |
| Player shield hit | 7 | 7 |
| Teletype | 8 | 8 |
| Identification through I | 9 | 9, via its own identification event |
| Cargo scoop | 10 | 10 |
| Torus drive | 11 | 11, sustained while the drive is active |
| Laser hits target | 12 | 12 |
| Hyperspace tunnel | 13 | 13; the enhanced jump also has its separate animation timer |
| Player missile / escape pod / retro rockets | 14 | 14 |
| Explosion | 15 | 15 |
| Hangar departure | 16 | 16 |
| ECM | 17 | 17; gameplay ECM duration is timed independently |
| Countdown | 18 | 18 after this fix |

Relevant original call sites include `$3476` (identification effect 9), `$34a4`
(missile lock effect 1), `$91a4` (ambush effect 2), `$e920` (AI laser effect 5),
`$153de` (hangar effect 16), and `$158ca` (hyperspace effect 13).

The initial review found the following replay differences. They are corrected
by the subsequent [replay repair](2026-10-05-amiga-original-effect-replay.md):

- The original finite-effect handler decrements a repeat counter and reloads
  the duration before fading or stopping (`$5c88..$5cce`). The enhanced player previously
  used `descriptor[5] + 2`, plus a fixed decay allowance. It did not implement
  the original finite repeat count. For example, uninterrupted missile lock
  lasted 18 services versus 34 in the original; an explosion lasted 38
  versus 74. Hangar, ECM and other envelopes also differed.
- Original effects with repeat byte 255 are sustained. The enhanced player
  previously bounded them to 40 services. Alerts can be requested again, whereas
  `flight.torus` requests the drive sound once, so that sound used to stop after about
  0.8 seconds in PAL even while torus travel continued.
- Pitch slides were clamped in the enhanced player. The original arithmetic and
  envelope/repeat handling were not identical.

Continuous beam/military audio, RCS, manual throttle and the synthesized
Atari-style energy bomb are established enhanced features, not missing ADF
samples to replace as part of this fix. Atari keeps its native PSG sounds;
only radio now reuses its existing countdown beep.

## Verification

Evidence and isolated emulator helpers are under each tree's
`build/countdown-audio-qa`. GUI tests use private executables, disk copies and
verified hidden Windows desktops; they do not use the user's emulator session.

The native audio suite checks receipt voices in UI/3D, rapid retriggering,
identification coexistence, finite lifetime, Effects OFF, music priority and
shutdown. Amiga also calls the real VBL routine for normal and galactic
countdowns, checks one beep per decrement and the final jump trigger, and
checks that quiet clears the new pending event. Interrupts are temporarily
disabled through Exec only inside the private test harness so exact service
counts can be measured without a concurrent VBL.

The existing communications and shield-impact suites are rerun on both
platforms. Asset tests verify the original countdown call and that its playback
stops before DMA repeats the original sample at PAL and NTSC rates.

Results:

- Atari: 12 native audio, 126 communications and six shield-impact scenarios passed.
- Amiga PAL: 15 native countdown/audio, 126 communications and six shield-impact
  scenarios passed. All 15 countdown/audio scenarios also passed on NTSC.
- Python discovery: 35 passed on Amiga and 34 on Atari. Each platform skipped
  one historical PNG identity check because the artwork has been customized.
- All 18 Amiga release variants and both Atari graphics distributions rebuilt
  successfully. The original Amiga sample-bank hash is unchanged in every build;
  none embeds the removed custom radio sample.

These checks validate code paths, voice state and assets. They do not replace
listening on real hardware for the unmodified effects listed above.


## Follow-up regression review

A separate review reran 1,263 native scenarios: 576 on Atari, 619 on PAL Amiga
and 68 targeted NTSC Amiga cases. All passed on isolated hidden emulator
desktops. The 69 Python tests passed again, with the same two customized-artwork
identity skips. No production-code changes were needed and no regression was
found within this coverage.

The additional linked-driver stress cases check request-array guards and
invalid/reserved IDs, all accepted Amiga effects, simultaneous receipt,
countdown, target-lock and shield-hit voices, and 48 mixed arrivals while each
continuous laser retains its reserved audio channel. Both platforms retain the
full 116-service ECM wave under audio competition, including Effects OFF.
At this review stage, real VBL clocks confirmed two-second Amiga and
three-second Atari jump timers. The subsequent timing adjustment extends the
Amiga timer to three seconds as well, without changing countdown beeps.

Broader native suites cover AI radio, message lifecycles, normal and mission
spawns, Constrictor/Cougar behaviour, Thargoid/Tharglet ownership and damage,
mission advancement, energy-bomb exemptions and Special Cargo transitions.
The ordinary sound-event IDs and original sound/music asset hashes are
unchanged. The selected Amiga build configuration was restored after the PAL
and NTSC checks. Detailed reports are under `build/countdown-regression-qa` in
each source tree.
