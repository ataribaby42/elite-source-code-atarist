# Original Amiga effect playback

The Amiga identification action now requests `sfx_identify`, appended after the
existing events and mapped to original effect 9. Missile lock retains effect 1.
Countdown and incoming radio messages retain their separate events sharing the
short original effect 18. Atari audio is unchanged.

## Replay

`src_amiga/asm/sounds.m68` now follows the original Elite 2.0 duration, repeat,
fade and pitch rules. The source of these rules is the handler at
`$5b4e..$5cce` in the preserved `resources/amiga/Elite 2.0.adf`. The original
sample bytes, descriptors and period table are unchanged.

Each finite effect counts down its descriptor duration. The original repeat
value zero still allows a second duration pass; a reload service does not advance
the pitch. After the last pass, effects either stop or decay through the original
zero-volume service before stopping. Muting or preempting a voice waits for
its actual sample period before disabling DMA, including periods beyond 428,
so restoring the pitch progression preserves the held-DAC shutdown fix.
Pitch slides use the original equality
limits and 12-bit arithmetic. The alternating-pitch handler also follows the
actual original routine.

The following uninterrupted lifetimes are measured after the voice starts.
Voice preemption, `quiet`, or a scene reset can still end an effect sooner.

| Effect | VBL services | PAL, 50 Hz | NTSC, 60 Hz |
| --- | ---: | ---: | ---: |
| Pulse / Mining firing sample (corrected audible start) | 9 | 0.18 s | 0.15 s |
| Identification | 10 | 0.20 s | 0.167 s |
| Missile lock | 34 | 0.68 s | 0.567 s |
| Explosion | 74 | 1.48 s | 1.233 s |
| Countdown / radio receipt | 2 | 0.04 s | 0.033 s |
| Hangar departure | 571 | 11.42 s | 9.517 s |
| ECM sound | 178 | 3.56 s | 2.967 s |

Gameplay ECM duration remains its independent 116-service timer. The hyperspace
and galactic animation timer is three seconds on both platforms, following the
subsequent timing adjustment. Neither timer depends on the
restored sound duration. The enhanced energy-bomb sample keeps its own baked-in
envelope and lifetime; continuous player lasers, RCS and manual throttle retain
their existing playback.

## Sustained sounds

The descriptor repeat value 255 now means sustained playback. Torus audio lasts
while the drive is active, rather than expiring after 40 services. Red-condition
alerts also sustain until the condition changes. Ordinary effects cannot replace
an active torus or alert voice, and continuous player lasers keep their reserved
channel. Incoming hits and radio receipts still retrigger their own voices.

Torus playback ends when the drive stops, the player docks or dies, Effects are
disabled, or audio is reset. A remembered drive request allows recovery after a
transient owner-state change between game-frame steps. `quiet` clears that
permission, so a reset cannot restart an old drive sound.

The dedicated pirate-ambush sound remains absent by request, pending a separate
discussion. AI laser firing stays silent. No spawn, mission or combat logic was
changed.

## Verification

`src_amiga/tests/native_original_effects.py` executes the original ADF handler
bytes against private scratch state and compares every service with the linked
enhanced player: pitch period, volume and active/stopped state. Only absolute
references to the oracle's data are relocated; its instructions are unchanged.
The tests also cover the actual identification path, torus lifetime and shutdown,
sound competition, reset and recovery after a transient owner change.

Tests run in private WinUAE copies on verified hidden Windows desktops. Test
artifacts and per-scenario reports are under
`src_amiga/build/original-effects-qa`.

Results:

- 366 PAL native scenarios passed: 27 original-handler comparisons and lifecycle
  cases, 15 identification/countdown/radio audio cases, six impact-retrigger
  cases, 50 request/channel-competition cases, five jump-timer cases, 126 comm
  cases, nine comm lifecycle cases, 49 identification/control/pixel cases,
  69 AI-radio cases and ten Special Cargo lifecycle cases.
- All 103 audio and jump-timer cases also passed in NTSC.
- Python discovery passed 35 tests; the historical PNG identity check was
  skipped because the artwork has been customized.
- All 18 Amiga distribution variants rebuilt successfully, retaining the original
  effect and music sample hashes. The selected build configuration was restored.
- The pixel suite requires cycle-exact emulation: the accelerated run failed
  its first marker comparison, while all 49 cases passed with accurate timing.
- The original ADF, historical source archive, Atari/original assembly sources
  and changelog are unchanged.

The original-handler comparison checks envelope state and timing; it does not
claim bit-identical recordings or replace a listening test on physical hardware.

The subsequent three-second jump-timer adjustment passed five native cases in
each of PAL and NTSC: both jump types with Effects ON/OFF, plus explicit timer
cancellation. All 18 Amiga variants rebuilt, and the selected configuration was
restored. The final circle still completes after the initial timer expires.
Evidence is under `src_amiga/build/warp-three-seconds-qa`.

## Pulse tail correction

The restored Pulse lifetime initially included one service during which the
original player still had DMA disabled. The original initialization at `$5b28`
sets the mute mask, and the update at `$5b4e` clears the channel's mute bit before
advancing its envelope. Counting that initialization service as audible playback
gave Pulse ten frames of DMA output instead of nine. At PAL frequency, this
restarted the 1,580-byte sample's attack just before expiry, causing a noisy tail.

The enhanced discrete laser event now starts at the original first audible
envelope state: period 427, three remaining duration steps, and nine services
until expiry. This preserves immediate response without the extra audible
frame. Pulse and Mining share this sample. Continuous Beam/Military audio and
the other effects are unchanged; no weapon damage or firing cadence changes.

The original-handler test now compares Pulse from the first audible service.
`src_amiga/tests/native_pulse_audio.py` also observes Paula's block-completion
interrupts at real frame boundaries: it clears the initial DMA request, rejects
another request before expiry, and checks DMA shutdown. The pre-fix binary
failed both the audible-state comparison and the hardware sample-repeat probe.
The Python sample-budget check covers PAL and NTSC and demonstrates why the old
ten-frame PAL playback exceeded the sample length.

Pulse-tail evidence is under `src_amiga/build/pulse-tail-qa`. Emulator tests use
private copies on verified hidden Windows desktops, with cycle-exact Paula
emulation and no host sound output. Only the standard `ELITE` and `ELITE_ALT`
distributions are rebuilt for this correction.

Verification passed: four real-frame Pulse DMA cases, 27 original-effect cases,
15 radio/countdown/identification cases, six shield-impact cases, 50 audio
competition cases and five jump-timer cases (107 native scenarios). Python
discovery passed 36 tests, with one historical-artwork identity test skipped.
Both standard Amiga builds passed executable and disk validation, and the
original sample-bank hash is unchanged.
