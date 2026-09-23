# Player shipyards on Amiga and Atari ST

The enhanced Amiga and Atari versions support the same 13 player hulls. Each
platform owns its assembly module, PNG importer and tests. The preserved original
version is unchanged. The target for this feature is **1 MB RAM** on both machines;
the standard Amiga configuration is 512 KB Chip RAM plus 512 KB expansion RAM.

## Buying and selling

The edited first menu row opens **Shipyards** between Equip and Galaxy. Single
click selects a hull and shows its full name. Double click purchases it; clicking
Ships again also purchases the selection. Each button shows the full hull price as a centered number without a currency suffix.
The unselected bottom line shows the current hull's trade-in value and cash.
The top menu uses the edited PNG's button rectangles at rows 175 through 181
for both clicks and pressed feedback. The in-flight Front bitmap replaces Launch
at the same origin, (18, 175).
Amiga pressed rectangles scale with the artwork in hires and interlaced modes.

Click the blue **Buy** or **Sell** word in the Equip title to toggle the mode;
**Equipment** retains the normal heading colour. Selling shows installed items and
their resale prices, irrespective of the station's technology level. Laser sales
use the existing mount selector, removing only the chosen laser. A replacement
laser refunds 50% of the old laser's price. Prices retain tenths of a credit.

Hull prices, 60% trade-in values, equipment categories, 50% equipment resale,
economy-dependent offers and the three Anarchy-only ships follow the current
Elite: Unbound source in `Elite-C64/elite-source-code-commodore-64`.

Ordinary equipment, cargo expansion and every laser must be sold before changing
hulls. Cargo, missiles, Naval Energy Unit, ECM Jammer and Cloaking Device transfer
only if the new hull has room. Each mounted laser and installed device uses 1 t;
missiles and cargo expansion use no cargo space. Naval Energy Unit uses 1 t,
regardless of its internal value of 2. Retro rockets count as one device.

A successful exchange adds the old hull's trade-in, deducts the new price, fills
the new fuel tank and assigns a fresh registration. No ordinary equipment is
automatically installed. A failed exchange or equipment replacement preserves
the original cash, hull and equipment. Cargo expansion cannot be sold while the
remaining cargo and devices exceed the base hold. Unique mission rewards cannot
be sold through Equip.

## Initial balance

Speeds and handling scale the existing 68000 Cobra baseline using C64 ratios.
The speed values below are native game units. Roll and pitch limits are tenths
of a degree per update. Hold capacities include the space used by equipment.

| Hull | Price (Cr) | Speed | Fuel (LY) | Roll / pitch | Shield strength | Missiles | Hold / expanded (t) | Laser mounts | Equipment category |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | ---: |
| Cobra Mk III | 100000 | 22 | 7.0 | 40 / 40 | 7 | 4 | 25 / 35 | All four | 0 |
| Adder | 27000 | 19 | 6.0 | 34 / 34 | 4 | 1 | 8 / 12 | Front, rear | 1 |
| Gecko | 32500 | 24 | 7.0 | 40 / 40 | 5 | 2 | 9 / 11 | All four | 1 |
| Moray | 36000 | 20 | 8.0 | 40 / 40 | 6 | 2 | 11 / 15 | All four | 4 |
| Cobra Mk I | 39500 | 20 | 6.0 | 28 / 29 | 5 | 3 | 14 / 20 | All four | 1 |
| Fer-de-Lance | 143500 | 24 | 8.5 | 34 / 34 | 8 | 3 | 9 / 11 | All four | 2 |
| Python | 205000 | 16 | 8.0 | 16 / 17 | 11 | 4 | 106 / 125 | All four | 3 |
| Boa | 240000 | 19 | 9.0 | 22 / 23 | 10 | 6 | 132 / 155 | Front, rear | 3 |
| Anaconda | 400000 | 11 | 10.0 | 16 / 17 | 13 | 16 | 215 / 253 | All four | 3 |
| Asp Mk II | 895000 | 31 | 12.5 | 34 / 34 | 10 | 1 | 6 / 9 | Front | 2 |
| Sidewinder | 20500 | 29 | 5.0 | 41 / 40 | 2 | 1 | 4 / 5 | Front | 4 |
| Krait | 30500 | 24 | 6.0 | 34 / 34 | 3 | 0 | 10 / 12 | Front | 4 |
| Mamba | 37500 | 25 | 6.0 | 40 / 40 | 4 | 2 | 10 / 12 | Front | 4 |

