# ECM wave timing

Date: 2026-09-17
Status: implemented
Trees: `src_atari`, `src_amiga` (applied separately). `src_orig` is not touched.

## 1. The defect

`ecm_on` is the flag that makes `ecm` (`combat.m68:117`, called once per game
frame from `main.m68:175`) destroy every missile in the world. Nothing else
starts an ECM wave: the player's ECM key, and a ship defending itself in
`do_locked` (`logic.m68:694`), both only request the ECM *sound* and rely on
the flag appearing.

In the original the flag belongs to the sound. The PSG effect definition
carries `set_fx flagptr,ecm_on` (`src_orig/asm/sounds.m68:1392`); `init_flagptr`
sets it when the effect starts and the driver clears it when the channel goes
quiet. The wave therefore lasts exactly as long as the sound.

Two consequences follow, and both are bugs:

- **`fx` returns early when Effects are OFF**, before anything is queued. The
  flag is never set, so **ECM does nothing at all with the sound switched
  off** — in the original, in `src_orig` and in `src_atari`.
- **`src_amiga` replaced the PSG driver with a Paula sample player that has no
  `flagptr` mechanism at all.** `ecm_on` is never written anywhere in that
  tree, only read in four places, so ECM never worked on the Amiga under any
  setting: no missile was ever destroyed, the player's ECM key only played a
  sound, the cockpit ECM indicator never lit, and a ship defending itself in
  `do_locked` stalled the missile for one frame and repeated for ever.

The Amiga player also returns early while music is playing, which would have
been a third way to lose the wave.

## 2. The fix

The same treatment `fx` already gives hyperspace. `sfx_hyperspace` sets
`warp_ticks` and `end_hyperspace` *before* the Effects gate precisely so that
the timing survives the sound being off; ECM now does the same.

| Step | Where |
| --- | --- |
| `ecm_wave` = 116 VBL ticks | local constant in each tree's `sounds.m68` |
| `ecm_ticks` counter | Atari: the module's own variable block, next to `warp_ticks`. Amiga: the module's BSS, next to `warp_ticks`. |
| Start the wave: set `ecm_ticks`, `st ecm_on` | `fx`, beside the hyperspace case, ahead of the Effects gate and of the music |
| Tick it down; at zero clear `ecm_on`, `who_ecm`, `f_echar` | `sound`, the VBL entry, beside `warp_ticks` |
| Clear counter and flags | `quiet` |

`ecm_on` now has exactly one owner, so the Atari's `fx_ecm` drops its
`set_fx flagptr,ecm_on` line. Besides removing the double ownership this fixes
a third, smaller bug: an effect that lost its channel to another sound used to
clear the flag and end the wave early.

`do_ecm` keeps its own `clr who_ecm` and `clr f_echar` at the end of the sound.
Those are idempotent and fire at the same moment, so they are left alone.

**116 ticks, 2.32 s at PAL 50 Hz**, is the length of the Atari effect,
obtained by running `do_ecm`'s state machine: the tone sweeps `ecm_min` (100)
to `ecm_max` (200) in `ecm_step` (50) and back, `ecm_dur` (20) times. The dead
constant `ecm_length` that tried to express this arithmetically is replaced.

Precision matters little in play: `ecm` clears every missile on the first game
frame the flag is up. The length only decides how long later missiles keep
being destroyed and, for the player's own ECM, how long his energy drains.

`sounds_vsize` rises from 84 to 85 words in `src_atari/asm/common.def`, because
that module's variable block was exactly full at 168 bytes. The Amiga keeps 84;
its `sounds` block is empty and `ecm_ticks` lives in the module's BSS.

## 3. What changes in play

On the Atari, ECM starts working with Effects OFF, and no longer ends early
when another sound takes the channel. Everything else is as before.

On the Amiga, ECM starts working at all: the player's ECM destroys missiles,
drains energy and lights the cockpit indicator, **and AI ships begin shooting
down the player's missiles** through `do_locked`, which never happened there.
That is a real change in difficulty, not only a repair, and it brings the Amiga
into line with the Atari.

## 4. Out of scope

`shields_fx` and `alert_fx` are the two other `flagptr` flags, and the Amiga
never sets either (`quiet` only clears `alert_fx`). Both are no more than
"this effect is already playing, do not start it again" guards, and the Amiga
driver already refuses to restart a held effect through `effect_ticks`, so the
consequence is cosmetic. Deliberately left alone.

## 5. Testing

Each tree already has a Unicorn harness that assembles its whole `sounds.m68`
and calls `fx`, `sound` and `quiet`: `tests/test_beam_sound.py` on the Atari and
`tests/test_music.py` on the Amiga. Three tests in each:

- the wave starts with Effects ON and with Effects OFF, and on the Amiga also
  while the music holds the channels;
- `ecm_on` stays up for `ecm_wave` ticks of `sound`, then goes down together
  with `who_ecm`, and stays down;
- `quiet` ends the wave.
