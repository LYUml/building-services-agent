"""Restore the pinned Windows x64 energy engine entirely inside this repository.
Run from the project's Python environment. No global installs or PATH changes.
"""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
URL="https://github.com/NatLabRockies/EnergyPlus/releases/download/v25.2.0/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64.zip"
SHA="4136901f7e1708f6536d84278e26ad88b414c7efc905febf6d49c2539a36f3cd"
COMMIT="9f8b6bd0b5a58fd4f97cfd8b9f7393f222a1bb43"


def verify_installation(archive, target):
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            if not (target / member.filename).resolve().is_relative_to(target.resolve()):
                raise RuntimeError("archive path escapes target")
        if not target.exists():
            with TemporaryDirectory(dir=target.parent) as staging:
                payload = Path(staging) / "energyplus"
                package.extractall(payload)
                payload.rename(target)
        for member in package.infolist():
            if member.is_dir():
                continue
            installed = target / member.filename
            if not installed.is_file() or installed.stat().st_size != member.file_size:
                raise RuntimeError(f"installed EnergyPlus file differs from verified archive: {member.filename}")
            with installed.open("rb") as disk_file, package.open(member) as archive_file:
                if hashlib.file_digest(disk_file, "sha256").digest() != hashlib.file_digest(archive_file, "sha256").digest():
                    raise RuntimeError(f"installed EnergyPlus file differs from verified archive: {member.filename}")


def main():
    if sys.prefix==sys.base_prefix:
        raise RuntimeError("activate/create this repository's .venv first")
    if not Path(sys.prefix).resolve().is_relative_to(ROOT):
        raise RuntimeError("use a virtual environment inside this repository")
    if platform.system()!="Windows" or platform.machine().lower() not in ("amd64","x86_64"):
        raise RuntimeError("bootstrap currently supports Windows x64 only")
    subprocess.run([sys.executable,"-m","pip","install","openstudio==3.11.0"],check=True)
    downloads=ROOT/"tools/downloads";downloads.mkdir(parents=True,exist_ok=True)
    archive=downloads/"energyplus.zip"
    if not archive.exists():urllib.request.urlretrieve(URL,archive)
    with archive.open("rb") as archive_file:
        actual=hashlib.file_digest(archive_file,"sha256").hexdigest()
    if actual!=SHA:raise RuntimeError("EnergyPlus archive checksum mismatch; refusing extraction")
    target=ROOT/"tools/energyplus-25.2"
    exe=target/"EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe"
    verify_installation(archive, target)
    repo=ROOT/"tools/openstudio-mcp"
    if not repo.exists():
        subprocess.run(["git","clone","https://github.com/NatLabRockies/openstudio-mcp.git",str(repo)],check=True)
        subprocess.run(["git","-C",str(repo),"checkout",COMMIT],check=True)
    head=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
    dirty=subprocess.check_output(["git","-C",str(repo),"status","--porcelain"],text=True).strip()
    if head!=COMMIT or dirty:raise RuntimeError("upstream checkout differs from inspected pin; do not overwrite it")
    subprocess.run([sys.executable,"-m","pip","install","-e",str(repo)],check=True)
    print(json.dumps({"energyplus":str(exe),"archive_sha256":actual,"openstudio_mcp_commit":head},indent=2))

if __name__=="__main__":main()
