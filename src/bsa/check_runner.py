"""Durable host-side unittest execution records; never engineering acceptance."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest
from .workspace import ROOT
from .cli import digest


def stamp():return datetime.now(timezone.utc).isoformat()


def write(path,data):
    if path.exists():raise ValueError('Fresh check record required')
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,indent=2,allow_nan=False);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)


def snapshot():
    files={ROOT/'pyproject.toml'}
    for folder,suffix in [('src','.py'),('tests','.py'),('contracts','.json'),('regulations','.json')]:
        files.update((ROOT/folder).rglob('*'+suffix))
    if any(not p.resolve().is_relative_to(ROOT) for p in files):raise ValueError('Check source escapes repository')
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(files)}


def selectors(names):
    if not isinstance(names,list) or not 1<=len(names)<=100 or len(set(names))!=len(names) or any(not isinstance(n,str) or not re.fullmatch(r'tests\.test_[A-Za-z0-9_]+(?:\.[A-Za-z_][A-Za-z0-9_]*){0,2}',n) for n in names):raise ValueError('Explicit unique repository unittest selectors required')
    return names


def outcome(result):
    counts={key:result[key] for key in ['tests_run','failures','errors','skipped','expected_failures','unexpected_successes']}
    if any(type(v) is not int or v<0 for v in counts.values()):raise ValueError('Nonnegative actual test counts required')
    passed=len(result['passed_tests'])
    if passed>counts['tests_run'] or len(result['executed_tests'])!=counts['tests_run'] or any(t not in result['executed_tests'] for t in result['passed_tests']):raise ValueError('Test counts contradict executed inventory')
    success=not any(counts[k] for k in ('failures','errors','unexpected_successes'))
    if result['successful'] is not success:raise ValueError('Unittest success contradicts test counts')
    suite_pass=success and passed>0
    return dict(passed=passed,suite_pass=suite_pass,all_tests_pass=suite_pass and passed==counts['tests_run'] and not any(counts[k] for k in counts if k!='tests_run'))


def worker(folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(ROOT/'runs') or (folder/'tests.json').exists():raise ValueError('Fresh repository worker record required')
    request=json.loads((folder/'request.json').read_text());names=selectors(request['tests'])
    class Observed(unittest.TextTestResult):
        def startTest(self,test):
            self.executed.append(test.id());super().startTest(test)
        def addSuccess(self,test):
            self.passed.append(test.id());super().addSuccess(test)
    runner=unittest.TextTestRunner(verbosity=2,resultclass=Observed)
    def create(*args,**kwargs):
        result=Observed(*args,**kwargs);result.executed=[];result.passed=[];return result
    runner.resultclass=create
    result=runner.run(unittest.defaultTestLoader.loadTestsFromNames(names))
    data=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),successful=result.wasSuccessful(),executed_tests=result.executed,passed_tests=result.passed,finished_utc=stamp())
    data.update(outcome(data));write(folder/'tests.json',data)
    return 0 if data['suite_pass'] else 1


def run(names,out):
    selectors(names);out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh repository runs output required')
    before=snapshot();out.mkdir(parents=True)
    request=dict(schema='bsa.check-request/1',tests=names,source_sha256=before,python=str(Path(sys.executable).resolve()),python_sha256=digest(Path(sys.executable)),python_version=sys.version)
    write(out/'request.json',request);started=stamp();clock=time.monotonic()
    with (out/'execution.log').open('xb') as log:
        process=subprocess.Popen([sys.executable,'-X','utf8','-m','bsa.check_runner','worker',str(out)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        write(out/'started.json',dict(started_utc=started,worker_pid=process.pid,host_pid=os.getpid()))
        code=process.wait()
    try:after=snapshot();same=after==before
    except (OSError,ValueError):after=None;same=False
    path=out/'tests.json';tests=json.loads(path.read_text()) if path.is_file() else None
    valid=tests is not None and code==(0 if outcome(tests)['suite_pass'] else 1)
    result=dict(schema='bsa.check-receipt/1',returncode=code,finished_utc=stamp(),elapsed_seconds=time.monotonic()-clock,source_unchanged=same,source_after=after,result=tests,suite_pass=bool(valid and same and tests['suite_pass']),all_tests_pass=bool(valid and same and tests['all_tests_pass']),design_accepted=False,status='source_changed' if not same else 'completed' if valid else 'worker_incomplete',artifacts={p.name:digest(p) for p in (out/'request.json',out/'started.json',out/'execution.log',path) if p.is_file()})
    write(out/'receipt.json',result);return result


def verify(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs'):raise ValueError('Repository check receipt required')
    receipt=json.loads((out/'receipt.json').read_text());request=json.loads((out/'request.json').read_text())
    selectors(request['tests'])
    if receipt.get('schema')!='bsa.check-receipt/1' or receipt.get('design_accepted') is not False or receipt.get('status')!='completed':raise ValueError('Completed unaccepted check receipt required')
    required={'request.json','started.json','execution.log','tests.json'}
    if set(receipt['artifacts'])!=required or any(digest(out/name)!=sha for name,sha in receipt['artifacts'].items()):raise ValueError('Check evidence changed or missing')
    if request['schema']!='bsa.check-request/1' or request['python']!=str(Path(sys.executable).resolve()) or request['python_sha256']!=digest(Path(sys.executable)) or request['python_version']!=sys.version:raise ValueError('Check interpreter differs')
    if receipt['source_unchanged'] is not True or receipt['source_after']!=request['source_sha256'] or snapshot()!=request['source_sha256']:raise ValueError('Check source changed; historical receipt is not current verification')
    tests=json.loads((out/'tests.json').read_text());expected=outcome(tests)
    if tests!=receipt['result'] or any(tests[k]!=v or receipt[k]!=v for k,v in expected.items() if k!='passed') or tests['passed']!=expected['passed'] or receipt['returncode']!=(0 if expected['suite_pass'] else 1):raise ValueError('Check outcome contradicts recorded process/tests')
    return dict(integrity_pass=True,tests_run=tests['tests_run'],**expected,design_accepted=False,scope='Local process/test counts and selected source-byte correspondence; not engineering acceptance or authenticated provenance')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('run');command.add_argument('tests',nargs='+');command.add_argument('--out',required=True)
    for name in ['verify','worker']:sub.add_parser(name).add_argument('out')
    args=parser.parse_args()
    if args.command=='worker':return worker(Path(args.out))
    result=run(args.tests,args.out) if args.command=='run' else verify(args.out)
    print(json.dumps(result if args.command=='verify' else {k:result[k] for k in ['status','returncode','suite_pass','all_tests_pass','design_accepted']},indent=2))
    return 0 if result['suite_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