Sidewinder, Krait and Mamba are offered only in Anarchy. The maximum normal offer
counts for economies 0 through 7 are 10, 8, 6, 5, 4, 4, 3, 1. The Anarchy bonuses
are 3, 3, 3, 2, 2, 2, 1, 0. Offer ordering follows Unbound, including its reduced
Anarchy lists for poorer economies.

Shield and energy bank capacities retain the existing Cobra values, with incoming
damage scaled as `round(damage * 7 / hull strength)`. Full shields therefore always
fill the original bars. Fer-de-Lance has one extra recharge grade. The existing
Cobra recharge intervals remain 24 / 15 / 9 ticks for no unit / extra unit / naval
unit; Fer-de-Lance uses 15 / 9 / 7. Laser power is independent of hull. Retro rocket
pricing has no C64 equivalent and retains 8000 Cr in every equipment category.

Player and AI missiles striking AI targets inflict 40 health damage. A standard
Cobra with 72 health survives the first hit. Stations and invincible objects
remain immune. Surviving ships react to the hit; player hits provoke defenders.
Destruction still goes through the existing bounty, mission and cargo logic.

Collisions use the C64 size classes. An object two or more classes larger than
the player is lethal. For other collisions, native damage starts at
`8 + floor(target health / 32)`, preserving 10 for an equal-size Cobra. One class
larger adds 4; one class smaller halves damage; two or more smaller quarters it.
The hull's shielding then scales that result. The colliding ship is destroyed
without a bounty, preventing repeated contacts with the same hull. The existing
Constrictor ram protection and station docking checks remain in place.

Speed, fuel, roll and pitch indicators use the current hull's limits. Autopilot,
fuel purchases, scooping, mission refills and manual controls use the same limits.
Hulls with more than four missile pylons use one state icon and a numeric count
in the original HUD strip. The status equipment list also supports two digits.

## Assets and saved commanders

Both `gfx` and `gfx_alt` must supply `ships.png`, `shipsplanetinfo.png`,
`shipyards.png` and `ship-atlases.json`. The existing bitmap IDs stay unchanged.
Each importer generates a separate masked `SHIPSPRITES.IMG` bank. Atari embeds
that bank directly. Amiga scales and losslessly compresses each tile into
`build/SHIPS_PACKED.IMG`, embeds the compressed bank, and decodes one tile into
a small reusable buffer before drawing. This also keeps hireslace ADFs within
the 880 KB floppy capacity.
The red editing frames never enter the game, and palette index 14 is rejected.
Status and the laser mount dialog use the current hull's status view; planet
data uses its right-facing overhead view; Shipyards uses upward overhead views.

The 256-byte commander record gains an optional `SHP1` tag and 16-bit hull ID
after the existing `RID1` registration extension. Missing or invalid hull tags
load as Cobra Mk III. Derived limits are rebuilt on load; they are not serialized.
Hull limits are also initialized before the attract screen draws any gauges.

## Verification

The native regression scenario generator is retained independently in each
platform's `tests/native_player_ships.py`. It exercises linked 68000 routines for
all hull purchases, cargo and missile boundaries, rejected transactions, laser
replacement and resale, reward transfer, offer lists, resistance, collisions,
missile damage and saved commanders. The image tests compare all 39 exported
sprites and masks with their exact PNG rectangles, including scaled Amiga views.

Runtime checks use private copies of WinUAE and Hatari on separate hidden Windows
desktops. Native scenario reports and captured screens are under each platform's
`build/shipyards-qa`. Standard 1 MB boots, Shipyards, selection, Equip buy/sell,
Anaconda status/planet views and the 16-missile HUD are included.

The final standard builds passed 93 native scenarios on Atari ST and 132 on
Amiga; the additional 39 Amiga scenarios verify every compressed sprite against
its uncompressed bytes. Each platform's Python suite ran 35 tests with one
historical artwork-baseline check skipped for the edited source graphics.
Both normal and alternate artwork distributions build successfully. The Amiga
PAL hireslace build also fits its ADF after sprite compression.
