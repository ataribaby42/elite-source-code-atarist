# Wide and multi-mode support

Date: 2026-09-20
Status: implemented in `src_amiga`

## Screens

`display=` selects the screen and `frame=` the cockpit. The row count follows the refresh rate, `hires` doubles the pixels across and `hireslace` doubles them down as well. Artwork, assets and gameplay are the same in every combination.

| `display=` | screen | view, `frame=no` | view, `frame=yes` | CPU |
| --- | --- | --- | --- | --- |
| `pal` | 320 x 256, or 320 x 200 framed | 320 x 168 | 256 x 112 | MC68000 |
| `ntsc` | 320 x 200 | 320 x 112 | 256 x 112 | MC68000 |
| `pal-hires` | 640 x 256, or 640 x 200 framed | 640 x 168 | 512 x 112 | MC68020 |
| `pal-hireslace` | 640 x 512, or 640 x 400 framed | 640 x 336 | 512 x 224 | MC68020 |
| `ntsc-hires` | 640 x 200 | 640 x 112 | 512 x 112 | MC68020 |
| `ntsc-hireslace` | 640 x 400 | 640 x 224 | 512 x 224 | MC68020 |

`frame=yes` is the default and builds the original game. `hires` and `hireslace` are accepted as the PAL spellings, and an interlaced screen needs a flicker fixer or a multisync monitor.

Every coordinate in the game is authored on a logical 320 x 200 grid. `zoom_x` and `zoom_y` in `asm/geometry.def` carry that grid to the physical screen, so a mode is a set of constants rather than a code path: one build of one source tree covers all six.

## The cockpit frame

`COCKPIT.PC1` draws hand-pixelled pillars down both sides of the view, from row 8 to row 119. They are drawn once at that height and no band of them repeats, so a taller view needs either new artwork or no frame.

`frame=no` takes the second way. `place_panel` in `asm/cockpit.m68` moves the bottom `panel_rows` of the decoded picture to the foot of the screen and clears everything above, so the view spans the full width and the pillars are cropped. Row 120 is the first row of panel content, measured on the asset, so `panel_rows: equ 80*zoom_y` loses nothing. The view name is printed in the game font into the strip above the view, which `clear_image` never touches.

`frame=yes` keeps the whole picture. The screen is then as tall as the artwork, `scr_rows: equ art_rows*zoom_y`, and the viewport is the window the frame leaves:

```
no_cols: equ 32     ; columns across the window
no_rows: equ 14     ; rows down it
```

`x_size`, `y_size`, `x_min` to `y_max`, `x_left`, `no_dust` and `arm_entries` follow from the formulas in `geometry.def`, so a framed build lands on the original 256 x 112 window at `x_left = 32` with 15 dust particles. `y_shift` and `panel_shift` are `scr_rows-art_rows*zoom_y`, which is zero at the artwork's height, so every instrument and scanner coordinate sits where the artwork puts it, and `diwstop_rows` equals `diwstop_art`. Two pieces read the flag directly: `tunnel_scale` is 1, and the view name is the artwork's own tile from `bit_views`.

## Geometry

`asm/geometry.def` holds the display geometry; no module contains a literal stride or plane offset. `bpr`, `scr_planes`, `scr_width`, `row_stride`, `plane1` to `plane3`, `scr_rows`, `scr_bytes`, `art_rows`, `art_bytes`, `panel_rows`, `y_shift`, `panel_shift`, `char_w`, `char_h` and the Copper values all derive from the three display flags. `raster.inc` takes the plane offsets from the symbols and `native_clear_span` generates the viewport clear for any width.

Derived alongside the viewport:

