# Ship registrations

This version adapts the registration concept from the companion Elite C64
project. Its own `asm/registration.m68` handles allocation, formatting, Status
and commander compatibility. No source imports from the Atari or C64 tree
are used.

## Visible behaviour

* `I` identifies a ship under the fixed crosshair as `Type AA-123`, including
  views without a fitted laser. An identification request takes precedence
  over the simultaneous missile-lock message; missile acquisition still occurs.
* Existing pirate classification (`ship_type == typ_pirate`) conceals the
  suffix as `??-???`. Anger or an attack on the player does not conceal a
  trader's or police ship's registration.
* Thargoids also conceal their registration, matching the pirate identity bit
  in the companion C64 project's `elite-data.asm` blueprint table. The same
  concealment also applies to Thargons (Tharglets), as requested for this port.
  The Constrictor displays its ID, matching its C64 blueprint's hostile-only
  flags. These display rules do not change `typ_alien` or combat logic.
* Stations use `C` for `spacestn`, `D` for the alien `dodec`, galaxy 1..8 and
  system index 000..255. Lave is `C1-007`. The actual station model determines
  the prefix, rather than importing C64 technology-level rules.
* AI ships, including Thargons, receive registrations. Missiles, cargo,
  asteroids, escape capsules and non-ship graphics keep type-only labels.
* The player's Status row shows `Registration: JS-042` initially, for both
  normal and max commanders. A successful escape assigns the replacement
  hull a new ID; the abandoned Cobra retains the old one. Failed escapes do
  not change identity.

## Storage and generator

`registration_id` adds four bytes before `nodes` in each object record:
two ASCII letters, a number 1..255 and a zero padding byte. Zero denotes an
unregistered object. Keeping the whole ID avoids changes when system or market
variables change. The model header, starting at `nodes`, retains its original
48-byte layout and asset format. `create_object` assigns or clears the field
after copying the model header, including when an object was copied from a
parent. Allocation and removal retain their existing slot handling.

A private eight-bit LFSR uses feedback `$B8` and cycles through 255 nonzero
states. It seeds itself from galaxy/system/market fields, with `$A5` as the
nonzero fallback. Letters also mix these fields. A candidate number already
used by a live ship or the player is skipped. With 30 object slots, the search
always terminates. Retired IDs may eventually be reused; this is a local ship
identity, not a galaxy-wide registry. Displaying an ID never advances the
generator, and registration code never reads or advances the gameplay RNG.

Message formatting reserves at most 25 name characters and seven suffix
characters in a 34-byte buffer. It then uses the existing message snapshot
and centring routine. Actual ship/station names fit without truncation.
Status uses columns 0 and 14 at y=74, between Cash and the forward-laser label.
There are no writes to executable code; public registration helpers preserve
all data/address registers (condition codes are scratch).

## Commander compatibility

The file size and existing serialized fields are unchanged. `disk.var_list`
appends one four-word entry after the original 178-byte payload:

| File offset, before scrambling | Contents |
| --- | --- |
| 178..181 | ASCII `RID1` version tag |
| 182..183 | Two uppercase ASCII letters |
| 184 | Binary registration number, 1..255 |
| 185 | Zero padding |
| 186..255 | Remaining unused tail |

The normal XOR scrambling still processes all 256 bytes. Restore validates
the tag, letters, number and padding. Missing/invalid extensions become
`JS-042`, without modifying any original commander fields. The extension is
written on the next save, and RAM save/restore uses the same routines.

## Validation

`tests/test_registration.py` executes the real MC68000 routines with optional
`unicorn==2.1.4`. It covers default/max commanders, generator period and RNG
isolation, a full object array, slot reuse and copying, type eligibility,
pirate masking, station formatting, message bounds, no-laser identification,
missile lock priority, successful/failed escapes, Status coordinates and
256-byte save/scramble/restore including legacy tails. Register preservation
and read-only executable memory are checked on MC68000 and MC68020 models.
OS file I/O, audio and UI drawing are stubbed in these focused tests.

Build normally with `build_amiga.bat`. For CPU tests, run
`python -m unittest discover -s src_amiga/tests -p test_registration.py -v`
with Unicorn available. Visual gameplay on an emulator or physical machine
remains a separate check.
