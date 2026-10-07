# Station farewells and contraband warnings

Both enhanced platforms add twenty station messages while retaining text IDs
0â€“109, the three-entry queue, the seven-second removal interval, the UI timer
pause, receipt audio and the pulsing player recipient ID.

## Departure with a criminal record

After the existing successful player launch, Clean players still receive the
original greeting. Offender and Fugitive players receive a randomly selected
cautionary farewell instead, except in Anarchy, where every player receives the
ordinary greeting. This selection is independent of the cargo, Scramble ID and
docking-clearance policy. Civilian AI ships retain
the original departure set; police Vipers remain excluded.

1. Have a good flight. Do not cause trouble out there.
2. Departure cleared. Stay on the right side of the law.
3. Fly safe, and keep your weapons to yourself.
4. You may leave. Keep out of trouble.
5. Safe travels. We expect better behaviour out there.
6. Departure confirmed. Do not add to your record.
7. Good flight. Leave the other traders in peace.
8. You are clear to depart. Make this a lawful trip.
9. On your way. We will be watching your record.
10. Have a safe journey. Give our patrols no reason to stop you.

## Contraband on entry into station space

When the existing S-entry inspection finds at least one complete tonne of
illegal goods, the station sends one warning addressed to the player. Multiple
illegal commodities produce one message per inspection. Detection still sends a
warning when the legal record is already capped at 255. Purchases do not send
this inspection message. Neither launching nor switching between flight UI and
3D repeats the inspection; the existing cargo checkpoint and its outer 512-unit
hysteresis boundary control rearming after leaving station space.

The warning uses the existing cargo laws, including inspection in Anarchy. It
does not add a second penalty, alter cargo, change police decisions, set a
docking ban or consume/reset the docking-message latch. A close approach can
therefore produce both a cargo warning and the existing clearance or denial.
Mission cargo keeps its existing exclusion from the inspection.

1. Illegal cargo detected. Your offence has been recorded.
2. Contraband found in your hold. Your record has been updated.
3. Cargo scan complete. Illegal goods detected.
4. You are carrying prohibited goods. This has been recorded.
5. Contraband detected. Your legal record has been updated.
6. Our scanners have detected illegal cargo aboard your ship.
7. Prohibited cargo found. This offence is on your record.
8. Illegal goods detected in your hold. Authorities notified.
9. Cargo inspection failed. Contraband has been recorded.
10. Your cargo violates the law. This offence has been logged.

## Shared exclusions and implementation

The Thargoid-controlled mission station, alien station models, absent/destroyed
stations and witch space stay silent. Active Cloaking Device suppresses the
message and beep without consuming cosmetic randomness; it does not change the
existing cargo-inspection penalty. A scrambled player ID remains `??-???`.

The new departure texts occupy IDs 110â€“119 and contraband texts 120â€“129. Both
sets use the existing unbiased ten-way station lottery, independent of gameplay,
spawn and registration randomness. No saved fields, object layouts or additional
cooldown/checkpoint flags are introduced. The platform implementations remain
independent in their respective source trees.

## Verification

`native_station_radio.py` executes the linked 68000 routines for all governments,
legal-status boundaries, hidden IDs, actual launches and mission progression,
all cargo slots, whole-tonne rounding, capped penalties, checkpoint rearming,
UI overflow, docking interactions, caller registers and RNG preservation. Each
new set is also checked for exactly 25 occurrences of each variant in 250 draws.
`native_ai_radio_render.py` covers every new text, including IDs above 127,
visible and hidden recipients, UI suppression, wrapping, mixed queues and
restoration of the caller's drawing state.

Validation completed with **857 native scenarios per platform** on verified
hidden desktops, plus **34 passing Atari Python tests and 35 passing Amiga
Python tests** (one existing artwork-identity skip in each tree). The native
runs include the new 145-case station suite, 128 render comparisons, existing
communications, departures, approaches, docking policy, lifecycle, cloaking,
spawn paths and Scramble ID checks. Standard ELITE and ELITE_ALT were built for
both platforms; no other Amiga variants were rebuilt. Reports, source snapshots
and build logs are in each tree's `build/station-radio-qa` directory.

The Anarchy departure exception was subsequently verified with 190 native
scenarios per platform (145 station-radio and 45 actual-departure cases). The
status/government matrix now requires ordinary farewells in Anarchy for every
legal-status boundary and both visible and hidden IDs. ELITE and ELITE_ALT were
rebuilt for each platform. Follow-up reports are in `build/station-radio-qa/anarchy`.
