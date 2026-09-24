; Fixed sprite row loops, instantiated with ROR or ROL at assembly time.
; No runtime code writes or cache maintenance; the shift count stays <= 8.
; Macro-local labels allow both variants to share the same source.
; Each screen word is read once, saved, masked, coloured and written once.
; D7 holds the screen bits the sprite keeps, so the row count is on the stack.

sprite_word macro
	; Plane offset, save buffer offset, plane data register.
	move.w \1(a0),d4 ; fetch screen word
	move.w d4,\2(a2) ; save it
	and.w d7,d4 ; clear the sprite pixels
	or.w \3,d4 ; draw them
	move.w d4,\1(a0) ; store screen word
	endm

sprite_rows_start macro
	move.l a5,-(sp) ; callers keep their object pointer in A5
	move.w #8,a5 ; save buffer step per word
	btst #dont_save,sp_flags(a4) ; don't save the background ?
	beq.s spr_saving\@
	lea spr_scratch(a6),a2 ; yes, the saves land in scratch
	sub.l a5,a5
spr_saving\@:
	move.w d7,-(sp) ; rows left
	endm

native_unclipped_rows macro
	sprite_rows_start
spr_row\@:
	q_push.l a0 ; save screen address
	move d2,mask(a6) ; initialise shift in variables
	clr.l pl_0(a6)
	clr.l pl_2(a6)
	move sp_width(a4),d6 ; loop for each word across
spr_word\@:
	move (a1)+,d3 ; get mask and rotate
	\1 d0,d3
	move d3,d4 ; save shift out
	and d1,d3 ; extract rotated bits
	or mask(a6),d3 ; combine with shift in
	move d3,d7 ; screen bits to keep
	and d2,d4 ; extract shift out
	move d4,mask(a6)
	move.l pl_0(a6),d5 ; get shift in bits (planes #0 & #1)
	swap d5
	move (a1)+,d3 ; draw sprite in plane #0
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	and d2,d4
	move d4,d5
	sprite_word 0,0,d3
	swap d5 ; draw sprite in plane #1
	move (a1)+,d3
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	and d2,d4
	move d4,d5
	move.l d5,pl_0(a6) ; save shift out bits
	sprite_word plane1,2,d3
	move.l pl_2(a6),d5 ; get shift in bits (planes #2 & #3)
	swap d5
	move (a1)+,d3 ; draw sprite in plane #2
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	and d2,d4
	move d4,d5
	sprite_word plane2,4,d3
	swap d5 ; draw sprite in plane #3
	move (a1)+,d3
	\1 d0,d3
	move d3,d4
	and d1,d3
	or d5,d3
	and d2,d4
	move d4,d5
	move.l d5,pl_2(a6) ; save shift out bits
	sprite_word plane3,6,d3
	addq.l #2,a0
	add.l a5,a2
	dbra d6,spr_word\@
	tst d0 ; any rotations ?
; Quelo: 		if <ne> then.s					yes
	beq q_sprites_m68_13\@
	move mask(a6),d7 ; get mask
	or d1,d7
	move pl_0(a6),d3
	sprite_word 0,0,d3
	move pl_1(a6),d3
	sprite_word plane1,2,d3
	move pl_2(a6),d3
	sprite_word plane2,4,d3
	move pl_3(a6),d3
	sprite_word plane3,6,d3
	add.l a5,a2
q_sprites_m68_13\@:
	q_pop.l a0 ; next pixel line
	add a3,a0
	subq.w #1,(sp)
	bpl spr_row\@
	addq.l #2,sp
	move.l (sp)+,a5
	tst d0 ; rotations performed ?
; Quelo: 	if <ne> then.s						yes
	beq q_sprites_m68_15\@
	q_inc sp_width(a4) ; extra word stored
q_sprites_m68_15\@:

	q_ret
	endm

native_clipped_rows macro
	sprite_rows_start
spr_row\@:
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
	clr d6 ; start with word #0
q_sprites_m68_33\@:
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
	move d3,d7 ; screen bits to keep
	and d2,d4 ; extract shift out
	move d4,mask(a6)
	move (a1)+,d3 ; draw sprite in plane #0
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_0(a6),d3
	and d5,d3
	and d2,d4
	move d4,pl_0(a6)
	sprite_word 0,0,d3
	move (a1)+,d3 ; draw sprite in plane #1
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_1(a6),d3
	and d5,d3
	and d2,d4
	move d4,pl_1(a6)
	sprite_word plane1,2,d3
	move (a1)+,d3 ; draw sprite in plane #2
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_2(a6),d3
	and d5,d3
	and d2,d4
	move d4,pl_2(a6)
	sprite_word plane2,4,d3
	move (a1)+,d3 ; draw sprite in plane #3
	\1 d0,d3
	move d3,d4
	and d1,d3
	or pl_3(a6),d3
	and d5,d3
	and d2,d4
	move d4,pl_3(a6)
	sprite_word plane3,6,d3
	addq.l #2,a0
	bra q_sprites_m68_36\@
q_sprites_m68_35\@:
	move mask(a6),d7 ; get mask
	or d1,d7
	or r_mask1(a6),d7
	move r_mask2(a6),d5 ; get data mask
	move pl_0(a6),d3 ; draw sprite in plane #0
	and d5,d3
	sprite_word 0,0,d3
	move pl_1(a6),d3 ; draw sprite in plane #1
	and d5,d3
	sprite_word plane1,2,d3
	move pl_2(a6),d3 ; draw sprite in plane #2
	and d5,d3
	sprite_word plane2,4,d3
	move pl_3(a6),d3 ; draw sprite in plane #3
	and d5,d3
	sprite_word plane3,6,d3
	addq.l #2,a0
q_sprites_m68_36\@:
	add.l a5,a2
	q_inc d6 ; next word
	cmp sp_width(a4),d6
	bls q_sprites_m68_33\@
	movem.l (sp)+,a0/a1 ; next pixel line
	add a3,a0
	add.l data_width(a6),a1
	subq.w #1,(sp)
	bpl spr_row\@
	addq.l #2,sp
	move.l (sp)+,a5

	q_ret
	endm
