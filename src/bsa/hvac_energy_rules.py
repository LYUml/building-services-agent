"""Bind saved HVAC rule checks to both variants of a completed design-day run."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .energy_completion import inspect
from .hvac_idf_rules import run as check_idf


def run(energy,basis,pack,sources,out):
    energy=Path(energy).resolve();out=Path(out).resolve()
    report=energy/'analysis.json'
    data=json.loads(report.read_text(encoding='utf-8'))
    before={str(report):digest(report)}
    if set(data.get('results',{}))!={'baseline','variant'}:
        raise ProjectError('exact design-day baseline and variant required')
    for name,row in data['results'].items():
        folder=energy/name
        expected=dict(row.get('artifacts',{}))
        native=row.get('completion',{}).get('artifacts',{})
        if any(expected[k]!=native[k] for k in expected.keys() & native.keys()):
            raise ProjectError('inconsistent native energy artifact hashes')
        expected.update(native)
        if not {'model.idf','model.osm','eplusout.sql','engine.log','eplusout.end','eplusout.err'}<=set(expected):
            raise ProjectError('incomplete native energy artifact binding')
        for file,sha in expected.items():
            path=(folder/file).resolve()
            if not path.is_relative_to(folder) or not path.is_file() or digest(path)!=sha:
                raise ProjectError('executed energy artifact differs: '+name+'/'+file)
            before[str(path)]=sha
        completion=inspect(folder,row['completion']['process_returncode'],data['engine'],data['engine_sha256'])
        if not completion['completion_verified']:raise ProjectError('native energy completion unverified: '+name)
    if any(out==Path(p) or out in Path(p).parents for p in before):
        raise ProjectError('output must not contain executed energy artifacts')
    out.mkdir(parents=True,exist_ok=False)
    checks={name:check_idf(energy/name/'model.idf',basis,pack,sources,out/name) for name in data['results']}
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in before.items()):
        raise ProjectError('executed energy artifacts changed during regulatory checks')
    passed=all(row['supported_checks_pass'] for row in checks.values())
    result=dict(status='pass' if passed else 'pending',inputs=before,inputs_unchanged=True,
                variants=checks,supported_checks_pass=passed,design_accepted=False,
                regulatory_compliance='not_established',
                scope='Both executed design-day variants, native completion and artifact identity, supported static sizing input limits only')
    (out/'energy-regulation-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
