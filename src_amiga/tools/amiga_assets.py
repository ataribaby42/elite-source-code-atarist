"""Read the supplied Amiga disk without changing it; recover the original PCM bank."""
import hashlib
from pathlib import Path
import struct

ADF_HASH = '3ef395dc1d73c86f7a8486329a24d2ced29b5c6b108df3da6cae1380b5666ee3'


def be32(data, offset=0):
    return struct.unpack_from('>I', data, offset)[0]


def ofs_file(image, header):
    def block(number):
        if not 0 <= number < len(image) // 512:
            raise ValueError('OFS block outside disk')
        return image[number * 512:(number + 1) * 512]
    head = block(header)
    number, chunks, seen = be32(head, 16), [], set()
    while number:
        if number in seen:
            raise ValueError('Cyclic OFS file')
        seen.add(number)
        data = block(number)
        if (be32(data) != 8 or be32(data, 4) != header or
                be32(data, 8) != len(chunks) + 1 or be32(data, 12) > 488 or
                sum(struct.unpack('>128I', data)) & 0xffffffff):
            raise ValueError('Invalid OFS data block')
        chunks.append(data[24:24 + be32(data, 12)])
        number = be32(data, 16)
    result = b''.join(chunks)
    if len(result) != be32(head, 324):
        raise ValueError('Truncated OFS file')
    return result


def extract_assets(adf: Path, target: Path):
    image = adf.read_bytes()
    if hashlib.sha256(image).hexdigest() != ADF_HASH:
        raise ValueError('Expected the supplied resources/amiga/Elite 2.0.adf; its checksum differs')
    game = ofs_file(image, 887)
    lengths = struct.unpack_from('>19H', game, 0x60d0)
    if sum(lengths) != 53908:
        raise ValueError('Unexpected Amiga sample bank')
    samples = game[0x5b1cc:0x5b1cc + sum(lengths)]
    # The original player uses eight-byte descriptors and a 16-note period table.
    descriptors = game[0x5fe4:0x5fe4+19*8]
    periods = struct.unpack_from('>16H', game, 0x5f5a)
    if any(descriptors[n*8] != n for n in range(19)):
        raise ValueError('Unexpected Amiga effect descriptors')
    (target / 'amiga-samples.bin').write_bytes(samples)
    offsets, position = [], 0
    for length in lengths:
        offsets.append(position)
        position += length
    (target / 'amiga-samples.inc').write_text(
        '; Original Amiga PCM samples: Wally Beben. Offsets and byte lengths.\n'
        'amiga_sample_offsets:\n    dc.l ' + ','.join(map(str, offsets)) + '\n'
        'amiga_sample_lengths:\n    dc.w ' + ','.join(map(str, lengths)) + '\n'
        'amiga_effect_descriptors:\n    dc.b ' + ','.join(map(str, descriptors)) + '\n'
        'amiga_effect_periods:\n    dc.w ' + ','.join(map(str, periods)) + '\n', encoding='ascii')
    return image[:1024], {'adf_sha256': ADF_HASH, 'sample_count': len(lengths),
                          'sample_bytes': len(samples), 'sample_sha256': hashlib.sha256(samples).hexdigest()}
