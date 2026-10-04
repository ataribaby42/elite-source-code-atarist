# DblNTSC display mode

Date: 2026-09-28
Status: implemented in `src_amiga`

Adds `display=dblntsc-hires` next to the [DblPAL mode](2026-09-25-amiga-dblpal-mode.md): the geometry of `ntsc-hireslace`, 640 x 400 with a 640 x 240 flight view, shown without interlace. It needs AGA, a 68020 and a 27 kHz monitor, and is built with `cpu=68020` like DblPAL.

## Programmed beam

DblNTSC.monitor differs from DblPAL.monitor only in its row count. On AA, with `BUG_ALICE_LHS_PROG`, the driver's values are:

| BEAMCON0 | HTOTAL | VTOTAL | MINROW |
| --- | --- | --- | --- |
| `$1b88` | `$81` (129) | `$1dd` (477) | 23 |

The line is the DblPAL one, 36.3 us, and a field has 478 lines. `geometry.def` picks VTOTAL by `display_ntsc`; the blanking and sync edges, the Copper list, the VBL server and the machine check are the DblPAL ones.

## Window

The window starts at the same colour clock as DblPAL's, with the same fetch and delay, and is centred vertically below MINROW: rows 50 to 449.

| DIWSTRT | DIWSTOP | DIWHIGH | DDFSTRT | DDFSTOP | BPLCON1 |
| --- | --- | --- | --- | --- | --- |
| `$325b` | `$c2fb` | `$0900` | `$28` | `$70` | `$1122` |
