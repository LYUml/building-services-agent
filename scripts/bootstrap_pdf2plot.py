"""Fetch exact MIT upstream helper files; optionally create isolated pinned runtime."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]


def run(install=False):
    lock=json.loads((ROOT/'adapters/pdf2plot/lock.json').read_text())
    destination=ROOT/'tools'/('pdf2plot-'+lock['commit'][:7]);destination.mkdir(parents=True,exist_ok=True)
    for name,expected in lock['files'].items():
        path=destination/name
        data=path.read_bytes() if path.exists() else urlopen('https://raw.githubusercontent.com/adamkucharski/pdf2plot/'+lock['commit']+'/'+name,timeout=30).read()
        if sha256(data).hexdigest()!=expected:raise ValueError('upstream file pin mismatch: '+name)
        if not path.exists():path.write_bytes(data)
    if install:
        runtime=ROOT/'tools/pdf2plot-runtime';python=runtime/'Scripts/python.exe'
        if not python.exists():subprocess.run([sys.executable,'-m','venv',str(runtime)],check=True)
        subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'adapters/pdf2plot/requirements.txt')],check=True)
        subprocess.run([str(python),'-c','import fitz; from importlib.metadata import version; print(version("PyMuPDF"))'],check=True)
    return destination

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--install',action='store_true');print(run(**vars(p.parse_args())))
