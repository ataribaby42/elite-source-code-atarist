; OCS low-resolution raster: four 40-byte planes per row, 160 bytes per row.
; Copper points at base+0/40/80/120; both bitplane modulos are 120.
; All addresses below are actual DMA-visible Chip RAM addresses.

native_plot macro
    not.w \1
    and.w \1,0(\3)
    and.w \1,40(\3)
    and.w \1,80(\3)
    and.w \1,120(\3)
    not.w \1
    move.w 0(\2),\4
    and.w \1,\4
    or.w \4,0(\3)
    move.w 2(\2),\4
    and.w \1,\4
    or.w \4,40(\3)
    move.w 4(\2),\4
    and.w \1,\4
    or.w \4,80(\3)
    move.w 6(\2),\4
    and.w \1,\4
    or.w \4,120(\3)
    endm

native_fill macro
    swap \1
    move.w \1,0(\3)
    swap \1
    move.w \1,40(\3)
    swap \2
    move.w \2,80(\3)
    swap \2
    move.w \2,120(\3)
    addq.l #2,\3
    endm

native_copy macro
    move.w 0(\1),0(\2)
    move.w 40(\1),40(\2)
    move.w 80(\1),80(\2)
    move.w 120(\1),120(\2)
    addq.l #2,\1
    addq.l #2,\2
    endm

native_save macro
    move.w 0(\1),(\2)+
    move.w 40(\1),(\2)+
    move.w 80(\1),(\2)+
    move.w 120(\1),(\2)+
    endm

native_restore macro
    move.w (\1)+,0(\2)
    move.w (\1)+,40(\2)
    move.w (\1)+,80(\2)
    move.w (\1)+,120(\2)
    addq.l #2,\2
    endm

native_sprite_save macro
    btst #dont_save,sp_flags(a4)
    bne native_no_save\@
    native_save a0,a2
native_no_save\@:
    endm
