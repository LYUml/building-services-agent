"""Install the pinned official Windows Radiance zip inside this workspace only."""
import hashlib
import json
from pathlib import Path
import platform
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/LBNL-ETA/Radiance/releases/download/rad6R0P2/Radiance_c1700d56_Windows.zip'
SHA='c4f02efcb4a33f4a43b7ce0ba58100544abc317a1be61f7b0425a64a66eb8a09'


def main():
    if platform.system()!='Windows':raise RuntimeError('bootstrap currently supports Windows only; supply your local Radiance installation on other platforms')
    archive=ROOT/'tools/downloads/radiance.zip';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():urllib.request.urlretrieve(URL,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA:raise RuntimeError('Radiance archive checksum mismatch')
    target=ROOT/'tools/radiance-6'
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (target/item.filename).resolve().is_relative_to(target):raise RuntimeError('unsafe archive path')
        if not target.exists():
            target.mkdir()
            z.extractall(target)
        for item in z.infolist():
            if item.is_dir():continue
            path=target/item.filename
            if not path.is_file() or hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(z.read(item)).digest():
                raise RuntimeError('installed Radiance file differs from verified archive: '+item.filename)
    print(json.dumps(dict(bin_dir=str(target/'bin'),archive_sha256=SHA)))

if __name__=='__main__':main()
