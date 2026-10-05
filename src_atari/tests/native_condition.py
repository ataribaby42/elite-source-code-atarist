"""Exercise the linked warning routine, including its real altitude caller."""


def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    body = [call('quiet')+' bclr #f_fx,user(a6)\n']
    names = []

    def case(name):
        names.append(name)
        body.append(f' move.w #{len(names)},qa_case\n'
                    ' move.w #2,condition(a6)\n move.w #max_energy,energy(a6)\n'
                    ' move.w #bar_width,altitude(a6)\n clr.w cabin_temp(a6)\n'
                    ' clr.w laser_temp(a6)\n clr.w police_record(a6)\n'
                    ' clr.w under_attack(a6)\n clr.w witch_space(a6)\n'
                    ' clr.w mission(a6)\n clr.w docked(a6)\n'
                    ' move.w #1,tharg_count(a6)\n clr.w text_frames(a6)\n'
                    ' move.l #$30000,planet_range(a6)\n move.l #$30000,sun_range(a6)\n')

    def check(expected, scratch=0, message=False):
        if scratch is not None:
            body.append(f' move.l #{scratch},d0\n')
        body.append(call('warnings')+f' cmp.w #{expected},condition(a6)\n bne fail\n')
        if message:
            body.append(' tst.w text_frames(a6)\n beq fail\n')

    case('Cold empty space: actual altitude calculation followed by warnings is Green')
    body.append(call('calc_altitude')+' tst.w d0\n bne fail\n')
    check(0, scratch=None)

    for energy in (0, 23, 24, 71, 72, 73, 96):
        for scratch in (0, 65535):
            expected = 2 if energy < 24 else 1 if energy < 72 else 0
            case(f'Energy {energy}/96, unrelated D0={scratch}: condition {expected}')
            body.append(f' move.w #{energy},energy(a6)\n')
            check(expected, scratch, message=energy < 24)

    for record in (1, 49, 50, 255):
        case(f'Legal record {record} still produces Yellow with full energy')
        body.append(f' move.w #{record},police_record(a6)\n')
        check(1)
    case('An angry ship still produces Yellow with full energy')
    body.append(' st under_attack(a6)\n')
    check(1)

    for temperature, expected in ((36, 0), (37, 1), (48, 1)):
        case(f'Laser temperature {temperature}/48: condition {expected}')
        body.append(f' move.w #{temperature},laser_temp(a6)\n')
        check(expected)
    for field, value, expected in (('altitude', 7, 2), ('altitude', 8, 0),
                                  ('cabin_temp', 35, 0), ('cabin_temp', 36, 2)):
        case(f'{field} {value}: condition {expected}')
        body.append(f' move.w #{value},{field}(a6)\n')
        check(expected, message=field == 'altitude' and expected == 2)

    for mission in (0x31, 0x32, 0x33, 0x34, 0x41, 0x42):
        expected = 2 if mission in (0x32, 0x33) else 0
        case(f'Mission ${mission:02x}: existing warning condition {expected}')
        body.append(f' move.w #${mission:x},mission(a6)\n')
        check(expected, message=expected == 2)
    case('Witch space retains its exception for altitude and cabin heat')
    body.append(' st witch_space(a6)\n clr.w altitude(a6)\n move.w #48,cabin_temp(a6)\n')
    check(0)

    for hull in range(13):
        case(f'Playable hull {hull}: fully charged and safe means Green')
        body.append(f' move.w #{hull},player_ship(a6)\n'+call('ship_apply')+call('calc_altitude'))
        check(0, scratch=None)

    case('Recharge clears Yellow at exactly three-quarter energy')
    body.append(' move.w #71,energy(a6)\n')
    check(1)
    body.append(' move.w #72,energy(a6)\n')
    check(0)
    case('Recharge clears Red into Yellow at exactly one-quarter energy')
    body.append(' move.w #23,energy(a6)\n')
    check(2, message=True)
    body.append(' move.w #24,energy(a6)\n')
    check(1)
    case('Clearing the attack flag returns a safe ship to Green')
    body.append(' st under_attack(a6)\n')
    check(1)
    body.append(' clr.w under_attack(a6)\n')
    check(0)
    body.append(call('quiet'))
    return ' include "common.def"\n include "macros.m68"\n', ''.join(body), 'qa_case: dc.w 0\n', names
