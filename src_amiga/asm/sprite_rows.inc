; Fixed sprite row loops, instantiated with ROR or ROL at assembly time.
; No runtime code writes or cache maintenance; the shift count stays <= 8.
; Macro-local labels allow both variants to share the same source.

native_unclipped_rows macro
	q_loop 1 ; loop for each pixel line
	q_push.l a0 ; save screen address
	move d2,mask(a6) ; initialise shift in variables
	clr.l pl_0(a6)
	clr.l pl_2(a6)
	btst #dont_save,sp_flags(a4) ; don't save the background ?
; Quelo: 		if <ne> then.s					yes
	beq q_sprites_m68_11\@
; No save-buffer writes for a sprite with dont_save set.
q_sprites_m68_11\@:
	move sp_width(a4),d6 ; loop for each word across
	q_loop 2
	native_sprite_save
	move (a1)+,d3 ; get mask and rotate
	\1 d0,d3
	move d3,d4 ; save shift out
	and d1,d3 ; extract rotated bits
	or mask(a6),d3 ; combine with shift in
	and d3,0(a0) ; clear current setting
	and d3,40(a0)
	and d3,80(a0)
	and d3,120(a0)
	and d2,d4 ; extract shift out
	move d4,mask(a6)
	move.l pl_0(a6),d5 ; get shift in bits (planes #0 & #1)
	swap d5
	move (a1)+,d3 ; draw sprite in plane #0
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	or d3,0(a0)
	and d2,d4
	move d4,d5
	swap d5 ; draw sprite in plane #1
	move (a1)+,d3
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	or d3,40(a0)
	and d2,d4
	move d4,d5
	move.l d5,pl_0(a6) ; save shift out bits
	move.l pl_2(a6),d5 ; get shift in bits (planes #2 & #3)
	swap d5
	move (a1)+,d3 ; draw sprite in plane #2
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	or d3,80(a0)
	and d2,d4
	move d4,d5
	swap d5 ; draw sprite in plane #3
	move (a1)+,d3
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	or d3,120(a0)
	addq.l #2,a0
	and d2,d4
	move d4,d5
	move.l d5,pl_2(a6) ; save shift out bits
	q_next 2,d6
	tst d0 ; any rotations ?
; Quelo: 		if <ne> then.s					yes
	beq q_sprites_m68_13\@
	move mask(a6),d3 ; get mask
	or d1,d3
	native_sprite_save
	and d3,0(a0)
	move pl_0(a6),d4
	or d4,0(a0)
	and d3,40(a0)
	move pl_1(a6),d4
	or d4,40(a0)
	and d3,80(a0)
	move pl_2(a6),d4
	or d4,80(a0)
	and d3,120(a0)
	move pl_3(a6),d4
	or d4,120(a0)
q_sprites_m68_13\@:
	q_pop.l a0 ; next pixel line
	add a3,a0
	q_next 1
	tst d0 ; rotations performed ?
; Quelo: 	if <ne> then.s						yes
	beq q_sprites_m68_15\@
	q_inc sp_width(a4) ; extra word stored
q_sprites_m68_15\@:

	q_ret
	endm

native_clipped_rows macro
	q_loop 1 ; loop for each pixel line
	movem.l a0/a1,-(sp) ; save screen and data pointers
	move d2,mask(a6) ; initialise shift in variables
	tst pre_rotate(a6) ; pre-rotation required ?
; Quelo: 		if <eq> then.s					no
	bne q_sprites_m68_29\@
	clr.l pl_0(a6)
	clr.l pl_2(a6)
	bra q_sprites_m68_30\@
q_sprites_m68_29\@:
	move (a1)+,d3 ; fetch pre-rotation bits
	\1 d0,d3
	and d2,d3
	move d3,mask(a6)
	move (a1)+,d3
	\1 d0,d3
	and d2,d3
	move d3,pl_0(a6)
	move (a1)+,d3
	\1 d0,d3
	and d2,d3
	move d3,pl_1(a6)
	move (a1)+,d3
	\1 d0,d3
	and d2,d3
	move d3,pl_2(a6)
	move (a1)+,d3
	\1 d0,d3
	and d2,d3
	move d3,pl_3(a6)
q_sprites_m68_30\@:
	btst #dont_save,sp_flags(a4) ; don't save the background ?
; Quelo: 		if <ne> then.s					yes
	beq q_sprites_m68_31\@
; No save-buffer writes for a sprite with dont_save set.
q_sprites_m68_31\@:
	clr d6 ; start with word #0
q_sprites_m68_33\@:
	native_sprite_save
	cmp max_data(a6),d6 ; any data left ?
; Quelo: 			if <le> then				yes
	bgt q_sprites_m68_35\@
	move (a1)+,d3 ; get mask and rotate
	\1 d0,d3
	move d3,d4 ; save shift out
	and d1,d3 ; extract rotated bits
	or mask(a6),d3 ; combine with shift in
	moveq #-1,d5 ; assume no extra mask
	tst d6 ; first word ?
; Quelo: 				if <eq> then.s			yes
	bne q_sprites_m68_37\@
	or l_mask1(a6),d3 ; OR mask with left edge mask
	and l_mask2(a6),d5 ; AND mask with data mask
q_sprites_m68_37\@:
	cmp sp_width(a4),d6 ; last word ?
; Quelo: 				if <eq> then.s			yes
	bne q_sprites_m68_39\@
	or r_mask1(a6),d3 ; OR mask with right edge mask
	and r_mask2(a6),d5 ; AND mask with data mask
q_sprites_m68_39\@:
	and d3,0(a0) ; clear current setting
	and d3,40(a0)
	and d3,80(a0)
	and d3,120(a0)
	and d2,d4 ; extract shift out
	move d4,mask(a6)
	move (a1)+,d3 ; draw sprite in plane #0
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_0(a6),d3
	and d5,d3
	or d3,0(a0)
	and d2,d4
	move d4,pl_0(a6)
	move (a1)+,d3 ; draw sprite in plane #1
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_1(a6),d3
	and d5,d3
	or d3,40(a0)
	and d2,d4
	move d4,pl_1(a6)
	move (a1)+,d3 ; draw sprite in plane #2
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_2(a6),d3
	and d5,d3
	or d3,80(a0)
	and d2,d4
	move d4,pl_2(a6)
	move (a1)+,d3 ; draw sprite in plane #3
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_3(a6),d3
	and d5,d3
	or d3,120(a0)
	addq.l #2,a0
	and d2,d4
	move d4,pl_3(a6)
	bra q_sprites_m68_36\@
q_sprites_m68_35\@:
	move mask(a6),d4 ; get mask
	or d1,d4
	or r_mask1(a6),d4
	move r_mask2(a6),d5 ; get data mask
	move pl_0(a6),d3 ; draw sprite in plane #0
	and d5,d3
	and d4,0(a0)
	or d3,0(a0)
	move pl_1(a6),d3 ; draw sprite in plane #1
	and d5,d3
	and d4,40(a0)
	or d3,40(a0)
	move pl_2(a6),d3 ; draw sprite in plane #2
	and d5,d3
	and d4,80(a0)
	or d3,80(a0)
	move pl_3(a6),d3 ; draw sprite in plane #3
	and d5,d3
	and d4,120(a0)
	or d3,120(a0)
	addq.l #2,a0
q_sprites_m68_36\@:
	q_inc d6 ; next word
	cmp sp_width(a4),d6
	bls q_sprites_m68_33\@
q_sprites_m68_34\@:
	movem.l (sp)+,a0/a1 ; next pixel line
	add a3,a0
	add.l data_width(a6),a1
	q_next 1

	q_ret
	endm
