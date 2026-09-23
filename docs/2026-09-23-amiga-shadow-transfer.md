# The shadow transfer: carrying only what changed to Chip RAM

Date: 2026-09-23
Status: implemented

## Why

On a 68020 or better with Fast RAM, `fastdraw=yes` draws the flight view into a Fast RAM shadow and `swap_screen` carries it to the screen once a frame. Carrying the whole view every frame puts `view_bytes` on the chip bus however little moved: 112,640 bytes in `pal-hireslace`, and it is the chip bus the 640 modes are bound by. Most frames change a small part of the view, so the transfer sends only the pieces that differ from what the target buffer already shows.

## Three viewports

The shadow allocation holds three viewports of `view_bytes` each. One is being drawn into. The other two hold exactly what each Chip buffer's flight view shows, one per buffer; these are the mirrors.

Once a frame has crossed, its target buffer shows exactly what the frame was drawn in, because every piece either matched that buffer's mirror or was sent. So the viewport the frame was drawn in is the new mirror of that buffer, and the mirror it replaces is cleared and drawn into next. The three trade places each frame and nothing is copied between them:

| frame | target | drawn into | mirror of buffer 1 | mirror of buffer 2 |
| --- | --- | --- | --- | --- |
| 1 | buffer 1 | A | B | C |
| 2 | buffer 2 | B | A | C |
| 3 | buffer 1 | C | A | B |
| 4 | buffer 2 | A | C | B |

`shadow_base` and `view_base` follow the viewport being drawn, so the drawing code needs no change: `dot_to_addr` and `solid_polygon` read `view_base` on every call.

## One frame

```
clear_image    clear the rows of the viewport about to be drawn that its old
               picture held, which the last transfer marked from that
               picture's empty-row flags
      |
      v
draw           every primitive inside the view writes the drawn viewport
      |
      v
swap_screen    for each row of the view:

                 target's mirror unknown? ----------- yes --> send every piece
                   | no
                 target shows the row empty? -------- yes --> send only the pieces
                   | no                                       that hold anything
                 each 16-byte piece:
                   equal to the target's mirror? ---- no  --> send it to Chip RAM
                                                      yes --> leave it

               then the drawn viewport becomes the target's mirror, the old
               mirror becomes the next frame's drawing viewport, present
```

A piece is sixteen bytes, one `movem.l` of four longs, and it is compared and sent straight from the registers the comparison loaded, so nothing is read twice. The mirror and the Chip buffer are addressed from the shadow pointer through index registers. Where the target shows something in a row, the row is tested for content only until its first piece that holds any.

For each buffer the transfer keeps one byte a row saying whether that buffer shows the row empty, set from the row it has just made the buffer show. Where it does, the mirror is not read at all. The same flags tell `clear_image` which rows of the replaced mirror to clear before the next frame draws into it.

## When a mirror is forgotten

A mirror is only right while nothing writes the flight view of its buffer except the transfer. Anything that does makes that buffer's mirror unknown, and the next transfer to it sends every piece:

| write | how it is caught |
| --- | --- |
| a primitive drawn while the shadow is not live, as a menu prompt is | `dot_to_addr` clears both mirrors |
| a frame drawn without the shadow | `swap_screen` clears both mirrors |
| a dual-screen block or a dual-screen sprite's restore | `amiga_flip_address` reports the address it hands out, and `forget_mirror` clears the mirror of the buffer it lands in |
| the credit scroller, which writes the shown buffer directly | it reports its own address to `forget_mirror` |

`forget_mirror` clears a mirror only for an address inside that buffer's flight view, so writes to the panel cost nothing.

## The `shadowcopy` option

| option | what the shadow carries | frame time line, with `frametime=yes` | counts in the transfer |
| --- | --- | --- | --- |
| `shadowcopy=changes`, the default | the pieces that changed | the times and the flags | no |
| `shadowcopy=counter` | the pieces that changed | also every piece the view has over how many crossed | yes |
| `shadowcopy=all` | every piece, every frame | also every piece the view has over `ALL` | no |

`all` takes the path a mirror of unknown contents takes, every frame, so it differs from the other two in that one decision and reads out the same figures; it is there to measure what carrying the changes saves. `./build_amiga.sh all shadowcopy=counter` builds every image with the option, since `all` passes its extra options on.

The frame time line, forty text columns across in `pal-hireslace`, for each option:

```
changes   025 004 001      FRONT              2.LF
counter   025 004 001      FRONT    7040/0206 2.LF
all       079 002 001      FRONT    7040/ALL  2.LF
          |   |   |                 |    |    |
          |   |   |                 |    |    flags
          |   |   clear             |    pieces that crossed, held over 16 frames
          |   draw                  every piece the view has
          work
```

The pieces count holds over the same sixteen frames as the times, so the digits stand still. `pal-hireslace` has 352 rows of 20 pieces, 7,040 in all.

## Measured

`pal-hireslace`, the work figure in milliseconds, on a 68020 or 68030 with Fast RAM, the `2` of the flags. The changes were measured with the build that counts them, which is how the pieces sent are known:

| scene | `all` | `counter` | pieces sent |
| --- | --- | --- | --- |
| the ELITE title | 79 | 25 | 206 |
| a Cobra Mk III turning | 88 | 85 | 3,800 |
| launching from the station | 100 | 84 | |

The gain shrinks as more of the view changes: a turning ship that fills half the view sends 3,800 of the 7,040 pieces, and those are written to Chip RAM whichever option is built.

## Testing

`src_amiga/tests/test_fastdraw.py` drives whole sequences of frames through the real `clear_image`, drawing and `swap_screen` and checks one property after every frame: the flight view of the buffer the frame was carried to equals the viewport it was drawn in, byte for byte. The sequences cover two longwords of a piece trading places, which a comparison by sums could not see, scattered pixels over 160 frames mixed with primitives drawn straight to Chip RAM, a large shape moving every frame, and a dual-screen block drawn while both mirrors are valid. `ELITE_SHADOW_EVERY=1` runs the same tests against `shadowcopy=all`.
