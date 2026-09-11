"""Verify the untouched historical ZIP against the known archive SHA-256."""
from pathlib import Path
import hashlib
import json
import sys
from zipfile import ZipFile

root = Path(__file__).resolve().parents[1]
archive = root.parent / 'resources/elite_atarist_source.zip'
expected_sha256 = '19496256fb315c5db71c92385783acf4590a682ee3aae0c6a3435d0ea5faa1e2'
try:
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Original archive SHA-256 differs')
    expected = json.loads((root / 'original-sha256.json').read_text())
    with ZipFile(archive) as zipped:
        if set(zipped.namelist()) != set(expected):
            raise ValueError('Original archive file list differs')
except (OSError, ValueError) as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(1)
print(f'Original ZIP is unchanged (SHA-256); it preserves all {len(expected)} historical files.')
