"""Prepare UCI train+test complete cases; preserve upstream input unchanged."""
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
folder = root / '.runtime/datasets'
archive = folder / 'uci-adult.zip'
rows = []
counts = {}
with zipfile.ZipFile(archive) as z:
    for name in ('adult.data', 'adult.test'):
        raw = z.read(name).decode('utf-8')
        candidates = list(csv.reader(io.StringIO('\n'.join(
            line for line in raw.splitlines() if line.strip() and not line.startswith('|')
        )), skipinitialspace=True))
        valid = [row for row in candidates if len(row) == 15 and '?' not in row]
        counts[name] = {'raw': len(candidates), 'complete': len(valid)}
        for row in valid:
            row[-1] = row[-1].removesuffix('.')
        rows.extend(valid)
assert len(rows) == 45222, len(rows)
output = folder / 'adult-complete.csv'
with output.open('w', newline='') as f:
    csv.writer(f).writerows(rows)
manifest = {
    'source': 'https://archive.ics.uci.edu/static/public/2/adult.zip',
    'source_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'counts': counts, 'combined_complete_rows': len(rows),
    'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'paper_claimed_rows': 45224,
    'note': 'Standard UCI complete cases yield 45222, two fewer than the paper. '
            'Do not fabricate rows. Upstream data/adult.data remains unchanged.'
}
(folder / 'adult-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
