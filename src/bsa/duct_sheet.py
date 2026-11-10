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


def add_flow_arrows(doc, spec, topology, scale, result):
    settings=spec.get('flow_arrows')
    if settings is None:return []
    if topology is None or result['flow_aggregation'].get('topology_pass') is not True or result['flow_aggregation'].get('flow_conserved') is not True:
        raise ValueError('Flow arrows require the conserved calculation tree')
    if not isinstance(settings,dict) or set(settings)!={'layer','length_m','width_m','fraction'}:
        raise ValueError('Explicit arrow layer, length, width and fractional position required')
    layer=settings['layer']
    if not isinstance(layer,str) or not layer.strip() or layer in doc.layers:
        raise ValueError('New nonempty arrow layer required')
    for key in ('length_m','width_m','fraction'):
        v=settings[key]
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
            raise ValueError('Positive finite arrow dimensions/position required')
    if settings['fraction']>=1:raise ValueError('Arrow position must lie inside section')
    planned=[]
    for name,entry in spec['sections'].items():
        line=doc.entitydb[entry['line_handle']]
        start,end=line.dxf.start,line.dxf.end
        if entry['from_node']!=topology[name]['from']:start,end=end,start
        dx,dy,dz=(end[i]-start[i] for i in range(3))
        length=math.hypot(dx,dy)*scale
        if abs(dz*scale)>1e-8 or length<=0:raise ValueError('Flow arrows require nonzero planar XY sections')
        if settings['length_m']>=length*settings['fraction']:
            raise ValueError('Arrow does not fit inside section; supply a smaller explicit size')
        flow=result['flow_aggregation'].get('section_flow_L_s',{}).get(name)
        row=next(r for r in result['sections'] if r['id']==name)
        if type(flow) not in (int,float) or not math.isfinite(flow) or flow<=0 or not math.isclose(flow,row['inputs']['flow_m3_s']*1000,rel_tol=1e-12):
            raise ValueError('Arrow direction requires matching positive supply-tree flow')
        ux,uy=dx/(length/scale),dy/(length/scale)
        tip=tuple(start[i]+(end[i]-start[i])*settings['fraction'] for i in range(3))
        back=settings['length_m']/scale;half=settings['width_m']/scale/2
        wings=[(tip[0]-ux*back-sign*uy*half,tip[1]-uy*back+sign*ux*half,tip[2]) for sign in (-1,1)]
        planned.append((name,tip,wings))
    doc.layers.new(layer,dxfattribs={'color':7})
    records=[]
    for name,tip,wings in planned:
        entities=[doc.modelspace().add_line(wing,tip,dxfattribs={'layer':layer}) for wing in wings]
        records.append(dict(section=name,from_node=topology[name]['from'],to_node=topology[name]['to'],
                            handles=[e.dxf.handle for e in entities],tip_m=[v*scale for v in tip],
                            wings_m=[[v*scale for v in p] for p in wings]))
    return records


def run(source, schedule, binding, output, *, inherited_schedule_sha256=None):
    source,schedule,binding,output=map(lambda p:Path(p).resolve(),(source,schedule,binding,output))
    paths=(source,schedule,binding)
    if output.exists() or any(output==p or output in p.parents for p in paths):
        raise ValueError('New output separate from all inputs required')
    pins={str(p):digest(p) for p in paths}
    spec=json.loads(binding.read_text(encoding='utf-8-sig'))
    result=json.loads(schedule.read_text(encoding='utf-8-sig'))
    if inherited_schedule_sha256 is not None:
        if 'schedule_sha256' in spec:
            raise ValueError('Inherited schedule hash cannot be overridden in binding')
        if pins[str(schedule)]!=inherited_schedule_sha256:
            raise ValueError('Inherited schedule producer changed')
        spec['schedule_sha256']=inherited_schedule_sha256
    if set(spec)-{'flow_arrows'}!={'source_sha256','schedule_sha256','basis','sections'}:

        raise ValueError('Exact source/schedule hashes, basis and sections required')
    if spec['source_sha256']!=pins[str(source)] or spec['schedule_sha256']!=pins[str(schedule)]:
        raise ValueError('Drawing or schedule source hash mismatch')
    if not isinstance(spec['basis'],str) or not spec['basis'].strip():raise ValueError('Explicit drawing binding basis required')
    if result.get('status')!='pass' or any(r['failures'] or not r['calculation'] for r in result['sections']):
        raise ValueError('Passing selected section schedule required')
    rows={r['id']:r for r in result['sections']}
    if len(rows)!=len(result['sections']) or set(rows)!=set(spec['sections']):
        raise ValueError('Exact unique section coverage required')
    topology=None;node_points={}
    if 'flow_aggregation' in result:
        edges=result['flow_aggregation'].get('sections')
        if not isinstance(edges,list):raise ValueError('Inherited flow tree lacks endpoint evidence; rerun aggregation')
        topology={edge['id']:edge for edge in edges}
        if len(topology)!=len(edges) or set(topology)!=set(rows):raise ValueError('Calculation tree section coverage mismatch')
    doc=ezdxf.readfile(source)
    from .cad_intake import METRES_PER_UNIT
    if doc.units not in METRES_PER_UNIT:raise ValueError('Known drawing length units required')
    scale=METRES_PER_UNIT[doc.units];original=snapshot(doc);used=set();edits={}
    for name,entry in spec['sections'].items():
        required={'line_handle','from_m','to_m','cells'}|({'from_node','to_node'} if topology is not None else set())
        if set(entry)!=required:raise ValueError('Exact line/endpoints/cells and inherited node identities required')
        if topology is not None:
            edge=topology[name];pair=(entry['from_node'],entry['to_node'])
            if pair not in ((edge['from'],edge['to']),(edge['to'],edge['from'])):
                raise ValueError('Drawing section endpoints differ from calculation tree')
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
            if topology is not None:
                node=entry['from_node' if key=='from_m' else 'to_node']
                if node in node_points and math.dist(node_points[node],expected)>1e-8:
                    raise ValueError('Shared calculation node is disconnected in drawing')
                node_points[node]=expected
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
    arrows=add_flow_arrows(doc,spec,topology,scale,result)
    expected=snapshot(doc)
    if any(expected[h]!=tags for h,tags in original.items() if h not in edits):
        raise ValueError('Unbound modelspace entity changed')
    if any(digest(p)!=pins[str(p)] for p in paths):raise ValueError('Inputs changed during drawing update')
    output.mkdir(parents=True)
    target=output/'Supply Air Distribution.dxf';doc.saveas(target)
    reopened=ezdxf.readfile(target)
    if snapshot(reopened)!=expected:raise ValueError('Saved DXF entity correspondence failed')
    evidence=dict(inputs=pins,dxf_sha256=digest(target),updated_sections=len(rows),bound_text_cells=len(edits),
        flow_arrows=arrows,flow_arrow_count=len(arrows),
        unchanged_unbound_modelspace=True,saved_dxf_correspondence=True,basis=spec['basis'],
        calculation_tree_endpoint_binding=topology is not None,bound_node_count=len(node_points),
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
