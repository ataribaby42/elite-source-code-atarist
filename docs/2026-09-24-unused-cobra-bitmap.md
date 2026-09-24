# Unused panel Cobra bitmap removal

Both enhanced versions use the current hull's runtime-generated portrait on
Status and in the laser mount dialog. The original 128 x 51 Cobra in `panels.png`
therefore had no remaining caller, but still occupied disk and bitmap memory.

## Asset format and loading

The PNGs in both platforms' `gfx` and `gfx_alt` directories remain unchanged.
Their independent `layout.json` files mark `bit_cobra` (ID 54) with
`export: false` and `offset: 0`. The compiler retains its four-byte table slot
as zero, skips its header and pixels, and packs subsequent records without a gap.
All 125 bitmap IDs remain stable; only 124 bitmap records are stored.

Each platform's loader reads the complete 125-entry table but loads only
`bit_stored` (124) records. This also applies to Atari's legacy COM-link path.
No code calls `find_bitmap` for the reserved Cobra ID. Runtime ship portraits
continue to use their own image buffers and drawing path. The small Cobra in
`gadgets.png` is outside this change and remains exported.

## Savings and memory boundaries

`BITMAPS.IMG` shrinks from 112,800 to 109,532 bytes: 3,268 bytes saved, comprising
the four-byte header and 3,264 planar pixel bytes. There is no replacement dummy
bitmap and no remaining hole in the file.

| Platform/display | Bitmap RAM saved |
| --- | ---: |
| Atari ST | 4,084 bytes |
| Amiga normal or WIDE | 4,084 bytes |
| Amiga HIRES | 8,164 bytes |
| Amiga HIRES-LACED | 16,324 bytes |

The masked representation uses ten bytes per 16 pixels, plus a four-byte image
header. Amiga's allocation now contains 125 pointers, 124 headers and 13,567
source columns expanded to the selected display scale. Atari reduces its
existing reserved bank by exactly 4,084 bytes, retaining the preceding spare
capacity. Its following regions move together under the existing relocation
and linker checks; the dedicated ship-image cache remains isolated.

Both builds verify the table count, the omitted ID, the number of stored records
and the expanded bitmap bank capacity. Amiga also retains the check that its
temporary loading picture fits the smaller bank.

## Verification

The PNG regression test decodes every remaining bitmap, compares all its pixels
with its source rectangle, checks unchanged IDs and contiguous storage, and then
repaints the entire Cobra rectangle in a temporary PNG. No generated asset may
change. The historical default bitmap hash is updated from the verified baseline
by removing only that record and adjusting table offsets.

All 14 Amiga variants and both Atari variants build and pass disk and memory
layout validation. The Python suites complete 34 Amiga and 35 Atari tests, with
one historical-artwork identity test skipped in each because the source PNGs
have been customized.

The 15 native ship-image scenarios pass on Atari and on Amiga in framed PAL,
WIDE PAL, HIRES and HIRES-LACED. They cover all hulls, Status, Planet Data,
Equipment, Shipyards, purchase, restore, new game and flight, including image
guard checks. Atari and normal/WIDE Amiga use 1 MB; higher-resolution Amiga
checks use 2 MB Chip plus 4 MB Fast RAM. Every emulator runs on a verified hidden
desktop with private test files. Atari's final memory capture also confirms that
all 124 loaded headers, pixels and masks match the disk bank and slot 54 is null.

Build reports, preserved input hashes and private emulator captures are under
each platform's `build/cobra-asset-qa` directory. The source PNG hashes are checked
against the pre-change copies; no archived graphics or original-game files are
modified.
