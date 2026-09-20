# Jettison cargo

During flight, double-click an item on **Cargo Hold Inventory** to offer up to one tonne for ejection, or the entire remaining amount when less is held. The prompt shows the exact amount using whole tonnes, whole kilograms or grams without rounding. The existing confirmation panel accepts its YES/NO buttons, `Y`/`N`, or `Esc` to cancel. Single-click still shows the item's description and value. Docked inventory and selling retain their original behaviour.

All 18 ordinary commodities qualify, regardless of market unit. **Minerals, Gold and Platinum use kilograms**, and Gem-Stones use grams; Food through Furs, Alien Items and Medical Supplies use tonnes. Each canister carries `min(held grams, 1,000,000)` of one commodity. For example, 300 kg produces a 300 kg canister, 1,500 kg produces a 1 t canister and leaves 500 kg, and 157 g produces a 157 g canister. Refugees and Thargoid documents remain excluded mission cargo. Empty entries cannot be ejected.

One successful confirmation creates one ordinary Cargo Canister 400 world units behind the player, using the existing tumbling logic and model. Each ejected canister receives a random rearward direction within 35.3 degrees of straight aft and a speed of 3�6 world units per movement step. Its individual maximum speed is set to the same value, so cruise logic does not accelerate it to the ordinary canister speed of 11. Each canister also starts at a random roll angle around its own flight axis, instead of sharing the same initial spin phase. This one-time orientation change leaves the rearward direction, speed and payload unchanged. The normalized orientation basis preserves the model shape while it spins. This is outside the canister's 150-unit player collision radius. The hold loses exactly the canister payload only after allocation and object creation succeed. A full 30-object bubble rejects the request without changing cargo or legal status. Slots awaiting deferred removal remain occupied until the normal removal pass.

The success signal reuses the short missile-lock beep; failure uses the existing error sound. Both follow the Effects setting. With Fuel Scoops and enough free hold space, the ejected canister can be collected for its exact original mass and commodity. The entire payload must fit; insufficient space does not transfer part of the cargo or discard a remainder. Ordinary salvage provides 1 t for tonne commodities, a random 1-10 kg for kilogram commodities, or a random 1-10 g for gram commodities. The quantity is chosen when scooped and limited by the remaining hold space in whole commodity units. These salvage limits do not alter the exact contents of player-ejected canisters.

The Jettison confirmation is non-blocking: flight, AI attacks and normal game
timing continue while it is open. Only Y/N, Escape and the YES/NO mouse buttons
are accepted during confirmation. The selected commodity is retained, and its
current quantity and the available object slots are checked again on YES.
If the cargo is no longer valid, YES rejects the request with the existing error
sound. Y and N are consumed by the dialog, so Y does not toggle cloaking.
Docking, hyperspace and death close the dialog when changing screens. Other
confirmation dialogs keep their existing behaviour.

## Legal status

Like C64 Elite Unbound, each successful ejection in the station's protection zone adds 15 legal-status points, except under Anarchy. Outside the zone there is no dumping penalty. Both games use Clean = 0, Offender = 1–49 and Fugitive = 50–255, so no conversion is needed. The addition saturates at 255. Cancelled or failed requests incur no penalty. Scooping has no immediate legal penalty. Each transition from outside into station space (the S zone) inspects the whole current hold: each complete tonne of Firearms adds 2 points, and Slaves or Narcotics add 4 points. This applies under every government and saturates at 255. Remaining inside, returning from flight menus and launching from the station do not repeat the inspection. Travelling at least 512 world units beyond the S boundary rearms the check for the next entry; brief S flicker within that margin does not. The existing purchase penalty and once-per-system police-response check remain unchanged.

## Implementation and verification

`cargo.m68` owns the inventory action and transaction. The displayed commodity indices are retained when drawing the icons, so combat losses cannot shift a later click to a different commodity or send the selection scan beyond the hold. Availability is checked again by the transaction. Successful ejection redraws Inventory, including its empty-hold state.

The object record contains a `cargo_mass` longword before the model header. Zero retains normal salvage; a positive value stores the exact player-ejected payload in grams. This adds two bytes per record compared with the earlier one-tonne marker (62 bytes for the 30 object slots and player record). `create_object` clears this field on every creation, including copies and reused slots; jettison sets it only after the barrel header has been loaded. The model data format, commander save format, object counters and deferred removal order are unchanged.

`bios.m68` exposes `confirm_yn` for the keyboard-enabled confirmation. Existing `confirm` callers keep their mouse-only behaviour. The Amiga copy retains its native input polling and sprite-buffer calculation.

The reference behaviour was checked against `JettisonCargoSpawn`, `JettisonCargoType`, `JettisonCargoPenalty` and the confirmation handler in the local Elite C64 Unbound source. This port uses the existing Inventory mouse interface rather than introducing the C64 keyboard screen.

Native checks used a private 1 MB Atari ST session in Hatari and a private Amiga session in WinUAE. Both exercised in-flight Inventory, cancellation, confirmed 1 t Medical Supplies, 300 kg Gold and 157 g Gem-Stones ejections, the +15 penalty for each, and return to the rear view. Runtime object records retained the exact commodity and gram payload. Diagnostic scripts, screenshots and results for the exact-mass extension are under each source tree's `build/jettison-mass-qa` directory.

The former CPU-emulation tests have been removed. Repeat ejection, cancellation,
recovery, full-hold/full-slot failure and drift/orientation checks in WinUAE
or on original hardware. The native checks above are historical results, not a
new runtime verification of the current build.
