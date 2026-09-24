; OCS low-resolution raster: scr_planes bitplane rows of bpr bytes per pixel row.
; Copper points at base+0/plane1/plane2/plane3; both bitplane modulos skip the rest.
; All addresses below are actual DMA-visible Chip RAM addresses.

native_plot macro
    ; Mask, colour masks, destination, two temporary data registers.
    not.w \1
    native_plot_word 0(\2),0(\3),\1,\4,\5
    native_plot_word 2(\2),plane1(\3),\1,\4,\5
    native_plot_word 4(\2),plane2(\3),\1,\4,\5
    native_plot_word 6(\2),plane3(\3),\1,\4,\5
    not.w \1
    endm

native_plot_word macro
    ; Colour, screen word, inverted mask, two temporary data registers.
    move.w \1,\5 ; fetch colour
    native_mask_word \5,\2,\3,\4
    endm

native_mask_word macro
    ; Colour register, screen word, inverted mask, temporary data register.
    move.w \2,\4 ; fetch screen word
    eor.w \1,\4 ; colour in the mask, screen outside it
    and.w \3,\4
    eor.w \1,\4
    move.w \4,\2 ; store screen word
    endm

native_mask_plot macro
    ; Mask, four plane words, destination, temporary data register.
    not.w \1
    native_mask_word \2,(\6),\1,\7
    native_mask_word \3,plane1(\6),\1,\7
    native_mask_word \4,plane2(\6),\1,\7
    native_mask_word \5,plane3(\6),\1,\7
    not.w \1
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

native_clear_burst macro
    ; A0 advances by one 16-byte line; the source is fixed and in Fast RAM.
    ifne emulated_burst ; a core without MOVE16 writes the same bytes
    rept 4
    move.l (zero_line+16).l,(a0)+
    endr
    else
	mc68040
    move16 (zero_line+16).l,(a0)+
    ifne cpu_68020
	mc68020
    else
	mc68000
    endc
    endc
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
