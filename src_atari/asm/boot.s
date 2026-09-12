; TOS launcher. Keep the game inside this process's TPA, above resident drivers.
; Move the linked image in multiples of 32 KB to preserve screen alignment.
    include "boot-config.inc"
    section text,code

startup_stack equ 4096

start:
    move.l 4(sp),a6              ; GEMDOS basepage
    move.l 4(a6),d6              ; exclusive end of this process's TPA
    and.l #$fffffffe,d6
    lea launcher_end(pc),a0
    move.l a0,d7
    sub.l #loader_address,d7
    bcc.s align_game
    moveq #0,d7
    bra.s game_positioned
align_game:
    add.l #$7fff,d7
    and.l #$ffff8000,d7          ; nonnegative relocation delta
game_positioned:
    move.l #game_address,a5
    adda.l d7,a5                 ; game entry / base, preserved by the loader
    move.l #required_ram,d4
    add.l d7,d4                  ; exclusive end of game workspace
    bcs memory_error
    move.l d6,d0
    sub.l #startup_stack,d0
    bcs memory_error
    cmp.l d0,d4
    bhi memory_error

    move.w #2,-(sp)              ; Physbase
    trap #14
    addq.l #2,sp
    move.l d0,a3
    and.l #$7fff,d0
    bne.s reserve_screen
    move.l a3,d0
    add.l #32768,d0
    cmp.l (a6),d0
    bls.s screen_ready           ; existing system screen below this TPA
    cmpa.l 4(a6),a3
    bhs.s screen_ready           ; usual system screen above this TPA
reserve_screen:
    move.l d6,d0
    sub.l #startup_stack+32768,d0
    bcs memory_error
    and.l #$ffff8000,d0
    cmp.l d4,d0
    blo memory_error
    move.l d0,a3                 ; private aligned primary screen
screen_ready:
    move.l d6,sp
    suba.l #16,sp                ; bootstrap stack, disjoint from game/screens

    ifd auto_start
    pea root_path(pc)
    move.w #$3b,-(sp)            ; AUTO data stays in the boot drive root
    trap #1
    addq.l #6,sp
    tst.l d0
    bmi load_error
    endif

    clr.w -(sp)
    pea loader_name(pc)
    move.w #$3d,-(sp)            ; Fopen(name, read-only)
    trap #1
    addq.l #8,sp
    tst.l d0
    bmi load_error
    move.w d0,d7
    move.l a5,d0
    sub.l #game_address-loader_address,d0
    move.l d0,-(sp)
    move.l #loader_size,-(sp)
    move.w d7,-(sp)
    move.w #$3f,-(sp)            ; Fread(handle, size, relocated loader)
    trap #1
    lea 12(sp),sp
    move.l d0,d6
    move.w d7,-(sp)
    move.w #$3e,-(sp)
    trap #1
    addq.l #4,sp
    cmp.l #loader_size,d6
    bne load_error
    lea finish_load(pc),a4       ; callback after ELITE.IMG has been read
    move.l a5,a0
    suba.l #game_address-loader_address,a0
    jmp (a0)

finish_load:
    cmp.l #game_size,d0
    bne load_error
    ifne patch_checksum
    bsr sum_game
    move.w d0,d4                ; preserve the on-disk protected-region sum
    endif
    move.l a5,d5
    sub.l #game_address,d5
    lea relocation_table(pc),a0
    lea relocation_end(pc),a2
    move.l a5,a1
relocate_next:
    cmpa.l a2,a0
    bhs.s relocation_done
    moveq #0,d0
    move.b (a0)+,d0
    bne.s relocate_address
    moveq #3,d1                 ; extended distance can start at an odd address
relocate_long:
    lsl.l #8,d0
    move.b (a0)+,d0
    dbra d1,relocate_long
relocate_address:
    adda.l d0,a1
    add.l d5,(a1)
    bra.s relocate_next
relocation_done:
    ifne patch_checksum
    bsr sum_game
    sub.w d4,d0
    move.l a5,a0
    adda.l #checksum_patch_offset,a0
    add.w d0,(a0)               ; adjust only relocation's contribution
    endif
    rts

    ifne patch_checksum
sum_game:
    move.l a5,a0
    adda.l #checksum_start_offset,a0
    move.l #checksum_length,d1
    moveq #0,d0
    moveq #0,d2
sum_byte:
    move.b (a0)+,d2
    add.w d2,d0
    subq.l #1,d1
    bne.s sum_byte
    rts
    endif

memory_error:
    pea memory_message(pc)
    bra.s show_error
load_error:
    pea load_message(pc)
show_error:
    move.w #9,-(sp)              ; Cconws, NUL-terminated
    trap #1
    addq.l #6,sp
    move.w #7,-(sp)              ; Crawcin
    trap #1
    addq.l #2,sp
    move.w #1,-(sp)
    move.w #$4c,-(sp)            ; Pterm(1)
    trap #1

    ifd auto_start
root_path: dc.b 92,0
    endif
loader_name: dc.b 'LOADER.IMG',0
memory_message:
    dc.b 'Not enough free ST RAM for Elite.',13,10
    dc.b 'Free memory must include the game,',13,10
    dc.b 'screen buffers and startup stack.',13,10
    dc.b 'Press a key.',13,10,0
load_message:
    dc.b 'Cannot read the Elite game files.',13,10
    ifd auto_start
    dc.b 'Keep all game data in the root',13,10
    dc.b 'of the boot disk. Press a key.',13,10,0
    else
    dc.b 'Keep ELITE.TOS and all game files',13,10
    dc.b 'in the same directory. Press a key.',13,10,0
    endif
relocation_table:
    incbin "game-relocations.bin"
relocation_end:
    even
launcher_end: