"""Recheck a saved straight circular IFC route before fresh hydraulic analysis."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_binding import prepare,reconcile
from .ifc_drawing import extract
from .network import run as analyse


def run(project,model,binding,ifc,out):
    paths=[Path(p).resolve() for p in (project,model,binding,ifc)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in paths}
    template,source,links=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[:3]]
    derived,evidence=prepare(template,source,links)
    geometry=extract(paths[3])
    if not geometry['calculated_checks_pass']:raise ProjectError('saved straight circular IFC profiles/ports failed verification')
    names=[r['name'] for r in geometry['segments']]
    expected=[name for pieces in links['segments'].values() for name in pieces]
    if len(names)!=len(set(names)) or set(names)!=set(expected):raise ProjectError('saved segment coverage differs from bound route')
    out.mkdir(parents=True,exist_ok=False)
    generated=out/'network-input.json';generated.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    (out/'saved-geometry.json').write_text(json.dumps(geometry,indent=2),encoding='utf-8')
    reconcile(paths[3],generated,links,source)
    calculation=analyse(generated,out/'analysis')
    reconcile(paths[3],generated,links,source)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('saved IFC network sources changed')
    result=dict(inputs=before,inputs_unchanged=True,saved_ifc_geometry_match=True,segments=evidence,
                calculated_checks_pass=calculation['calculated_checks_pass'],design_accepted=False,
                scope='Saved straight hollow circular segments and directed port route reconciled to source-derived network; fresh pressure budget only',
                pending=['equipment/product and physical junction applicability','controls, suction, clashes and full engineering/regulatory acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'ifc-network.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
