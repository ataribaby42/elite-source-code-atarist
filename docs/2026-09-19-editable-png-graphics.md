# Editable PNG graphics

Each enhanced game has eight independent source images in its own `gfx` directory.
Edit `src_atari/gfx` for Atari or `src_amiga/gfx` for Amiga. Neither build reads the
other tree, `resources/gfx_assets`, or existing generated assets to reconstruct
the graphics. The resource images remain reference previews.

## Editing and building

Use any PNG editor and keep the original canvas dimensions. RGB, RGBA and indexed
PNG exports all work. **RGB values determine the game indices; PNG palette order
and PNG storage indices do not matter.** All eight images use the same editing
palette below, matching the palette supplied by the user.

| Game index | PNG RGB |
| --- | --- |
| 0 | `#00FFFF` (transparent in ordinary sprites) |
| 1 | `#929292` |
| 2 | `#494949` |
| 3 | `#FF6D00` |
| 4 | `#FF00FF` |
| 5 | `#FFFF00` |
| 6 | `#DB0000` |
| 7 | `#92FF00` |
| 8 | `#66AA00` |
| 9 | `#496D00` |
| 10 | `#92B6FF` |
| 11 | `#496DDB` |
| 12 | `#0024DB` |
| 13 | `#000000` (opaque black) |
| 14 | `#FF0000` (the pulse/colour-cycle slot) |
| 15 | `#FFFFFF` |

Cyan distinguishes transparent index 0 from opaque black 13. Dark red identifies
6, while bright red identifies 14. These are editing swatches, not replacements
for the game's hardware palettes: a full-screen index-0 pixel displays black,
not cyan, and index 14 takes its existing runtime colour or colour cycle.
The two PC1 palette headers stay unchanged. In particular, the supplied editing
green `#66AA00` maps to index 8, whose original hardware value remains `$350`.

Fully transparent PNG pixels (alpha 0) also map to index 0, regardless of their
hidden RGB. Partially transparent pixels are rejected because the game has no
alpha blending. Other pixels must exactly match a swatch; there is no nearest
colour matching or automatic quantization. An invalid pixel reports its RGB and
coordinates before any generated files are changed. Avoid antialiasing and
colour-profile conversion, and use nearest-neighbour scaling for editor zoom.
The monochrome font uses only cyan/transparent background (0) and white (15).

Run the usual `build_atari.bat` or `build_amiga.bat`. PNG compilation happens before
assembly and writes the platform's `assets` directory. Do not edit generated
`BITMAPS.IMG`, `COCKPIT.PC1`, `TEXTSCR.PC1`, `ELITECHR.IMG` or `MISSILE_*.IMG` files.
Other assets, including `TITLE.PC1`, `TEXTURE.PC1` and `LOGO.PC1`, retain their
existing workflow. The preserved `src_orig` build and historical ZIP are unchanged.

The enhanced builds require Pillow in the Python environment used for building:

```powershell
python -m pip install Pillow
```

To compile graphics alone, run `python src_atari/tools/gfx_assets.py` or
`python src_amiga/tools/gfx_assets.py` from the repository root.

## Sheet layout

All sheets are native resolution, with cells filled left to right, top to bottom.
Artwork starts at each cell's top-left corner. Only the original bitmap rectangle
inside each cell is exported; unused cell padding is not artwork. Keep each
bitmap's original dimensions. `gfx/layout.json` lists the exact rectangles
(`[x, y, width, height]`), game names and IDs; it is format metadata, not artwork.

| PNG | Canvas | Cell layout and contents |
| --- | --- | --- |
| `cockpit.png` | 320 × 200 | Full `COCKPIT.PC1` screen |
| `textscr.png` | 320 × 200 | Full `TEXTSCR.PC1` screen |
| `font.png` | 128 × 48 | 16 columns of 8 × 8 glyphs; ASCII 32–127, including blank slots |
| `cargo.png` | 240 × 128 | 5 columns of 48 × 32 cells; bitmap IDs 0–19 |
| `equipment.png` | 448 × 432 | 4 columns of 112 × 48 cells; IDs 32–47, then equipment labels 58–74 |
| `panels.png` | 320 × 576 | One column of 320 × 96 cells; IDs 20, 21, 48, 49, 54, 113 |
| `characters.png` | 320 × 288 | 5 columns of 64 × 72 cells; heads 75–84, then bodies 85–94 |
| `gadgets.png` | 384 × 432 | 6 columns of 64 × 48 cells; remaining bitmap IDs in ascending order, then four missile states |

Missile states are empty, installed, active and locked. Each has a 16 × 6 source
rectangle, but only its first 10 columns are painted; keep the final six columns
at index 0 (cyan or fully transparent). The entire 10 × 6 missile area is opaque,
including its black pixels,
matching the original fixed sprite masks. Missile binaries are embedded during
assembly; they are not additional disk files.

## Binary compatibility and validation

The supplied default PNGs reproduce all eight generated binary files byte for
byte, including after migration to the RGB editing palette. Full default Atari
and Amiga game executables and distributed data files were also compared against
builds made before the initial PNG workflow change.

`layout.json` retains the historical bitmap ordering and PC1 packet boundaries
and trailer bytes, without storing a second copy of the pixel artwork. PNG pixels
always supply the output. Changed PC1 runs are recompressed within each 40-byte
plane scanline, as required by the game's decoder. Existing memory-capacity checks
still reject a screen that becomes too large for its runtime loading buffer.

The build validates dimensions, RGB swatches and alpha before writing any
generated asset. It never requires edited images to match historical hashes.
The regression test for historical identity runs only while the PNG file hashes
still match the supplied defaults; it skips after customization. Other regression
tests modify temporary PNG copies and check the resulting pixels, font bits,
missile masks, RGB/RGBA exports, reordered palettes (including storage indices
above 15), transparent pixels and validation failures.

The one-time migration preserved every index in the unmodified artwork. The
edited Amiga `panels.png` and `gadgets.png` had already merged the two black
entries; their original transparent positions were restored from the default
artwork while retaining the edited colours. This positional recovery is only a
migration step, never part of the build. Old files and migration reports are
under each tree's `build/png-rgb-migration`; subsequent edits are resolved solely
from the new PNG's RGB and alpha.

```powershell
python -B -m unittest discover -s src_atari/tests -p test_gfx_assets.py -v
python -B -m unittest discover -s src_amiga/tests -p test_gfx_assets.py -v
```
