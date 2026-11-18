"""Build committed source prerelease assets, never environments or private runs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib
import zipfile
from build_candidate import build, ROOT


def package(out):
    out = Path(out).resolve()
    result = build(out)
    version = tomllib.loads(subprocess.check_output(['git', 'show', result['commit'] + ':pyproject.toml'], cwd=ROOT, text=True))['project']['version']
    archive = out / result['archive']
    with zipfile.ZipFile(archive, 'a', compression=zipfile.ZIP_DEFLATED) as stream:
        info = zipfile.ZipInfo('.bsa-release.json', date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        stream.writestr(info, json.dumps(dict(schema='bsa.release-source/1', commit=result['commit'], version=version), sort_keys=True) + '\n')
        if stream.testzip() is not None:
            raise ValueError('Release CRC check failed')
    renamed = archive.with_name('building-services-agent-' + version + '-source.zip')
    archive.rename(renamed)
    with renamed.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    result.update(archive=renamed.name, version=version,
                  sha256=digest,
                  bytes=renamed.stat().st_size)
    with zipfile.ZipFile(renamed) as stream:
        result.update(entries=len(stream.infolist()), uncompressed_bytes=sum(i.file_size for i in stream.infolist()))
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (out / 'SHA256SUMS').write_text(result['sha256'] + '  ' + renamed.name + '\n', encoding='ascii')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    print(json.dumps(package(p.parse_args().out), indent=2))
