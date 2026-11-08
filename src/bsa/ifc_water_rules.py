"""Check a saved, source-reconciled network_coordination producer."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_binding import reconcile
from .water_pipe_regulations import run as check


def run(producer,model,binding,basis,pack,sources,out):
    producer=Path(producer).resolve();model=Path(model).resolve();binding=Path(binding).resolve()
    report=producer/'network-binding.json';before=digest(report)
    data=json.loads(report.read_text())
    for path in (model,binding):
        if data['inputs'].get(str(path))!=digest(path):raise ProjectError('producer source identity differs')
    required={'bim/model.ifc','network-input.json','analysis/network.json'}
    if not required<=set(data['artifacts']):raise ProjectError('missing producer native artifact coverage')
    def verify():
        for path in (model,binding):
            if data['inputs'].get(str(path))!=digest(path):raise ProjectError('producer source identity differs')
        for name,sha in data['artifacts'].items():
            p=(producer/name).resolve()
            if not p.is_relative_to(producer) or not p.is_file() or digest(p)!=sha:raise ProjectError('producer artifact changed: '+name)
        if digest(report)!=before:raise ProjectError('producer report changed')
    verify()
    reconcile(producer/'bim/model.ifc',producer/'network-input.json',json.loads(binding.read_text()),json.loads(model.read_text()))
    result=check(producer/'network-input.json',basis,pack,sources,out)
    verify()
    result['saved_ifc_binding']=dict(producer_report_sha256=before,ifc_sha256=digest(producer/'bim/model.ifc'),saved_geometry_reconciled=True)
    (Path(out)/'water-pipe-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
