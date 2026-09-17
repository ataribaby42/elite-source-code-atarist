# Faction AI Targeting Implementation Plan

**Goal:** Let every combat ship attack the nearest hostile ship of another faction, with the player as one ordinary candidate, instead of always attacking the player.

**Architecture:** The object record's existing `target` pointer gains three meanings: `no_target` (-1), `0` for the player, or a pointer to another object record. A new group of small routines in `combat.m68` classifies ships and picks the nearest hostile candidate once per frame per ship, round robin. `do_attack` in `logic.m68` stops assuming the enemy is at the world origin and works from `target` instead. Damage branches on whether the target is the player or a ship.

**Tech Stack:** Motorola 68000 assembler (vasm `-m68000`, Quelo-derived macros in `asm/macros.m68`), Python 3 + `unicorn==2.1.4` for unit tests.

**Spec:** `docs/2026-09-17-faction-ai-targeting-design.md`

**Status:** executed. This file is the record of the plan as it was carried
out, and its code listings are that snapshot, not the current source. Several
behaviours were changed afterwards on play testing -- `npc_damage` is 5 here
and 3 in the tree, and the missile, Thargon, provocation and police-launch
rules all moved. The spec's body is the current statement of behaviour and its
final section lists every amendment with its reason; read that, not this, to
learn how the game behaves today.

## Global Constraints

