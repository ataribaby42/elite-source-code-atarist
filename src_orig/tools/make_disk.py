"""Create a deterministic 720 KB Atari ST FAT12 disk with optional AUTO startup."""
from pathlib import Path
import struct


def make_disk(files: list[Path], destination: Path, *, auto_program: Path | None = None):
    image = bytearray(80 * 2 * 9 * 512)
    image[:11] = b'\xeb\x3c\x90ELITE ST'
    struct.pack_into('<HBHBHHBHHH', image, 11, 512, 2, 1, 2, 112, 1440, 0xf9, 3, 9, 2)
    fat = bytearray(3 * 512)
    fat[:3] = b'\xf9\xff\xff'
    root_offset = 7 * 512
    data_offset = 14 * 512
    next_cluster = 2

    def set_fat(cluster, value):
        pos = cluster * 3 // 2
        word = int.from_bytes(fat[pos:pos+2], 'little')
        word = ((word & 0x000f) | (value << 4)) if cluster & 1 else ((word & 0xf000) | value)
        fat[pos:pos+2] = word.to_bytes(2, 'little')

    def write_content(content):
        nonlocal next_cluster
        count = (len(content) + 1023) // 1024
        first = next_cluster if count else 0
        if data_offset + (next_cluster - 2 + count) * 1024 > len(image):
            raise ValueError('Disk is full')
        for n in range(count):
            cluster = next_cluster + n
            set_fat(cluster, 0xfff if n == count-1 else cluster+1)
            pos = data_offset + (cluster-2)*1024
            part = content[n*1024:(n+1)*1024]
            image[pos:pos+len(part)] = part
        next_cluster += count
        return first

    def entry(name, first, size, attribute=0x20):
        if name in ('.', '..'):
            stem, ext = name, ''
        else:
            stem, _, ext = name.upper().partition('.')
            if not stem or len(stem) > 8 or len(ext) > 3 or '.' in ext:
                raise ValueError(f'Not an 8.3 filename: {name}')
        record = bytearray(32)
        record[:11] = (stem.ljust(8) + ext.ljust(3)).encode('ascii')
        record[11] = attribute
        struct.pack_into('<HHHI', record, 22, 0, 0x1421, first, size)
        return record

    if len(files) + (auto_program is not None) > 112:
        raise ValueError('FAT12 root directory is full')
    records = []
    names = set()
    for path in sorted(files, key=lambda p: p.name):
        name = path.name.upper()
        if name in names or (auto_program is not None and name == 'AUTO'):
            raise ValueError(f'Duplicate disk entry: {name}')
        names.add(name)
        content = path.read_bytes()
        records.append(entry(name, write_content(content), len(content)))
    if auto_program is not None:
        program = auto_program.read_bytes()
        if program[:2] != b'\x60\x1a':
            raise ValueError('AUTO/ELITE.PRG must be a TOS executable')
        program_cluster = write_content(program)
        directory_cluster = next_cluster
        directory = bytearray(1024)
        directory[:32] = entry('.', directory_cluster, 0, 0x10)
        directory[32:64] = entry('..', 0, 0, 0x10)
        directory[64:96] = entry('ELITE.PRG', program_cluster, len(program))
        records.append(entry('AUTO', write_content(directory), 0, 0x10))
    image[root_offset:root_offset+len(records)*32] = b''.join(records)
    image[512:4*512] = fat
    image[4*512:7*512] = fat
    # Atari boot sectors are executable only when their BE word sum is $1234.
    if sum(struct.unpack('>256H', image[:512])) & 0xffff == 0x1234:
        image[510] ^= 1
    destination.write_bytes(image)


def verify_disk(path: Path, files: list[Path], *, auto_program: Path | None = None):
    """Read directory entries and FAT chains back, comparing every byte."""
    image = path.read_bytes()
    if len(image) != 737280 or image[512:2048] != image[2048:3584]:
        raise ValueError('Invalid disk size or inconsistent FAT copies')
    expected = {p.name.upper(): p.read_bytes() for p in files}
    if auto_program is not None:
        expected['AUTO/ELITE.PRG'] = auto_program.read_bytes()
    actual = {}
    visited = set()

    def read_chain(cluster):
        content = bytearray()
        while cluster < 0xff8:
            if cluster in visited or not 2 <= cluster <= 714:
                raise ValueError('Invalid FAT chain')
            visited.add(cluster)
            start = 7168 + (cluster-2)*1024
            content += image[start:start+1024]
            raw = int.from_bytes(image[512+cluster*3//2:514+cluster*3//2], 'little')
            cluster = (raw >> 4) if cluster & 1 else (raw & 0xfff)
        return content

    directories = set()

    def read_directory(content, prefix='', own_cluster=0):
        dots = {}
        for pos in range(0, len(content), 32):
            record = content[pos:pos+32]
            if not record[0]:
                break
            stem, ext = record[:8].decode().rstrip(), record[8:11].decode().rstrip()
            name = stem + ('.' + ext if ext else '')
            attribute = record[11]
            cluster, size = struct.unpack_from('<HI', record, 26)
            if name in ('.', '..'):
                if not prefix or name in dots or attribute != 0x10 or size:
                    raise ValueError('Invalid directory dot entry')
                dots[name] = cluster
                continue
            full_name = prefix + name
            if full_name in actual or full_name in directories:
                raise ValueError('Duplicate disk entry')
            if attribute == 0x10:
                if full_name != 'AUTO' or auto_program is None or size:
                    raise ValueError('Unexpected disk directory')
                directories.add(full_name)
                read_directory(read_chain(cluster), full_name+'/', cluster)
            elif attribute == 0x20:
                data = read_chain(cluster) if size else bytearray()
                if len(data) != (size+1023)//1024*1024 or (not size and cluster):
                    raise ValueError('File size does not match its FAT chain')
                actual[full_name] = bytes(data[:size])
            else:
                raise ValueError('Unexpected directory attribute')
        if prefix and dots != {'.': own_cluster, '..': 0}:
            raise ValueError('Incorrect AUTO directory parent/self entries')

    read_directory(image[3584:7168])
    if directories != ({'AUTO'} if auto_program is not None else set()):
        raise ValueError('Missing AUTO directory')
    if actual != expected:
        raise ValueError('Disk contents differ from the distribution files')
