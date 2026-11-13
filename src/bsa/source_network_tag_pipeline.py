"""Compose finite source-linked tags, native DWG/PDF and independent review."""
import argparse
import json
from pathlib import Path
from . import source_network_tags as tags,source_network_tag_review as review
from . import ifc_native as native
from .cli import digest
from .workspace import allowed


def methods():
    return [Path(m.__file__).resolve() for m in (tags,review,native)]+[Path(__file__).resolve()]


def inputs(base,schedule,autocad):
    return {str(p):digest(p) for p in [base/'delivery.json',schedule/'schedule.json',autocad,*methods()]}


def run(base,schedule,out,autocad):
    base,schedule,out,autocad=[Path(p).resolve() for p in (base,schedule,out,autocad)]
    if not all(allowed(p) for p in (base,schedule,out)) or out.exists() or not autocad.is_file() or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (base,schedule)):
        raise ValueError('Fresh separate host-selected output and explicit AutoCAD required')
    pins=inputs(base,schedule,autocad)
    # The final independent review replays both upstream ancestries and their
    # shared analysis identity; generated intermediates never imply acceptance.
    placement=tags.study(base,schedule,out/'annotations')
    if placement['selected'] is None:raise ValueError('Complete annotation placement unavailable; native generation blocked')
    native.run(out/'annotations/Tagged Network Study.dxf',base/'layout/sheet.json',out/'native',autocad)
    result=review.review(out/'annotations',out/'native',out/'review')
    if inputs(base,schedule,autocad)!=pins:raise ValueError('Tag pipeline sources or methods changed')
    record=dict(source_delivery=str(base),source_schedule=str(schedule),autocad=str(autocad),inputs=pins,
        components=len(placement['selected']),ancestry_verified=result['ancestry_verified'],native_reopen_verified=result['native_reopen_verified'],
        plot_visual_review='pending',design_accepted=False,
        pending=['actual plotted PDF visual inspection','physical source calibration','complete pressure and equipment selection','installation detail and full engineering acceptance'])
    record['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'delivery.json').write_text(json.dumps(record,indent=2));return record


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected tag pipeline output required')
    record=review.load(out/'delivery.json');base=Path(record['source_delivery']).resolve();schedule=Path(record['source_schedule']).resolve()
    if not allowed(base) or not allowed(schedule):raise ValueError('Host-selected source workspaces required')
    if record['inputs']!=inputs(base,schedule,Path(record['autocad'])):raise ValueError('Tag pipeline inputs/methods changed')
    required={'annotations/placement.json','annotations/Tagged Network Study.dxf','native/section.dwg','native/sheet.pdf','native/native-verification.json','native/native-reopen/source-export.dxf','review/review.json'}
    if not required<=set(record['artifacts']):raise ValueError('Tag pipeline artifact coverage missing')
    for name,sha in record['artifacts'].items():
        p=(out/name).resolve()
        if not p.is_relative_to(out) or digest(p)!=sha:raise ValueError('Tag pipeline artifact changed')
    nested=review.load(out/'review/review.json')
    if Path(nested['study']).resolve()!=out/'annotations' or Path(nested['native_output']).resolve()!=out/'native':raise ValueError('Tag pipeline review points outside its stages')
    placement=review.load(out/'annotations/placement.json')
    if Path(placement['source_delivery']).resolve()!=base or Path(placement['source_schedule']).resolve()!=schedule:raise ValueError('Tag pipeline annotation ancestry differs')
    result=review.verify(out/'review')
    if record['components']!=result['checks']['component_count'] or any(record[k]!=result[k] for k in ('ancestry_verified','native_reopen_verified','plot_visual_review','design_accepted')):raise ValueError('Tag pipeline summary differs from independent review')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('run');a.add_argument('delivery');a.add_argument('schedule');a.add_argument('--out',required=True);a.add_argument('--autocad',required=True)
    s.add_parser('verify').add_argument('out');a=p.parse_args()
    r=run(a.delivery,a.schedule,a.out,a.autocad) if a.command=='run' else verify(a.out)
    print(json.dumps({k:r[k] for k in ('components','ancestry_verified','native_reopen_verified','plot_visual_review','design_accepted')},indent=2));raise SystemExit(2)
