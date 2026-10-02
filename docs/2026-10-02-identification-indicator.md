# Pending identification indicator

The enhanced Atari and Amiga builds show a hollow light-green square at the
centre of the flight sight while an `I` identification request is pending.
Successful identification consumes the request and removes the square. `U`
cancels the request and unarms any armed or locked missile. Cancelling only
identification does not display the "missile not targeted" error. Missile
inventory is unchanged.

The square is five logical pixels wide and high, with a one-pixel outline and a
transparent centre. Its centre is offset one logical pixel upward from the
viewport centre to align with the laser sight. It is available in all four views, including views without
a fitted laser. Amiga display scaling and the framed/frameless viewport geometry
determine its physical size and position.

Each platform implements the indicator in its own `asm/cockpit.m68`, using the
existing `id_trigger` state. Only the `U` dispatch in `asm/action.m68` calls the
new `cancel_targeting` wrapper. Automatic missile resets retain their existing
`unarm_missile` entry point and do not cancel identification. The request's
existing identification and reset paths remain in use; no new saved state is
needed.

## Verification

Each platform's `tests/native_id_indicator.py` runs 49 native checks: actual
`I`/`U` key dispatch with all three missile states; inventory preservation;
automatic missile reset; successful identification with and without a laser;
and pixel comparisons for four views, five laser configurations and both screen
buffers. The comparisons require precisely the green outline, preserve the
surrounding and interior pixels, and verify that `U` restores the original sight.

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
