# Random Encounters Implementation Plan

> Historical design/implementation record. The optional CPU-emulation test
> suite was removed on 2026-09-19. References below to its dependency, test
> files, sample harness code and commands are historical, not current setup
> instructions. Use each source tree's README for current checks.

> Routing update, 2026-09-21: the single `create_pirates` hook described below
> missed torus events. Both entries now use `spawn_pirate_wave`; see
> [normal-flight and torus routing](2026-09-21-random-encounter-torus-routing.md).

**Goal:** Half of the ordinary deep-space pirate waves become a small group that
is already fighting itself, which the player flies into rather than is ambushed
by.

**Architecture:** One new routine, `random_encounter`, with five small helpers
and four tables, all private to `combat.m68`. It is reached from a single
substitution at the end of `create_pirates`, behind guards that send every
mission state down the existing `pirate_attack` path. The members are created
in `log_cruise`; the faction targeting feature already makes them hostile to
each other and `retarget` starts the fight.

**Tech Stack:** Motorola 68000 assembler (vasm `-m68000`, Quelo-derived macros
in `asm/macros.m68`), Python 3 + `unicorn==2.1.4` for unit tests.

**Spec:** `docs/2026-09-17-random-encounter-design.md`

## Global Constraints

- **Git is the user's job.** Per `AGENTS.md`: "The user handles all Git
  operations exclusively. Do not run any Git commands." No task commits,
  stages, branches or inspects git. Each task ends by reporting the changed
  files so the user can commit.
- **Documentation is English.** Per `AGENTS.md`.
- **Documentation lives flat in `docs/`.** Per `AGENTS.md`: no subdirectories,
  and the documents do not reference authoring skills.
- **Two trees, no sharing.** Gameplay changes go into `src_atari` and
  `src_amiga` separately. No platform switches, no cross-tree imports.
  `src_orig` is never touched.
- **Tasks 1-4 change `src_atari` only.** Task 5 ports the finished, tested
  result to `src_amiga`.
- **Build from the repository root:** `build_atari.bat`, `build_amiga.bat`.
- **Run tests from the repository root:**
  `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
- **No loose files in the project root.** Intermediate output belongs in the
  tree's `build` directory.
- **Assembler style:** new routines use `q_subr`, plain `rts` and `.local`
  labels, matching `is_combat_ship` and `pick_target`. A routine that returns
  condition codes keeps a single exit.
- **Existing behaviour is unchanged.** Any failure in the existing suites is a
  regression, not an expected update. `pirate_attack`, `random_pirate` and
  every mission spawn keep their behaviour exactly.
- **`common.def` is not touched.** The roles and the spacing are local
  constants of `combat.m68`; the working state goes in that module's own
  `q_vars` block, which uses 12 of its 32 bytes.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `src_atari/asm/combat.m68` | Everything: constants, module variables, the six routines and the four tables, and the substitution in `create_pirates` |
| `src_atari/tests/test_faction_ai.py` | The whole suite for this feature; it already assembles `combat.m68` and has the object-pool and random stubs the encounter needs |
| `src_amiga/asm/combat.m68`, `src_amiga/tests/test_faction_ai.py` | The identical port |
| `src_atari/README.md`, `src_amiga/README.md` | A section describing the feature |
| `docs/2026-09-17-random-encounter-design.md` | The spec; updated only if implementation contradicts it |

---

### Task 1: Harness groundwork and the ship tables

The suite's `rand` stub answers 0 for everything, which is what every existing
test wants and useless for a routine whose whole job is a roll. It becomes
faithful to the real routine instead, driven by a scratch word that defaults to
zero, so no existing test changes.

**Files:**
- Modify: `src_atari/asm/combat.m68` (local constants after `spacing1`, new
  routine and tables before `; ---- LOCAL DATA ----`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Produces:
  - `role_pirate` = 1, `role_trader` = 2, `role_thargoid` = 3, `role_viper` = 4,
    `role_bounty` = 5, `spacing2` = 1000 — local constants of `combat.m68`.
    Numbered from one because a zero byte ends a row of `encounter_groups`.
  - `encounter_type` — entry `D0.W` = role; exit `D0.W` = object type.
    Corrupts `D0`, `D1`, `D2`, `A0`.
  - `encounter_pirates`, `no_encounter_pirates` = 7,
    `encounter_traders`, `no_encounter_traders` = 4, `encounter_fixed`.

- [ ] **Step 1: Make the `rand` stub faithful**

In `src_atari/tests/test_faction_ai.py`, add a scratch word beside the others:

```python
    ALLOC_BUDGET, RANDOM_VALUE, ALLOC_POOL = 0x50000, 0x50002, 0x51000
    #: GET_DIST's answer. PREPARE seeds it with STUB_DISTANCE, so a test only
    #: plants a value when the distance itself is what it is exercising.
    DIST_VALUE = 0x50004
    #: RAND's 16-bit input, before it is scaled into the caller's range. Zero
    #: gives zero for every range, which is what every earlier test expects.
    RAND_VALUE = 0x50008
