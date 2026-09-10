"""One-time, read-only import of the 1988/1990 Quelo sources to vasm syntax.

The converted files in src_atari/asm are the editable source of the modern build.
This converter is retained for provenance; the normal build never imports
src-orig or overwrites the edited assembly files.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent / 'src-orig'
INVERT = dict(zip('eq ne gt le ge lt hi ls hs lo vc vs pl mi cc cs'.split(),
                  'ne eq le gt lt ge ls hi lo hs vs vc mi pl cs cc'.split()))
MACROS = set('global inc dec push pop dz even loop next trap_call bdos bios ext_bios flash let subr save_all restore_all sec clc sfx module ret call hclr jp vars end_vars abs rs action'.split())


def field(text):
    """Quelo operand field ends at whitespace outside a quoted string."""
    quote = None
    for i, c in enumerate(text):
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        elif c.isspace():
            if text[:i].rstrip().endswith(',') or text[i:].lstrip().startswith(','):
                continue
            return text[:i], text[i:].strip()
        elif c == ';':
            return text[:i], text[i:].strip()
    return text, ''


class Converter:
    def __init__(self, name):
        self.name = name
        self.serial = 0
        self.macro = False
        self.offset = False
        self.ifs = []
        self.loops = []

    def label(self):
        self.serial += 1
        return f'q_{self.name}_{self.serial}' + (r'\@' if self.macro else '')

    def condition(self, text, size, target, invert=False, branch=''):
        # Two source conditions use OR; short circuit in source order.
        if ' or ' in text:
            first, second = text.split(' or ', 1)
            if invert:
                skip = self.label()
                return self.condition(first, size, skip, branch=branch) + self.condition(second, size, target, True, branch) + [skip + ':']
            return self.condition(first, size, target, branch=branch) + self.condition(second, size, target, branch=branch)
        m = re.fullmatch(r'\s*(.*?)\s*<([^>]+)>\s*(.*?)\s*', text)
        if not m:
            raise ValueError(f'Unrecognized condition: {text!r}')
        lhs, cc, rhs = m.groups()
        out = []
        if lhs:
            if not rhs:
                raise ValueError('Comparison requires two operands')
            out.append(f'\tcmp{size} {rhs},{lhs}')
        if invert:
            if cc.startswith('\\'):
                # Used only by CALL/JP in the shared macro file.
                # Emit one conditional assembly arm per possible condition.
                for key, opposite in INVERT.items():
                    out += [f"\tifc '{cc}','{key}'", f'\tb{opposite}{branch} {target}', '\tendc']
                return out
            cc = INVERT[cc]
        out.append(f'\tb{cc}{branch} {target}')
        return out

    def convert(self, text):
        original_name = '.'.join(self.name.rsplit('_', 1)).upper()
        out = [f'; Ported from src-orig/{original_name}; edit this copy.']
        for number, line in enumerate(text.split('\x1a', 1)[0].splitlines(), 1):
            try:
                out.extend(self.line(line))
            except Exception as exc:
                raise ValueError(f'{self.name}:{number}: {line}\n{exc}') from exc
        if self.ifs or self.loops or self.macro:
            raise ValueError(f'{self.name}: unclosed structure')
        return '\n'.join(out) + '\n'

    def line(self, line):
        if not line.strip() or line.lstrip().startswith(('*', ';')):
            return [line]
        label = ''
        body = line
        if not line[0].isspace() or re.match(r'\s*\S+:', line):
            m = re.match(r'\s*(\S+)\s*(.*)', line)
            label, body = m.groups()
            label = label.rstrip(':')
            if not body:
                return [label + (': equ __RS' if self.offset else ':')]
        parts = body.split(None, 1)
        op = parts[0].lower()
        tail = parts[1] if len(parts) > 1 else ''
        base, _, suffix = op.partition('.')
        size = '.' + suffix if suffix else ''
        arg, comment = field(tail)
        arg = re.sub(r'\bnargs\b', 'NARG', arg)
        # Quelo word-sized character literals are left-justified; vasm's
        # one-character literals already have the ASCII value in the low byte.
        arg = re.sub(r"('[^']')(?:>>8|/256)", r'\1', arg)
        arg = re.sub(r'#-(\\[1-9])', r'#-(\1)', arg)
        arg = arg.replace(r'\a', r'\A')
        if base in {'subr', 'global', 'size'}:
            arg = arg.lower()
        if self.name == 'init_m68' and base == 'ifnc':
            arg = arg.replace("'INIT'", "'init'")
        if base in {'vars', 'offset'}:
            self.offset = True
        elif base in {'module', 'section'}:
            self.offset = False
        if self.offset:
            arg = re.sub(r'(?<![A-Za-z0-9_)])\*', '__RS', arg)
        prefix = [label + ':'] if label else []
        if base == 'macro':
            self.macro = True
            if label in MACROS:
                label = 'q_' + label
            return [f'{label} macro']
        if base == 'endm':
            self.macro = False
        if base == 'include':
            name = arg.lower()
            if '.' not in name:
                name += '.m68'
            return [f'\tinclude "{name}"']
        if base in {'if', 'while'}:
            term = 'then' if base == 'if' else 'do'
            m = re.match(r'(.*?)\s+' + term + r'(\.s)?(?:\s.*)?$', tail)
            if not m:
                raise ValueError('Malformed structured condition')
            expression, branch = m.groups()
            branch = branch or ''
            start, end = self.label(), self.label()
            if base == 'if':
                self.ifs.append([start, end, False])
                return prefix + [f'; Quelo: {body}'] + self.condition(expression, size, start, True, branch)
            self.loops.append(('while', start, end))
            return prefix + [start + ':'] + self.condition(expression, size, end, True, branch)
        if base == 'else':
            start, end, used = self.ifs[-1]
            if used:
                raise ValueError('Duplicate else')
            self.ifs[-1][2] = True
            return [f'\tbra{size} {end}', start + ':']
        if base == 'endi':
            start, end, used = self.ifs.pop()
            return [(end if used else start) + ':']
        if base == 'repeat':
            start, end = self.label(), self.label()
            self.loops.append(('repeat', start, end))
            return [start + ':']
        if base in {'until', 'endr', 'endw'}:
            kind, start, end = self.loops.pop()
            if base == 'until':
                # The condition consumes up to two operands; discard its comment.
                m = re.match(r'(.*?<[^>]+>)(.*)', tail)
                left, rest = m.groups()
                right = field(rest.lstrip())[0] if not left.strip().startswith('<') else ''
                return self.condition(left + ' ' + right, size, start, True) + [end + ':']
            if (base == 'endw') != (kind == 'while'):
                raise ValueError('Mismatched loop end')
            return [f'\tbra{size} {start}', end + ':']
        if base == 'break':
            end = self.loops[-1][2]
            if tail.startswith('if'):
                m = re.match(r'if(\.[bwl])?\s+(.*?<[^>]+>)(.*)', tail)
                cmp_size, left, rest = m.groups()
                right = field(rest.lstrip())[0] if not left.strip().startswith('<') else ''
                return self.condition(left + ' ' + right, cmp_size or '', end, branch=size)
            return [f'\tbra{size} {end}']
        if base == 'proc':
            return [label + ':']
        if base == 'db':
            op = 'dc.b'
        if base == 'exitm':
            op = 'mexit'
        if base == 'section':
            arg = 'text,code'
        if base == 'offset':
            op = 'rsset'
        if base == 'ds' and self.offset:
            op = 'rs' + (size or '.w')
        if base == 'xref':
            op = 'xref'
        if base in {'list', 'nolist', 'opt'}:
            return ['; Original listing option: ' + body]
        if base in MACROS:
            op = 'q_' + op
        if base in {'ret', 'call', 'jp'}:
            arg = arg.replace('<', '').replace('>', '')
            if base == 'ret' and arg not in INVERT and arg not in {'', 'return'}:
                comment, arg = tail, ''
        if base == 'dz':
            # Quelo stripped the string delimiter before macro substitution.
            if tail.startswith('<'):
                end = tail.index('>')
                arg, comment = '"' + tail[1:end] + '"', tail[end+1:].strip()
            return prefix + [f'\tdc.b {arg},0' + (f' ; {comment}' if comment else '')]
        if base == 'ds' and not size and arg == '0':
            return prefix + (['\trs.w 0'] if self.offset else ['\teven'])
        if base == 'endm':
            return ['\tendm']
        if base in {'rts', 'rte', 'nop', 'reset'} and arg:
            arg, comment = '', tail
        if base == 'equ' and label == 'valid':
            return ['\tifnd valid', f'valid equ {arg}', '\tendc']
        if self.name == 'checksum_m68' and base == 'move' and arg == '#valid,ok_checksum(a6)':
            return ['\txdef checksum_expected', 'checksum_expected:', f'\t{op} {arg} ; {comment}']
        # Preserve operand whitespace rules; all comments get a delimiter.
        if label:
            return [f'{label}: {op} {arg}' + (f' ; {comment}' if comment else '')]
        return [f'\t{op} {arg}'.rstrip() + (f' ; {comment}' if comment else '')]


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overwrite', action='store_true', help='explicitly replace all converted files (destroys edits in src_atari/asm)')
    args = parser.parse_args()
    modules = re.findall(r'^\s+link (\w+)', (ORIGINAL / 'ELITE.LNK').read_text(), re.M)
    out = ROOT / 'asm'
    out.mkdir(exist_ok=True)
    files = [name.upper() + '.M68' for name in modules]
    files += ['COMMON.DEF', 'MACROS.M68', 'BITLIST.M68', 'ICONS.M68', 'NOTES.M68', 'LOADER.M68', 'OBJECTS.M68', 'OBJECTS.DAT', 'ELITECHR.M68']
    for name in files:
        dest = out / name.lower()
        if dest.exists() and not args.overwrite:
            raise SystemExit(f'Refusing to overwrite edited source: {dest}')
        converted = Converter(name.lower().replace('.', '_')).convert((ORIGINAL / name).read_text(encoding='latin1'))
        if name.endswith('.M68') and name not in {'MACROS.M68','BITLIST.M68','ICONS.M68','NOTES.M68','OBJECTS.M68','ELITECHR.M68'}:
            converted = '\tinclude "common.def"\n' + converted
        dest.write_text(converted, encoding='utf-8')
    (ROOT / 'modules.txt').write_text('\n'.join(modules) + '\n')


if __name__ == '__main__':
    main()
