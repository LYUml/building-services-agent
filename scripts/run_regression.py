"""Run stdlib unittest discovery with retained logs,live progress and source hashes.

This reports failures and skips unchanged;it never repairs the host or enables
optional native tests. Output must be a new directory under this repository's runs.
"""
import argparse
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z']).decode('utf-8').split('\0')
    files={ROOT/name for name in names if name and (ROOT/name).is_file()}
    for directory,pattern in [('src','*.py'),('tests','*.py'),('contracts','*.json')]:files.update((ROOT/directory).rglob(pattern))
    files.add(Path(__file__).resolve())
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(files)}


def write(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(path)


def run(out,pattern='test*.py'):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('New repository runs directory required')
    before=sources();out.mkdir(parents=True)
    started=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
    record=dict(command=['unittest','discover','-s','tests','-p',pattern,'-v'],
        revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tracked_changes=subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','HEAD'],text=True).splitlines(),
        started_utc=started,source_sha256=before,python=sys.version,design_accepted=False)
    write(out/'start.json',record)

    class Result(unittest.TextTestResult):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.case=None;self.finished=0;self.successes=0

        def addSuccess(self,test):
            self.successes+=1;super().addSuccess(test)

        def update(self,state):
            write(out/'progress.json',dict(state=state,started_utc=started,elapsed_seconds=time.monotonic()-tick,
                started=self.testsRun,finished=self.finished,current_test=self.case,
                passed=self.successes,
                failures=len(self.failures),errors=len(self.errors),skipped=len(self.skipped),
                expected_failures=len(self.expectedFailures),unexpected_successes=len(self.unexpectedSuccesses)))

        def startTest(self,test):
            self.case=test.id();super().startTest(test);self.update('running')

        def stopTest(self,test):
            self.finished+=1;super().stopTest(test);self.update('running');self.stream.flush()

    sys.path.insert(0,str(ROOT))
    write(out/'progress.json',dict(state='discovering',started_utc=started))
    with (out/'unittest.log').open('w',encoding='utf-8',buffering=1) as stream:
        with redirect_stdout(stream),redirect_stderr(stream):
            suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern)
            result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    after=sources();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
    final=dict(**record,finished_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-tick,
        invocations=result.testsRun,failures=[dict(test=t.id(),traceback=trace) for t,trace in result.failures],
        errors=[dict(test=t.id(),traceback=trace) for t,trace in result.errors],skipped=[dict(test=t.id(),reason=reason) for t,reason in result.skipped],
        expected_failures=[dict(test=t.id(),traceback=trace) for t,trace in result.expectedFailures],unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
        source_unchanged=not changed,changed_sources=changed,tests_successful=result.wasSuccessful())
    final['passed']=result.successes
    final['no_tests_discovered']=result.testsRun==0
    final['regression_pass']=result.testsRun>0 and result.wasSuccessful() and not changed
    final['log_sha256']=digest(out/'unittest.log');write(out/'result.json',final)
    result.case=None;result.update('complete')
    return final


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--pattern',default='test*.py');args=parser.parse_args()
    result=run(args.out,args.pattern)
    print(json.dumps({k:result[k] for k in ('invocations','passed','source_unchanged','regression_pass')},indent=2))
    raise SystemExit(0 if result['regression_pass'] else 1)
