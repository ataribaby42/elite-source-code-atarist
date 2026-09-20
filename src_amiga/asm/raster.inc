; OCS low-resolution raster: scr_planes bitplane rows of bpr bytes per pixel row.
; Copper points at base+0/plane1/plane2/plane3; both bitplane modulos skip the rest.
; All addresses below are actual DMA-visible Chip RAM addresses.

native_plot macro
    not.w \1
    and.w \1,0(\3)
    and.w \1,plane1(\3)
    and.w \1,plane2(\3)
    and.w \1,plane3(\3)
    not.w \1
    move.w 0(\2),\4
    and.w \1,\4
    or.w \4,0(\3)
    move.w 2(\2),\4
    and.w \1,\4
    or.w \4,plane1(\3)
    move.w 4(\2),\4
    and.w \1,\4
    or.w \4,plane2(\3)
    move.w 6(\2),\4
    and.w \1,\4
    or.w \4,plane3(\3)
    endm

native_plot_cached macro
    ; Mask, two cached pairs of plane words, destination, temporary data register.
    not.w \1
    and.w \1,(\4)
    and.w \1,plane1(\4)
    and.w \1,plane2(\4)
    and.w \1,plane3(\4)
    not.w \1
    move.l \2,\5
    swap \5
    and.w \1,\5
    or.w \5,(\4)
    move.w \2,\5
    and.w \1,\5
    or.w \5,plane1(\4)
    move.l \3,\5
    swap \5
    and.w \1,\5
    or.w \5,plane2(\4)
    move.w \3,\5
    and.w \1,\5
    or.w \5,plane3(\4)
    endm

native_fill macro
    ; Four cached plane words, followed by the destination address register.
    move.w \1,(\5)
    move.w \2,plane1(\5)
    move.w \3,plane2(\5)
    move.w \4,plane3(\5)
    addq.l #2,\5
    endm

native_copy macro
    move.w 0(\1),0(\2)
    move.w plane1(\1),plane1(\2)
    move.w plane2(\1),plane2(\2)
    move.w plane3(\1),plane3(\2)
    addq.l #2,\1
    addq.l #2,\2
    endm

native_save macro
    move.w 0(\1),(\2)+
    move.w plane1(\1),(\2)+
    move.w plane2(\1),(\2)+
    move.w plane3(\1),(\2)+
    endm

native_restore macro
    move.w (\1)+,0(\2)
    move.w (\1)+,plane1(\2)
    move.w (\1)+,plane2(\2)
    move.w (\1)+,plane3(\2)
    addq.l #2,\2
    endm

native_sprite_save macro
    btst #dont_save,sp_flags(a4)
    bne native_no_save\@
    native_save a0,a2
native_no_save\@:
    endm

native_clear_span macro
    ; Zero x_size/8 bytes at plane displacement \1 from A0; D0-D6/A1 hold zero.
clr_off set 0
    rept (x_size/8)/32
    ifeq clr_off+\1
    movem.l d0-d6/a1,(a0)
    endc
    ifne clr_off+\1
    movem.l d0-d6/a1,clr_off+\1(a0)
    endc
clr_off set clr_off+32
    endr
    rept ((x_size/8)-clr_off)/4
    move.l d0,clr_off+\1(a0)
clr_off set clr_off+4
    endr
    endm
