# Amiga ship atlases

This document records the original three indexed, 4-bit PNG atlases and their
camera conventions. They were superseded on September 24 by
[runtime ship images](2026-09-24-runtime-ship-images.md) in both enhanced games.
The original PNGs and extraction metadata are archived in
[`resources/gfx_assets`](../resources/gfx_assets). They are no longer present in
the source graphics folders or required by builds. The dimensions and views
below remain the reference for the native renderer.

| Atlas | PNG size | Game image, excluding border | Cell pitch, including border | View |
| --- | --- | --- | --- | --- |
| `ships.png` | 520 x 212 | 128 x 51 | 130 x 53 | Rear and above, matching the Cobra orientation in `panels.png` |
| `shipsplanetinfo.png` | 136 x 188 | 32 x 45 | 34 x 47 | Top, nose right, matching the Cobra orientation in `gadgets.png` |
| `shipyards.png` | 264 x 172 | 64 x 41 | 66 x 43 | Top, nose up |

The game-image sizes are the actual extraction rectangles in `gfx/layout.json`:
`bit_cobra` (ID 54), `bit_small_cobra` (ID 95) and `bit_equipment[0]` (ID 32).
The equipment image is **64 x 41**, not its original sheet's 112 x 48 grid cell.
Each image has a separate one-pixel external frame in UI index 6 (`#FF0000`).
The frame is excluded from the game-image rectangle. Adjacent frames therefore
make a two-pixel separator.

Each atlas uses four columns and four rows. Read left to right, top to bottom:

1. Sidewinder
2. Adder
3. Krait
4. Gecko
5. Moray
6. Mamba
7. Cobra Mk I
8. Cobra Mk III
9. Fer-de-Lance
10. Python
11. Boa
12. Anaconda
13. Asp Mk II

The last three cells are empty. All artwork is centered and scaled uniformly
per ship and per view to fit its rectangle, including modeled guns. Physical
size differences between ships are intentionally not retained.

The archived [`ship-atlases.json`](../resources/gfx_assets/ship-atlases.json)
records the order, palette, dimensions, reference bitmap IDs and exact
border-free `[x, y, width, height]` rectangles used for extraction.
For zero-based ship index `i`, the image begins at
`x = (i % 4) * cell_width + 1`, `y = (i // 4) * cell_height + 1`.

## Rendering and palette

The original PNG renderer read the actual Amiga ship vertices, surface normals,
polygons, details and first material variant from `asm/objects.dat`. It decoded the
two-row, four-plane material patterns in `asm/vector.m68`'s `panel_colours`
table. The aft view uses an orthographic camera 45 degrees above the ship,
without yaw or roll; the other two views are directly overhead.

Panels use the original flat colours and pixel dithering, without antialiasing
or added black outlines. Model lines, windows, engine panels and shaded areas
are retained. The exact UI PNG RGB palette from the
[editable PNG guide](2026-09-19-editable-png-graphics.md) is embedded in all
three files, with PNG indices matching game indices.

- Index 0 is the cyan editing background and becomes transparent on extraction.
- Zero bits inside opaque dithered panels become opaque black, index 13.
- The dynamic engine/flash index 14 is replaced by steady red, index 6.
- No image pixel uses index 14; its unused palette entry retains the standard
  UI palette value.

## Validation

The initial September 23 work prepared artwork only. Its checks covered mesh
counts, reference extraction dimensions, image bounds, the 4-bit indexed PNG
header, exact palette, red frames, empty cells and absence of index 14. All RGB
values were also validated using the graphics compiler's read-only `read_png`
function.

The obsolete one-off PNG generator, review images and temporary verification
report were removed after migration to runtime rendering. The archived originals
remain available for comparison. Current renderer and memory-ownership checks
are described in the [runtime ship images notes](2026-09-24-runtime-ship-images.md).
