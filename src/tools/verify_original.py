"""Verify that the complete original directory still matches its initial hash manifest."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[1]
expected = json.loads((root / 'original-sha256.json').read_text())
actual = {str(p.relative_to(root.parent / 'src-orig')).replace('\\', '/'):
          hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (root.parent / 'src-orig').rglob('*') if p.is_file()}
changed = sorted(name for name in expected.keys() | actual.keys() if expected.get(name) != actual.get(name))
if changed:
    print('Original directory differs: ' + ', '.join(changed), file=sys.stderr)
    sys.exit(1)
print(f'All {len(expected)} original files are unchanged (SHA-256).')
