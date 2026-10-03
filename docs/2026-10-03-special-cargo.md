# Special Cargo

Implemented independently in the enhanced Atari ST and Amiga builds. The preserved original build is unchanged.

## Player flow

On the Buy screen, click the blue **Buy** heading to switch to **Special Cargo**. Click **Special** to return to ordinary commodities. The bottom Buy button also returns to ordinary commodities.

With no active contract, Special Cargo lists up to 15 destinations and their entry fees in credits. One mouse click on a row pays its fee and accepts that contract. Insufficient cash leaves the contract and cash unchanged. An empty list displays **No contracts**.

After acceptance, the screen shows the destination and current delivery value. Reopening Special Cargo displays these details without charging again. Status shows `Cargo:<destination> <value> CR` below Cash, with a magenta label and white destination and value. It is drawn after the equipment graphics so the information remains readable. Only one contract can be active.

The entry fee shown in the offer list is not the delivery reward. Both are calculated using Elite Unbound's original rules. For example, an entry fee of 636.0 Cr can produce a delivery value of 5090.4 Cr.

On the local or galactic chart, docked or in flight, **W** selects the active contract's destination and displays its name and distance. It does not act during a hyperspace countdown. With no contract, it displays **Docked!** at a station or plays the normal error beep in flight; neither path waits or pauses the game. Outside the charts W only beeps. **V** opens the existing version/credits scroll only in an in-flight 3D cockpit view; on all UI pages, including charts, V only beeps.

## Delivery rules

- Docking at the destination pays the current value once and completes the contract. **Cargo Delivered** then shows the destination and amount paid for up to 96 vertical blanks: approximately 1.92 seconds at 50 Hz or 1.60 seconds at 60 Hz. Normal Status or the original story-mission screen follows.
- A navigation key or bottom-menu click dismisses the receipt immediately. The selected screen opens after the original docking mission dispatcher has run, so the normal Status fallback cannot overwrite it. If a story message or mission decision is due, it is handled first. With no navigation input, the receipt closes automatically.
- Every docking at another system halves the remaining value, rounding down to tenths of a credit. A value reduced to zero expires.
- Launching, ordinary hyperspace jumps without docking, reopening menus and loading a commander do not reduce the value or pay it out.
- Completing a galactic hyperspace jump cancels the contract. Destination coordinates remain available to the offer generator, matching Unbound.
- Special Cargo uses no ordinary hold space. It cannot be sold or jettisoned as a commodity and survives a player-ship purchase.
- The original Unbound legal-status calculation is retained, including eight-bit wraparound when accepting a contract with a legal penalty.

## Reference and implementation

The reference is the local Elite Unbound C64 source, `1-source-files/main-sources/elite-special-cargo.asm`, with its accompanying `game-docs/elite-unbound-missions.md` and `game-docs/special-cargo-port-validation.md` in the sibling `Elite-C64/elite-source-code-commodore-64` project.

Each tree owns an `asm/courier.m68` module. The generator uses a private copy of the galaxy seed; visiting the offer screen never consumes the flight random-number stream. It preserves the reference's byte carries, candidate traversal, 16-bit distance-square overflow, integer square root, and separate entry-fee and reward arithmetic. Inputs include the current system, galaxy, market fluctuation, legal status, score, player hull and previous destination coordinates.

The real docking path calls settlement after setting the docked flag and before the existing `dock_check` story dispatcher. Payment clears the active value before displaying the receipt. Receipt input is polled between vertical blanks; a selected action is consumed once after `dock_check`. Story mission fields, normal cargo and navigation state are separate from the contract. The galactic-jump hook runs only when that jump completes.

Saved commanders remain 256 bytes. An optional eight-byte **SCG1** extension follows the existing SHP1 tail: four-byte tag, unsigned word reward in tenths, and two destination-coordinate bytes. Earlier fields retain their offsets. Old commanders without this tag load with no contract; an active contract with coordinates absent from the current galaxy is discarded. New commanders initialize an empty extension. Transient offer lists and screen state are not saved.

## Validation

The native regression suites run the assembled 68000 code in Hatari and WinUAE, each on a verified separate hidden Windows desktop with private emulator and disk copies.

- `native_special_cargo.py`: 168 scenarios covering independent Unbound-reference offer vectors across all eight galaxies and all 13 player hulls, legal and market edge cases, acceptance, insufficient credits, duplicate clicks, inventory independence, ship purchasing, payment, depreciation, expiry, save/load and old-commander migration.
- `native_special_cargo_ui.py`: 11 scenarios covering the actual mouse dispatcher, Buy/Special switching, all 15 visible rows, the final row's price, details, Status, empty offers, maximum value, delivery receipt and chart targeting. Captured screens are also inspected visually.
- `native_special_cargo_lifecycle.py`: 10 scenarios exercising real docking, launch and hyperspace entry points, including existing story states. Expensive transitions and unrelated world initialization are substituted where needed; settlement and story dispatch remain native.
- `native_special_cargo_input.py`: 48 scenarios covering 25 navigation keys, all 15 bottom icons through native hit testing, ignored flight keys, timer expiry, early keyboard/mouse dismissal, actual docking and ordering with a simultaneous Thargoid mission. Timed-input cases substitute the clock wait to inject events at a precise tick; the mission-order case substitutes the interactive offer after checking the real dispatcher reaches it.
- `native_w_context.py`: 32 W/V keyboard-dispatch scenarios covering docked/in-flight UI pages, both charts with and without contracts, hyperspace countdowns, and all four 3D views. Prompt pixels are compared for the immediate **Docked!** response and unchanged UI. Blocking credits, timed waits and sound playback are intercepted to verify which actions are requested without hanging a failing test.

Additional regression and build results are recorded under each tree's `build/special-cargo-qa` directory.

The complete regression run passes 4,451 native scenarios per platform across 21 suites. Besides the 237 Special Cargo cases, these cover player ships, AI systems and loadouts, laser bursts and impact audio, mission spawn paths, Thargoids and Thargons, death cargo, missile collisions and explosions, shield flashes, Worm shields, hull balance, flight, ship graphics, missile indicators, identification and model drawing bounds. Python discovery passes 34 tests per tree, with one existing artwork-identity check skipped for the selected alternate graphics.

The build matrix passes both Atari artwork variants and 18 Amiga variants: both artwork sets, framed PAL, and the eight wide display modes with the appropriate 68000 or 68020 target. The user's original build options are restored after the matrix.

During visual QA, the isolated WinUAE setup sometimes displayed incomplete existing Status fields. This was also reproduced by booting the preserved pre-Special-Cargo ADF from `build/ai-burst-qa/boot/game.adf`, with its original variable layout. It therefore predates this feature; its rendering cause remains unresolved. Comparison captures are in `build/special-cargo-before/boot`, and ordinary keyboard-driven checks of the new Cargo line are in `build/special-cargo-live/boot`. An alignment mismatch in the temporary QA helper was corrected separately. Neither diagnostic modification changes the distributed game.
