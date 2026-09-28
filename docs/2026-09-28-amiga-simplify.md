# Amiga code simplification

Date: 2026-09-28
Status: implemented in `src_amiga`

Follows [fast drawing](2026-09-21-amiga-fastdraw.md), the [shadow transfer](2026-09-23-amiga-shadow-transfer.md) and the [DblPAL mode](2026-09-25-amiga-dblpal-mode.md). The game looks and plays the same.

## Alignment for the 68020

A 68020 fetches instructions a longword at a time, so a loop runs faster when it starts on a longword. Every module now starts on one (`cnop 0,4` in `q_module`), and so do the busy routines of `graphics.m68`: the clear, the shadow transfer, and the polygon, line, dot and circle drawing. A change in one module no longer shifts the code of the next.

## Shared code

- `q_wait_clear` waits for the blitter before the viewport is written.
- `q_st_to_ocs` converts ST colours to OCS, for the palette and the planet data screen.
- `q_ui_box` draws the rectangle outlines of the options, cargo, equipment, disk and galaxy screens.
- `q_copy_longs` and `q_clear_longs` copy or clear a fixed length four bytes at a time. They replace the byte and word loops for object records, model data, variables, ship graphics, the hold, text buffers, the palette, the sky, the planet screen and the galaxy chart. From 64 bytes `q_clear_longs` writes a zero register instead of `clr`, which is slower up to the 68030. An odd length stops the build.
- `geometry.def` names its constants: `ddf_ideal`, `diwhigh_both`, `bpl_mod`, `view_offset`.
- Both charts draw their range circle with `range_circle` in `galaxy.m68`, and the galactic chart calls `build_sprite` instead of keeping its own copy.

## Screens

Every mode allocates its two screens with `AllocMem` after the machine check, where only DblPAL did before. A machine short of Chip RAM gets "This Elite needs more Chip RAM." in the shell, or in a window from Workbench. `say_and_stop` in `system.m68` prints this and the AGA and 68020 message. With 512 KB of memory in all, the program is too big to load, and AmigaDOS reports the error before the game starts.

The shadow's viewport always starts at the top left, so `view_base` was always `shadow_base` and is gone. `common.def` stops the build if that ever changes.

## MOVE16 removed

The `MOVE16` code is gone: nothing called its clear of the Chip RAM screen any more, and emptying the Fast RAM mirror with it is slower than `move.l` on a 68040 and 68060, since `MOVE16` reads its zero line as well as writing. The transfer, `clear_image` and the startup probe have one path for every processor, and the frame time line drops its `M`.
