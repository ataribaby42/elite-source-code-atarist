# fastdraw: where the flight view is drawn and cleared

Date: 2026-09-21
Status: implemented

## Why

The 640 modes are bound by the chip bus, not by the processor. Four hires bitplanes fetch 160 words a raster line against 80 in a 320 mode, and the CPU gets the slots that are left, so every primitive pays for the fetch: `native_plot` is sixteen Chip accesses per plotted word, and a filled polygon writes the same 8 bytes per 16 pixels as the clear. A scene that overdraws the view pays the clear's cost again for each pass, which is what the launch sequence does.

## The three clears

`clear_image` writes `y_size` rows of `x_size/8` bytes in each of four planes and nothing reads them. Three things can do it, and which one wins is a property of the hardware, so `probe_cpu` chooses at startup rather than the build choosing:

| machine | clear | flag |
| --- | --- | --- |
| 68000 or 68010 | the blitter, while the CPU carries on | `B` |
| 68020 or better with Fast RAM | the CPU, into a Fast RAM shadow | `F` |
| 68020 or better without | the CPU, into Chip RAM | `C` |

`fastdraw=yes` puts the first two in the image and every call in `all` passes it; `fastdraw=no` leaves only the third.

### The Fast RAM shadow

`fastdraw=yes` on a 68020 or better draws the viewport into a Fast RAM buffer and `swap_screen` copies it to the screen once per frame, so the bus carries one pass of `view_bytes` however busy the scene. `view_base` is that buffer minus `y_top*row_stride`, so the address arithmetic every primitive already does, base plus row times stride plus x over eight, lands in the shadow unchanged. Two places pick the base: `dot_to_addr`, which every dot, line, character, sprite and block goes through, and the row address in `solid_polygon`, which computes its own. The panel, the scanner and the instruments keep writing straight to the screen. A dual-screen `block` inside the viewport writes the shadow and the other buffer at the same offset, because the copy only reaches the one buffer it is about to present; `flight.m68` paints the fuel leak that way.

Measured on a 68060 flying towards the station:

| mode | frame | clear |
| --- | --- | --- |
| `pal-hires`, Chip | 40 ms | 19 ms |
| `pal-hires`, Fast | 24 ms | 1 ms |
| `pal-hireslace`, Chip | 80 ms | 39 ms |
| `pal-hireslace`, Fast | 47 ms | 2 ms |

A framed viewport does not span whole rows, so the shadow compiles out there.

### The blitter

A 68000 gets nothing from the shadow even where there is Fast RAM to hold it: the full-viewport copy would cost that processor more than the sparse drawing it replaces. So on a 68000 or 68010 no shadow is allocated and the blitter does the clear instead, asynchronously. `clear_image` programmes the registers and returns; the whole object loop, the projection, the AI and the panel run while the fill proceeds, and `wait_clear` drains BBUSY at the top of the four routines that begin writing inside the viewport, `draw_space`, `draw_all`, `block` and `print_string`, and once more in `swap_screen` so nothing is presented half filled.

One D-only fill with minterm zero covers the viewport in every mode. A frameless viewport is one flat run, so the blit is 64-word rows with no modulo; an inset one is four runs per screen row, one per plane, and because the plane spacing equals `bpr` the same modulo carries the blit from plane to plane and from row to row:

| build | width | height | BLTDMOD | bytes |
| --- | --- | --- | --- | --- |
| framed `pal`, `ntsc` | 16 words | 448 | 8 | 14,336 |
| framed hires | 32 words | 448 | 16 | 28,672 |
| framed interlaced | 32 words | 896 | 16 | 57,344 |
| wide `pal` | 64 words | 220 | 0 | 28,160 |
| wide `pal-hires` | 64 words | 440 | 0 | 56,320 |
| wide `pal-hireslace` | 64 words | 880 | 0 | 112,640 |

The drain is bounded, so a blit that never reports idle costs one stuttered frame rather than a hang.

`BLTPRI` stays clear: giving the blitter priority would stall the 68000 and make the clear synchronous again. The game leaves the OS alive, so `amiga_entry` takes the blitter with `OwnBlitter` when it takes the display and `amiga_exit` gives it back. `blit_fits` in `geometry.def` is the assembly-time condition: the height has to fit the ten-bit BLTSIZE field, and a flat run has to divide into whole blit rows.

An inset viewport is the one shape neither the shadow nor MOVE16 fits, so the blitter is the framed build's only accelerated clear.

### MOVE16

From the 68040 up, `MOVE16` writes a whole sixteen byte line at once, and the CPU clear uses it where it exists. Measured on a 68060 it changes nothing: the transaction width buys no extra bus slots. The path stays because it costs nothing and another memory controller may answer differently.

`clear_burst_ok` in `geometry.def` is the assembly-time condition: the viewport must span whole rows and hold a whole number of sixteen byte lines, which is true of every frameless build and of no framed one. Either test failing keeps the `movem.l` span loop.

AmigaDOS aligns a hunk to eight bytes, not sixteen, so `clear_image` reads the screen's own alignment. On an eight byte start a pair of long writes covers the half line at each end and the burst runs one line shorter; anything else falls back to the spans. The source is sixteen zero bytes in the `workspace` section, which is not Chip attributed and lands in Fast RAM where the machine has any. `MOVE16` ignores the low four bits of both addresses, so the block is 32 bytes and the source points into the middle of it, which keeps the transfer inside the zeros whatever the section alignment turns out to be.
