# Station clipping and ship screen fixes

Date: 2026-09-24

The independent Amiga and Atari versions contain the same four fixes.

## Station collision and death

The supplied `deathbug.uss` contains a Moray death animation after energy depletion. One screen buffer already has extensive damage outside the flight viewport, while the other retains the cockpit. Alternating those buffers explains the reported white flashing. The snapshot does not contain the preceding collision frames, so it cannot identify the original invalid write by itself.

A separate native reproduction found an overflow in the four viewport intersection routines. Projected coordinates are signed 16-bit values, but their differences can reach 65535. The old signed-word subtraction and division could produce an intersection outside the viewport. The polygon filler then overran its edge workspace. A nearby rotated Coriolis reproduced the failure at position `(0, -200, 200)`, after fourteen successive rotations of 71 about Z and 37 about X with orthogonalization. The exception capture showed overwritten polygon arm pointers.

`clip_interpolate` now subtracts sign-extended coordinates in 32 bits, multiplies unsigned distance magnitudes and divides by the unsigned axis span. A crossing lies between the endpoints, so the product fits 32 bits and the quotient fits 16 bits. The sign is reapplied before adding the first coordinate. A zero axis span bypasses division. All four intersection routines use this helper, independently in each source tree.

This fix addresses the reproduced memory corruption; the exact pre-snapshot sequence remains unavailable. No collision balance, death animation timing or shadow-transfer behavior was changed.

The snapshot uses a 68000, 512 KB Chip RAM plus 512 KB Slow RAM, and the framed 256 by 112 viewport. It cannot use the Amiga Fast RAM shadow path, which requires a full-width viewport, a 68020 or later, and Fast RAM. Therefore `shadowcopy=changes` was not active in this report.

## Ship screens

- After a successful purchase, clear the bottom input line after rebuilding Shipyards and before printing the confirmation. This prevents the confirmation from being printed over Trade-in.
- Center the 128-pixel ship atlas in the 208-pixel laser placement panel: its X position changes from 102 to 94 in both Buy and Sell modes.
- Move the Planet Data ship from Y=53 to Y=52. Draw it after the grey distance line and arrow, allowing its opaque pixels to cover the line.

## Verification

All emulator diagnostics used private executable, configuration and disk copies on verified hidden Windows desktops. The Amiga tests used a 68000 with 512 KB Chip and 512 KB Slow RAM; Atari tests used a 68000 ST with 1 MB RAM.

- `tests/native_station_clipping.py` in each platform tree: 192 exact intersection checks, including extreme signed coordinates, plus 1152 nearby Coriolis poses. Every render checked guard patterns in both cockpit margins across all four bitplanes. All 1344 cases passed on each platform.
- `tests/native_station_death.py`: repeated real station collisions outside the docking opening drain the Moray's shields and energy, assert the energy-depletion death reason, then execute the complete death animation. Front and rear view cases check both screen buffers and completion of the exploding object. Both cases passed on both platforms. The fixture uses the game's `max_shield` constant; an earlier diagnostic fixture accidentally exceeded that limit and was corrected.
- `tests/native_shipyard_visuals.py`: real purchase confirmation, Buy/Sell laser dialogs and Planet Data pages. Each platform passed 37 exact sprite comparisons: 13 planet images and two dialogs for each of the 12 ships with laser mounts. The purchase confirmation was also visually checked.
- Normal and ALT graphics distributions built successfully for both platforms. Runtime checks above used normal graphics; ALT variants received build validation.

Native captures, reports, payload listings and private emulator launch helpers are under each platform's `build/deathbug-qa` directory. The original supplied snapshot was read without modification. A save-state embeds its original executable, so testing the fix requires booting the rebuilt disk rather than resuming that old state.
