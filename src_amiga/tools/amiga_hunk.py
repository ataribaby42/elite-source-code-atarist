"""Validate the Kickstart 1.x Hunk subset emitted by the Amiga build."""
import struct


def verify_hunk(data, section_names):
    if len(data) % 4:
        raise ValueError('Unaligned Hunk executable')
    words = struct.unpack('>' + 'I' * (len(data) // 4), data)
    pos = 0

    def read():
        nonlocal pos
        if pos >= len(words):
            raise ValueError('Truncated Hunk executable')
        value = words[pos]
        pos += 1
        return value

    if [read(), read()] != [1011, 0]:
        raise ValueError('Expected HUNK_HEADER without resident libraries')
    count, first, last = read(), read(), read()
    if first != 0 or last != count - 1 or count != len(section_names):
        raise ValueError('Hunk section table does not match the link map')
    allocations = [read() for _ in range(count)]
    result = {}
    for index, name in enumerate(section_names):
        kind, size = read() & 0x3fffffff, read() * 4
        flags = allocations[index] & 0xc0000000
        if kind not in (1001, 1002, 1003) or size > (allocations[index] & 0x3fffffff) * 4:
            raise ValueError('Invalid Hunk allocation: ' + name)
        if kind == 1003 and size > 262144:
            raise ValueError('BSS exceeds the Kickstart 1.x clearing limit: ' + name)
        if name in ('amiga_video', 'amiga_audio', 'amiga_copper') and flags != 0x40000000:
            raise ValueError('DMA section is not allocated in Chip RAM: ' + name)
        result[name] = {'bytes': size, 'chip_ram': flags == 0x40000000}
        if kind != 1003:
            pos += size // 4
        while True:
            record = read()
            if record == 1010:
                break
            if record == 1004:
                while True:
                    number = read()
                    if not number:
                        break
                    target = read()
                    if target >= count:
                        raise ValueError('Relocation targets an unknown Hunk')
                    for _ in range(number):
                        offset = read()
                        if offset & 1 or offset + 4 > size:
                            raise ValueError('Relocation outside section: ' + name)
            elif record == 1008:
                while True:
                    length = read()
                    if not length:
                        break
                    pos += length
                    read()
            elif record == 1009:
                length = read()
                pos += length
            else:
                raise ValueError('Unexpected or non-Kickstart-1.x Hunk record: ' + str(record))
    if pos != len(words):
        raise ValueError('Trailing Hunk data')
    return result
