# Editable PNG graphics

Each enhanced game has independent source images in its own `gfx` directory.
Edit `src_atari/gfx` for Atari or `src_amiga/gfx` for Amiga. Neither build reads the
other tree, `resources/gfx_assets`, or existing generated assets to reconstruct
the graphics. The resource images remain reference previews and archives,
including the former ship PNG atlases.

The build option `altgfx=yes|no` defaults to `no`, selecting `gfx/`. With
`altgfx=yes`, all required PNGs and `layout.json` come from the same tree's
`gfx_alt/` directory instead. Missing files are errors; there is no fallback
to `gfx/`. To prepare another source set, copy the complete `gfx/` directory
to `gfx_alt/`, then edit those PNGs using the same dimensions and palette.

```powershell
.\build_atari.bat altgfx=yes
.\build_amiga.bat altgfx=yes
```

Use `altgfx=no` to switch back. Both selections write the usual `assets/` and
distribution paths, replacing the preceding build's graphics. The selected
option is recorded in `build/verification.json` under `build_options.altgfx`.

On Amiga, `frame=no` selects `cockpit_noframe.png` instead of `cockpit.png`
from the selected `gfx/` or `gfx_alt/` directory. It uses the same 320 x 200
canvas, cockpit palette and `layout.json` metadata, and generates `COCKPIT.PC1`
for every PAL/NTSC, WIDE, HIRES and interlaced display mode. `frame=yes` keeps
using `cockpit.png`.

## Editing and building

Use any PNG editor and keep the original canvas dimensions. RGB, RGBA and indexed
PNG exports all work. **RGB values determine the game indices; PNG palette order
and PNG storage indices do not matter.** The converter selects the palette by
filename: `cockpit.png` and Amiga's `cockpit_noframe.png` use the cockpit palette, while all other source PNGs use
the UI base palette. The same rules apply to both platforms and both source sets.

| Game index | UI PNG RGB | Cockpit PNG RGB |
| --- | --- | --- |
| 0 | `#00FFFF` | `#00FFFF` |
| 1 | `#929292` | `#929292` |
| 2 | `#494949` | `#494949` |
| 3 | `#FF6D00` | `#FF6D00` |
| 4 | `#FF00FF` | `#FF00FF` |
| 5 | `#FFFF00` | `#FFFF00` |
| 6 | `#FF0000` | `#DB0000` |
| 7 | `#92FF00` | `#92FF00` |
| 8 | `#6DB600` | `#6DB600` |
| 9 | `#496D00` | `#496D00` |
| 10 | `#92B6FF` | `#92B6FF` |
| 11 | `#496DDB` | `#496DDB` |
| 12 | `#0024DB` | `#0024DB` |
| 13 | `#000000` | `#000000` |
| 14 | `#6D4900` | `#FF0000` |
| 15 | `#FFFFFF` | `#FFFFFF` |

Relative to the former shared editing palette, UI index 6 changes from
`#DB0000` to `#FF0000`, index 8 from `#66AA00` to `#6DB600`, and index 14 from
`#FF0000` to `#6D4900`. Cockpit PNGs only change index 8. The old editing green
`#66AA00` is no longer accepted. Bright red `#FF0000` means UI index 6 or cockpit
index 14; the filename resolves that distinction without relying on PNG indices.

The RGB values represent the original ST palette entries, with two editing
exceptions: cyan distinguishes transparent index 0 from opaque black 13, and
bright red marks the cockpit's pulsing index 14. A full-screen index-0 pixel
still displays black. The PC1 hardware palette headers and all game pixel
indices stay unchanged; index 8 remains hardware `$350`.

`gadgets.png` is a shared atlas with UI controls, cockpit symbols and missile
states. Edit it with the UI base palette; the game displays each sprite using
the active screen palette. The monochrome font also uses the UI palette, but
only indices 0 and 15 are allowed. Some colours change at runtime: UI index 14
can flash red/white, cockpit index 14 pulses, and alien portraits can recolour
selected entries. A static PNG shows the base palette or editing marker.

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
`python src_amiga/tools/gfx_assets.py` from the repository root. These standalone
commands use `gfx/`; use the build option above for `gfx_alt/`.

## Sheet layout

All sheets are native resolution, with cells filled left to right, top to bottom.
Artwork starts at each cell's top-left corner. Only the original bitmap rectangle
inside each cell is exported; unused cell padding is not artwork. Keep each
bitmap's original dimensions. The selected directory's `layout.json` lists the exact rectangles
(`[x, y, width, height]`), game names and IDs; it is format metadata, not artwork.

