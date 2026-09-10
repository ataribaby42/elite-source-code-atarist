"""Create a deterministic, non-bootable 720 KB Atari ST FAT12 data disk."""
from pathlib import Path
import struct


def make_disk(files: list[Path], destination: Path):
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

    for index, path in enumerate(sorted(files, key=lambda p: p.name)):
        if index >= 112:
            raise ValueError('FAT12 root directory is full')
        name, ext = path.name.upper().rsplit('.', 1)
        if len(name) > 8 or len(ext) > 3:
            raise ValueError(f'Not an 8.3 filename: {path.name}')
        content = path.read_bytes()
        count = (len(content) + 1023) // 1024
        first = next_cluster if count else 0
        if data_offset + (next_cluster - 2 + count) * 1024 > len(image):
            raise ValueError('Disk is full')
        entry = root_offset + index * 32
        image[entry:entry+11] = (name.ljust(8) + ext.ljust(3)).encode('ascii')
        image[entry+11] = 0x20
        struct.pack_into('<HHHI', image, entry+22, 0, 0x1421, first, len(content))
        for n in range(count):
            cluster = next_cluster + n
            set_fat(cluster, 0xfff if n == count-1 else cluster+1)
            pos = data_offset + (cluster-2)*1024
            part = content[n*1024:(n+1)*1024]
            image[pos:pos+len(part)] = part
        next_cluster += count
    image[512:4*512] = fat
    image[4*512:7*512] = fat
    # Atari boot sectors are executable only when their BE word sum is $1234.
    if sum(struct.unpack('>256H', image[:512])) & 0xffff == 0x1234:
        image[510] ^= 1
    destination.write_bytes(image)


def verify_disk(path: Path, files: list[Path]):
    """Read directory entries and FAT chains back, comparing every byte."""
    image = path.read_bytes()
    if len(image) != 737280 or image[512:2048] != image[2048:3584]:
        raise ValueError('Invalid disk size or inconsistent FAT copies')
    expected = {p.name.upper(): p.read_bytes() for p in files}
    actual = {}
    for pos in range(3584, 7168, 32):
        entry = image[pos:pos+32]
        if not entry[0]:
            break
        name = entry[:8].decode().strip() + '.' + entry[8:11].decode().strip()
        cluster, size = struct.unpack_from('<HI', entry, 26)
        content, visited = bytearray(), set()
        while cluster >= 2 and cluster < 0xff8:
            if cluster in visited or cluster > 714:
                raise ValueError('Invalid FAT chain')
            visited.add(cluster)
            start = 7168 + (cluster-2)*1024
            content += image[start:start+1024]
            raw = int.from_bytes(image[512+cluster*3//2:514+cluster*3//2], 'little')
            cluster = (raw >> 4) if cluster & 1 else (raw & 0xfff)
        actual[name] = bytes(content[:size])
    if actual != expected:
        raise ValueError('Disk contents differ from the distribution files')
