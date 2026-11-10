"""Bind passing duct schedules to existing single-line DXF sheets.

Updates explicit TEXT cells only after source and section centreline checks.
Native reopening and plot review are separate mandatory acceptance stages.
"""
import json
from pathlib import Path
import math
import ezdxf
from .cli import digest


def cell_values(row):
    i,c=row['inputs'],row['calculation']
    return [row['id'],f"{i['flow_m3_s']*1000:.1f}",
            f"{i['width_m']*1000:.0f} x {i['height_m']*1000:.0f}",
            f"{c['actual_velocity_m_s']:.2f}",f"{c['friction_Pa_m']:.3f}"]


def snapshot(doc):
    # Include all modelspace DXF tags, including polyline vertices and entity styles.
    from ezdxf.lldxf.tagwriter import TagCollector
    return {e.dxf.handle:repr(TagCollector.dxftags(e)) for e in doc.modelspace()}


def run(source, schedule, binding, output):
    source,schedule,binding,output=map(lambda p:Path(p).resolve(),(source,schedule,binding,output))
    paths=(source,schedule,binding)
    if output.exists() or any(output==p or output in p.parents for p in paths):
        raise ValueError('New output separate from all inputs required')
    pins={str(p):digest(p) for p in paths}
    spec=json.loads(binding.read_text(encoding='utf-8-sig'))
    result=json.loads(schedule.read_text(encoding='utf-8-sig'))
    if set(spec)!={'source_sha256','schedule_sha256','basis','sections'}:
        raise ValueError('Exact source/schedule hashes, basis and sections required')
    if spec['source_sha256']!=pins[str(source)] or spec['schedule_sha256']!=pins[str(schedule)]:
        raise ValueError('Drawing or schedule source hash mismatch')
    if not isinstance(spec['basis'],str) or not spec['basis'].strip():raise ValueError('Explicit drawing binding basis required')
    if result.get('status')!='pass' or any(r['failures'] or not r['calculation'] for r in result['sections']):
        raise ValueError('Passing selected section schedule required')
    rows={r['id']:r for r in result['sections']}
    if len(rows)!=len(result['sections']) or set(rows)!=set(spec['sections']):
        raise ValueError('Exact unique section coverage required')
    doc=ezdxf.readfile(source)
    from .cad_intake import METRES_PER_UNIT
    if doc.units not in METRES_PER_UNIT:raise ValueError('Known drawing length units required')
    scale=METRES_PER_UNIT[doc.units];original=snapshot(doc);used=set();edits={}
    for name,entry in spec['sections'].items():
        if set(entry)!={'line_handle','from_m','to_m','cells'}:raise ValueError('Explicit line, metre endpoints and five TEXT cells required')
        line=doc.entitydb.get(entry['line_handle'])
        if line is None or line.dxftype()!='LINE' or line.dxf.handle not in original:
            raise ValueError('Bound centreline must be a modelspace LINE')
        if line.dxf.handle in used:raise ValueError('Duplicate entity binding')
        used.add(line.dxf.handle)
        for key,point in [('from_m',line.dxf.start),('to_m',line.dxf.end)]:
            expected=entry[key]
            if len(expected)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in expected):raise ValueError('Finite 3D metre endpoints required')
            if math.dist([v*scale for v in point],expected)>1e-8:
                raise ValueError('Centreline geometry differs from binding')
        cells=entry['cells']
        if not isinstance(cells,list) or len(cells)!=5:raise ValueError('Five schedule cells required')
        values=cell_values(rows[name])
        for index,(cell,value) in enumerate(zip(cells,values)):
            if set(cell)!={'handle','expected_text'}:raise ValueError('Cell handle and prior text required')
            e=doc.entitydb.get(cell['handle'])
            if e is None or e.dxftype()!='TEXT' or e.dxf.handle not in original or e.dxf.handle in used:
                raise ValueError('Unique modelspace TEXT binding required')
            used.add(e.dxf.handle)
            if e.dxf.text!=cell['expected_text'] or (index==0 and e.dxf.text!=name):
                raise ValueError('Prior schedule cell or identity mismatch')
            edits[e.dxf.handle]=value;e.dxf.text=value
    expected=snapshot(doc)
    if any(expected[h]!=tags for h,tags in original.items() if h not in edits):
        raise ValueError('Unbound modelspace entity changed')
    if any(digest(p)!=pins[str(p)] for p in paths):raise ValueError('Inputs changed during drawing update')
    output.mkdir(parents=True)
    target=output/'Supply Air Distribution.dxf';doc.saveas(target)
    reopened=ezdxf.readfile(target)
    if snapshot(reopened)!=expected:raise ValueError('Saved DXF entity correspondence failed')
    evidence=dict(inputs=pins,dxf_sha256=digest(target),updated_sections=len(rows),bound_text_cells=len(edits),
        unchanged_unbound_modelspace=True,saved_dxf_correspondence=True,basis=spec['basis'],
        scope='Existing single-line centreline geometry retained; selected dimensions and flow/friction schedule updated. No physical-width or routing regeneration.',
        native_reopen_pass=False,plot_visual_review='pending',design_accepted=False)
    (output/'drawing-update.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    return evidence


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('schedule');parser.add_argument('binding')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    result=run(args.source,args.schedule,args.binding,args.out)
    print(result['updated_sections'],'sections updated; native/plot acceptance pending')
