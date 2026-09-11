# Mission 5 completion

The alien Dodecahedron station must be destroyed before normal hyperspace
is available. The mission follows `$50` (briefing pending), `$51` (briefed),
`$52` (alien system), `$53` (station destroyed), then zero after docking at
a normal station and receiving the ECM jammer. `next_mission` remains 6.

The inherited code advanced this objective only in `combat.check_hit`.
A missile impact or fatal collision called `explode_object` directly,
leaving an exploded station with mission `$52` and a blocked hyperdrive.

`combat.explode_object` now advances `$52` to `$53` and sets
`station_destroyed` when a Dodecahedron first starts exploding. Its existing
register save covers this check. Other types, inactive mission states and
already exploding objects do not advance the objective. The old station
transition has been removed from `check_hit` to avoid counting a laser kill
twice. Constrictor mission handling remains in its original laser-hit path.

Damage, health, score, bounty handling, fragments, RNG and object record
layout are unchanged. The station starts with 1024 health. Energy Bomb still
skips the three reserved planet/station/sun records in normal space; it does
not destroy this station or complete the mission. A subsequent system reset
clears `station_destroyed` while retaining `$53` until the reward is received.

The station's IFF label is `Alien Space Station ??-???`; its hidden
registration does not alter mission or object data. See [registration notes](REGISTRATION.md).

## Validation

`tests/test_missions.py` assembles this tree's routines and model sources and
runs them on MC68000 and MC68020 using optional `unicorn==2.1.4`. It covers all
four lasers, missile arrival with sparse/partial/full object pools, a fatal
collision, Energy Bomb, repeat calls, other mission states and object types,
Constrictor progression, normal-station immunity, registers, the next-system
reset and a single reward. Executable test memory is read-only.

Rendering/audio, missile travel, fragment directions, cargo release and
player shield damage are stubbed. These tests are not a full playthrough in
an emulator or on hardware. Registration tests separately check masking,
RNG isolation, object/register preservation and existing IFF/missile behaviour.

The preserved `src_orig` version retains its historical gameplay.
