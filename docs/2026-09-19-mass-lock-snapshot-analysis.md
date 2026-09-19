# Mass-lock diagnosis from a WinUAE snapshot

The supplied `mass-lock-bug.uss` was examined as a memory dump, without restoring
it in WinUAE or executing any emulated instructions. No gameplay code was changed.
Decoded chunks, assembler-derived structure offsets and `analysis.json` are in
`src_amiga/build/mass-lock-qa`.

## Finding

An abandoned Anaconda remains in object slot 5 and keeps `trader_count` at 1.
The torus admission check uses the global trader/pirate/Thargoid counts, without
checking distance or whether a ship has been abandoned. This object is outside
scanner range but still blocks the torus drive.

| Snapshot field | Value |
| --- | --- |
| Game variable base (A6) | `$00C38116` |
| Anaconda record | `$00C387B0`, slot 5 (zero-based) |
| Registration | `MG-038` |
| Type / category | 16 (Anaconda) / 0 (trader) |
| Flags byte | `$01`: in use, not pending removal |
| Position | X = 67,171; Y = 41,875; Z = −19,902 |
| Stored range | 81,604 world units |
| Current scanner scale | 24,576 world units |
| Logic | 0 (`log_none`) |
| Attack response / missiles | 0 (`act_nothing`) / 0 |
| Health | 9 of 112 |
| Speed | 10 |
| Trader / pirate / Thargoid counts | 1 / 0 / 0 |

The active-object scan agrees with those counters; this is an actual remaining
object, not an orphaned counter. The planet is 239,248 units away (torus threshold
155,648), and the sun is 565,696 units away (threshold 131,072). Neither causes
this lock. Player speed is the required maximum, 22; the player is neither docked
nor in witchspace.

An active Worm escape capsule also exists in slot 6, at range 12,215 with
`log_cruise`. Its category is shuttle, so it does not contribute to this mass-lock
check. Its presence is consistent with an escape, but the snapshot alone does
not prove which ship launched it or whether the player or another ship caused
the Anaconda's damage.

## Code path

1. `asm/combat.m68`, `launch_escape`, sets the abandoned mothership's logic to
   `log_none`, its attack response to `act_nothing`, and its missile count to zero.
   It leaves the mothership in use and classified as a trader.
2. `asm/logic.m68`, `logic_vectors`, maps `log_none` directly to `return`.
   Ordinary `do_cruising` ships are marked for removal beyond `radar_range`;
   the abandoned hull no longer runs that routine.
3. `asm/main.m68`, `remove_object`, decrements the category counter when the
   object is actually removed. The distant hull has not been marked for removal.
4. `asm/flight.m68`, `torus`, rejects activation as soon as any trader, pirate
   or Thargoid count is nonzero, before checking planet/sun proximity.
5. `asm/radar.m68` rejects a blip when any coordinate exceeds `radar_scale`.
   This Anaconda exceeds that limit in both X and Y, explaining its absence.

These observations identify the lock condition conclusively. The combination of
inert logic, disabled attack response and low health identifies the abandonment
path; the precise earlier encounter history cannot be recovered from one frame.

## Validation of the dump interpretation

The snapshot contains 512 KB CRAM and 512 KB BRAM. Chunk lengths, padding and
zlib payloads were read according to the upstream
[WinUAE save-state implementation](https://github.com/tonioni/WinUAE/blob/master/savestate.cpp).
BRAM was mapped at `$00C00000`; A6 was read from the CPU chunk. Structure offsets
were emitted by the bundled assembler using the build's alignment settings.

The actual snapshot instructions at `$00C10982` read trader offset `$02CC`, pirate
offset `$02CA`, and Thargoid-count offset `$1A5D`, then branch around the mass-lock
message only when their OR is zero. The scanner instruction at `$00C18788`
compares against A6 offset `$3BBE`, whose saved value is 24,576. These checks
validate the decisive offsets against snapshot machine code rather than relying
only on a current linker map.

This diagnostic preceded the gameplay change. The subsequent
[abandoned-hull cleanup fix](2026-09-19-abandoned-hull-mass-lock-fix.md) removes
distant abandoned hulls in both enhanced versions while preserving nearby
hulls and ordinary encounters.
