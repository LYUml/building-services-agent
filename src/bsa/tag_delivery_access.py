"""Fixed-host AI access to the existing tagged native delivery pipeline."""
from pathlib import Path
from . import source_network_tag_pipeline as pipeline,workspace
from .cli import digest


def summary(out,data):
    out=Path(out).resolve();root=(workspace.project_root() or workspace.ROOT/'runs').resolve()
    if not out.is_relative_to(root):raise ValueError('Selected project delivery required')
    artifacts=[]
    for name in ('delivery.json','native/section.dwg','native/sheet.pdf'):
        path=out/name;sha=digest(path)
        if name!='delivery.json' and data['artifacts'].get(name)!=sha:raise ValueError('Tagged artifact differs from producer')
        artifacts.append(dict(path=str(path),project_path=path.relative_to(root).as_posix(),sha256=sha,bytes=path.stat().st_size))
    return dict(status='review_required',components=data['components'],ancestry_verified=data['ancestry_verified'],
        native_reopen_verified=data['native_reopen_verified'],plot_visual_review=data['plot_visual_review'],
        pressure_budget_complete=False,design_accepted=False,pending=data['pending'],artifacts=artifacts,
        scope='Tagged source-model delivery from existing delivery/schedule; actual visual inspection, physical calibration, complete pressure/equipment/installation and engineering acceptance remain separate.')


def run(base,schedule,out,autocad):
    if autocad is None:raise ValueError('Explicit host AutoCAD startup configuration required')
    return summary(out,pipeline.run(base,schedule,out,autocad))


def inspect(out):
    out=Path(out).resolve();before=digest(out/'delivery.json')
    checked=pipeline.verify(out);result=summary(out,checked)
    if digest(out/'delivery.json')!=before or result['artifacts'][0]['sha256']!=before:raise ValueError('Tagged delivery changed during inspection')
    result['integrity_pass']=True;return result
