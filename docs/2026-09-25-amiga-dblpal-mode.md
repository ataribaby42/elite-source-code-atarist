# DblPAL display mode

Date: 2026-09-25
Status: implemented in `src_amiga`

Extends [wide and multi-mode support](2026-09-20-amiga-wide-and-multi-mode-support.md) with `display=dblpal-hires`: the geometry of `pal-hireslace`, 640 x 512 with a 640 x 352 flight view (512 x 224 framed), shown without interlace. Every frame carries all 512 rows, so there are no half frames and no flicker. It needs AGA and a 27 kHz monitor.

The image is built with `cpu=68020`, which every AGA machine has. At startup it checks for a 68020 or better and for Alice in VPOSR's chip ID, before anything else, and on a machine without either it says so in the shell, or in a window when started from Workbench, and quits. Its two screens are allocated only after that check, so an A500 with 512 KB of Chip RAM still loads the program and gets the message.

## Geometry

The logical space and the scale are those of `pal-hireslace`: `zoom_x` and `zoom_y` are both 2, and `display_tall` stands for "a logical row covers two physical rows", which interlace and DblPAL share. Everything that doubles rows for interlace does so for DblPAL through `display_tall`; only what depends on fields stays on `display_lace`: the LACE bit, the modulo that skips a row, the window that counts the rows of one field and the plane pointers moved a row down on the short field.

## Display registers

| BPLCON0 | FMODE | DIWSTRT | DIWSTOP | DIWHIGH | DDFSTRT | DDFSTOP | BPLCON1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `$4240` | `$0001` | `$2a5b` | `$2afb` | `$0a00` | `$28` | `$70` | `$1122` |

Four bitplanes of super-hires need FMODE's 32-bit fetch, so the mode is AGA only. DIWSTOP reaches only 383 rows, so DIWHIGH supplies the high bits, and once written it supplies every one of them, DIWSTRT's included. The values above are for the flight screen; 200-row artwork changes DIWSTOP and DIWHIGH only.

## Programmed beam

The mode drives its own sync with the values AmigaOS gives DblPAL.monitor on AA, where Alice pushes a programmed picture 8 colour clocks right (`BUG_ALICE_LHS_PROG`), so HTOTAL, VTOTAL and MINROW are the driver's AA ones.

| BEAMCON0 | HTOTAL | VTOTAL | MINROW |
| --- | --- | --- | --- |
| `$1b88` | `$81` (129) | `$23d` (573) | 23 |

The blanking and sync edges come from the ECS branch of the shared `monitorstuff.h`: HBSTRT 1, HBSTOP 30, HSSTRT 10, HSSTOP 19, VBSTRT 0, VBSTOP MINROW, VSSTRT MINROW/3, VSSTOP twice that. BEAMCON0 `$1b88` is VARVBLANK, LOLDIS, VARVSYNC, VARHSYNC, VARBEAMEN and BLANKEN. The beam values sit in the Copper list, with BEAMCON0 last, and `amiga_exit` puts back the standard PAL or NTSC BEAMCON0 and FMODE.

graphics.library's own VBL server writes the Workbench monitor's VTOTAL, VBSTRT and VBSTOP every field. The game's VBL server, which runs after it, writes the programmed values back; without that the game and its music ran at half speed on real AGA.

## Window position

The window opens at the driver's default view position, VPMINX plus half of VPRANGEX with FETCH1 `$28`, and vertically centred below MINROW: where Workbench puts a 640 x 512 DblPAL screen. DDFSTRT moves in whole fetch cycles, so the fetch starts a colour clock before the window and BPLCON1 delays the picture by that clock, as graphics.library does. On real AGA the first column still went missing behind the window's left edge, so the picture is delayed one super-hires pixel more and DIWHIGH closes the window one pixel later.

## Frame times

A DblPAL field outruns V8 alone, so the frame time reads the beam line as VBEAMPOS gives it, V10-V8 above V7-V0. Lines per field and the line length come from the programmed beam: a line is 36.3 us.