```

Replace the `rand` half of the stub text:

```python
        text += ('\nrandom:\n\tmoveq #0,d0\n\tmove.w $%x,d0\n\trts\n'
                 % cls.RANDOM_VALUE)
        # RAND scales a 16-bit value into 0..D2-1 exactly as MATHS does, so a
        # test can ask for a chosen index instead of a chosen bit pattern.
        text += ('\nrand:\n'
                 '\tmoveq #0,d0\n'
                 '\tmove.w $%x,d0\n'
                 '\tmulu d2,d0\n'
                 '\tswap d0\n'
                 '\trts\n' % cls.RAND_VALUE)
```

Add the helper that asks for an index rather than a bit pattern:

```python
    def roll(self, index, count):
        """Plant the RAND input that yields `index` out of `count`."""
        self.scratch(self.RAND_VALUE, -(-index * 65536 // count) if index else 0)
```

- [ ] **Step 2: Write the failing test**

Add to `CONSTANTS` in `src_atari/tests/test_faction_ai.py`:

```python
    'role_pirate', 'role_trader', 'role_thargoid', 'role_viper', 'role_bounty',
    'spacing2', 'encounter_pirates', 'encounter_traders', 'encounter_groups',
    'no_encounter_pirates', 'no_encounter_traders',
    'gecko', 'moray', 'adder', 'mamba', 'asp', 'sidewinder', 'anaconda',
    'cobra_mk1', 'ferdelance', 'boa', 'wolf',
    'splanet', 'govern', 'rand_limit', 'rand_range', 'x_vector', 'y_vector',
    'mission', 'pirate_ctr',
```

Add to `COMBAT`:

```python
          'encounter_type',
```

And the tests:

```python
    def test_a_role_rolls_only_from_its_own_table(self):
        """RANDOM_PIRATE's range holds the Thargoid, the Boa and the Wolf. The
        encounter's raiders are chosen deliberately and hold none of them."""
        tables = {
            'role_pirate': ('krait', 'gecko', 'moray', 'adder', 'mamba', 'asp',
                            'sidewinder'),
            'role_trader': ('cobra', 'python', 'anaconda', 'cobra_mk1'),
        }
        self.prepare()
        for role, ships in tables.items():
            with self.subTest(role=role):
                expected = {self.symbols[name] for name in ships}
                seen = set()
                for index in range(len(ships)):
                    self.roll(index, len(ships))
                    seen.add(self.call('encounter_type',
                                       d0=self.symbols[role]))
                self.assertEqual(seen, expected)
                for name in ('thargoid', 'boa', 'wolf', 'ferdelance', 'viper'):
                    self.assertNotIn(self.symbols[name], seen)

    def test_a_fixed_role_names_one_ship(self):
        self.prepare()
        for role, ship in (('role_thargoid', 'thargoid'),
                           ('role_viper', 'viper'),
                           ('role_bounty', 'ferdelance')):
            with self.subTest(role=role):
                for index in range(4):  # the roll must not reach these
                    self.roll(index, 4)
                    self.assertEqual(self.call('encounter_type',
                                               d0=self.symbols[role]),
                                     self.symbols[ship])
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k role -v`
Expected: FAIL with vasm reporting `encounter_type` and the role constants
undefined.

- [ ] **Step 4: Add the constants**

In `src_atari/asm/combat.m68`, after `spacing1: equ 700 ; spacing of squadrons`:

```
spacing2: equ 1000 ; spacing of encounter groups
; Roles a random encounter's template can ask for. The pirate and trader roles
; roll from their own tables, which are narrower than RANDOM_PIRATE's type
; range on purpose; the other three name one ship and are never rolled.
; Numbered from one: a zero byte ends a row of ENCOUNTER_GROUPS, so no role
; may be zero or the walk would stop in the middle of a template.
role_pirate: equ 1
role_trader: equ 2
role_thargoid: equ 3
role_viper: equ 4
role_bounty: equ 5
```

- [ ] **Step 5: Add the routine and its tables**

In `src_atari/asm/combat.m68`, immediately before `; ---- LOCAL DATA ----`:

```
; ******************************************************
; **												  **
; ** ENCOUNTER_TYPE - CHOOSE A SHIP FOR A GROUP ROLE  **
; **												  **
; ******************************************************

; Turns one of a template's roles into an object type. The pirate and trader
; roles roll from their own tables; the other three name a single ship.

; Entry: D0 = role
; Exit:  D0 = object type

; Regs: D0, D1, D2, A0 corrupt.
; Subr: RAND

	q_subr encounter_type,global

	cmp #role_pirate,d0
	beq.s .pirates
	cmp #role_trader,d0
	beq.s .traders
	sub #role_thargoid,d0 ; the three the template names outright
	add d0,d0
	lea encounter_fixed(pc),a0
	move (a0,d0),d0
	rts
.pirates:
	lea encounter_pirates(pc),a0
	moveq #no_encounter_pirates,d2
	bra.s .roll
.traders:
	lea encounter_traders(pc),a0
	moveq #no_encounter_traders,d2
.roll:
	jsr rand ; 0..D2-1
	add d0,d0
	move (a0,d0),d0

	q_ret


; Ships a random encounter may roll. Neither table holds the Thargoid, which a
; template names where it wants one, and the pirates leave out the Boa and the
; Wolf: the encounter's raiders are the small and medium ships.

encounter_pirates:

	dc.w krait,gecko,moray,adder,mamba,asp,sidewinder

no_encounter_pirates: equ (*-encounter_pirates)/2

encounter_traders:

	dc.w cobra,python,anaconda,cobra_mk1

no_encounter_traders: equ (*-encounter_traders)/2

; Indexed by role minus ROLE_THARGOID.

encounter_fixed:

	dc.w thargoid,viper,ferdelance
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, the whole file, including every earlier test — the `rand` stub
still answers zero wherever no test plants a value.

- [ ] **Step 7: Build and hand over**

Run: `build_atari.bat`
Expected: links, with the checksum and RAM checks passing.

Report `src_atari/asm/combat.m68` and `src_atari/tests/test_faction_ai.py` as
changed.

---

### Task 2: Choosing a template

**Files:**
- Modify: `src_atari/asm/combat.m68`
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: the role constants of Task 1.
- Produces:
  - `encounter_groups` — the template table.
  - `encounter_skip` — entry `A0` = ptr: a row; exit `A0` = ptr: the next row.
    Corrupts `A0`.
  - `encounter_template` — entry none; exit `A0` = ptr: the chosen row's first
    role/count pair. Corrupts `D0`, `D1`, `D2`, `A0`.

- [ ] **Step 1: Write the failing test**

Add `'encounter_template'` and `'encounter_skip'` to `COMBAT`, and add
`UC_M68K_REG_A0` to the `unicorn.m68k_const` import. Then:

```python
    #: Section 4.3 of the spec, as the assembler should encode it.
    TEMPLATES = (
        (1, 0, (('role_thargoid', 1), ('role_pirate', 2))),
        (1, 0, (('role_thargoid', 1), ('role_trader', 2))),
        (4, 0, (('role_pirate', 2), ('role_trader', 2))),
        (3, 2, (('role_pirate', 2), ('role_viper', 2))),
        (3, 1, (('role_pirate', 2), ('role_viper', 1))),
        (2, 0, (('role_pirate', 2), ('role_bounty', 1))),
        (2, 0, (('role_pirate', 2), ('role_bounty', 1), ('role_trader', 1))),
    )

    def government(self, value):
        self.word(VARIABLES + self.symbols['splanet'] + self.symbols['govern'],
                  value)

    def pairs_at(self, address):
        """Decode role/count pairs up to the terminating zero."""
        out = []
        while self.cpu.mem_read(address, 1)[0]:
            role, count = self.cpu.mem_read(address, 2)
            out.append((role, count))
            address += 2
        return out

    def expected_pairs(self, template):
        return [(self.symbols[role], count) for role, count in template[2]]

    def test_the_template_table_matches_the_spec(self):
        self.prepare()
        address = self.symbols['encounter_groups']
        for weight, govern, _ in self.TEMPLATES:
            self.assertEqual(self.cpu.mem_read(address, 2)[0], weight)
            self.assertEqual(self.cpu.mem_read(address, 2)[1], govern)
            address += 2
            while self.cpu.mem_read(address, 1)[0]:
                address += 2
            address += 1
        self.assertEqual(self.cpu.mem_read(address, 1)[0], 0, 'table must end')

    def chosen_template(self):
        self.call('encounter_template')
        return self.pairs_at(self.cpu.reg_read(UC_M68K_REG_A0))

    def test_a_template_is_never_chosen_against_its_government(self):
        """Two templates carry police and are gated; the rest always apply."""
        self.prepare()
        for govern in range(8):
            allowed = [t for t in self.TEMPLATES if t[1] <= govern]
            total = sum(t[0] for t in allowed)
            seen = []
            for index in range(total):
                self.government(govern)
                self.roll(index, total)
                seen.append(self.chosen_template())
            with self.subTest(govern=govern):
                self.assertEqual(
                    seen, [self.expected_pairs(t) for t in allowed
                           for _ in range(t[0])],
                    'government %d chose the wrong templates' % govern)

    def test_the_weights_hold(self):
        """Section 4.4: a Thargoid in an eighth of encounters, a fifth under
        anarchy where the police templates drop out."""
        self.prepare()
        for govern, share in ((0, 2 / 10), (1, 2 / 13), (7, 2 / 16)):
            allowed = [t for t in self.TEMPLATES if t[1] <= govern]
            total = sum(t[0] for t in allowed)
            thargoids = 0
            for index in range(total):
                self.government(govern)
                self.roll(index, total)
                roles = [role for role, _ in self.chosen_template()]
                thargoids += self.symbols['role_thargoid'] in roles
            with self.subTest(govern=govern):
                self.assertAlmostEqual(thargoids / total, share, places=6)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k template -v`
Expected: FAIL with vasm reporting `encounter_template`, `encounter_skip` and
`encounter_groups` undefined.

- [ ] **Step 3: Add the table**

In `src_atari/asm/combat.m68`, after `encounter_fixed`:

```
; Groups a random encounter may place, from section 4.3 of the design. Each row
; is a weight, the lowest government it may appear under, then role and maximum
; count pairs ended by a zero byte. The actual count is RAND(max)+1, which is 1
; for a maximum of 1, so a fixed member and a variable one follow one rule.

encounter_groups:

	dc.b 1,0,role_thargoid,1,role_pirate,2,0
	dc.b 1,0,role_thargoid,1,role_trader,2,0
	dc.b 4,0,role_pirate,2,role_trader,2,0
	dc.b 3,2,role_pirate,2,role_viper,2,0
	dc.b 3,1,role_pirate,2,role_viper,1,0
	dc.b 2,0,role_pirate,2,role_bounty,1,0
	dc.b 2,0,role_pirate,2,role_bounty,1,role_trader,1,0
	dc.b 0 ; end of the table

	even
```

- [ ] **Step 4: Add the two routines**

Immediately after the table:

```
; ***********************************************
; **										   **
; ** ENCOUNTER_SKIP - STEP TO THE NEXT TEMPLATE **
; **										   **
; ***********************************************

; Entry: A0 = ptr: a row of ENCOUNTER_GROUPS
; Exit:  A0 = ptr: the row after it

; Regs: A0 corrupt.

	q_subr encounter_skip

	addq.l #2,a0 ; past the weight and the government
.pairs:
	tst.b (a0)
	beq.s .done
	addq.l #2,a0
	bra.s .pairs
.done:
	addq.l #1,a0 ; past the terminator

	q_ret


; ********************************************************
; **													**
; ** ENCOUNTER_TEMPLATE - CHOOSE A GROUP FOR THE SYSTEM **
; **													**
; ********************************************************

; Picks one row by weight, ignoring every row the system's government forbids.
; Two passes: the first totals the weights allowed here, the second walks again
; and stops where the roll runs out. The total is never zero, because five of
; the seven rows carry no government condition.

; Entry: None
; Exit:  A0 = ptr: the chosen row's first role/count pair

; Regs: D0, D1, D2, A0 corrupt.
; Subr: RAND, ENCOUNTER_SKIP

	q_subr encounter_template,global

	move splanet+govern(a6),d1 ; the system the player is in
	moveq #0,d2 ; weight available here
	lea encounter_groups(pc),a0
.total:
	moveq #0,d0
	move.b (a0),d0 ; this row's weight
	beq.s .roll ; end of the table
	cmp.b 1(a0),d1 ; government high enough for it ?
	blo.s .total_next
	add d0,d2
.total_next:
	bsr encounter_skip
	bra.s .total
.roll:
	jsr rand ; 0..D2-1
	move d0,d2 ; the roll
	lea encounter_groups(pc),a0
.pick:
	moveq #0,d0
	move.b (a0),d0
	cmp.b 1(a0),d1 ; skipped rows spend no weight
	blo.s .pick_next
	sub d0,d2
	bmi.s .chosen
.pick_next:
	bsr encounter_skip
	bra.s .pick
.chosen:
	addq.l #2,a0 ; past the weight and the government

	q_ret
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, the whole file.

- [ ] **Step 6: Build and hand over**

Run: `build_atari.bat`
Expected: links cleanly.

Report the two changed files.

---

### Task 3: Building the group

**Files:**
- Modify: `src_atari/asm/combat.m68` (the `q_vars combat` block at line 50, and
  new routines)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `encounter_template`, `encounter_type`, `spacing2`.
- Produces:
  - `encounter_row`, `encounter_lead`, `encounter_role`, `encounter_left`,
    `encounter_seat` — module variables of `combat`.
  - `encounter_place` — entry `A4` = the first member; exit none.
  - `encounter_offset` — entry `A4` = a follower; exit none.
  - `encounter_member` — entry `encounter_role` set; exit carry set when a
    member was created, clear when the object pool was empty.
  - `random_encounter` — entry none, exit none.

- [ ] **Step 1: Write the failing test**

Add `'random_encounter'`, `'encounter_member'`, `'encounter_place'`,
`'encounter_offset'` to `COMBAT`, `'orbit'` and `'vector_pos'` to `STUBBED`,
and `'encounter_lead'`, `'encounter_seat'` to `CONSTANTS`. Then:

```python
    def encounter(self, govern=7, template=0, budget=8):
        """Run RANDOM_ENCOUNTER with a chosen template and a stocked pool."""
        allowed = [t for t in self.TEMPLATES if t[1] <= govern]
        total = sum(t[0] for t in allowed)
        index = sum(t[0] for t in allowed[:template])
        self.government(govern)
        self.roll(index, total)
        self.scratch(self.ALLOC_BUDGET, budget)
        self.call('random_encounter')
        return [self.ALLOC_POOL + n * self.symbols['obj_len']
                for n in range(budget - self.member_budget())]

    def member_budget(self):
        return int.from_bytes(self.cpu.mem_read(self.ALLOC_BUDGET, 2), 'big')

    def test_a_group_is_built_from_its_template(self):
        """RAND answers its lowest index, so every 1-2 role gives one ship."""
        self.prepare()
        self.watch_stubs()
        members = self.encounter(govern=7, template=2)  # pirates and traders
        self.assertEqual(len(members), 2)
        pirates = {self.symbols[n] for n in
                   ('krait', 'gecko', 'moray', 'adder', 'mamba', 'asp',
                    'sidewinder')}
        traders = {self.symbols[n] for n in
                   ('cobra', 'python', 'anaconda', 'cobra_mk1')}
        self.assertIn(self.read(members[0], 'type'), pirates)
        self.assertIn(self.read(members[1], 'type'), traders)

    def test_every_member_cruises_and_hunts_nobody_yet(self):
        self.prepare()
        for member in self.encounter(govern=7, template=6):
            self.assertEqual(self.read(member, 'logic'),
                             self.symbols['log_cruise'])
            self.assertEqual(self.read(member, 'target', 4),
                             self.symbols['no_target'])
            self.assertTrue(self.read(member, 'flags')
                            & (1 << (8 + self.symbols['in_use'])))

    def test_no_group_exceeds_four_members(self):
        self.prepare()
        for template in range(len(self.TEMPLATES)):
            with self.subTest(template=template):
                self.prepare()
                self.roll(1, 2)  # every 1-2 role gives its maximum
                self.assertLessEqual(len(self.encounter(govern=7,
                                                        template=template)), 4)

    def test_a_group_finishes_short_when_the_pool_runs_dry(self):
        self.prepare()
        members = self.encounter(govern=7, template=2, budget=1)
        self.assertEqual(len(members), 1)

    def test_the_group_is_placed_ahead_of_the_player(self):
        """ORBIT is stubbed to answer behind him; ENCOUNTER_PLACE must mirror
        it into the hemisphere he is facing, keeping the radius."""
        self.prepare()
        self.watch_stubs()
        self.encounter(govern=7, template=2)
        self.assertIn('orbit', self.entered)
        self.assertIn('vector_pos', self.entered)
        self.assertGreaterEqual(self.read(self.ALLOC_POOL, 'zpos', 4), 0)

    def test_nothing_is_announced(self):
        self.prepare()
        self.watch_stubs()
        self.encounter(govern=7, template=2)
        self.assertNotIn('disp_message', self.entered)
        self.assertNotIn('fx', self.entered)
```

The `orbit` stub must answer with a position behind the player so the mirroring
is exercised. Replace its plain `rts` by adding it to the hand-written stubs in
`stubs()`, before the generic loop:

```python
        # ORBIT answers a fixed position behind the player, so
        # ENCOUNTER_PLACE's mirroring into the front hemisphere is exercised.
        text += ('\norbit:\n'
                 '\tmove.l #1234,xpos(a4)\n'
                 '\tmove.l #-5678,ypos(a4)\n'
                 '\tmove.l #-20000,zpos(a4)\n'
                 '\trts\n')
        done = {'alloc_object', 'get_dist', 'random', 'rand', 'orbit'}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k encounter -v`
Expected: FAIL with vasm reporting `random_encounter` and its helpers
undefined.

- [ ] **Step 3: Add the module variables**

In `src_atari/asm/combat.m68`, inside the existing `q_vars combat` block, after
`magnitude: rs.w 1`:

```
encounter_row: rs.l 1 ; ptr: the chosen template's next role/count pair
encounter_lead: rs.l 1 ; ptr: the group's first member, zero until it exists
encounter_role: rs.w 1 ; the role being placed
encounter_left: rs.w 1 ; how many of that role are still to come
encounter_seat: rs.w 1 ; which offset the next follower takes
```

That is 14 bytes on top of the block's existing 12, inside its 32.

- [ ] **Step 4: Add the placement helpers**

After `encounter_template` in `src_atari/asm/combat.m68`:

```
; **************************************************
; **											  **
; ** ENCOUNTER_PLACE - PUT THE FIRST MEMBER OUT   **
; **											  **
; **************************************************

; The ambush's own range, but always in the half of space the player is facing
; and pointing back at him. ORBIT computes z = r*sin(a)*cos(b), so the sign of
; ZPOS is the only thing to correct and the radius is untouched. Facing him is
; not decoration: the range reaches RADAR_RANGE, and DO_CRUISING removes an
; object that passes it, so a group in LOG_CRUISE facing away would delete
; itself within a frame or two.

; Entry: A4 = ptr: the first member
; Exit:  None

; Regs: D0, D1, D2, A0 corrupt.
; Subr: RAND, ORBIT, VECTOR_POS

	q_subr encounter_place

	move #rand_range,d2 ; range = rand(rand_range)+rand_limit
	jsr rand
	add #rand_limit,d0
	ext.l d0
	move #360,d1
	jsr orbit
	tst.l zpos(a4) ; did it land behind him ?
	bpl.s .ahead
	neg.l zpos(a4) ; mirror it in front
.ahead:
	jmp vector_pos ; point it at him and return


; ****************************************************
; **												**
; ** ENCOUNTER_OFFSET - STEP A FOLLOWER ASIDE		**
; **												**
; ****************************************************

; Moves a copied member one step along the first member's own axes, in the
; manner of PIRATE_ATTACK's squadron. Four seats cover any group this design
; can build.

; Entry: A4 = ptr: a follower holding the first member's position and vectors
; Exit:  None

; Regs: D0, D1, D6, A0, A1, A2 corrupt.

	q_subr encounter_offset

	move encounter_seat(a6),d0
	addq #1,encounter_seat(a6)
	and #3,d0 ; four seats, wrapping
	asl #2,d0
	lea encounter_positions(pc),a0
	move (a0,d0),d1 ; A1 = ptr: the vector to step along
	lea (a4,d1.w),a1
	move 2(a0,d0),d0 ; the spacing
	lea xpos(a4),a2 ; A2 = ptr: the coordinates
	q_loop 1,d6,3
	move (a1)+,d1
	muls d0,d1
	asl.l #2,d1
	swap d1
	ext.l d1
	add.l d1,(a2)+
	q_next 1,d6

	q_ret


; Where a follower sits relative to the first member.

encounter_positions:

	dc.w x_vector,+spacing2
	dc.w x_vector,-spacing2
	dc.w y_vector,+spacing2
	dc.w y_vector,-spacing2
```

- [ ] **Step 5: Add the member builder and the routine**

After `encounter_positions`:

```
; ****************************************************
; **												**
; ** ENCOUNTER_MEMBER - CREATE ONE SHIP OF A GROUP	**
; **												**
; ****************************************************

; Entry: ENCOUNTER_ROLE = the role to place
; Exit:  IF a member was created THEN carry set ELSE carry clear

; Regs: D0, D1, D2, D6, A0, A1, A2, A4, A5 corrupt.
; Subr: ALLOC_OBJECT, ENCOUNTER_PLACE, COPY_OBJECT, ENCOUNTER_OFFSET,
;		ENCOUNTER_TYPE, CREATE_OBJECT

	q_subr encounter_member

	jsr alloc_object ; a record for it
	bcc.s .none ; none left
	tst.l encounter_lead(a6) ; is this the first of the group ?
	bne.s .follower
	move.l a4,encounter_lead(a6)
	bsr encounter_place
	bra.s .build
.follower:
	move.l encounter_lead(a6),a5 ; its position and vectors
	jsr copy_object
	bsr encounter_offset
.build:
	move encounter_role(a6),d0
	bsr encounter_type
	move d0,type(a4)
	move.b #1,flags(a4) ; in use
	move #log_cruise,logic(a4) ; nobody here is attacking the player
	move.l #no_target,target(a4) ; RETARGET gives it one of its own
	st velocity(a4) ; CREATE_OBJECT raises it to VEL_MAX
	jsr create_object
	ori #1,ccr ; created
	rts
.none:
	andi #$fe,ccr ; the pool is empty
	rts


; ****************************************************
; **												**
; ** RANDOM_ENCOUNTER - A GROUP ALREADY AT WAR		**
; **												**
; ****************************************************

; Places a small group in deep space whose members are hostile to each other
; under the faction rules, in front of the player and at the ambush's range.
; Nothing is announced and nothing is aimed at him: he has flown into somebody
; else's fight. RETARGET starts it, because the members are a thousand units
; apart and he is at least sixteen thousand away.

; Entry: None
; Exit:  None

; Regs: ?
; Subr: ENCOUNTER_TEMPLATE, ENCOUNTER_MEMBER, RAND

	q_subr random_encounter,global

	bsr encounter_template ; A0 = the chosen row's first pair
	move.l a0,encounter_row(a6)
	clr.l encounter_lead(a6) ; no first member yet
	clr encounter_seat(a6)
.roles:
	move.l encounter_row(a6),a0
	moveq #0,d0
	move.b (a0),d0 ; the role, zero ends the row
	beq.s .done
	move d0,encounter_role(a6)
	moveq #0,d2
	move.b 1(a0),d2 ; how many of it at most
	addq.l #2,a0
	move.l a0,encounter_row(a6)
	jsr rand ; 0..max-1
	q_inc d0 ; 1..max
	move d0,encounter_left(a6)
.one:
	bsr encounter_member
	bcc.s .done ; the pool is empty; the group ends here
	q_dec encounter_left(a6)
	bne.s .one
	bra.s .roles
.done:
	rts
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, the whole file.

- [ ] **Step 7: Build and hand over**

Run: `build_atari.bat`
Expected: links, and the module variable check passes — the block now uses 26
of its 32 bytes.

Report the two changed files.

---

### Task 4: The substitution, and the mission guards

The task the spec is most careful about. Every mission that spawns a named ship
must keep the old path.

**Files:**
- Modify: `src_atari/asm/combat.m68` (`create_pirates`, its final
  `bra pirate_attack`)
- Modify: `src_atari/tests/test_faction_ai.py`

**Interfaces:**
- Consumes: `random_encounter`.
- Produces: nothing new; `create_pirates` keeps its signature.

- [ ] **Step 1: Write the failing test**

Add `'create_pirates'` to `COMBAT` and `'pirate_attack'` to `STUBBED`. Then:

```python
    def deep_space_wave(self, mission, coin):
        """Drive CREATE_PIRATES to the point where it would spawn a wave."""
        self.prepare()
        self.watch_stubs()
        self.var('mission', mission)
        self.var('radar_obj', 0)        # deep space
        self.var('pirate_count', 0)
        self.var('pirate_ctr', 1)       # the countdown expires on this call
        self.government(7)
        self.scratch(self.RANDOM_VALUE, coin)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.call('create_pirates')

    def test_a_mission_wave_is_never_replaced(self):
        """$21 and $52 spawn Thargoids, $41 the Cougar, $15 the Constrictor.
        $15 cannot reach the substitution, and is tested anyway so the guard
        survives an edit to the Constrictor branch above it."""
        for mission in (0x15, 0x21, 0x41, 0x52):
            for coin in (0, 1):
                with self.subTest(mission=mission, coin=coin):
                    self.deep_space_wave(mission, coin)
                    self.assertIn('pirate_attack', self.entered)
                    self.assertNotIn('create_object', self.entered)

    def test_an_ordinary_wave_is_replaced_on_half_the_rolls(self):
        for coin, encounter in ((0, False), (1, True)):
            with self.subTest(coin=coin):
                self.deep_space_wave(0x00, coin)
                self.assertEqual('pirate_attack' not in self.entered, encounter)
                self.assertEqual('create_object' in self.entered, encounter)

    def test_no_encounter_outside_deep_space(self):
        self.prepare()
        self.watch_stubs()
        self.var('mission', 0)
        self.var('radar_obj', 1)  # inside station space
        self.var('pirate_count', 0)
        self.var('pirate_ctr', 1)
        self.scratch(self.RANDOM_VALUE, 1)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.call('create_pirates')
        self.assertNotIn('pirate_attack', self.entered)
        self.assertNotIn('create_object', self.entered)
```

`'pirate_count'` and `'radar_obj'` are already in `CONSTANTS`; add
`'pirate_ctr'` if Task 1 did not.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -k wave -v`
Expected: FAIL — an ordinary wave always reaches `pirate_attack`, because no
substitution exists yet.

- [ ] **Step 3: Add the substitution**

In `src_atari/asm/combat.m68`, replace the last two lines of `create_pirates`:

```
	move d0,pirate_ctr(a6)
	bra pirate_attack ; attack by pirates
```

with:

```
	move d0,pirate_ctr(a6)
; Half of the ordinary deep space waves become an encounter instead. Every
; mission that spawns a named ship keeps the old path: $21 and $52 want
; Thargoids, $41 the Cougar, and $15 the Constrictor, which cannot reach this
; point but is tested here so the guard survives an edit to the branch above.
	move mission(a6),d0
	cmp #$15,d0
	beq pirate_attack
	cmp #$21,d0
	beq pirate_attack
	cmp #$41,d0
	beq pirate_attack
	cmp #$52,d0
	beq pirate_attack
	jsr random ; a fair coin
	btst #0,d0
	bne random_encounter
	bra pirate_attack ; attack by pirates
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s src_atari/tests -p test_faction_ai.py -v`
Expected: PASS, the whole file.

- [ ] **Step 5: Run every suite that touches these spawns**

Run: `python -m unittest discover -s src_atari/tests -p test_missions.py -v`
Expected: PASS. This suite drives the Constrictor and alien station objectives
and is the direct check that mission spawning still works.

Run: `python -m unittest discover -s src_atari/tests -p "test_*.py"`
Expected: PASS, the whole Atari suite.

- [ ] **Step 6: Build and hand over**

Run: `build_atari.bat`
Expected: links cleanly.

Report the two changed files.

---

### Task 5: Port to the Amiga tree and document

**Files:**
- Modify: `src_amiga/asm/combat.m68`, `src_amiga/tests/test_faction_ai.py`
- Modify: `src_atari/README.md`, `src_amiga/README.md`

**Interfaces:**
- Consumes: the finished Atari implementation.
- Produces: the identical feature in the Amiga tree.

- [ ] **Step 1: Confirm the trees still match where they should**

Run: `diff src_atari/asm/combat.m68 src_amiga/asm/combat.m68`
Expected: only the differences Tasks 1 to 4 introduced in `src_atari`. The two
files were byte-identical before this work, so anything else means something
was edited in the wrong tree.

- [ ] **Step 2: Copy both files across**

`combat.m68` and `test_faction_ai.py` are byte-identical between the trees, so
copy them. Preserve LF line endings and do not let a text-mode write turn them
into CRLF.

- [ ] **Step 3: Run both suites in full**

Run: `python -m unittest discover -s src_atari/tests -p "test_*.py"`
Run: `python -m unittest discover -s src_amiga/tests -p "test_*.py"`
Expected: PASS, both.

- [ ] **Step 4: Build both games**

Run: `build_atari.bat`
Run: `build_amiga.bat`
Expected: both produce their distribution files with the symbol, checksum, A6
relocation, RAM bounds and module variable capacity checks passing.

- [ ] **Step 5: Document**

Add a `## Random encounters` section to both `src_atari/README.md` and
`src_amiga/README.md`, in English, immediately before `## Faction AI
targeting`. Cover: half of the deep-space pirate waves become a group that is
already fighting itself; the seven group shapes and the two that need a
government with police; the two ship tables and why the Thargoid, the Boa and
the Wolf are not in them; that nothing is announced; that the group appears
ahead of the player at the ambush's range; and that every mission spawn keeps
the old path. Point at `tests/test_faction_ai.py` for the coverage, matching
the style of the existing README sections.

Report every changed file to the user for a single commit, and note the three
follow-ups from the spec that play testing should settle: whether half is the
right substitution rate, whether encounters are over before the player reaches
them, and whether cargo from fights he did not join strains the object pool.

---

## Self-Review

**Spec coverage**

| Spec section | Task |
| --- | --- |
| 4.1 Ship tables | 1 |
| 4.2 Roles | 1 |
| 4.3 Templates | 2 |
| 4.4 Thargoid frequency | 2 (the weights test) |
| 5 Selecting a template | 2 |
| 6 Building the group | 3 |
| 7.1 The substitution point and the mission guards | 4 |
| 7.2 Spawns the substitution cannot reach | 4 (the `$15`/`$21`/`$41`/`$52` and deep-space tests), 5 (the full `test_missions.py` run) |
| 7.3 Counter side effects | 4 (`create_pirates` reached only through its own gates), 5 (full suites) |
| 8 Performance | 2 and 3 (two table walks and at most four creations, no per-frame work) |
| 9 Files touched | 1 to 5 |
| 10 Testing | 1 to 4 |
| 11 Risks | 5 (handover note) |

No spec section is unimplemented. Section 9's `common.def` row was corrected in
the spec before this plan was written: the roles, the spacing and the working
state all live in `combat.m68`.

**Placeholder scan**

No "TBD", "TODO", "similar to Task N" or "add error handling" remains. Every
code step carries the code to be written.

**Type consistency**

- `encounter_type`, `encounter_template`, `encounter_skip`, `encounter_place`,
  `encounter_offset`, `encounter_member` and `random_encounter` are spelled
  identically in their definitions, their call sites and the test routine
  lists.
- `encounter_pirates`, `encounter_traders`, `encounter_fixed`,
  `encounter_groups` and `encounter_positions` likewise.
- `encounter_row` and `encounter_lead` are longs everywhere; `encounter_role`,
  `encounter_left` and `encounter_seat` are words everywhere.
- The role constants are `role_pirate`, `role_trader`, `role_thargoid`,
  `role_viper`, `role_bounty` in the assembler, the table and the tests.
- `encounter_member` and `alloc_object` share one convention: carry set means a
  record was obtained.
- `RAND_VALUE` and the `roll()` helper are used with the same meaning in
  Tasks 1, 2, 3 and 4.
