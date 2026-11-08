"""Download only hash-pinned rule sources; never silently adopt updated official bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('pack',type=Path);parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();root=args.out.resolve();root.mkdir(parents=True,exist_ok=True)
pack=json.loads(args.pack.read_text(encoding='utf-8-sig'))
for name,source in pack['sources'].items():
    if 'sha256' not in source:continue  # Index-only entries are not executable rules.
    target=(root/source['cache_filename']).resolve()
    if not target.is_relative_to(root) or not source['url'].startswith('https://'):raise ValueError('invalid source destination/URL')
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('existing source digest mismatch: '+name)
        print(name+': existing pinned bytes verified');continue
    with urllib.request.urlopen(source['url'],timeout=60) as response:data=response.read(50*1024*1024+1)
    if len(data)>50*1024*1024 or hashlib.sha256(data).hexdigest()!=source['sha256']:raise ValueError('download changed or exceeded budget: '+name)
    with target.open('xb') as stream:stream.write(data)
    print(name+': downloaded pinned bytes')
