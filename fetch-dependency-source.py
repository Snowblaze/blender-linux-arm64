#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Download the pinned Blender dependency source archives and verify hashes."""
import argparse, csv, hashlib, os, urllib.request
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('names', nargs='*')
p.add_argument('--all', action='store_true')
p.add_argument('--manifest', type=Path, default=None)
p.add_argument('--output', type=Path, default=Path('dependency-sources'))
a = p.parse_args()
manifest = a.manifest or Path(__file__).parent/'dependency-sources.tsv'
if not manifest.exists():
    manifest = Path(__file__).parent/'logs/dependency-sources.tsv'
rows = list(csv.DictReader(manifest.open(), delimiter='\t'))
names = {x.upper() for x in a.names}
known = {x['name'] for x in rows}
if names-known: p.error('Unknown dependencies: '+', '.join(sorted(names-known)))
if not a.all and not names: p.error('Specify dependency names or --all')
a.output.mkdir(parents=True, exist_ok=True)
for row in rows:
    if not a.all and row['name'] not in names: continue
    target = a.output / row['file']
    if not target.exists():
        temp = target.with_name(target.name+'.part')
        print('Downloading', row['name'], row['blender_mirror'], flush=True)
        try:
            with urllib.request.urlopen(row['blender_mirror'], timeout=120) as response, temp.open('wb') as out:
                while chunk := response.read(1024*1024): out.write(chunk)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    digest = hashlib.new(row['hash_type'].lower())
    with target.open('rb') as f:
        while chunk := f.read(1024*1024): digest.update(chunk)
    if digest.hexdigest().lower() != row['hash'].lower():
        raise SystemExit('Checksum mismatch: '+str(target))
    print('Verified', target, flush=True)
