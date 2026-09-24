# Viewport rendering bounds

Date: 2026-09-24

This follows the station collision investigation in `2026-09-24-death-and-ship-screen-fixes.md`. The audit covers the independent Amiga and Atari renderers, including ship meshes, debris, missiles, hangar panels and the animated title letters. It also covers clipped lines and flight messages.

## Findings and changes

The previous polygon intersection correction already applies to every model through `draw_panel` and `c_solid_polygon`. It is not a station-specific workaround.

`c_line` still contained four independent copies of the old signed-word intersection arithmetic. Differences between signed screen coordinates can exceed 32767. The native baseline failed the exact line comparison for `(56, 16000)` to `(-1, -32767)`. Each clipping branch now calls the corresponding overflow-safe polygon intersection routine. Those routines retain the full coordinate differences and avoid division by a zero axis span.

`disp_message` previously copied an unbounded string into a 128-byte buffer and centered it without checking the viewport width. A string wider than the view could produce a large positive offset from the unsigned shift of a negative value. It now copies at most `no_cols` characters, terminates the buffer, and centers that bounded result. Control bytes below ASCII space become spaces, so a flight message cannot invoke cursor movement. Formatted text on the other UI screens continues to use its existing separate path.

The polygon clipping lists held only 15 vertices. A rotated and scaled version of the actual 12-vertex Letter I face produces 16 vertices after all four clipping passes. A native regression reproduced the overwrite of the variables after the second list. Both lists now hold 16 vertices. `add_vertex` also checks the end of the selected list before writing. If a future or malformed face exceeds that capacity, `c_solid_polygon` discards the incomplete polygon after restoring its saved registers. It cannot overwrite the next workspace. The graphics variables occupy 560 bytes inside the existing 600-byte allocation; the change does not enlarge the allocated module workspace.

The audit also checked the callers of the unclipped raster primitives. Model faces route through clipping when their outcodes require it. The laser wedges and energy-bomb lines generate coordinates inside the view. Stars, dust and explosion dots use the clipped pixel path. The raw raster routines retain their existing requirement that callers supply valid screen coordinates.

## Native verification

Every GUI emulator ran with private executable, disk and configuration copies on a verified, separate hidden Windows desktop. The user's emulator and supplied save-state were not modified.

The line tests compare the complete rendered screen with a reference using Python integer clipping and the native raw line raster. The text tests cover empty strings, the row-width boundaries, 127- and 255-character inputs, control bytes, and the first and last text rows. The model tests fill all pixels outside the viewport with a guard pattern and check it after every draw. All 43 object types are exercised at four rotations and 18 near-camera or off-screen positions, for 3096 cases per full run.

| Platform and mode | Line/text cases | Model poses | Result |
| --- | ---: | ---: | --- |
| Atari ST, framed, 68000, 1 MB | 208 | 3096 | Passed |
| Amiga framed, 68000, 512 KB Chip + 512 KB Slow | 208 | 3096 | Passed before the additional vertex-list guard |
| Amiga PAL WIDE, 320 x 176 view | 216 | 3096 | Passed |
| Amiga PAL HIRES, 640 x 176 view | 216 | 3096 | Passed |
| Amiga PAL HIRES-LACED, 640 x 352 view | 216 | 3096 | Passed |
| Amiga NTSC WIDE, 320 x 120 view | 216 | 3096 | Passed |
| Amiga NTSC HIRES, 640 x 120 view | 216 | 3096 | Passed |
| Amiga NTSC HIRES-LACED, 640 x 240 view | 216 | 3096 | Passed |

The six full-width runs use the final source, a 68020, 2 MB Chip RAM and 4 MB Fast RAM, with direct rendering. Their extra line cases explicitly include adjacent physical rows at the upper and lower edges, testing both interlaced field parities. These are functional bounds tests, not timing or minimum-memory measurements for the expanded modes.

The Letter I reproduction and deliberate attempt to append one vertex beyond the list both pass on the final Amiga and Atari builds with 1 MB RAM. The tests are in each platform's `tests/native_polygon_capacity.py`. The other native suite generators are `native_viewport_bounds.py` and `native_all_models_bounds.py`.

The final framed Amiga build also passed a further 344 guarded renders on the 68000 with 512 KB Chip and 512 KB Slow RAM: all 43 models, four rotations and two close-camera positions. This run includes the new vertex-list guard. The final Atari full 3096-pose run includes that guard as well.

## Shadow transfer

`native_shadow_viewport.py` compares every byte of a presented frame against direct rendering of the same scene into a separate reference buffer. The Fast RAM shadow is verified active. Reference rendering preserves the real buffers and their mirrors, allowing successive shadow frames to exercise the ordinary changed-block path rather than forcing a full refresh each time.

All 312 frame comparisons passed separately in PAL WIDE, PAL HIRES, PAL HIRES-LACED and NTSC HIRES-LACED with `fastdraw=yes shadowcopy=changes`. Each run covers 210 line frames, including repeated and empty frames, 16 text frames, and two poses of all 43 models. The complete-screen comparison also verifies the untouched area below the viewport. No shadow-transfer changes were needed.

The original death snapshot has a framed viewport on a 68000 with no Fast RAM shadow. The original corruption and the newly reproduced line and vertex-list faults therefore do not require `shadowcopy=changes` to occur. The exact frames preceding the supplied snapshot remain unavailable; this audit does not claim to replay that precise sequence.

## Build outputs and evidence

All fourteen Amiga NORMAL/ALT distributions were rebuilt: framed plus PAL/NTSC WIDE, HIRES and HIRES-LACED. Both Atari NORMAL/ALT distributions were rebuilt. Runtime checks use normal graphics; ALT variants received build validation.

Native payloads, listings, reference captures, emulator logs and reports are under each source tree's `build/viewport-qa`. Amiga mode reports are in `final-*/viewport`, `final-*/models` and `shadow-*/shadow`. Early harness failures, such as a debugger pipe not opening, remain in the diagnostic history; their successful retries have separate completed report files. Source comparisons were made against local pre-change copies without using Git.
