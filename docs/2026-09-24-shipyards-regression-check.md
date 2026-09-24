# Shipyards and menu regression check

The review covered the player hull integration and the subsequent changes to the
Equip title toggle, top-row menu rectangles and in-flight Front replacement.
No game source changes were needed during this review. No confirmed gameplay
regression was found in the completed checks.

## Completed checks

| Check | Atari ST | Amiga |
| --- | --- | --- |
| Python regression suite | 34 passed, 1 skipped | 34 passed, 1 skipped |
| Linked 68000 ship scenarios | 93 passed | 132 passed |
| Flight integration scenarios | 14 passed | 14 passed on repeat |
| Top-row pressed feedback | All 8 exact pixel matches | All 8 exact pixel matches |
| Front replacement and pressed feedback | Exact pixel matches | Exact pixel matches |
| Blue title word mouse action | Buy to Sell and back | Buy to Sell and back |
| Standard build and disk validation | Passed | Passed |

Both emulators used 1 MB RAM. Amiga used Kickstart 1.3 with 512 KB Chip RAM and
512 KB expansion RAM. Each emulator ran from private executable, configuration
and disk copies on a verified hidden Windows desktop.

The ship scenarios cover purchases for all hulls, trade-in and equipment resale,
cargo and missile limits, atomic rejection, laser replacement, unique reward
transfer, old save migration, hull save/restore, collision classes, damage and
offer lists. The additional 39 Amiga cases validate native sprite decompression.

The flight integration check creates a departure system for each of the 13
hulls, draws its cockpit and runs eight game frames at the hull's speed and
control limits. It then executes the normal Launch action with an Anaconda.
The independent scenario generators are retained as
`src_atari/tests/native_player_flight.py` and
`src_amiga/tests/native_player_flight.py`.

The two skipped checks compare customized PNGs with the historical, unmodified
artwork. Exact sprite extraction, palette, mask and border checks still ran.
Source inspection also checked the laser mount dialog, save layout, hull-limit
initialization and specialized menu click handlers.

## Test harness findings and limits

The Amiga helper previously placed its allocation bootstrap 32,000 bytes past a
cursor backup pointer without proving that this space belonged to that buffer.
This caused a harness failure before the native scenarios began. The helper now
temporarily uses only the game's known 256-byte default commander block, saves
and verifies its restoration, and allocates its subsequent scratch space through
Exec. The corrected helper completed all 132 ship scenarios and the menu checks.

The first extended flight run subsequently timed out without reporting success.
A repeat with per-scenario progress reporting completed all 14 cases. No game
code was changed between those flight runs. The timeout's cause remains
unconfirmed; the successful repeat is not proof that the earlier observation
cannot recur. Both logs are retained for further diagnosis.

Evidence is under each platform's `build/shipyards-qa`, in `regression-*.log`.
Amiga reports are in its `boot` subdirectory; Atari reports are directly in the
QA directory. The Amiga flight logs are `regression-flight.log` and
`regression-flight-progress.log`.

This check does not establish long-session stability, every mission path,
physical hardware compatibility or runtime correctness of every Amiga display
mode. The earlier normal/alternate builds and PAL hireslace build remain valid,
but the runtime checks here use the standard framed display.

## Follow-up: Shipyards cursor trails

A million-credit commander exposed a missed case in the original review.
The bottom line started at column 4 but printed 37 characters, so its final
character wrapped to row 200 and wrote outside the screen. In the reproduced
Amiga allocation, the other screen began eight bytes later and held the cursor
background. Repeated clicks redrew the overflowing line and then restored the
corrupted background at each cursor position. Four clicks reproduced 136 stray
pixels. The earlier menu checks hid the cursor and used a small cash balance.

The bottom line now displays only the trade-in value, as requested; the cash
field and its label have been removed independently from both platforms.
The longest trade-in prompt occupies 18 of the 36 available character cells.

The independent `tests/native_shipyard_cursor.py` generators exercise actual
VBL click timing and foreground dispatch with all three cursor types, four
empty tile positions, and Equipment/Shipyards menu round trips. They cover the
Cobra and the largest trade-in (Asp), with million-credit and maximum unsigned
cash balances, and change cash after capturing the baseline to verify that it
does not affect the displayed prompt. Each platform passed 30 full-screen
pixel comparisons with no cursor trails on the final implementation, in an
isolated emulator with 1 MB RAM.

Evidence is retained under each platform's `build/shipyards-qa` in
`clicks-trade-only*.log`; the Amiga captures and `clicks-verification.json` are
in `clicks`, while Atari snapshots and the same report are in the QA directory.
