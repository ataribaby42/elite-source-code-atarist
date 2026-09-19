# BBC/C64-style starfield

Both working source trees own a native MC68000 implementation of the BBC/C64 Elite stardust model. There is no 6502 interpreter or platform switch.

The original algorithms are by Ian Bell and David Braben. The implementation was developed using Mark Moxon's annotated sources:

- [BBC Micro STARS1](https://elite.bbcelite.com/cassette/main/subroutine/stars1.html) and [C64 STARS1](https://elite.bbcelite.com/c64/main/subroutine/stars1.html): depth-dependent forward expansion and distant replacement particles.
- [BBC Micro STARS6](https://elite.bbcelite.com/cassette/main/subroutine/stars6.html) and [C64 STARS6](https://elite.bbcelite.com/c64/main/subroutine/stars6.html): rear-view contraction and replacement particles on the viewport borders.
- [BBC Micro STARS2](https://elite.bbcelite.com/cassette/main/subroutine/stars2.html) and [C64 STARS2](https://elite.bbcelite.com/c64/main/subroutine/stars2.html): depth-dependent sideways travel and incoming-edge replacement.

## Motion and recycling

Each of the existing 15 particles per view has signed 16.16 screen offsets and an unsigned 8.8 depth. The four views retain independent particle arrays. Near particles move faster than distant ones.

Normal translation maps the game's speed, bounded to 0..22, linearly to a visual speed of 1..33 in all four views. Zero throttle retains a slow drift, restoring the original ST starfield's nonzero-minimum behavior within the depth-dependent BBC/C64 model. Full throttle advances depth and sideways travel at 150% of the previous maximum rate. The increase is spread over the whole throttle range; there is no special boost at full throttle.

The shared depth step is `64 + floor(speed * 2048 / 22)`, ranging from 64 to 2112 in 8.8 units. Fractional visual speed is retained instead of rounding to whole speed units. This changes only starfield translation; ship speed, steering and object movement are unchanged.

- Forward/rear depth changes by the shared step. Radial displacement uses the original `q = (step / depth_high_byte) | 1`, multiplied by the signed integer screen offset. The subpixel remainder and the BBC odd-quotient rounding are retained.
- Forward particles that leave the viewport or become nearer than depth 16 respawn at a random distant position. The depth byte uses the original `random | 144`; the new position avoids the immediate centre.
- Rear particles that reach depth 160 respawn on one of the four borders, with depth 10..137. Particles that leave through the top or bottom instead wrap to the opposite vertical edge, retaining their complete 16.16 overshoot and receiving a random horizontal position and a new rear-view depth. Sending these pitch-driven departures to random side edges accumulated stars into vertical columns during steady climbing or diving. Horizontal-only departures still use the four-border replacement.
- Side particles travel by `step / (8 * depth_high_byte)` pixels per update, retaining 1/256-pixel precision. Horizontal departures respawn at the incoming edge: right edge in the left view, left edge in the right view. Vertical departures wrap to the opposite edge while retaining the complete 16.16 boundary overshoot; horizontal position and depth are randomized. Preserving the distance travelled past the edge prevents steady roll from synchronizing replacement stars into horizontal rows. Their depth byte uses the original `random | 8`.
- Retro rockets reverse translation and incoming edges, while steering keeps the signs of the actual view.
- Coloured torus/hyperspace trails retain their separate depth step of 128 and their existing repeated drawing, duration and growth.

All coordinates use the complete 256 x 112 viewport. Every star is always **one pixel**, at every depth. Normal particles use the existing dark grey palette colour, also used by the hyperspace tunnel. Coloured jump trails retain their existing colours. The original BBC/C64 distance-based point sizes are deliberately omitted at the user's request.

## Adaptation to this game

The BBC/C64 routines are a behavioral basis, not a byte-for-byte reproduction of 6502 arithmetic. Signed 16.16 positions preserve fractional movement without sign-magnitude arithmetic or byte overflow. The minimum visual drift does not change the ship's physical minimum speed of zero.

Roll and pitch use the game's own sine/cosine values, converted to Q14. In-plane rotation accumulates subpixel deltas. Vertical rotation uses the 512-pixel object projection scale, including the perspective denominator, so stars follow the scene during steering. The old constant vertical translation and the BBC front-view pitch approximation's horizontal bias are not used.

Resetting the system refreshes both cached sine/cosine pairs after clearing the control angles. In particular, zero pitch needs a cosine of one before the first control input. Leaving the startup cosine at zero collapsed the side-view particles towards the centre immediately after launch; stale values from the title scene could also cause unintended rotation.

Locking the controls for torus travel, hyperspace or an escape capsule also refreshes both cached sine/cosine pairs and the control indicators. This prevents residual starfield rotation during a jump and after returning to normal flight. The lock routine preserves all general-purpose registers.

The view-dependent in-plane/vertical angles are:

| View | In-plane angle | Vertical angle |
| --- | --- | --- |
| Front | Roll | Negative pitch |
| Rear | Negative roll | Pitch |
| Left | Negative pitch | Negative roll |
| Right | Pitch | Roll |

The flight frame draws the distant white sky first, then the planet and sun, then the moving starfield, followed by all other 3D objects, laser beams, the laser sight and viewport messages. Stars therefore overlay the planet and sun, while ships, stations, other objects and the UI can cover them. Each object layer retains its existing depth order. The unfiltered renderer used by hangars and other scenes is unchanged. The starfield draws the current particle positions, then rotates and advances them for the following frame. Coordinates are checked after rotation and movement; invalid depths are recycled before division. Coloured jump trails keep their existing repeated drawing, duration and growth. The existing witchspace suppression remains in effect.

The runtime no longer loads `DCOS.DAT` or `DSIN.DAT`, and their former 29,412-byte workspace allocation is removed. The original files under `assets` remain unchanged for reference. Builds omit the files from the disk images and remove stale copies from their generated distribution directory.

## Distant white sky

Game Options includes **Stars: ON/OFF**, enabled by default. OFF hides the distant white stars and restores the moving starfield to yellow; ON uses dark grey moving particles against the white sky. Coloured warp trails are unchanged. OFF returns before sky rendering, projection, cache maintenance or orientation updates. Switching back ON resets the orientation and invalidates the pixel cache; clicking ON while already enabled preserves the current sky. The preference is saved in bit 6 of the existing user-options byte (commander offset 10 / $0A): zero means ON, one means OFF. Startup and default Jameson keep ON, including `commander=max`. Older saves leave this previously unused bit clear and therefore load with ON. `restore_state` calls `restore_sky` to update the renderer cache after loading or selecting a default commander. `set_sky_enabled` keeps the saved flag and renderer cache synchronized. The save remains 256 bytes, including the unchanged registration extension, and is portable between Atari and Amiga.

A separate background contains 1,024 fixed star directions, each drawn as one white pixel. These stars respond only to ship rotation, not forward speed, retro rockets or torus translation. All four views share the same orientation and catalogue, so returning to a direction restores the same constellation. The existing moving dark grey dust is unchanged.

The white sky is the first flight layer. Planets, the sun, dark grey dust, ships, stations, lasers, the sight and messages can all cover it. Hangar/title rendering is unchanged, and witchspace retains its existing absence of stars.

`tools/make_sky.py` reproducibly generates `asm/sky.dat` from a private fixed seed. It does not consume the game's random sequence. The catalogue and its conservative binary cone tree occupy 12,276 bytes; the renderer reserves 512 bytes of workspace and uses no world-object slots. Each rejected tree node skips its entire subtree. Accepted leaves contain four stars; only visible points reach perspective division and the pixel cache. There is no floating-point arithmetic, allocation, self-modifying code or runtime trigonometry generation.

The celestial-to-ship matrix retains Q24 fractional components and follows the game's roll-then-pitch order once per flight simulation frame, including frames showing flight menus. Periodic normalisation bounds long-session scale drift. A Q14 matrix is derived for the selected view. When neither orientation nor view changes, the renderer simply replots cached coordinates. A bounded 64-pixel cache provides headroom above the intended sparse density.

## Validation

The former CPU-emulation test suite has been removed. Build and file-format
checks remain available through the normal build and `tests/` discovery.
Gameplay validation requires WinUAE or original hardware.

Check all four views, sustained roll and pitch, zero and full throttle, rear-view recycling, cockpit clipping and object occlusion. Toggle the white sky and verify that its setting survives commander save/load.

