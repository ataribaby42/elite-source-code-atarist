# Runtime ship images

Both enhanced source trees own an independent `asm/shipgfx.m68`. It reads the
relocated flight vertices, the first linked surface variant and the existing
`vector.m68` material patterns. No mesh copy, external atlas or generated bitmap
file is needed for these pictures. The original-version source is unaffected.

## Images and lifecycle

| Buffer | Count | Authoring dimensions | Bytes, including sprite headers and masks |
| --- | ---: | --- | ---: |
| Shipyards | 13 | 64 x 41 | 21,372 |
| Current ship: Status and laser dialog | 1 | 128 x 51 | 4,084 |
| Current ship: Planet Data | 1 | 32 x 45 | 904 |

Only Shipyards has a complete atlas. The two other buffers each hold one image,
for a total of 26,360 image bytes, plus guard words and renderer scratch. Reopening
a UI screen reuses these images; ordinary drawing and flight do not regenerate them.

`ship_graphics_init` builds Shipyards once after object relocation, before the
first UI screen. `ship_apply` updates hull limits and invokes `ship_refresh` to
regenerate the two current-ship images. Existing new-game restore, commander
load and successful purchase paths all pass through this routine. Loading the
same hull also regenerates its images. Failed purchases do not change them.

Projection follows the former PNG renderer: orthographic rear/above at 45 degrees
for Status, overhead with the nose right for Planet Data, overhead with the nose
up for Shipyards. Only nodes referenced by visible surfaces determine the fit.
Each hull is centered and uniformly scaled with a one-pixel margin. Convex faces
use filled spans; model detail lines remain, without an added outline. Native
integer rasterization can differ from the old Pillow images at individual edge
pixels. Surface order, material dithering, perspective and orientation remain.

Material zero becomes opaque UI black (13); flashing material 14 becomes steady
red (6). Empty pixels remain transparent zero. Red PNG editing borders do not
exist in runtime images.

WIDE changes neither authoring dimensions nor fit. Amiga HIRES and HIRES-LACED
keep the same UI scale as PNG-derived sprites: 2x horizontally and, when laced,
2x vertically. The cached images remain unscaled. `ship_put_bitmap` expands one
masked row at a time into a separate, fixed-capacity buffer, so higher resolution
does not multiply the persistent atlas allocation.

## Memory ownership

- Amiga gives the cache and renderer scratch a dedicated `ship_graphics` BSS
  Hunk. The loader reserves it independently of screens, bitmap expansion,
  sprite backups, flight graphics, shadows and UI workspaces.
- Atari reserves the section explicitly between `cockpit_end` and `vars` inside
  its NOLOAD workspace. `ram_end`, launcher allocation and runtime relocation
  include it. The cockpit file-size check uses `cockpit_end`, so the cache is
  never counted as spare asset-loading capacity.
- Both builds verify the three buffer capacities. Amiga verifies complete Hunk
  ownership; Atari verifies both neighboring boundaries.
- Every pixel write checks unsigned X/Y limits, which also reject negative
  coordinates. Fixed arrays cover the existing maximum node count and the
  largest image height. Persistent images and render/row scratch do not overlap.
- Guard words surround the image bank, its individual image groups and scratch.
  Native regression tests inspect them after rendering, screen changes, commander
  transitions and flight, and hash the Shipyards bank to detect in-range damage.

## Build inputs and archive

The three old PNG files (`ships.png`, `shipsplanetinfo.png`, `shipyards.png`)
and `ship-atlases.json` are archived in
[`resources/gfx_assets`](../resources/gfx_assets) and are not imported. They have
been removed from `gfx` and `gfx_alt`; builds work with them absent. The obsolete
PNG generator and its temporary review files have also been removed. Stale ship
binary exports are still removed from `assets` and the Amiga build directory
when compiling graphics, with regression tests covering this cleanup.

Editing the archive does not change either game, and `altgfx=yes` does not select
different ship models or portraits. Each platform builds its own renderer and
uses its own existing model and material data. The normal PNG workflow continues
to supply menus, equipment artwork, fonts and other UI graphics. The general
bitmap ordering remains compatible, but its original Cobra tiles no longer
supply Status, laser mount selection or Planet Data.

The unused 128 x 51 Cobra in `panels.png` is now excluded from the general
bitmap bank as well. Its source pixels remain in the PNG and ID 54 stays
reserved with a null offset, while its payload and runtime allocation are
removed. The separate small Cobra cell in `gadgets.png` is unchanged. See
[unused Cobra bitmap removal](2026-09-24-unused-cobra-bitmap.md).

No ship bitmap bank is read from disk or embedded in the executable. The complete
Shipyards atlas and the two current-ship images exist only in reserved runtime
memory. PNG editing borders and unused atlas cells therefore need no storage.

## Measured savings

Figures compare the completed implementation against the preceding production
builds, with the same commander and display options, before the subsequent
removal of the unused panel Cobra. Alternate artwork gives the same savings.
One KiB is 1,024 bytes.

| Build | Executable bytes saved | RAM bytes saved |
| --- | ---: | ---: |
| Atari ST | 85,032 | 71,456 |
| Amiga framed PAL | 24,520 | 2,868 |
| Amiga WIDE PAL | 24,516 | 2,864 |
| Amiga HIRES PAL | 24,424 | 6,796 |
| Amiga HIRES-LACED PAL | 29,104 | 19,488 |

Atari RAM figures include the aligned game workspace reservation. Amiga figures
sum executable Hunk allocations; existing dynamic general bitmap and shadow
allocations are unchanged. Disk-image container sizes remain 720/880 KiB; smaller
executables leave more free filesystem blocks. Runtime rasterization adds work
at startup and when the player's hull is restored or changed, not during flight.

Removing the unused panel Cobra additionally saves 3,268 bytes in `BITMAPS.IMG`
for every build. Its RAM saving is 4,084 bytes on Atari and normal/WIDE Amiga,
8,164 in Amiga HIRES and 16,324 in HIRES-LACED. The executable-size figures above
do not include this separate data-file saving.

## Validation

All 14 Amiga and both Atari distributions assemble and pass their existing disk,
relocation and memory-layout checks. Python suites pass 33 Amiga and 34 Atari
tests, with the existing historical-artwork identity check skipped in each.
The updated PNG tests also prove missing ship PNGs do not affect asset generation.

Private emulator sessions use separate, verified hidden Windows desktops and
owned executable/configuration/disk copies under `build/runtime-ships-qa`.
The native fixture covers all 13 hulls through Status, Planet Data, Equipment and
Shipyards, then purchase, saved-position restore, new game and flight. Generated
Amiga and Atari image bytes agree. All image dimensions, transparency masks,
one-pixel margins and palette exclusions pass; bounds remain within one pixel of
the former PNG rasterization. The higher-resolution tests verify every opaque
Planet Data pixel against the correctly expanded cached image at its actual UI
destination.

Atari and framed/WIDE PAL Amiga run on 1 MB. HIRES and HIRES-LACED image tests use
an expanded Amiga (2 MB Chip plus 4 MB Fast, 68020); their existing larger general
bitmap allocations do not fit the tested 512 KB Chip plus 512 KB slow setup.
This change reduces their memory use but does not replace those allocations.

QA comparison sheets use cyan to identify transparency. Screen previews must
instead decode index zero as black and crop to the UI's 200 authoring rows; using
the PNG editing palette for a raw screen dump produces a misleading cyan
background without changing the running game's palette.
