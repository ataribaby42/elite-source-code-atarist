# BBC/C64-style starfield

Both working source trees own a native MC68000 implementation of the BBC/C64 Elite stardust model. There is no 6502 interpreter or platform switch.

The original algorithms are by Ian Bell and David Braben. The implementation was developed using Mark Moxon's annotated sources:

- [BBC Micro STARS1](https://elite.bbcelite.com/cassette/main/subroutine/stars1.html) and [C64 STARS1](https://elite.bbcelite.com/c64/main/subroutine/stars1.html): depth-dependent forward expansion and distant replacement particles.
- [BBC Micro STARS6](https://elite.bbcelite.com/cassette/main/subroutine/stars6.html) and [C64 STARS6](https://elite.bbcelite.com/c64/main/subroutine/stars6.html): rear-view contraction and replacement particles on the viewport borders.
- [BBC Micro STARS2](https://elite.bbcelite.com/cassette/main/subroutine/stars2.html) and [C64 STARS2](https://elite.bbcelite.com/c64/main/subroutine/stars2.html): depth-dependent sideways travel and incoming-edge replacement.

## Motion and recycling

Each of the existing 15 particles per view has signed 16.16 screen offsets and an unsigned 8.8 depth. The four views retain independent particle arrays. Near particles move faster than distant ones.

Normal translation uses the game's speed, bounded to 0..22:

- Forward/rear depth changes by `speed * 64` in 8.8 units. Radial displacement uses the original `q = (64 * speed / depth_high_byte) | 1`, multiplied by the signed integer screen offset. The subpixel remainder is retained.
- Forward particles that leave the viewport or become nearer than depth 16 respawn at a random distant position. The depth byte uses the original `random | 144`; the new position avoids the immediate centre.
- Rear particles that leave the viewport or reach depth 160 respawn on one of the four borders, with depth 10..137.
- Side particles travel by `8 * speed / depth_high_byte` pixels per update. Horizontal departures respawn at the incoming edge: right edge in the left view, left edge in the right view. Vertical departures respawn at the opposite vertical edge. Their depth byte uses the original `random | 8`.
- Retro rockets reverse translation and incoming edges, while steering keeps the signs of the actual view.

All coordinates use the complete 256 x 112 viewport. Every star is always **one pixel**, at every depth. Normal stars retain the existing yellow colour. The original BBC/C64 distance-based point sizes are deliberately omitted at the user's request.

## Adaptation to this game

The BBC/C64 routines are a behavioral basis, not a byte-for-byte reproduction of 6502 arithmetic. Signed 16.16 positions preserve fractional movement without sign-magnitude arithmetic or byte overflow. A stopped ship has no translational drift.

Roll and pitch use the game's own sine/cosine values, converted to Q14. In-plane rotation accumulates subpixel deltas. Vertical rotation uses the 512-pixel object projection scale, including the perspective denominator, so stars follow the scene during steering. The old constant vertical translation and the BBC front-view pitch approximation's horizontal bias are not used.

The view-dependent in-plane/vertical angles are:

| View | In-plane angle | Vertical angle |
| --- | --- | --- |
| Front | Roll | Negative pitch |
| Rear | Negative roll | Pitch |
| Left | Negative pitch | Negative roll |
| Right | Pitch | Roll |

The normal frame draws the current particle positions, then rotates and advances them for the following frame, matching the object's draw/update order. Coordinates are checked after rotation and movement; invalid depths are recycled before division. Coloured jump trails keep their existing repeated drawing, duration and growth. The existing witchspace suppression remains in effect.

The runtime no longer loads `DCOS.DAT` or `DSIN.DAT`, and their former 29,412-byte workspace allocation is removed. The original files under `assets` remain unchanged for reference. Builds omit the files from the disk images and remove stale copies from their generated distribution directory.

## Validation

`tests/test_starfield.py` assembles the actual game routines and runs them with Unicorn 2.1.4. Tests cover the BBC depth/radial laws, sideways parallax, stopped motion, incoming edges, rear recycling, retro rockets, steering against a geometric projection reference, subpixel movement, and one-pixel drawing at every depth.

The complete cloud is exercised over hundreds of frames on MC68000 and MC68020 CPU models with executable memory write-protected. Guarded buffers check that no drawing reaches the cockpit. These are CPU-level checks; they do not establish emulator gameplay quality or a frame-rate measurement.

