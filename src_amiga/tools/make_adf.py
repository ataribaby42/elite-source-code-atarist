"""Create and verify a standard 880 KB OFS AmigaDOS floppy."""
import struct
from tools.amiga_assets import ofs_file, be32


def make_adf(files, target, bootblock):
    image = bytearray(901120)
    image[:1024] = bootblock
    reserved = {0, 1, 880, 881}
    free = iter(n for n in range(2, 1760) if n not in reserved)
    used = set(reserved)
    def allocate():
        try:
            n = next(free)
        except StopIteration:
            raise ValueError('Amiga floppy is full') from None
        used.add(n)
        return n
    def put(n, data):
        struct.pack_into('>I', data, 20, 0)
        checksum = -sum(struct.unpack('>128I', data)) & 0xffffffff
        struct.pack_into('>I', data, 20, checksum)
        image[n*512:(n+1)*512] = data
    def header(n, name, kind, parent):
        b = bytearray(512)
        struct.pack_into('>II', b, 0, 2, n if kind != 1 else 0)
        struct.pack_into('>I', b, 12, 72 if kind in (1, 2) else 0)
        encoded = name.encode('ascii')
        if len(encoded) > 30:
            raise ValueError('OFS name too long')
        b[432] = len(encoded)
        b[433:433+len(encoded)] = encoded
        struct.pack_into('>II', b, 500, parent, 0)
        struct.pack_into('>i', b, 508, kind)
        return b
    root = header(880, 'Elite', 1, 0)
    struct.pack_into('>III', root, 312, 0xffffffff, 881, 0)
    directories = {'': (880, root)}
    entries = {}
    def add_entry(parent, name, n, h):
        pn, pb = directories[parent]
        key = len(name)
        for c in name.upper():
            key = (key * 13 + ord(c)) & 0x7ff
        offset = 24 + (key % 72)*4
        struct.pack_into('>I', h, 496, be32(pb, offset))
        struct.pack_into('>I', pb, offset, n)
    for path, data in files.items():
        parent, _, name = path.rpartition('/')
        if parent and parent not in directories:
            dn = allocate()
            dh = header(dn, parent, 2, 880)
            add_entry('', parent, dn, dh)
            directories[parent] = dn, dh
        pn = directories[parent][0]
        n = allocate()
        h = header(n, name, -3, pn)
        struct.pack_into('>I', h, 324, len(data))
        blocks = [allocate() for _ in range((len(data)+487)//488)]
        struct.pack_into('>I', h, 16, blocks[0] if blocks else 0)
        for i, bn in enumerate(blocks):
            part = data[i*488:(i+1)*488]
            b = bytearray(512)
            struct.pack_into('>5I', b, 0, 8, n, i+1, len(part), blocks[i+1] if i+1<len(blocks) else 0)
            b[24:24+len(part)] = part
            put(bn, b)
        current, hn = h, n
        for start in range(0, max(1, len(blocks)), 72):
            group = blocks[start:start+72]
            struct.pack_into('>I', current, 8, len(group))
            for j, bn in enumerate(group):
                struct.pack_into('>I', current, 308-j*4, bn)
            if start+72 < len(blocks):
                nxt = allocate()
                struct.pack_into('>I', current, 504, nxt)
                if hn != n:
                    put(hn, current)
                hn, current = nxt, bytearray(512)
                struct.pack_into('>II', current, 0, 16, hn)
                struct.pack_into('>I', current, 500, n)
                struct.pack_into('>i', current, 508, -3)
            elif hn != n:
                put(hn, current)
        add_entry(parent, name, n, h)
        put(n, h)
        entries[path] = n
    for n, h in directories.values():
        put(n, h)
    bitmap = bytearray(512)
    for n in range(2, 1760):
        if n not in used:
            offset = 4 + ((n-2)//32)*4
            struct.pack_into('>I', bitmap, offset, be32(bitmap, offset) | (1 << ((n-2)%32)))
    struct.pack_into('>I', bitmap, 0, -sum(struct.unpack('>128I', bitmap)) & 0xffffffff)
    image[881*512:882*512] = bitmap
    verify_adf(image, files)
    target.write_bytes(image)
    return {'blocks_used': len(used), 'files': {p: len(b) for p, b in files.items()}}


def verify_adf(image, expected):
    """Walk directory hashes, file/extension tables and bitmap independently."""
    if len(image) != 901120 or image[:4] != b'DOS\0':
        raise ValueError('Expected an 880 KB OFS disk')
    total = 0
    for word in struct.unpack('>256I', image[:1024]):
        total += word
        total = (total & 0xffffffff) + (total >> 32)
    if total != 0xffffffff or be32(image, 8) != 880:
        raise ValueError('Invalid bootblock checksum or root pointer')
    used = {0, 1}
    found = {}

    def block(n, checksum=True):
        if n < 2 or n >= 1760 or n in used:
            raise ValueError('Invalid or multiply allocated OFS block')
        used.add(n)
        b = image[n*512:(n+1)*512]
        if checksum and sum(struct.unpack('>128I', b)) & 0xffffffff:
            raise ValueError('Invalid OFS block checksum')
        return b

    root = block(880)
    if be32(root) != 2 or be32(root, 508) != 1 or be32(root, 312) != 0xffffffff:
        raise ValueError('Invalid OFS root')
    bitmap = block(be32(root, 316))

    def directory(parent, head, prefix):
        for slot in range(72):
            n = be32(head, 24+slot*4)
            while n:
                h = block(n)
                if be32(h) != 2 or be32(h, 4) != n or be32(h, 500) != parent:
                    raise ValueError('Invalid OFS directory entry')
                length = h[432]
                name = h[433:433+length].decode('ascii')
                key = len(name)
                for c in name.upper():
                    key = (key * 13 + ord(c)) & 0x7ff
                if not 1 <= length <= 30 or key % 72 != slot:
                    raise ValueError('Invalid OFS name hash')
                path = prefix + name
                if be32(h, 508) == 2:
                    directory(n, h, path+'/')
                elif be32(h, 508) == 0xfffffffd:
                    data_blocks = []
                    ext = h
                    while True:
                        count = be32(ext, 8)
                        if count > 72:
                            raise ValueError('Oversized OFS block table')
                        data_blocks.extend(be32(ext, 308-j*4) for j in range(count))
                        nxt = be32(ext, 504)
                        if not nxt:
                            break
                        ext = block(nxt)
                        if be32(ext) != 16 or be32(ext, 4) != nxt or be32(ext, 500) != n:
                            raise ValueError('Invalid OFS extension')
                    if be32(h, 16) != (data_blocks[0] if data_blocks else 0):
                        raise ValueError('Invalid OFS first data block')
                    for i, bn in enumerate(data_blocks):
                        b = block(bn)
                        if be32(b, 16) != (data_blocks[i+1] if i+1 < len(data_blocks) else 0):
                            raise ValueError('OFS chain disagrees with the block table')
                    if path in found:
                        raise ValueError('Duplicate OFS file')
                    found[path] = ofs_file(image, n)
                else:
                    raise ValueError('Unsupported OFS entry type')
                n = be32(h, 496)
    directory(880, root, '')
    for n in range(2, 1760):
        free = bool(be32(bitmap, 4+((n-2)//32)*4) & (1 << ((n-2)%32)))
        if free == (n in used):
            raise ValueError('OFS bitmap disagrees with allocated blocks')
    if found != expected:
        raise ValueError('ADF file readback differs from build inputs')
