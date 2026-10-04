# Title screen draw order

A fix, not a feature: on the attract screen the rotating ship was drawn over
both captions instead of behind them. Applies to `src_atari` and `src_amiga`.
`src_orig` keeps the original order, as it keeps every other 1988 behaviour.

## 1. Symptom

The attract screen shows one ship at a time, turning and drifting towards the
viewer, with the ship's name across the top row in orange and `Load new
commander ?` across the bottom in light blue. Both captions were cut into by
the ship's wireframe whenever it crossed them, which it does on every large
ship as it comes forward: the lines were drawn through the glyphs, leaving the
text broken and hard to read against the model.

## 2. Root cause

`clear_image`, `text_blatt` and `draw_all` all write straight into the
invisible screen, so the last writer to touch a pixel owns it. The per-frame
loop in `attract` (`attract.m68`) ran in this order:

    jsr clear_image
    ...
    jsr text_blatt      ; the ship's name, row 0
    ...
    jsr text_blatt      ; "Load new commander ?", the last row
    jsr get_range
    jsr draw_object     ; adds the ship to the depth-sorted draw list
    jsr draw_all        ; and renders that list
    jsr update_inst
    jsr swap_screen

The captions were blatted first and the ship rendered on top of them. This is
the 1988 order -- both trees matched `src_orig` exactly here, so the fault is
original and not something the conversion introduced.

`draw_object` only inserts the object into the draw list; `draw_all` is what
puts lines on the screen, so the pair has to be considered together.

## 3. The fix

Draw the ship first and the captions last, so the glyphs are the last thing
written and the model passes behind them:

    jsr clear_image
    jsr get_range
    jsr draw_object
    q_push.l a5         ; DRAW_ALL takes A5 from the draw list
    jsr draw_all
    q_pop.l a5
    ...                 ; both captions, unchanged
    jsr update_inst
    jsr swap_screen

Three details make this more than moving two lines:

- **The captions move as pairs.** `disp_message` fills the single shared
  `text_buffer` and `text_blatt` prints it immediately, so the second
  `disp_message` overwrites what the first one left. Each `disp_message` has to
  travel with its own `text_blatt`, which is why the whole block moves rather
  than just the two `text_blatt` calls.
- **A5 has to be saved.** The ship's name is read with `move.l text(a5),a0`,
  and `draw_all` does `move.l obj_ptr(a0),a5` for every record it renders. In
  the attract screen there happens to be only one object, so A5 would survive
  by luck; `q_push.l`/`q_pop.l` makes it survive by construction.
- **`update_inst` stays last.** It paints the dashboard, which lies outside the
  view window, so it neither covers the captions nor is covered by them. It is
  left where it was.

## 4. Scope

`tumble_letters`, the other loop in `attract.m68` that calls `clear_image` and
`draw_all`, blats no text and is untouched. The in-flight view is untouched:
its ordering lives in `game_logic`, where messages are drawn after the world
already.

## 5. Testing

There is no automated test. The attract screen is a rendering loop with no
observable state to assert on, and the module has never had a harness. The
change is covered by both trees still assembling and linking, by both suites
still passing unchanged, and by the loop reading identically in the two trees.
