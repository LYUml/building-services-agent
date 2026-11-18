"""Build committed source prerelease assets, never environments or private runs."""
import argparse
import json
from pathlib import Path
from build_candidate import build


def package(out):
    out = Path(out).resolve()
    result = build(out)
    version = result['version']
    archive = out / result['archive']
    renamed = archive.with_name('building-services-agent-' + version + '-source.zip')
    archive.rename(renamed)
    result['archive'] = renamed.name
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (out / 'SHA256SUMS').write_text(result['sha256'] + '  ' + renamed.name + '\n', encoding='ascii')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    print(json.dumps(package(p.parse_args().out), indent=2))
