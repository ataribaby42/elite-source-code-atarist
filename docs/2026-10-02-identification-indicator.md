# Identification and missile targeting indicators

The enhanced Atari and Amiga builds show a hollow light-green square at the
centre of the flight sight while an `I` identification request is pending.
While a missile is armed but has no locked target (`missile_state = 1`), the
same outline is light grey. A pending identification request takes priority
and makes it light green, even while a missile is armed or locked. Once
identification ends, the square returns to grey if the missile is still waiting
for a target; otherwise it disappears. Locking a target removes the grey square.
`U` cancels the request and unarms any armed or locked missile. Cancelling only
identification does not display the "missile not targeted" error. Missile
inventory is unchanged.

The square is five logical pixels wide and high, with a one-pixel outline and a
transparent centre. Its centre is offset one logical pixel upward from the
viewport centre to align with the laser sight. It is available in all four views, including views without
a fitted laser. Amiga display scaling and the framed/frameless viewport geometry
determine its physical size and position.

Each platform implements the indicator in its own `asm/cockpit.m68`, using the
existing `id_trigger` and `missile_state` states. The chosen colour is kept on
the stack across the four edge draws because `block` clobbers its colour
register. Only the `U` dispatch in `asm/action.m68` calls the
new `cancel_targeting` wrapper. Automatic missile resets retain their existing
`unarm_missile` entry point and do not cancel identification. The request's
existing identification and reset paths remain in use; no new saved state is
needed.

## Verification

Each platform's `tests/native_id_indicator.py` runs 49 native checks: actual
`I`/`U` key dispatch with all three missile states, plus actual `T` arming;
inventory preservation;
automatic missile reset; successful identification with and without a laser;
and pixel comparisons for four views, five laser configurations and both screen
buffers. The comparisons require precisely the light-grey or light-green
outline, including green priority while armed or locked, returning to grey
after identification clears while armed, and removal after locking or `U`.
They preserve the surrounding and interior pixels and restore the original
sight. Both indicators also work without a fitted laser.

The Amiga test explicitly drains the viewport clear before drawing the sight,
matching the normal `draw_space` call that precedes it in a game frame. Without
that synchronization, a direct test call can race the asynchronous clear and
produce an invalid baseline for the existing laser bitmap.

On 2 October 2026, 647 native scenarios passed on each platform, covering the
49 identification checks plus missile indicators (148), shared AI systems
(257), encounter and mission spawns (83), shield flashes (66), missile impacts
(22), missile collisions (8), and player flight limits (14). The framed PAL
Amiga identification, shield-flash and missile-impact checks used cycle-exact
68000 timing. The remaining Amiga suites also passed; the extended timing run
covered missile collisions and flight limits.

The identification suite additionally passed all 49 cases on each of the
frameless PAL and frameless NTSC hires-interlace Amiga builds. Each platform's
ordinary test suite passed 34 tests, with one existing artwork identity test
skipped. Native emulator runs used verified, separate hidden Windows desktops
and private executable, configuration and disk copies under the relevant
source tree's `build` directory.

All 20 distribution builds passed: two Atari artwork variants and eighteen
Amiga artwork/display combinations. The final standard ST and ADF disk images
match the copies used by the final native runs. Reports and hashes are retained
in each source tree's `build/id-indicator-qa/summary.json`.

## Missile targeting square update, 3 October 2026

The light-grey pending-lock square and green identification priority passed
all 49 expanded native indicator scenarios on each platform. The existing
148 missile inventory/display scenarios also passed, for 197 scenarios per
platform. Amiga indicator checks used cycle-exact 68000 emulation. Tests ran
on verified hidden desktops with private emulator and disk copies; both
selected distribution builds succeeded and their disk images match the tested
copies. Reports and build logs are in each tree's `build/missile-sight-qa`.