| PNG | Canvas | Cell layout and contents |
| --- | --- | --- |
| `cockpit.png` | 320 × 200 | Full `COCKPIT.PC1` screen |
| `cockpit_noframe.png` (Amiga) | 320 × 200 | `COCKPIT.PC1` source for `frame=no` |
| `textscr.png` | 320 × 200 | Full `TEXTSCR.PC1` screen |
| `font.png` | 128 × 48 | 16 columns of 8 × 8 glyphs; ASCII 32–127, including blank slots |
| `font16.png` (Amiga) | 256 × 48 | Independent 16 × 8 versions of the same glyphs for 640-pixel-wide modes |
| `cargo.png` | 240 × 128 | 5 columns of 48 × 32 cells; bitmap IDs 0–19 |
| `equipment.png` | 448 × 432 | 4 columns of 112 × 48 cells; IDs 32–47, then equipment labels 58–74 |
| `panels.png` | 320 × 576 | One column of 320 × 96 cells; IDs 20, 21, 48, 49, 113; Cobra cell 54 is retained as artwork only |
| `characters.png` | 320 × 288 | 5 columns of 64 × 72 cells; heads 75–84, then bodies 85–94 |
| `gadgets.png` | 384 × 432 | 6 columns of 64 × 48 cells; remaining bitmap IDs in ascending order, then four missile states |

**The Cobra image in `panels.png` is not used by either the Amiga or Atari game.**
It remains in the PNG as reference artwork only; no game asset is generated
from it. Both games render the current player's ship from its 3D model instead.

The old 128 x 51 Cobra's `layout.json` entry
keeps ID 54 and its source rectangle for reference, with `export: false` and
`offset: 0`. The bitmap file retains a null pointer at that ID but contains no
Cobra header, pixels or padding; all other IDs remain unchanged. Editing the
Cobra cell therefore has no effect on generated assets. The PNG itself is unchanged.

Missile states are empty, installed, active and locked. Each has a 16 × 6 source
rectangle, but only its first 10 columns are painted; keep the final six columns
at index 0 (cyan or fully transparent). The entire 10 × 6 missile area is opaque,
including its black pixels,
matching the original fixed sprite masks. Missile binaries are embedded during
assembly; they are not additional disk files.

## Runtime ship images and archived PNGs

The three ship views are rendered from native models in both enhanced games,
outside this PNG conversion workflow. Shipyards keeps a complete 13-tile atlas
of 64 x 41 images. Status and the laser mount dialog share a single 128 x 51
image of the current hull; Planet Data uses a single 32 x 45 image. Startup
generates Shipyards, while new game, commander load and hull purchase refresh
the two current-ship pictures. These cached dimensions do not depend on WIDE,
HIRES or HIRES-LACED; drawing applies the selected UI scale.

`ships.png`, `shipsplanetinfo.png`, `shipyards.png` and `ship-atlases.json` are
archived in [`resources/gfx_assets`](../resources/gfx_assets). Neither `gfx/`
nor `gfx_alt/` needs them, and editing the archived PNGs has no effect on builds.
The obsolete one-off PNG generator and its temporary previews were removed.
To change these pictures, use the platform's model/material data or its own
`asm/shipgfx.m68`; the original Cobra tiles in the general PNG sheets no longer
supply the player pictures on these screens.

The converter removes stale `SHIPSPRITES.IMG`, `SHIPSPRITES_SCALED.IMG` and
`SHIPS_PACKED.IMG` exports from `assets/`, and from the Amiga build directory
when supplied by the build. They are not regenerated or needed at runtime.
Other PNG-derived assets continue to compile normally. See
[runtime ship images](2026-09-24-runtime-ship-images.md) for buffer ownership,
camera views, palette handling and validation.

## Binary compatibility and validation

The initial PNG workflow reproduced the original generated binary files byte
for byte, including after migration to the per-image RGB palettes. The current
bitmap bank deliberately omits the unused panel Cobra while preserving all
remaining pixel data and bitmap IDs. Its default hash fixture reflects this
compaction. See the [Cobra bitmap removal notes](2026-09-24-unused-cobra-bitmap.md)
for file sizes, RAM savings and loader checks.

`layout.json` retains the historical bitmap ordering and PC1 trailer bytes,
without storing a second copy of the pixel artwork. The standard source set
keeps historical PC1 packet boundaries; the alternate cockpit uses optimized
packet boundaries so its artwork fits the existing loading buffer. PNG pixels
always supply the output. Changed PC1 runs are recompressed within each 40-byte
plane scanline, as required by the game's decoder. Existing memory-capacity checks
still reject a screen that becomes too large for its runtime loading buffer.

The build validates dimensions, RGB swatches and alpha before writing any
generated asset. It never requires edited images to match historical hashes.
The regression test for historical identity runs only while the PNG file hashes
still match the supplied defaults; it skips after customization. Other regression
tests modify temporary PNG copies and check the resulting pixels, font bits,
missile masks, RGB/RGBA exports, reordered palettes (including storage indices
above 15), per-image red/brown mapping, transparent pixels and validation failures.

All 32 PNGs in both platforms' `gfx/` and `gfx_alt/` were migrated from the shared
palette to their screen palettes while preserving every game index. All eight
generated binary assets in each of the four sets were compared byte for byte
before and after this migration. Verified historical default fixtures still
match the original asset hashes. Backups and migration reports are under each
tree's `build/screen-palettes-*` directory.

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