- **Git is the user's job.** Per `AGENTS.md`: "The user handles all Git operations exclusively. Do not run any Git commands." No task commits, stages, branches or inspects git. Each task ends by reporting the changed files so the user can commit.
- **Documentation is English.** Per `AGENTS.md`, all project documentation is written in English.
- **Two trees, no sharing.** Gameplay changes go into `src_atari` and `src_amiga` separately. Do not add platform switches or cross-tree imports. `src_orig` is never touched.
- **Tasks 1-9 change `src_atari` only.** Task 10 ports the finished, tested result to `src_amiga`. Tasks 11 onwards are follow-ups, each applied to both trees and each already done.
- **Build from the repository root:** `build_atari.bat`, `build_amiga.bat`.
- **Run tests from the repository root:** `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
- **No loose files in the project root.** Intermediate output belongs in the tree's `build` directory.
- **Assembler style:** new routines use `q_subr`, plain `rts` and `.local` labels, matching the existing `ai_laser_aim` and `laser_in_sights`. A routine that returns condition codes must keep a single exit and end with `q_ret`, because `q_ret` redefines the shared `return` label.
- **Existing behaviour against the player is bit-for-bit unchanged.** Any test in `tests/test_lasers.py` that fails is a regression, not an expected update.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `src_atari/asm/common.def` | Type-range and `no_target` constants, three new globals |
| `src_atari/asm/combat.m68` | Faction classification, distance ranking, target selection, NPC damage, kill bookkeeping guard, missile gate |
| `src_atari/asm/logic.m68` | Target coordinates and validation, generalised attack logic and aiming |
| `src_atari/asm/main.m68` | `target` initialisation, round-robin cursor |
| `src_atari/asm/special.m68` | Ship-to-ship beam drawing |
| `src_atari/tests/test_faction_ai.py` | The whole suite for this feature |

---

### Task 1: Faction classification

**Files:**
- Modify: `src_atari/asm/common.def` (near the object type block, `common.def:280`)
- Modify: `src_atari/asm/combat.m68` (new routines before `q_subr explode_object`)
- Create: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `first_combat: equ cobra`, `last_combat: equ transporter` in `common.def`
  - `is_combat_ship` — entry `A4` = object record; exit `D0.W` = 1 when the object takes part in faction targeting, 0 otherwise, Z set when 0. Corrupts `D0` only.
  - `is_hostile` — entry `A5` = hunter, `A4` = candidate; exit `D0.W` = 1 when hostile, Z set when 0. Corrupts `D0`, `D1`, `D2`, `A0`.

- [ ] **Step 1: Write the failing test**

Create `src_atari/tests/test_faction_ai.py`:

```python
"""Faction AI targeting on MC68000/MC68020.

The real routines are assembled out of asm/ with vasm and executed under
Unicorn. World services the game would normally provide are stubbed.
Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_raster import routine
from test_viewport import assemble, preamble

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE,
                         UC_PROT_READ, UC_PROT_EXEC)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7,
        UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

CODE, STOP, VARIABLES, STACK = 0x10000, 0x1000, 0x30000, 0x90000
CPUS = (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020) if Uc else ()

# Routines pulled out of the real sources. Later tasks extend these lists.
COMBAT = ['is_combat_ship', 'is_hostile']
LOGIC = []

CONSTANTS = [
    'objects', 'obj_len', 'max_objects', 'type', 'flags', 'in_use', 'remove',
    'angry', 'logic', 'log_attack', 'log_cruise', 'log_exploding',
    'ship_type', 'attack_type', 'act_attack', 'act_runaway', 'target',
    'no_target', 'xpos', 'ypos', 'zpos', 'obj_range', 'health', 'pre_attack',
    'on_course', 'this_obj', 'radar_range', 'first_combat', 'last_combat',
    'typ_trader', 'typ_pirate', 'typ_shuttle', 'typ_police', 'typ_alien',
    'viper', 'thargon', 'thargoid', 'cougar', 'constr', 'spacestn',
    'cobra', 'transporter',
]

# Faction relation from the spec, section 4.2.
HOSTILITY = {
    'typ_trader':  {'typ_pirate', 'typ_alien'},
    'typ_pirate':  {'typ_trader', 'typ_shuttle', 'typ_police', 'typ_alien'},
    'typ_shuttle': {'typ_pirate', 'typ_alien'},
    'typ_police':  {'typ_pirate', 'typ_alien'},
    'typ_alien':   {'typ_trader', 'typ_pirate', 'typ_shuttle', 'typ_police'},
}


def ship_table():
    """Yield (name, type number, ship_type, attack_type) for each modelled object."""
    table = (ROOT / 'asm/objects.m68').read_text().split('include')[0]
    data = (ROOT / 'asm/objects.dat').read_text()
    for number, name in enumerate(re.findall(r'^\s*dc\.l\s+(\w+)\s*$', table, re.M)):
        record = re.search(r'^' + name + r':\s+dc\.l\s+\w+\s+dc\.l\s+\w+\s+'
                           r'dc\.l\s+\w+\s+dc\s+([^\n]+)', data, re.M)
        if record:
            values = [int(v) for v in record[1].split(',')]
            yield name, number, values[9], values[10]


@unittest.skipIf(Uc is None, 'optional faction AI tests require unicorn==2.1.4')
class FactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = {name: (ROOT / 'asm' / (name + '.m68')).read_text()
               for name in ('combat', 'logic')}
        names = COMBAT + LOGIC
        combat, logic = src['combat'], src['logic']
        assembly = preamble()
        assembly += combat[combat.index('slow_charge:'):combat.index('\tq_module combat')]
        assembly += logic[logic.index('fire_range:'):logic.index('\tq_module logic')]
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + CONSTANTS) + '\n'
        assembly += '\n'.join(routine(combat, name) for name in COMBAT)
        assembly += '\n'.join(routine(logic, name) for name in LOGIC)
        assembly += cls.stubs()
        cls.code, cls.symbols = assemble(assembly, names + CONSTANTS)
        cls.symbols['no_target'] -= 1 << 32  # dc.l -1 reads back unsigned

    @classmethod
    def stubs(cls):
        """World services this suite does not exercise."""
        return ''

    def prepare(self, model=None):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model or CPUS[0])
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, (len(self.code) + 4095) // 4096 * 4096,
                             UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(VARIABLES, bytes(0x8000))
        self.slot = lambda n: (VARIABLES + self.symbols['objects']
                               + n * self.symbols['obj_len'])
        self.ship, self.other = self.slot(0), self.slot(1)

    def word(self, address, value):
        self.cpu.mem_write(address, struct.pack('>H', value & 0xffff))

    def long(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))

    def var(self, name, value, size=2):
        (self.long if size == 4 else self.word)(VARIABLES + self.symbols[name], value)

    def field(self, slot, name, value, size=2):
        (self.long if size == 4 else self.word)(slot + self.symbols[name], value)

    def read(self, slot, name, size=2):
        value = int.from_bytes(self.cpu.mem_read(slot + self.symbols[name], size), 'big')
        return value - (1 << 8 * size) if value >> (8 * size - 1) else value

    def call(self, name, a4=None, d0=0):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_D0, d0)
        self.cpu.reg_write(UC_M68K_REG_A4, a4 if a4 is not None else self.other)
        self.cpu.reg_write(UC_M68K_REG_A5, self.ship)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(self.symbols[name], STOP, count=2000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        return self.cpu.reg_read(UC_M68K_REG_D0) & 0xffff

    def test_combat_whitelist_covers_exactly_the_fighting_ships(self):
        for cpu in CPUS:
            for name, number, _, _ in ship_table():
                with self.subTest(cpu=cpu, ship=name):
                    self.prepare(cpu)
                    expected = (number in (self.symbols['viper'], self.symbols['thargon'])
                                or self.symbols['first_combat'] <= number
                                <= self.symbols['last_combat'])
                    self.field(self.other, 'type', number)
                    self.assertEqual(bool(self.call('is_combat_ship')), expected)

    def test_mission_ships_and_scenery_are_never_combat_ships(self):
        self.prepare()
        for name in ('cougar', 'constr', 'spacestn'):
            with self.subTest(object=name):
                self.field(self.other, 'type', self.symbols[name])
                self.assertEqual(self.call('is_combat_ship'), 0)

    def test_faction_hostility_matrix(self):
        for cpu in CPUS:
            for hunter, hostile in HOSTILITY.items():
                for victim in HOSTILITY:
                    with self.subTest(cpu=cpu, hunter=hunter, victim=victim):
                        self.prepare(cpu)
                        self.field(self.ship, 'ship_type', self.symbols[hunter])
                        self.field(self.other, 'ship_type', self.symbols[victim])
                        self.assertEqual(bool(self.call('is_hostile')),
                                         victim in hostile)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: FAIL. `assemble` raises `AssertionError` with vasm output naming `is_combat_ship`, `is_hostile`, `no_target`, `first_combat` and `last_combat` as undefined symbols.

- [ ] **Step 3: Add the constants**

In `src_atari/asm/common.def`, immediately after `max_obj_num: equ __RS` (the end of the object type block):

```
; Types that take part in faction targeting. THARGON sits outside the range
; and is tested separately; COUGAR and CONSTR fall outside it on purpose.

first_combat: equ cobra ; first type in the contiguous combat range
last_combat: equ transporter ; last type in the contiguous combat range
```

In the same file, immediately after the `target: rs.l 1` line of the object record definition:

```
; TARGET holds NO_TARGET when nothing is selected, 0 for the player, or a
; pointer to the target's object record.

no_target: equ -1
```

- [ ] **Step 4: Add the routines**

In `src_atari/asm/combat.m68`, directly above `q_subr explode_object,global`:

```
; ****************************************************
; **												**
; ** IS_COMBAT_SHIP - DOES THIS OBJECT TAKE PART ?  **
; **												**
; ****************************************************

; Tests whether an object takes part in faction targeting, either as a hunter
; or as a victim. The contiguous type range covers the traders, the pirates
; and the shuttles; VIPER and THARGON sit outside it. The station, canisters,
; missiles, title letters, panels and both mission ships are excluded.

; Entry: A4 = ptr: object record
; Exit:  D0 = 1 when the object takes part, 0 otherwise (Z set)

; Regs: D0 corrupt.

	q_subr is_combat_ship,global

	move type(a4),d0
	cmp #viper,d0 ; police
	beq.s .yes
	cmp #thargon,d0 ; tharglet
	beq.s .yes
	cmp #first_combat,d0 ; traders, pirates and shuttles
	blo.s .no
	cmp #last_combat,d0
	bhi.s .no
.yes:
	moveq #1,d0
	rts
.no:
	moveq #0,d0
	rts


; ******************************************
; **									  **
; ** IS_HOSTILE - FACTION RELATION TEST	  **
; **									  **
; ******************************************

; Tests whether the hunter's faction attacks the candidate's faction. Bit n of
; a mask entry means "hostile to SHIP_TYPE n". The Constrictor also carries
; TYP_ALIEN, but IS_COMBAT_SHIP rejects it, so inside this system TYP_ALIEN
; means a Thargoid or a Thargon.

; Entry: A5 = ptr: hunter's record
;		 A4 = ptr: candidate's record
; Exit:  D0 = 1 when hostile, 0 otherwise (Z set)

; Regs: D0, D1, D2, A0 corrupt.

	q_subr is_hostile,global

	moveq #0,d0
	move ship_type(a5),d1
	lea faction_mask(pc),a0
	move.b 0(a0,d1.w),d1 ; hunter's hostility mask
	move ship_type(a4),d2
	btst d2,d1
	beq.s .done
	moveq #1,d0
.done:
	rts

; Hostility masks indexed by SHIP_TYPE.

faction_mask:

	dc.b $82,$95,$82,$00,$82,$00,$00,$17
	; trader pirate shuttle debris police bounty missile alien

	even

```

- [ ] **Step 5: Run the test to verify it passes, then hand over**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, three tests.

Then run the full build to confirm nothing else broke:

Run: `build_atari.bat`
Expected: builds without errors; the external-symbol and RAM-bounds checks pass.

Report to the user for commit: `src_atari/asm/common.def`, `src_atari/asm/combat.m68`, `src_atari/tests/test_faction_ai.py`.

---

### Task 2: Distance ranking

**Files:**
- Modify: `src_atari/asm/combat.m68` (after `is_hostile`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `chebyshev_range` — entry `A5` = first object, `A4` = second object; exit `D0.L` = `max(|dx|,|dy|,|dz|)`. Corrupts `D0`, `D1`.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`, extend the routine list and add the test:

```python
COMBAT = ['is_combat_ship', 'is_hostile', 'chebyshev_range']
```

```python
    def place(self, slot, x, y, z):
        for axis, value in zip('xyz', (x, y, z)):
            self.field(slot, axis + 'pos', value, 4)

    def test_chebyshev_range_is_the_largest_axis_difference(self):
        cases = [((0, 0, 0), (300, 0, 0), 300),
                 ((0, 0, 0), (0, -400, 0), 400),
                 ((0, 0, 0), (100, 200, -700), 700),
                 ((1000, 2000, 3000), (1000, 2000, 3000), 0),
                 ((-5000, 0, 0), (5000, 0, 0), 10000),
                 ((6000, -6000, 100), (-6000, 6000, 100), 12000)]
        for cpu in CPUS:
            for hunter, candidate, expected in cases:
                with self.subTest(cpu=cpu, hunter=hunter, candidate=candidate):
                    self.prepare(cpu)
                    self.place(self.ship, *hunter)
                    self.place(self.other, *candidate)
                    self.call('chebyshev_range')
                    self.assertEqual(self.cpu.reg_read(UC_M68K_REG_D0), expected)

    def test_chebyshev_range_is_symmetric(self):
        self.prepare()
        self.place(self.ship, -120, 4000, 88)
        self.place(self.other, 900, -3000, 12)
        self.call('chebyshev_range')
        forward = self.cpu.reg_read(UC_M68K_REG_D0)
        self.cpu.reg_write(UC_M68K_REG_A5, self.other)
        self.call('chebyshev_range', a4=self.ship)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_D0), forward)
```

Note: `call` writes `A5 = self.ship`, so the symmetry test calls the routine a second time through `call` with the roles swapped by passing `a4=self.ship` after temporarily pointing `A5` at the other slot; `call` re-writes `A5`, so replace the second call with a direct invocation:

```python
    def call_with(self, name, a5, a4):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A4, a4)
        self.cpu.reg_write(UC_M68K_REG_A5, a5)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(self.symbols[name], STOP, count=2000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        return self.cpu.reg_read(UC_M68K_REG_D0)
```

and write the symmetry test as:

```python
    def test_chebyshev_range_is_symmetric(self):
        self.prepare()
        self.place(self.ship, -120, 4000, 88)
        self.place(self.other, 900, -3000, 12)
        forward = self.call_with('chebyshev_range', self.ship, self.other)
        backward = self.call_with('chebyshev_range', self.other, self.ship)
        self.assertEqual(forward, backward)
        self.assertEqual(forward, 7000)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k chebyshev -v`
Expected: FAIL with vasm reporting `chebyshev_range` undefined.

- [ ] **Step 3: Implement the routine**

In `src_atari/asm/combat.m68`, after the `faction_mask` table:

```
; ***********************************************
; **										   **
; ** CHEBYSHEV_RANGE - CHEAP DISTANCE RANKING  **
; **										   **
; ***********************************************

; Largest axis difference between two objects. Used only to rank candidates
; against each other, so no square root and no division are needed. Ships stay
; within a few tens of thousands of units because anything beyond scanner
; range is removed, so the signed subtraction cannot overflow.

; Entry: A5 = ptr: first object
;		 A4 = ptr: second object
; Exit:  D0.L = max(|dx|,|dy|,|dz|)

; Regs: D0, D1 corrupt.

	q_subr chebyshev_range,global

	move.l xpos(a4),d0
	sub.l xpos(a5),d0
	bpl.s .x_positive
	neg.l d0
.x_positive:
	move.l ypos(a4),d1
	sub.l ypos(a5),d1
	bpl.s .y_positive
	neg.l d1
.y_positive:
	cmp.l d1,d0
	bhs.s .y_done
	move.l d1,d0
.y_done:
	move.l zpos(a4),d1
	sub.l zpos(a5),d1
	bpl.s .z_positive
	neg.l d1
.z_positive:
	cmp.l d1,d0
	bhs.s .done
	move.l d1,d0
.done:
	rts

```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, five tests.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build. Report `src_atari/asm/combat.m68` and `src_atari/tests/test_faction_ai.py` to the user for commit.

---

### Task 3: Globals, target initialisation and target coordinates

**Files:**
- Modify: `src_atari/asm/common.def` (global block, after `hit_check: rs.w 1` at `common.def:861`)
- Modify: `src_atari/asm/main.m68` (`alloc_object`, `main.m68:251`)
- Modify: `src_atari/asm/logic.m68` (new routine before `q_subr do_attack`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `no_target` from Task 1.
- Produces:
  - Globals `retarget_slot` (word), `npc_kill` (word), `target_range` (long).
  - `target_coords` — entry `A5` = object record; exit `D0.L`, `D1.L`, `D2.L` = the target's world coordinates, `(0,0,0)` for the player. Corrupts `D0`, `D1`, `D2`, `A0`.
  - `alloc_object` now returns a record whose `target` is `no_target`.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`:

```python
LOGIC = ['target_coords']
CONSTANTS += ['retarget_slot', 'npc_kill', 'target_range']
```

Add the tests:

```python
    def test_target_coords_returns_the_origin_for_the_player(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.place(self.ship, 700, -200, 1500)
                self.field(self.ship, 'target', 0, 4)
                self.call('target_coords')
                for register in (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2):
                    self.assertEqual(self.cpu.reg_read(register), 0)

    def test_target_coords_returns_the_targets_position(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.place(self.ship, 700, -200, 1500)
                self.place(self.other, -1234, 5678, 90)
                self.field(self.ship, 'target', self.other, 4)
                self.call('target_coords')
                values = [self.cpu.reg_read(r) for r in
                          (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2)]
                values = [v - (1 << 32) if v >> 31 else v for v in values]
                self.assertEqual(values, [-1234, 5678, 90])
```

Import `UC_M68K_REG_D1` and `UC_M68K_REG_D2` at the top of the file alongside `UC_M68K_REG_D0`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k target_coords -v`
Expected: FAIL with vasm reporting `target_coords`, `retarget_slot`, `npc_kill` and `target_range` undefined.

- [ ] **Step 3: Add the globals, the initialisation and the routine**

In `src_atari/asm/common.def`, directly after `hit_check: rs.w 1 ; flag  check for laser hit`:

```
retarget_slot: rs.w 1 ; slot whose ship re-targets on this frame
npc_kill: rs.w 1 ; flag  this kill was inflicted by another ship
target_range: rs.l 1 ; scratch  distance from the attacker to its target
```

In `src_atari/asm/main.m68`, inside `alloc_object`, on the success path. Replace:

```
	btst #in_use,flags(a4) ; record free ?
; Quelo: 		if <eq> then.s					yes
	bne.s q_main_m68_25
	q_pop d7 ; restore D7
	q_sec set ; carry flag (alloc ok)
	rts ; return
```

with:

```
	btst #in_use,flags(a4) ; record free ?
; Quelo: 		if <eq> then.s					yes
	bne.s q_main_m68_25
	move.l #no_target,target(a4) ; a fresh record has no AI target
	q_pop d7 ; restore D7
	q_sec set ; carry flag (alloc ok)
	rts ; return
```

The initialisation belongs here and not in `create_object`, because `fire_missile` writes `target(a4)` before it calls `create_object`.

In `src_atari/asm/logic.m68`, directly above `q_subr do_attack`:

```
; The one place that knows TARGET = 0 means the player, who is the origin of
; every object coordinate. NO_TARGET also reads back as the origin; callers
; must establish that a target exists before relying on the result.
	q_subr target_coords,global

	move.l target(a5),d0
	ble.s .player
	move.l d0,a0
	move.l xpos(a0),d0
	move.l ypos(a0),d1
	move.l zpos(a0),d2
	rts
.player:
	moveq #0,d0
	moveq #0,d1
	moveq #0,d2
	rts

```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, seven tests.

Run: `python -m unittest discover -s src_atari/tests -p test_lasers.py -v`
Expected: PASS, no regression from the `alloc_object` change.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build; the RAM-bounds check confirms the three new globals fit.

Report `src_atari/asm/common.def`, `src_atari/asm/main.m68`, `src_atari/asm/logic.m68`, `src_atari/tests/test_faction_ai.py`.

---

### Task 4: Target selection

**Files:**
- Modify: `src_atari/asm/combat.m68` (after `chebyshev_range`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `is_combat_ship`, `is_hostile`, `chebyshev_range`, `no_target`.
- Produces: `pick_target` — entry `A5` = hunter's record; exit `target(a5)` set to `no_target`, `0` or a record pointer, `D0.W` = 1 when a target was found. Corrupts `D0`-`D3`, `A0`, `A1`, `A4`.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`:

```python
COMBAT = ['is_combat_ship', 'is_hostile', 'chebyshev_range', 'pick_target']
```

```python
    def ship_at(self, slot, kind, x, y, z, ship_type=None, attack=None):
        """Put a usable in-use ship of type `kind` into a slot."""
        self.field(slot, 'flags', 1 << self.symbols['in_use'], 1)
        self.field(slot, 'type', self.symbols[kind])
        self.field(slot, 'ship_type', self.symbols[
            ship_type if ship_type else 'typ_pirate'])
        self.field(slot, 'attack_type', self.symbols[attack or 'act_attack'])
        self.field(slot, 'logic', self.symbols['log_cruise'])
        self.field(slot, 'target', self.symbols['no_target'], 4)
        self.place(slot, x, y, z)
        self.field(slot, 'obj_range', max(abs(x), abs(y), abs(z)), 4)

    def test_nearest_hostile_ship_wins(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.ship_at(self.slot(1), 'cobra', 0, 0, 6000, 'typ_trader')
                self.ship_at(self.slot(2), 'cobra', 0, 0, 2000, 'typ_trader')
                self.ship_at(self.slot(3), 'cobra', 0, 0, 9000, 'typ_trader')
                self.assertEqual(self.call('pick_target'), 1)
                self.assertEqual(self.read(self.ship, 'target', 4), self.slot(2))

    def test_player_competes_under_the_same_rule(self):
        for distance, expects_player in ((900, True), (3000, False)):
            with self.subTest(distance=distance):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, distance, 'typ_pirate')
                self.field(self.ship, 'obj_range', distance, 4)
                self.ship_at(self.slot(1), 'cobra', 0, 0, distance + 2000, 'typ_trader')
                self.field(self.slot(1), 'obj_range', distance + 2000, 4)
                self.call('pick_target')
                expected = 0 if expects_player else self.slot(1)
                self.assertEqual(self.read(self.ship, 'target', 4), expected)

    def test_trader_ignores_the_player_until_angry(self):
        self.prepare()
        self.ship_at(self.ship, 'cobra', 0, 0, 500, 'typ_trader')
        self.field(self.ship, 'obj_range', 500, 4)
        self.ship_at(self.slot(1), 'krait', 0, 0, 4000, 'typ_pirate')
        self.field(self.slot(1), 'obj_range', 4000, 4)
        self.call('pick_target')
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))
        flags = 1 << self.symbols['in_use'] | 1 << self.symbols['angry']
        self.field(self.ship, 'flags', flags, 1)
        self.call('pick_target')
        self.assertEqual(self.read(self.ship, 'target', 4), 0)

    def test_candidates_are_filtered(self):
        cases = [('not in use', lambda s: self.field(s, 'flags', 0, 1)),
                 ('flagged for removal', lambda s: self.field(
                     s, 'flags', 1 << self.symbols['in_use']
                     | 1 << self.symbols['remove'], 1)),
                 ('exploding', lambda s: self.field(
                     s, 'logic', self.symbols['log_exploding'])),
                 ('not a combat ship', lambda s: self.field(
                     s, 'type', self.symbols['spacestn'])),
                 ('mission ship', lambda s: self.field(
                     s, 'type', self.symbols['cougar'])),
                 ('same faction', lambda s: self.field(
                     s, 'ship_type', self.symbols['typ_pirate'])),
                 ('beyond scanner range', lambda s: self.field(
                     s, 'obj_range', self.symbols['radar_range'] + 1, 4))]
        for label, break_it in cases:
            with self.subTest(reason=label):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                break_it(self.slot(1))
                self.assertEqual(self.call('pick_target'), 0)
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])

    def test_a_hunter_never_targets_itself(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
        self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
        self.assertEqual(self.call('pick_target'), 0)
        self.assertEqual(self.read(self.ship, 'target', 4), self.symbols['no_target'])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k pick -v`
Expected: FAIL with vasm reporting `pick_target` undefined.

- [ ] **Step 3: Implement the routine**

In `src_atari/asm/combat.m68`, after `chebyshev_range`:

```
; ****************************************************
; **												**
; ** PICK_TARGET - CHOOSE THE NEAREST HOSTILE SHIP  **
; **												**
; ****************************************************

; Selects the nearest hostile candidate for a hunter. The player is an
; ordinary candidate whenever the hunter's faction attacks him, or whenever
; the hunter is angry because the player has already shot at it; ANGRY only
; adds him to the set and never locks the choice. Candidates are limited to
; the player's scanner range, so fights only happen where the player can see
; them. OBJ_RANGE is reused throughout: it is the distance from the player and
; is already computed by GET_RANGE.

; Entry: A5 = ptr: hunter's record
; Exit:  TARGET updated, D0 = 1 when a target was found, 0 otherwise

; Regs: D0, D1, D2, D3, A0, A1, A4 corrupt.
; Subr: IS_COMBAT_SHIP, IS_HOSTILE, CHEBYSHEV_RANGE

	q_subr pick_target,global

	q_push d7 ; save the loop counter
	move.l #no_target,target(a5) ; nothing chosen yet
	move.l #$7fffffff,d3 ; best distance so far
	btst #angry,flags(a5) ; player already provoked this ship ?
	bne.s .player
	cmp #typ_pirate,ship_type(a5) ; pirates and aliens always hunt him
	beq.s .player
	cmp #typ_alien,ship_type(a5)
	bne.s .ships
.player:
	move.l obj_range(a5),d3 ; the player sits at the origin
	clr.l target(a5)
.ships:
	lea objects(a6),a4 ; scan every object record
	q_loop 1,max_objects
	cmpa.l a4,a5 ; never target itself
	beq.s .next
	btst #in_use,flags(a4)
	beq.s .next
	btst #remove,flags(a4)
	bne.s .next
	cmp #log_exploding,logic(a4)
	beq.s .next
	cmp.l #radar_range,obj_range(a4) ; inside the player's scanner ?
	bhi.s .next
	bsr is_combat_ship
	beq.s .next
	bsr is_hostile
	beq.s .next
	bsr chebyshev_range ; D0.L = distance from the hunter
	cmp.l d3,d0
	bhs.s .next ; no closer than the best so far
	move.l d0,d3
	move.l a4,target(a5)
.next:
	lea obj_len(a4),a4 ; next object
	q_next 1
	moveq #0,d0
	cmp.l #no_target,target(a5)
	beq.s .done
	moveq #1,d0
.done:
	q_pop d7 ; restore the loop counter

	q_ret

```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, twelve tests.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build. Report `src_atari/asm/combat.m68` and `src_atari/tests/test_faction_ai.py`.

---

### Task 5: Entering and leaving combat

**Files:**
- Modify: `src_atari/asm/combat.m68` (after `pick_target`)
- Modify: `src_atari/asm/main.m68` (object loop at `main.m68:113`, and the loop tail)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `pick_target`, `retarget_slot`.
- Produces:
  - `combat_state` — entry `D1.W` = a logic value; exit `D0.W` = 0 ineligible, 1 passive, 2 already fighting. Corrupts `D0`.
  - `retarget` — entry `A5` = current object, `this_obj` = its slot number; exit `target` and `logic` updated when it is this object's turn. Corrupts `D0`-`D3`, `A0`, `A1`, `A4`.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`:

```python
COMBAT = ['is_combat_ship', 'is_hostile', 'chebyshev_range', 'pick_target',
          'combat_state', 'retarget']
CONSTANTS += ['log_peel_off', 'log_run_off', 'log_avoid', 'log_launch',
              'log_fly_planet', 'log_locked', 'log_timer']
```

```python
    PASSIVE = ('log_cruise', 'log_fly_planet')
    FIGHTING = ('log_attack', 'log_peel_off', 'log_run_off', 'log_avoid')
    LOCKED = ('log_launch', 'log_exploding', 'log_locked', 'log_timer')

    def test_combat_state_classifies_every_logic(self):
        for state, expected in ([(s, 1) for s in self.PASSIVE]
                                + [(s, 2) for s in self.FIGHTING]
                                + [(s, 0) for s in self.LOCKED]):
            with self.subTest(state=state):
                self.prepare()
                self.cpu.reg_write(UC_M68K_REG_D1, self.symbols[state])
                self.assertEqual(self.call_keeping_d1('combat_state'), expected)

    def test_a_cruising_ship_enters_combat(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
                self.field(self.ship, 'health', 90)
                self.field(self.ship, 'on_course', 7)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_attack'])
                self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))
                self.assertEqual(self.read(self.ship, 'on_course'), 0)
                self.assertEqual(self.read(self.ship, 'pre_attack'), 90)

    def test_a_launching_or_docking_ship_is_never_interrupted(self):
        for state in self.LOCKED:
            with self.subTest(state=state):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
                self.field(self.ship, 'logic', self.symbols[state])
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'logic'), self.symbols[state])
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])

    def test_a_fighter_without_a_candidate_disengages(self):
        for state in self.FIGHTING:
            with self.subTest(state=state):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
                self.field(self.ship, 'logic', self.symbols[state])
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_cruise'])
                self.assertEqual(self.read(self.ship, 'on_course'), 1)

    def test_a_fighter_keeps_its_state_when_the_target_changes(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
        self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
        self.field(self.ship, 'logic', self.symbols['log_run_off'])
        self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_run_off'])
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))

    def test_only_this_frames_slot_re_targets(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
        self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
        self.var('this_obj', 0)
        self.var('retarget_slot', 1)
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'target', 4), self.symbols['no_target'])
        self.var('retarget_slot', 0)
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))

    def test_a_runaway_ship_never_hunts(self):
        self.prepare()
        self.ship_at(self.ship, 'python', 0, 0, 0, 'typ_trader', attack='act_runaway')
        self.field(self.ship, 'obj_range', self.symbols['radar_range'] + 1, 4)
        self.ship_at(self.slot(1), 'krait', 0, 0, 2000, 'typ_pirate')
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'target', 4), self.symbols['no_target'])
        self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_cruise'])
```

Add `'python'` to `CONSTANTS` and this helper next to `call`:

```python
    def call_keeping_d1(self, name):
        """Like call, but leaves D1 as the test set it."""
        d1 = self.cpu.reg_read(UC_M68K_REG_D1)
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_D1, d1)
        self.cpu.reg_write(UC_M68K_REG_A5, self.ship)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(self.symbols[name], STOP, count=2000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        return self.cpu.reg_read(UC_M68K_REG_D0) & 0xffff
```

`prepare` must also default `this_obj` and `retarget_slot` to 0, which the zeroed variable block already does.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k "combat_state or retarget or enters or interrupt or disengage" -v`
Expected: FAIL with vasm reporting `combat_state` and `retarget` undefined.

- [ ] **Step 3: Implement the routines**

In `src_atari/asm/combat.m68`, after `pick_target`:

```
; ****************************************************
; **												**
; ** COMBAT_STATE - IS THIS LOGIC OPEN TO A FIGHT ? **
; **												**
; ****************************************************

; Classifies a logic type for target selection. Launch, docking, explosion and
; missile logics run to their end untouched; a cruising ship may be drawn into
; a fight; a fighting ship only swaps targets.

; Entry: D1 = logic type
; Exit:  D0 = 0 ineligible, 1 passive, 2 already fighting

; Regs: D0 corrupt.

	q_subr combat_state,global

	moveq #1,d0 ; passive, may be drawn in
	cmp #log_cruise,d1
	beq.s .done
	cmp #log_fly_planet,d1
	beq.s .done
	moveq #2,d0 ; already in a fight
	cmp #log_attack,d1
	beq.s .done
	cmp #log_peel_off,d1
	beq.s .done
	cmp #log_run_off,d1
	beq.s .done
	cmp #log_avoid,d1
	beq.s .done
	moveq #0,d0 ; leave this logic alone
.done:
	rts


; **************************************************
; **											  **
; ** RETARGET - REFRESH ONE SHIP'S FACTION TARGET **
; **											  **
; **************************************************

; Called for each object in the main loop. One slot re-targets per game frame,
; so the whole scan costs about MAX_OBJECTS comparisons per frame instead of
; MAX_OBJECTS squared. A ship must be a combat ship and able to fight back,
; which excludes the Python, the Shuttle and the Transporter.

; Entry: A5 = ptr: current object
; Exit:  None

; Regs: D0, D1, D2, D3, A0, A1, A4 corrupt.
; Subr: IS_COMBAT_SHIP, COMBAT_STATE, PICK_TARGET

	q_subr retarget,global

	move this_obj(a6),d0 ; this slot's turn this frame ?
	cmp retarget_slot(a6),d0
	bne .done ; no
	move.l a5,a4 ; a hunter must be a combat ship
	bsr is_combat_ship
	beq .done
	cmp #act_attack,attack_type(a5) ; and must be able to fight back
	bne .done
	move logic(a5),d1 ; may this logic be disturbed ?
	bsr combat_state
	tst d0
	beq.s .done ; no
	move d0,-(sp) ; remember passive or fighting
	bsr pick_target
	move (sp)+,d1
	tst d0 ; anything hostile in range ?
	beq.s .nothing
	cmp #1,d1 ; was it cruising ?
; Quelo: 	if <eq> then.s						yes
	bne.s .done
	move #log_attack,logic(a5) ; turn to attack
	clr on_course(a5)
	move health(a5),pre_attack(a5)
	bra.s .done
.nothing:
	cmp #2,d1 ; was it fighting ?
	bne.s .done
	move #log_cruise,logic(a5) ; nothing left to fight, fly off
	move #1,on_course(a5)
.done:
	rts

```

In `src_atari/asm/main.m68`, in the object loop, insert the call directly before `jsr do_logic`:

```
	jsr mini_radar
	jsr retarget ; refresh this ship's faction target
	jsr do_logic ; perform logic
```

and add `retarget` to the `xref` list at the top of `main.m68` alongside the other `combat` entry points.

At the end of the object loop, after the loop has finished all slots, advance the cursor once per frame. Replace:

```
	lea obj_len(a5),a5 ; next object
	q_inc this_obj(a6)
	cmp #max_objects,this_obj(a6)
```

with the same three lines, and after the loop's closing branch add:

```
	q_inc retarget_slot(a6) ; next ship re-targets on the following frame
	cmp #max_objects,retarget_slot(a6)
	blo.s .slot_ok
	clr retarget_slot(a6)
.slot_ok:
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, nineteen tests.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build; the external-symbol check confirms the new `xref`.

Report `src_atari/asm/combat.m68`, `src_atari/asm/main.m68`, `src_atari/tests/test_faction_ai.py`.

---

### Task 6: Generalised attack logic

**Files:**
- Modify: `src_atari/asm/logic.m68` (`ai_laser_aim` at `logic.m68:380`, `ai_laser_miss_threshold` at `logic.m68:413`, `do_attack` at `logic.m68:435`, `peel_off_check` at `logic.m68:820`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `target_coords`, `target_range`, `no_target`.
- Produces:
  - `validate_target` — entry `A5`; exit `D0.W` = 1 when the target is usable, 0 otherwise and `target` reset to `no_target`. Corrupts `D0`, `A0`.
  - `target_range_calc` — entry `A5` with a validated target; exit `target_range` set. Corrupts `D0`-`D2`, `A4`.
  - `do_attack` now attacks `target(a5)`; `ai_laser_aim` and `ai_laser_miss_threshold` read `target_range`.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`:

```python
LOGIC = ['target_coords', 'validate_target', 'target_range_calc']
```

```python
    def test_validate_target_accepts_the_player_and_live_ships(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
        self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
        self.field(self.ship, 'target', 0, 4)
        self.assertEqual(self.call('validate_target'), 1)
        self.field(self.ship, 'target', self.slot(1), 4)
        self.assertEqual(self.call('validate_target'), 1)

    def test_validate_target_drops_dead_and_missing_targets(self):
        cases = [('no target', lambda: self.field(
                     self.ship, 'target', self.symbols['no_target'], 4)),
                 ('freed record', lambda: self.field(self.slot(1), 'flags', 0, 1)),
                 ('being removed', lambda: self.field(
                     self.slot(1), 'flags', 1 << self.symbols['in_use']
                     | 1 << self.symbols['remove'], 1)),
                 ('exploding', lambda: self.field(
                     self.slot(1), 'logic', self.symbols['log_exploding']))]
        for label, break_it in cases:
            with self.subTest(reason=label):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                break_it()
                self.assertEqual(self.call('validate_target'), 0)
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])

    def test_target_range_uses_obj_range_for_the_player(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 4321, 'typ_pirate')
        self.field(self.ship, 'obj_range', 4321, 4)
        self.field(self.ship, 'target', 0, 4)
        self.call('target_range_calc')
        self.assertEqual(self.read(VARIABLES, 'target_range', 4), 4321)
        self.assertEqual(self.read(self.ship, 'obj_range', 4), 4321)
```

`read(VARIABLES, ...)` works because `read` adds the symbol offset to whatever base it is given.

The behavioural tests for aiming and firing at a ship are added in Task 9, once the full `do_attack` chain including `get_dist` and `random` is assembled. Task 6's own gate is: `tests/test_lasers.py` must still pass unchanged, which proves the player-facing path is untouched.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k "validate or target_range" -v`
Expected: FAIL with vasm reporting `validate_target` and `target_range_calc` undefined.

- [ ] **Step 3: Implement the changes**

In `src_atari/asm/logic.m68`, directly after `target_coords`:

```
; A target can vanish without any destruction event, because DO_CRUISING and
; REMOVE_OBJECT free records silently. Two tests per frame cover every path.
	q_subr validate_target,global

	move.l target(a5),d0
	beq.s .usable ; 0 is the player, who never vanishes
	cmp.l #no_target,d0
	beq.s .none
	move.l d0,a0
	btst #in_use,flags(a0)
	beq.s .none
	btst #remove,flags(a0)
	bne.s .none
	cmp #log_exploding,logic(a0)
	beq.s .none
.usable:
	moveq #1,d0
	rts
.none:
	move.l #no_target,target(a5)
	moveq #0,d0
	rts


; OBJ_RANGE must keep meaning "distance from the player", because RADAR,
; COLLISION and DO_CRUISING all depend on it. The attacker's distance to its
; own target therefore lives in its own scratch variable.
	q_subr target_range_calc,global

	move.l target(a5),d0
	bne.s .ship
	move.l obj_range(a5),target_range(a6) ; the player is the origin
	rts
.ship:
	move.l d0,a4
	jsr get_dist ; D2.L = distance between A5 and A4
	move.l d2,target_range(a6)
	rts

```

Replace `ai_laser_aim` (`logic.m68:380`) entirely with:

```
; BBC's two aim cones, expressed in the game's Q14 orientation vectors.
; The 12288-unit fire-range guard keeps each component of the line of fire
; safely inside signed words. Compare dot products directly: no square root
; and no division are needed.
	q_subr ai_laser_aim

	moveq #0,d0
	tst.l target_range(a6)
	ble.s .done
	cmp.l #fire_range,target_range(a6)
	bhi.s .done
	movem.l d3-d5,-(sp)
	moveq #0,d5
	bsr target_coords ; (D0,D1,D2) = the target's position
	sub.l xpos(a5),d0 ; direction from the shooter to the target
	sub.l ypos(a5),d1
	sub.l zpos(a5),d2
	move.w d0,d3
	muls.w z_vector+i(a5),d3
	move.w d1,d4
	muls.w z_vector+j(a5),d4
	add.l d4,d3
	move.w d2,d4
	muls.w z_vector+k(a5),d4
	add.l d4,d3
	move.w target_range+2(a6),d4
	mulu.w #unit*32/36,d4
	cmp.l d4,d3
	blt.s .restore
	moveq #1,d5 ; within the firing cone, but can still miss
	move.w target_range+2(a6),d4
	mulu.w #unit*35/36,d4
	cmp.l d4,d3
	blt.s .restore
	moveq #2,d5 ; within the narrower hit cone
.restore:
	move.l d5,d0
	movem.l (sp)+,d3-d5
.done:
	rts
```

In `ai_laser_miss_threshold`, replace the first instruction:

```
	move.l obj_range(a5),d0
```

with:

```
	move.l target_range(a6),d0
```

Replace `peel_off_check` (`logic.m68:820`) entirely with:

```
	q_subr peel_off_check

	lea target_range(a6),a0 ; range this peel distance is compared against
	move.l target(a5),d0 ; chasing another ship ?
	ble.s .player ; NO_TARGET and the player both mean the origin
	move velocity(a5),d0 ; a pair of ships has no closing speed
	bra.s .distance
.player:
	lea obj_range(a5),a0
	move approach(a6),d0 ; flying away from us ?
	bmi.s .away ; yes
.distance:
	mulu #600,d0 ; calculate peel distance
	divu turn_rate(a5),d0
	add #1024,d0
	bra.s .compare
.away:
	clr d0 ; peel distance = 0
.compare:
	q_hclr d0 ; set carry if within distance
	cmp.l (a0),d0

	q_ret
```

In `do_attack`, replace the opening block. The old opening is:

```
	q_subr do_attack

	bset #angry,flags(a5) ; angry with player
	tst radar_obj(a6) ; within space station space ?
```

The new opening is:

```
	q_subr do_attack

	bsr validate_target ; is there still something to fight ?
	tst d0
; Quelo: 	if <eq> then.s						no
	bne.s .have_target
	move #log_cruise,logic(a5) ; fly off
	move #1,on_course(a5)
	rts
.have_target:
	tst.l target(a5) ; fighting the player ?
	bne.s .not_player
	bset #angry,flags(a5) ; only he gets the cockpit warning
.not_player:
	bsr target_range_calc ; distance to whatever is being fought
	tst radar_obj(a6) ; within space station space ?
```

Then in the body of `do_attack`, make these four replacements:

1. `cmp.l #fire_range,obj_range(a5) ; close enough to fire ?` becomes
   `cmp.l #fire_range,target_range(a6) ; close enough to fire ?`
2. `st ai_laser(a5)` becomes `move d0,ai_laser(a5) ; 1 = miss, 2 = hit`
3. The damage strength block. Replace:

```
	cmp #constr,type(a5)
	bne.s .ordinary_power
	moveq #6,d0 ; original Constrictor projectile strength
	bra.s .damage
.ordinary_power:
	move rating(a6),d0
	add d0,d0
	lea damage(pc),a0
	move (a0,d0),d2
	jsr rand
	q_inc d0 ; original per-projectile damage, unchanged
.damage:
```

with:

```
	tst.l target(a5) ; shooting at the player ?
	bne.s .npc_power ; no, another ship
	cmp #constr,type(a5)
	bne.s .ordinary_power
	moveq #6,d0 ; original Constrictor projectile strength
	bra.s .damage
.ordinary_power:
	move rating(a6),d0
	add d0,d0
	lea damage(pc),a0
	move (a0,d0),d2
	bra.s .roll
.npc_power:
	moveq #npc_damage,d2 ; the player's rating means nothing here
.roll:
	jsr rand
	q_inc d0 ; original per-projectile damage, unchanged
.damage:
```

4. The delivery. Replace:

```
	mulu.w (sp)+,d0 ; combine the old projectile's repeated hits into one hit
	jsr reduce_shields ; A5 is the shooter: selects front/aft by its position
```

with:

```
	mulu.w (sp)+,d0 ; combine the old projectile's repeated hits into one hit
	tst.l target(a5) ; the player or another ship ?
	bne.s .hit_ship
	jsr reduce_shields ; A5 is the shooter: selects front/aft by its position
	bra.s .laser_sound
.hit_ship:
	bsr damage_target
```

and change the accuracy-miss branch so the beam is drawn as a miss. Replace:

```
	cmp.w d2,d0
	blo.s .laser_sound ; keep the beam and optional firing sound, skip all damage
```

with:

```
	cmp.w d2,d0
	bhs.s .on_target
	move #1,ai_laser(a5) ; drawn as a miss, no damage
	bra.s .laser_sound
.on_target:
```

Finally, add the new local constant next to the other `do_attack` constants at the top of `logic.m68`, after `fire_range`:

```
npc_damage: equ 5 ; fixed AI to AI strength, the middle of the DAMAGE table
```

and add `damage_target` to the `xref` list at the top of `logic.m68` (it is implemented in Task 7).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, twenty-three tests.

Run: `python -m unittest discover -s src_atari/tests -p test_lasers.py -v`
Expected: PASS with no changes. This is the gate proving that combat against the player is unchanged. If a laser test fails, the player path has been altered and the change must be corrected, not the test.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: the build fails the external-symbol check on `damage_target` until Task 7 lands. If the toolchain refuses to link, note this and continue to Task 7 before reporting; the two tasks are committed together.

Report `src_atari/asm/logic.m68` and `src_atari/tests/test_faction_ai.py`.

---

### Task 7: NPC damage and kill bookkeeping

**Files:**
- Modify: `src_atari/asm/combat.m68` (`damage_target` after `retarget`; `explode_object` at `combat.m68:206`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `npc_kill`, `no_target`.
- Produces: `damage_target` — entry `A5` = shooter with an NPC target, `D0.W` = hit power; exit the target's `health` reduced and the target destroyed when it runs out. Corrupts `D0`-`D2`, `A0`, `A1`, `A4`.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`:

```python
COMBAT = ['is_combat_ship', 'is_hostile', 'chebyshev_range', 'pick_target',
          'combat_state', 'retarget', 'damage_target', 'explode_object']
CONSTANTS += ['no_bounty', 'invincible', 'point', 'no_radar', 'force',
              'exp_timer', 'collided', 'kill_rating', 'score', 'rating',
              'police_record', 'bounty', 'thargoid', 'dodec', 'mission']
```

Replace the `stubs` class method with the world services `explode_object` needs:

```python
    #: Subroutines explode_object and damage_target call, stubbed so the test
    #: can observe *whether* they ran rather than emulate the whole world.
    STUBBED = ('add_kill', 'inc_record', 'release_cargo', 'target_lost',
               'alloc_object', 'copy_object', 'create_object',
               'random_direction', 'move_object', 'rand', 'random',
               'disp_message', 'fx', 'get_dist')

    @classmethod
    def stubs(cls):
        # alloc_object must report "no records left" (carry clear) so
        # explode_object takes its GIVE_UP path instead of building platlets.
        text = '\nalloc_object:\n\tandi #$fe,ccr\n\trts\n'
        return text + ''.join(f'\n{name}:\n\trts\n' for name in cls.STUBBED
                              if name != 'alloc_object')
```

and record which stubs ran:

```python
    def watch_stubs(self):
        self.entered = []
        for name in self.STUBBED:
            def trace(cpu, address, size, user, name=name):
                self.entered.append(name)
            self.cpu.hook_add(UC_HOOK_CODE, trace,
                              begin=self.symbols[name], end=self.symbols[name])
```

Add `self.STUBBED` names to the `names` list in `setUpClass` so their addresses appear in the symbol table:

```python
        names = COMBAT + LOGIC + list(cls.STUBBED)
```

The tests:

```python
    def test_damage_target_reduces_the_targets_health(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.slot(1), 'health', 100)
                self.call('damage_target', d0=12)
                self.assertEqual(self.read(self.slot(1), 'health'), 88)
                self.assertNotIn('add_kill', self.entered)

    def test_a_lethal_hit_explodes_the_target_without_crediting_the_player(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.slot(1), 'health', 4)
                self.call('damage_target', d0=9)
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertNotIn('add_kill', self.entered)
                self.assertNotIn('inc_record', self.entered)
                self.assertIn('release_cargo', self.entered)
                self.assertIn('target_lost', self.entered)
                flags = self.read(self.slot(1), 'flags', 1)
                self.assertTrue(flags & 1 << self.symbols['no_bounty'])
                self.assertEqual(self.read(VARIABLES, 'npc_kill'), 0)

    def test_a_player_kill_still_credits_score_and_record(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
        self.var('npc_kill', 0)
        self.call_with('explode_object', self.ship, self.slot(1))
        self.assertIn('add_kill', self.entered)
        self.assertIn('inc_record', self.entered)
        flags = self.read(self.slot(1), 'flags', 1)
        self.assertFalse(flags & 1 << self.symbols['no_bounty'])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k "damage_target or lethal or player_kill" -v`
Expected: FAIL with vasm reporting `damage_target` undefined.

- [ ] **Step 3: Implement the routine and the guards**

In `src_atari/asm/combat.m68`, after `retarget`:

```
; *********************************************
; **										 **
; ** DAMAGE_TARGET - HIT ANOTHER SHIP		 **
; **										 **
; *********************************************

; Applies laser damage from one ship to another. The player takes damage
; through REDUCE_SHIELDS instead; this path exists only for AI against AI.
; NPC_KILL tells EXPLODE_OBJECT that the player made no kill here, so his
; score, rating, bounty and police record are all left alone.

; Entry: A5 = ptr: shooter, whose TARGET is another ship
;		 D0 = hit power
; Exit:  None

; Regs: D0, D1, D2, A0, A1, A4 corrupt.
; Subr: EXPLODE_OBJECT, TARGET_LOST, RELEASE_CARGO

	q_subr damage_target,global

	move.l target(a5),a4
	sub d0,health(a4) ; reduce the target's health
	q_ret cc ; still alive
	st npc_kill(a6) ; the player gets no credit for this
	bsr explode_object
	bsr target_lost ; his missile may have been locked on it
	jsr release_cargo ; containers still drop
	q_sfx explosion
	clr npc_kill(a6)

	q_ret

```

In `explode_object` (`combat.m68:206`), guard the two bookkeeping calls. Replace:

```
	st exploded(a6) ; object exploded
	bsr add_kill ; add kill rating
	tst collided(a6) ; collided with object ?
; Quelo: 	if <eq> then.s						no
	bne.s q_combat_m68_13
```

with:

```
	st exploded(a6) ; object exploded
	tst npc_kill(a6) ; did the player make this kill ?
; Quelo: 	if <eq> then.s						yes
	bne.s .no_credit
	bsr add_kill ; add kill rating
	bra.s .credited
.no_credit:
	bset #no_bounty,flags(a4) ; and pay no bounty either
	bra.s q_combat_m68_13 ; never touch his police record
.credited:
	tst collided(a6) ; collided with object ?
; Quelo: 	if <eq> then.s						no
	bne.s q_combat_m68_13
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, twenty-six tests.

Run: `python -m unittest discover -s src_atari/tests -p test_lasers.py -v`
Expected: PASS, no regression. The player's own kills go through `explode_object` with `npc_kill` clear and behave exactly as before.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build; the `damage_target` symbol referenced by Task 6 now resolves.

Report `src_atari/asm/combat.m68` and `src_atari/tests/test_faction_ai.py`.

---

### Task 8: Missiles stay player-facing

**Files:**
- Modify: `src_atari/asm/combat.m68` (`low_energy` at `combat.m68:800`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `target`.
- Produces: no new symbols. `low_energy` launches a missile or Thargons only when the shooter's target is the player.

- [ ] **Step 1: Write the failing test**

In `src_atari/tests/test_faction_ai.py`:

```python
COMBAT += ['low_energy']
```

Add `'launch_escape'`, `'launch_missile'`, `'thargons'`, `'start_peel_off'` to `STUBBED`, and add:

```python
    def test_a_ship_fighting_another_ship_launches_no_missile(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.ship, 'no_missiles', 3)
                self.call('low_energy')
                self.assertNotIn('launch_missile', self.entered)
                self.assertNotIn('thargons', self.entered)
                self.assertIn('launch_escape', self.entered)

    def test_a_ship_fighting_the_player_still_launches_missiles(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 2000, 'typ_pirate')
        self.field(self.ship, 'target', 0, 4)
        self.field(self.ship, 'no_missiles', 3)
        self.var('random_return', 0)  # always inside the launch probability
        self.call('low_energy')
        self.assertIn('launch_missile', self.entered)
```

The `random` stub must return 0 so the probability test passes. Change the stub for `random` and `rand` to:

```python
        text += '\nrandom:\n\tmoveq #0,d0\n\trts\nrand:\n\tmoveq #0,d0\n\trts\n'
```

and drop `random`/`rand` from the generic `rts` list. Add `'no_missiles'` to `CONSTANTS`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k missile -v`
Expected: FAIL. The first test fails because `launch_missile` is entered even when the target is another ship.

- [ ] **Step 3: Implement the gate**

In `src_atari/asm/combat.m68`, in `low_energy`, replace:

```
	q_subr low_energy

	bsr launch_escape ; random launch of escape capsule
	tst no_missiles(a5) ; any missiles left ?
```

with:

```
	q_subr low_energy

	bsr launch_escape ; random launch of escape capsule
	tst.l target(a5) ; AI against AI is fought with lasers only
; Quelo: 	if <ne> then.s						not the player
	bne.s q_combat_m68_97
	tst no_missiles(a5) ; any missiles left ?
```

`q_combat_m68_97` is the existing label that already closes the missile block, so the branch skips exactly the missile and Thargon release.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, twenty-eight tests.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build.

Report `src_atari/asm/combat.m68` and `src_atari/tests/test_faction_ai.py`.

---

### Task 9: Ship-to-ship beam drawing

**Files:**
- Modify: `src_atari/asm/special.m68` (`draw_ai_laser` at `special.m68:264`)
- Modify: `src_atari/tests/test_lasers.py` (extend, do not replace, the existing AI beam coverage)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `target`, `ai_laser` holding 1 for a miss and 2 for a hit.
- Produces: no new symbols. `draw_ai_laser` draws towards the target's projected position when the target is another ship.

- [ ] **Step 1: Write the failing test**

The existing `tests/test_lasers.py` already assembles `draw_ai_laser` with a `c_line` hook that records `(d0, d1, d2, d3)` endpoints in `self.lines`. Add to `LaserTests` in that file:

```python
    def test_ai_beam_at_a_ship_ends_on_the_target(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            with self.subTest(cpu=model):
                self.prepare(model)
                target = self.ship + self.symbols['obj_len']
                self.cpu.mem_write(target + self.symbols['flags'],
                                   struct.pack('>H', (1 << self.symbols['in_use']) << 8))
                for axis, value in zip(('x', 'y', 'z'), (2000, 1000, 6000)):
                    self.cpu.mem_write(target + self.symbols['this_' + axis + 'pos'],
                                       struct.pack('>i', value))
                self.cpu.mem_write(self.ship + self.symbols['target'],
                                   struct.pack('>I', target))
                self.obj('ai_laser', 2)
                self.lines.clear()
                self.call('draw_ai_laser')
                self.assertEqual(len(self.lines), 1)
                x0, y0, x1, y1 = self.lines[0]
                # 512 * 2000 / 6000 and 512 * 1000 / 6000, the game's projection.
                self.assertEqual((x1, y1), (170, 85))

    def test_ai_beam_at_the_player_is_unchanged(self):
        self.prepare()
        self.cpu.mem_write(self.ship + self.symbols['target'], struct.pack('>I', 0))
        self.obj('ai_laser', 2)
        self.lines.clear()
        self.call('draw_ai_laser')
        self.assertEqual(len(self.lines), 1)
        x0, y0, x1, y1 = self.lines[0]
        self.assertIn(x1, (-128, 127))  # still sent to a screen edge

    def test_a_missed_ai_beam_lands_near_but_not_on_the_target(self):
        self.prepare()
        target = self.ship + self.symbols['obj_len']
        self.cpu.mem_write(target + self.symbols['flags'],
                           struct.pack('>H', (1 << self.symbols['in_use']) << 8))
        for axis, value in zip(('x', 'y', 'z'), (2000, 1000, 6000)):
            self.cpu.mem_write(target + self.symbols['this_' + axis + 'pos'],
                               struct.pack('>i', value))
        self.cpu.mem_write(self.ship + self.symbols['target'], struct.pack('>I', target))
        self.obj('ai_laser', 1)
        self.lines.clear()
        self.call('draw_ai_laser')
        x0, y0, x1, y1 = self.lines[0]
        self.assertTrue(-4 <= x1 - 170 <= 3, x1)
        self.assertTrue(-2 <= y1 - 85 <= 1, y1)

    def test_a_target_behind_the_camera_draws_nothing(self):
        self.prepare()
        target = self.ship + self.symbols['obj_len']
        self.cpu.mem_write(target + self.symbols['flags'],
                           struct.pack('>H', (1 << self.symbols['in_use']) << 8))
        self.cpu.mem_write(target + self.symbols['this_zpos'], struct.pack('>i', -500))
        self.cpu.mem_write(self.ship + self.symbols['target'], struct.pack('>I', target))
        self.obj('ai_laser', 2)
        self.lines.clear()
        self.call('draw_ai_laser')
        self.assertEqual(self.lines, [])
```

Add `'target'` to the `constants` list in `test_lasers.py`'s `setUpClass`.

Also add a test in `test_faction_ai.py` that the aim result reaches `ai_laser`:

```python
    def test_ai_laser_records_hit_or_miss(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 0, 'typ_pirate')
        for value in (0, 1, 2):
            self.field(self.ship, 'ai_laser', value)
            self.assertEqual(self.read(self.ship, 'ai_laser'), value)
```

Add `'ai_laser'` to `CONSTANTS`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_lasers.py -k ai_beam -v`
Expected: FAIL. The beam still ends at a screen edge, so `(x1, y1)` is `(-128, …)` or `(127, …)` rather than `(170, 85)`.

- [ ] **Step 3: Implement the branch**

In `src_atari/asm/special.m68`, in `draw_ai_laser`, replace the endpoint block. The old block is:

```
; BBC sends the beam to the opposite screen edge. Its moving endpoint is
; cosmetic; AI damage has already been decided from the actual firing angle.
	move.w #x_min,d2
	tst.w d0
	bpl.s .endpoint
	move.w #x_max,d2
.endpoint:
	moveq #0,d3
	move.b this_zpos+3(a5),d3
	mulu.w #y_max-y_min+1,d3
	lsr.w #8,d3
	neg.w d3
	add.w #y_max,d3
	jsr c_line
```

The new block is:

```
	move.l target(a5),d4 ; shooting at another ship ?
	ble.s .screen_edge ; no, keep the original endpoint
	move.l d4,a1
	move.l this_zpos(a1),d6
	ble .restore ; the target is behind the camera
	cmp.l #32767,d6
	bhi .restore
	move.l this_xpos(a1),d4
	move.l this_ypos(a1),d5
	moveq #9,d7
	asl.l d7,d4
	divs.w d6,d4
	bvs .restore
	asl.l d7,d5
	divs.w d6,d5
	bvs .restore
	cmp.w #32000,d4 ; keep deltas inside the 16-bit line clipper
	bgt .restore
	cmp.w #-32000,d4
	blt .restore
	cmp.w #32000,d5
	bgt .restore
	cmp.w #-32000,d5
	blt .restore
	cmp.w #2,ai_laser(a5) ; a hit lands exactly on the target
	beq.s .aimed
	movem.l d0-d1,-(sp) ; RANDOM's scratch registers are D0 and D1
	jsr random ; the same magnitude as the player's tip jitter
	and.w #7,d0
	subq.w #4,d0
	add.w d0,d4
	jsr random
	and.w #3,d0
	subq.w #2,d0
	add.w d0,d5
	movem.l (sp)+,d0-d1
.aimed:
	move.w d4,d2
	move.w d5,d3
	jsr c_line
	bra .restore

; BBC sends the beam at the player to the opposite screen edge. Its moving
; endpoint is cosmetic; AI damage has already been decided from the actual
; firing angle.
.screen_edge:
	move.w #x_min,d2
	tst.w d0
	bpl.s .endpoint
	move.w #x_max,d2
.endpoint:
	moveq #0,d3
	move.b this_zpos+3(a5),d3
	mulu.w #y_max-y_min+1,d3
	lsr.w #8,d3
	neg.w d3
	add.w #y_max,d3
	jsr c_line
```

`D4`-`D7` and `A1` are free here, because the routine saved `D0-D7/A0-A5` on entry. Add `random` to the `xref` list at the top of `special.m68` if it is not already there.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_lasers.py -v`
Expected: PASS, including the four new beam tests and every pre-existing one.

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, twenty-nine tests.

- [ ] **Step 5: Build and hand over**

Run: `build_atari.bat`
Expected: clean build.

Report `src_atari/asm/special.m68`, `src_atari/tests/test_lasers.py`, `src_atari/tests/test_faction_ai.py`.

---

### Task 10: Port to the Amiga tree and verify the whole feature

**Files:**
- Modify: `src_amiga/asm/common.def`, `src_amiga/asm/combat.m68`, `src_amiga/asm/logic.m68`, `src_amiga/asm/main.m68`, `src_amiga/asm/special.m68`
- Create: `src_amiga/tests/test_faction_ai.py`
- Modify: `src_amiga/tests/test_lasers.py`
- Modify: `src_atari/README.md`, `src_amiga/README.md`

**Interfaces:**
- Consumes: the finished Atari implementation.
- Produces: the identical feature in the Amiga tree.

- [ ] **Step 1: Confirm the two trees still match where they should**

Run: `diff src_atari/asm/logic.m68 src_amiga/asm/logic.m68`
Run: `diff src_atari/asm/combat.m68 src_amiga/asm/combat.m68`
Expected: the only differences are the ones this plan introduced in `src_atari`. Both files were byte-identical before this work apart from their "Ported from" header comment, so any other difference means something was edited in the wrong tree.

- [ ] **Step 2: Apply the same changes to the Amiga tree**

Copy each change from Tasks 1 to 9 into the matching `src_amiga/asm` file by hand or with a diff, preserving each file's own "Ported from" header line. Do not introduce a shared include, a platform switch or a cross-tree import: `AGENTS.md` forbids them.

Copy `src_atari/tests/test_faction_ai.py` to `src_amiga/tests/test_faction_ai.py` unchanged; `ROOT` resolves relative to the file, so it picks up the Amiga sources automatically. Apply the `test_lasers.py` additions from Task 9 to `src_amiga/tests/test_lasers.py` as well.

- [ ] **Step 3: Run both suites in full**

Run: `python -m unittest discover -s src_atari/tests -v`
Expected: PASS, the whole Atari suite including docking, missions, scanner and registration.

Run: `python -m unittest discover -s src_amiga/tests -v`
Expected: PASS, the whole Amiga suite.

- [ ] **Step 4: Build both games**

Run: `build_atari.bat`
Run: `build_amiga.bat`
Expected: both produce their distribution files in `output_atari` and `output_amiga` with the symbol, checksum, A6 relocation and RAM-bounds checks passing.

- [ ] **Step 5: Document and hand over**

Add a section to both `src_atari/README.md` and `src_amiga/README.md`, in English, describing the feature: the faction relation, hunters versus victims, the scanner-range limit, that the player is an ordinary candidate, that Cougar and Constrictor stand outside the system, that AI against AI uses lasers only, and that NPC kills award the player nothing while still dropping cargo. Point at `tests/test_faction_ai.py` for the coverage, matching the style of the existing `LASERS.md` and README sections.

Report every changed file to the user for a single commit, and note the two follow-ups from the spec that play testing should settle: whether NPC fights are too slow at the shipped `mood` values, and whether containers from NPC kills starve `alloc_object`.

---

### Task 11: Fix the attack run's steering (follow-up, done)

Play testing after Task 10 showed a trader picking a pirate and then flying
straight past it, firing only when the pirate crossed its sights.

**Files:**
- Modify: `src_atari/asm/logic.m68`, `src_amiga/asm/logic.m68`
- Modify: `src_atari/tests/test_faction_ai.py`, `src_amiga/tests/test_faction_ai.py`

**Cause:** spec §6.2 requires `do_attack` to hand `auto_pilot` the coordinates
from `target_coords`. Task 6 above generalised the aiming, `target_range`, the
miss threshold and `peel_off_check`, but not the steering, and the plan's own
Self-Review table credited §6.2 to Task 6 without that substitution ever being
written. The tail of `do_attack` still flew at `(0,0,0)`, which is the player,
because he is the origin of every object coordinate.

- [x] **Step 1: Write the failing test**

`do_attack` joins the `LOGIC` list in `test_faction_ai.py`, together with
`ai_laser_aim`, `ai_laser_miss_threshold`, `peel_off_check` and
`speed_control`, which it calls; `auto_pilot` and `reduce_shields` join the
stub list, and the rating `damage` table is appended to the assembly because
`do_attack` indexes it with `lea damage(pc),a0`. A Unicorn hook on the
`auto_pilot` stub records `D0`-`D2`:

```python
    def test_a_hunter_flies_towards_its_ship_target(self):
        ...
        self.assertEqual(self.steer(), (9000, 4000, -5000))

    def test_a_hunter_fighting_the_player_still_flies_at_the_origin(self):
        ...
        self.assertEqual(self.steer(), (0, 0, 0))
```

Expected: the first fails with `(0, 0, 0) != (9000, 4000, -5000)` on both CPU
models; the second passes, which is what proves the player path was never
broken.

- [x] **Step 2: Replace the hardcoded origin**

In `do_attack`, at `q_logic_m68_41`:

```
q_logic_m68_41:
	bsr target_coords ; auto-pilot towards whatever is being fought
	bsr auto_pilot
```

`target_coords` returns `(0,0,0)` for `target = 0`, so the player path assembles
to the same steering it always had.

- [x] **Step 3: Verify**

Both suites in full and both builds.

---

### Task 12: Damage reaction for AI against AI (follow-up, done)

**Files:**
- Modify: `src_atari/asm/common.def`, `src_amiga/asm/common.def`
- Modify: `src_atari/asm/combat.m68`, `src_amiga/asm/combat.m68`
- Modify: `test_faction_ai.py`, `test_lasers.py`, `test_enemy_escape.py`,
  `test_missions.py` in both trees
- Modify: `src_atari/README.md`, `src_amiga/README.md`
- Modify: the spec, which gains §6.4.1

**Cause:** the spec described how a ship delivers damage to another ship but
never how it reacts to taking it. `damage_target` subtracted health and stopped
there, while the player's fire ran a ship through `check_hit`'s break-off and,
on a heavy hit, `low_energy`. A ship shot by another ship therefore kept flying
straight.

- [x] **Step 1: Write the failing tests**

In `test_faction_ai.py`, a `hit` helper fires at a ship in slot 1 and watches
the stubs: the break-off for each starting logic (`log_cruise`, `log_run_off`,
`log_attack`, `log_peel_off`), for `act_runaway` and for `act_nothing`; the
`low_energy` retreat on a heavy hit and its absence on a light one; and no
missile even when the hit ship's own target is the player.

Expected: they fail on an undefined `hit_reaction`.

- [x] **Step 2: Split `hit_reaction` out of `check_hit`**

The block in `check_hit` between the `obj_hit` guard and
`move laser_power(a6),d0` becomes `q_subr hit_reaction,global` verbatim, ending
in `rts` at the merged `q_combat_m68_73/71/69` labels. `check_hit` calls it
where the block used to sit. Nothing else moves: the police record, `no_entry`
and `prepare_vipers` belong to the player's legal status, which the spec puts
out of scope.

- [x] **Step 3: Add `npc_hit` and gate the missile, but not the Thargons**

`npc_hit: rs.w 1` goes into the workspace block of `common.def`, next to
`npc_kill`. In `low_energy`, after the existing `tst.l target(a5)` gate:

```
	tst npc_hit(a6) ; driven off by another ship, not by the player ?
	bne.s q_combat_m68_97 ; yes, no missile either
```

A Thargon is not a missile, though: it is an ordinary faction ship, it makes no
sound and `do_missile` never touches it, so the NPC branch still releases one.
It takes the fixed `npc_thargon_prob` instead of the player's rating, and
`thargons` reads `npc_hit` to release 2..3 rather than 4..7 so a single
Thargoid cannot empty the object pool. Spec §6.6 carries the reasoning.

- [x] **Step 4: Give `damage_target` both reactions**

It saves the shooter, swaps `A5` to the ship that was hit, calls `hit_reaction`
before subtracting the damage so the ordering matches `check_hit`, then repeats
`check_hit`'s "over half its energy gone since `pre_attack`" test and calls
`low_energy` with `npc_hit` set. The kill path is unchanged apart from moving
the record into `A4` itself, because `low_energy` and friends may clobber `A4`.

- [x] **Step 5: Teach the other suites about the new routine**

`test_lasers.py`, `test_enemy_escape.py` and `test_missions.py` assemble
`check_hit` out of the real source, so each lists `hit_reaction` alongside it.
`test_lasers.py` passing unchanged otherwise is the proof that the player's own
fire still provokes exactly the old reaction.

- [x] **Step 6: Verify and document**

Both suites in full, both builds, and the README section in each tree.

---

### Task 13: The player's own state must not govern an NPC fight (follow-up, done)

A sweep of every `(a6)` global reachable from `do_attack` and the routines under
it, prompted by the Thargon gate turning out to be the second defect of that
same kind.

**Files:**
- Modify: `src_atari/asm/logic.m68`, `src_amiga/asm/logic.m68`
- Modify: `test_faction_ai.py` in both trees
- Modify: the spec, which gains §6.2.1

**Findings:** two more instances, one false alarm, and four already correct.

- `cloaking_on` and `controls_locked` in `do_attack` stopped **all** AI fire,
  whoever the target was. Neither state hides one ship from another, so
  AI-against-AI fire froze for the length of a docking computer sequence, after
  an escape capsule launch, and for as long as the player stayed cloaked.
  Hyperspace clears the objects and the torus is refused while any trader,
  pirate or Thargoid exists, so those two callers of `lock_controls` never
  showed it.
- `radar_obj` is **correct as it stands** and must not be narrowed: station
  space is `$22500` against a scanner range of `$6000`, so whenever the player
  is inside it every ship he can see is inside it too. It describes the region,
  not the player.
- `laser_type` in `release_cargo` is reached only for an asteroid, which the
  whitelist keeps out of the faction system; `target_lost`'s player globals are
  deliberate; `explode_object`'s `mission` and `station_destroyed` fire only for
  ships that cannot be targeted; `approach` and `rating` were already narrowed
  by Tasks 6, 7 and 12.

- [x] **Step 1: Write the failing test**

`do_attack` needs a hunter that will certainly shoot, which needs a controllable
`get_dist`: the stub now reads a scratch long that `prepare` seeds with
`STUB_DISTANCE`, so every existing test is unaffected. The fixture puts the
hunter square behind the world origin looking down +Z, so the player and a ship
parked on the origin give it the same range and the same line of fire, and
`ai_laser` answers whether it fired.

Expected: the fixture test passes both ways; the two AI-against-AI cases fail
with `False != True`, once per global.

- [x] **Step 2: Narrow the two gates**

```
	tst.l target(a5) ; shooting at the player ?
	bne.s .may_fire ; no, and neither of his states hides another ship
	tst cloaking_on(a6) ; cloaking device on ?
	bne no_fire ; yes
	tst controls_locked(a6)
	bne no_fire
.may_fire:
```

- [x] **Step 3: Comment `radar_obj` so it is not "fixed" later**

A note above it giving both constants and the conclusion.

- [x] **Step 4: Verify**

Both suites in full and both builds.

---

### Task 14: Missiles between ships (follow-up, done)

Reverses the "lasers only" decision of spec §6.6, which rested on two claims
that only ever applied to `do_missile` and to `launch_missile`, never to
missiles as such.

**Files:**
- Modify: `asm/common.def`, `asm/combat.m68`, `asm/logic.m68` and
  `tests/test_faction_ai.py` in both trees; `tests/test_enemy_escape.py` in
  both trees; the spec; both READMEs

- [x] **Step 1: A second logic value**

`log_ai_missile` at the end of the logic list, and a second `do_locked` entry
at the end of `logic_vectors`. A ship's missile therefore flies, defends
against and detonates exactly like the player's, and the value is the only
thing that tells them apart afterwards.

- [x] **Step 2: `launch_missile` aims at whatever is being fought**

`target` greater than zero picks the ship branch: the 2000-unit minimum range
is measured with `get_dist` to that ship rather than through `obj_range`, the
player's cloaking device is not consulted, the missile is created as
`log_ai_missile` with `target` copied across, and neither `sfx_alert` nor
"Incoming missile" is issued. Anything else keeps the original player path
untouched, which also makes a stray `no_target` harmless.

- [x] **Step 3: `low_energy` lets it go**

Away from the player the roll is `npc_launch_prob` (the old
`npc_thargon_prob`, renamed now that it governs both releases); a Thargoid
still releases thargons, anything else fires a missile, and only at a real
ship -- `target` must be greater than zero, which excludes the player and
`no_target`. The player-facing missile keeps its `target = 0` **and**
`npc_hit` clear condition from Task 12, so no missile reaches him out of a
fight he is not in.

- [x] **Step 4: Nothing may chase a freed record**

New `drop_missiles` removes every missile flying at a dying object and reports
whether one of them was the player's. `target_lost` uses it in place of its
single `check_missile` removal and prints "Target lost" only on that report.
`check_missile` itself is narrowed to `log_locked`, because its other caller
(`vector.m68:1000`) uses it to refuse the player a fresh lock. `do_locked`
gains the `target_lost` call that `check_hit` and `damage_target` already had.

- [x] **Step 5: Bookkeeping and the player's own equipment**

`do_locked` sets `npc_kill` around `explode_object` for a ship's missile, and
consults `ecm_jammed` only for the player's.

- [x] **Step 6: Retire the three tests that asserted the old rule**

`test_a_ship_fighting_another_ship_launches_no_missile` and the two beside it
described the behaviour being replaced. They become tests of the new contract,
and `test_enemy_escape.py` gains a `get_dist` stub because `launch_missile`
now calls it.

- [x] **Step 7: Verify**

Both suites in full and both builds. The three narrowings were checked by
mutation: removing the `npc_kill` guard, the `log_locked` filter in
`drop_missiles` and the one in `check_missile` each fails a test.

- [x] **Step 8: Audit the three player-facing behaviours**

Every routine on them was diffed against `src_orig`. `fire_missile`,
`target_missile`, `unarm_missile`, `engage_ecm`, `ecm`, `ecm_check` and
`do_missile` are identical to the 1988 original, and `low_energy`'s player
branch is identical from `.player:` onwards. `launch_missile`'s player path
differs only by one write moving an instruction earlier.

The audit found one real regression in Step 4: `do_locked` called `target_lost`
while the killing missile was still in the object list, so `drop_missiles`
found it and answered every successful player missile kill with "Target lost".
Fixed by flagging the missile `remove` first and having `drop_missiles` skip
records already flagged, with a test for each of the two missile kinds.

It also found that the player's ECM had no test at all. Four were added, and a
mutation of each of the three behaviours -- silencing the player-facing launch,
making `ecm_check` ignore missiles, and disabling his ECM jammer -- now fails
tests.

- [x] **Step 13: Check the ECM jammer**

`jammer_toggle`, `engage_ecm` and `thanks5`, which awards it, are identical to
the 1988 original. It had no test of its own, which mattered more than it
looked: the ECM repair turned a ship's answer from a no-op into a wave that
really destroys the missile, so the jammer went from decorative to
load-bearing.

The audit also **reversed a mistake of Task 13's own**. That task had narrowed
`ecm_jammed` in `do_locked` to the player's missiles, on the reading that it
protects his own shots. It does not: `engage_ecm` refuses him his own ECM while
the jammer is on, so it is an emitter that silences the use of ECM around him
for everyone. It belongs with `radar_obj`, not with `cloaking_on`, and the
narrowing is removed; that branch is byte-identical to 1988 again. Four tests
now cover it, and a mutation that ignores the jammer fails them.

- [x] **Step 12: Count the Constrictor objective wherever it dies**

The increment lived in `check_hit`, so only a laser kill finished mission #1;
a missile or a ram left it running. It also fired whatever the mission state
was. Moved into `explode_object` beside the alien station's, sharing one
"already exploding" guard and each keeping its own state guard. Three tests
cover laser, missile and ramming end to end, one covers the state guard and
the double count, and one records that the energy bomb cannot reach it.
Both mutations -- dropping the state guard, and pointing the type test at the
wrong ship -- fail tests.

- [x] **Step 11: Check the three mission ships**

The alien station is sound: `explode_object` finishes objective #5 on every
destruction path, guarded against double counting, and the `dodec` is outside
the whitelist so no ship can ever shoot it.

The Cougar and the Constrictor were **broken**, and had been since Task 6.
`pirate_attack` spawns them in `log_attack` with the `no_target` that
`alloc_object` leaves; `retarget` skips them because they are not combat ships;
so the first `do_attack` frame read "nothing to fight" and sent them cruising
away. Missions 3 and 4 would have been unwinnable. `do_attack` now asks
`is_combat_ship` before acting on a missing target, and both spawn sites name
the player outright. Four tests cover it, including that a whitelisted ship
with nothing left still disengages. `test_lasers.py` assembles `do_attack`, so
it lists `is_combat_ship` too.

- [x] **Step 10: Sweep the whole feature for drift**

Every routine in `combat.m68` and `logic.m68` was compared with `src_orig`
ignoring comments. 27 of the 47 in `combat.m68` and 17 of the 26 in
`logic.m68` are byte-identical to the 1988 original, and each remaining
difference belongs to a named task here or to earlier work in this repository
(`fire`, `laser_in_sights` and `launch_bomb` to the laser rework, the
`logic_vectors` photon slot to its removal). Nothing has drifted.

Two tests were added: the whole AI-against-AI fight driven through the real
`retarget` and `do_attack`, and `peel_off_check`'s choice of input. Both were
confirmed by mutation -- measuring a ship target's range from the player breaks
the fight test at the aiming cone.

- [x] **Step 9: Audit the player's missile lock**

`target_missile`, `unarm_missile`, `fire_missile` and `inst_missiles` are
identical to the 1988 original; `check_sights` was not touched by this work
(its differences are the ship identification feature). The one routine the lock
depends on that did change is `check_missile`, and `tests/test_registration.py`
already assembles the real `check_sights` and the real `check_missile`
together. Two tests were added there for the case the narrowing could have
broken -- a missile already on intercept refusing a second lock -- and both
directions of a mutation to that filter now fail them.

---

## Self-Review

**Spec coverage**

| Spec section | Task |
| --- | --- |
| 4.1 Combat participants | 1 |
| 4.2 Factions | 1 |
| 4.3 Hunters and victims | 5 (the `act_attack` gate in `retarget`) |
| 4.4 The player as a candidate | 4 |
| 4.5 Target storage, `no_target`, `alloc_object` | 3 |
| 5 Target selection, metric, cadence, validation | 2, 4, 5, 6 |
| 5.1 Entering and leaving combat | 5 |
| 6.1 `target_coords` | 3 |
| 6.2 `do_attack`, `target_range`, aiming, `peel_off_check` | 6 |
| 6.3 `angry` and the cockpit warning | 6 |
| 6.4 Damage | 6 (strength), 7 (delivery) |
| 6.5 NPC kills | 7 |
| 6.6 Missiles, ECM, energy bomb | 8, then 14 |
| 7 Rendering | 9 |
| 8 Performance | 5 (round robin), 2 (metric) |
| 6.2.1 The player's own state | 13 |
| 6.4.1 The damaged ship's reaction | 12 |
| 9 Files touched | 10 |
| 10 Testing | 1 to 14 |
| 11 Risks | 10 (handover note), 12 and 14 (two added) |
| 12 Amendments | 11 to 14 |

No spec section is unimplemented.

**Placeholder scan**

No "TBD", "TODO", "similar to Task N" or "add error handling" remains. Every code step carries the code to be written.

**Type consistency**

- `is_combat_ship`, `is_hostile`, `chebyshev_range`, `pick_target`, `combat_state`, `retarget`, `damage_target` are spelled identically in their definitions, their call sites and the test routine lists.
- `target_coords`, `validate_target`, `target_range_calc` likewise.
- `target_range` is a long everywhere; `retarget_slot` and `npc_kill` are words everywhere.
- `no_target` is `-1` in the assembler and is sign-corrected once in the test harness.
- `ai_laser` holds 0, 1 or 2 in Tasks 6 and 9 consistently, and every pre-existing reader only tests it for non-zero.