- `no_dust` scales with the viewport area counted in logical pixels, so the moving starfield keeps its density of 15 stars in a 256 x 112 view and a sharper screen does not add particles.
- `left_arm` and `right_arm` hold one x coordinate per clipped polygon row and are sized by `arm_entries`.
- `action_vsize` covers the scroll buffer, which is sized by `no_cols`.
- `proj_shift_x` and `proj_shift_y` carry the projection per axis, because a hires screen doubles horizontally while a progressive one keeps its row count.
- `circle_stretch` widens circles where a pixel is half as wide as it is tall, so planets and suns stay round on a non-interlaced hires screen.
- `dither_bit` holds each dither phase for two rows on an interlaced screen, so both fields see the alternation instead of one comb of each.
- `sky.dat` is generated from the widest viewport, so its cone cull stays conservative for a shorter one.

`sky_project_star` culls a star before its divide by multiplying the depth by `x_max+2` and `y_max+2` and shifting by 9. That is exact for any viewport: the negative edge is the wider one and DIVS truncates toward zero. It costs two 16-bit multiplies per candidate star.

## Artwork and sprites

Assets are authored at 320 x 200 and expanded to the display when they load.

`draw_screen` in `asm/graphics.m68` widens a DEGAS screen while it decodes it: one source byte becomes a word through a 256-entry table, so 40 source bytes make exactly 80 and the plane boundaries fall out on their own. An interlaced build then runs `double_rows`, which lays every decoded row down twice, working backwards because source and destination overlap.

`read_bitmaps` in `asm/init.m68` widens the sprite bank as it reads it, emitting two columns of mask and four planes for each source column, and duplicating rows for an interlaced screen. The rotation loops in `sprite_rows.inc` work on the widened data unchanged, so no instruction is patched at run time. The expanded bank is 140,750 bytes on a 320-wide screen and 560,000 interlaced, past the 262,144-byte Kickstart 1.x hunk clearing limit, so `bitmap_bank` is allocated at startup and freed at exit. `build.py` measures the asset against `bitmap_bytes` and refuses a bank that would not fit.

Text follows the same split: `display_char` keeps its byte logic and widens the finished result through the same table, so ink and paper masks stay byte-sized.

## Scenery built for the old window

The docking bay and the hangar were modelled to fill the original 256 x 112 window exactly, so a wider view sees past their walls. `geometry.def` names the two ratios once, `view_num_x` over `view_den_x` and the vertical pair, and the cross sections scale with them:

- `tunnel_x` and `tunnel_y` size the bay walls, doors and pulsing rings. `tunnel_scale` doubles them for a frameless view, so the mouth passes the frame edges at z = 800 instead of z = 400.
- `hangar_x`, `hangar_top` and `hangar_bottom` size the hangar and the bay end wall, and `hangar_ship_x` and `hangar_ship_y` place the parked ships. The walls end 1600 units ahead of the viewer, where the modelled 400 and 175 project exactly onto the edges of the original window; the scaled values project onto the edges of whatever view is in use, rounded up so the edge is covered.

## Display window

Artwork screens are 200 logical rows. Rather than move every text and icon coordinate, the Copper display window follows the screen in use: `amiga_rows_full` for the flight view, `amiga_rows_art` for the title, charts, market, status and planet data. `DIWSTOP` is the only register involved, and the two values are equal on NTSC and in a framed build, where the call is a no-op.

## Chip RAM

The two screens are `scr_bytes` each, from 32,000 bytes in a framed 320-wide build to 163,840 in PAL interlaced hires. Each screen is its own BSS hunk, so each stays below the 262,144-byte Kickstart 1.x clearing limit; `build.py` checks that the two are equal. The sprite bank is allocated rather than linked, as above.

## Validation

`python -B -m unittest discover -s src_amiga/tests` passes in every display mode and with the frame either way. The tests read the geometry from the assembled constants rather than from literals, so one suite covers every layout.

`build.py` checks what the geometry cannot: the two screens are equal, each asset fits the workspace buffer it loads into, the expanded sprite bank fits `bitmap_bytes`, and the disk image reads back byte for byte. Runtime behaviour on hardware is not covered.
