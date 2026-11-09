"""Source/native rectangular path verification before fixed-speed fan intersection."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .rectangular_binding import verified_study
from .rectangular_fan import run as solve


def run(project,model,binding,ifc,analysis,curve,out):
    paths=[Path(p).resolve() for p in (project,model,binding,ifc,analysis,curve)]
    out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate native fan output required')
    before={str(p):digest(p) for p in paths}
    verified_study(*paths[:5])
    result=solve(paths[0],paths[5],out)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('native fan sources changed during solve')
    result.update(inputs=before,inputs_unchanged=True,geometry_bound=True,native_path_correspondence_pass=True,
        ifc_sha256=digest(paths[3]),
        native_binding_scope='Source/native saved rectangular path dimensions, true arc lengths, per-piece K and directed ports; fan equipment itself is not authored or selected')
    result['pending']=[p for p in result['pending'] if p!='Native geometry binding and branches/loops']+['Native fan equipment, ports and product selection','Branches/loops and flow balancing']
    (out/'fan.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
