"""Verified single tee assembly to a local-X/Z outline diagram and schedule."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import ezdxf
import ifcopenshell
import ifcopenshell.util.system as system
import ifcopenshell.util.placement as placement
from .cli import digest
from .tee_assembly import verify
from .tee_geometry import placement_matrix


def run(model,tee_spec,assembly_spec,out):
    paths=[Path(p).resolve() for p in (model,tee_spec,assembly_spec)];model,tee_spec,assembly_spec=paths;out=Path(out).resolve()
    before={str(p):digest(p) for p in paths}
    spec,assembly=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]]
    checks=verify(model,spec,assembly['pipe_lengths_m'])
    if not checks['assembly_checks_pass']:raise ValueError('saved assembly verification failed')
    f=ifcopenshell.open(str(model))
    if len(f.by_type('IfcElement'))!=4 or len(f.by_type('IfcPipeFitting'))!=1:raise ValueError('exact assembly coverage required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents for p in paths):raise ValueError('new repository output required')
    doc=ezdxf.new('R2013');doc.units=6;doc.appids.new('BSA_IFC')
    for name in ('BSA_PIPE_AXIS','BSA_OUTLINE','BSA_LABEL'):doc.layers.new(name)
    msp=doc.modelspace();expected=[];rows=[]
    def line(a,b,guid,layer):
        ent=msp.add_line(tuple(a),tuple(b),dxfattribs={'layer':layer});ent.set_xdata('BSA_IFC',[(1000,guid)])
        expected.append((tuple(ent.dxf.start),tuple(ent.dxf.end),guid,layer))
    inverse=np.linalg.inv(placement_matrix(spec));tee=f.by_type('IfcPipeFitting')[0]
    R,L,B=spec['outer_radius_m'],spec['main_half_length_m'],spec['branch_length_m'];inner=2*spec['inner_radius_m']
    outline=[(-R,-L),(R,-L),(R,-R),(B,-R),(B,R),(R,R),(R,L),(-R,L)]
    for a,b in zip(outline,outline[1:]+outline[:1]):line(a,b,tee.GlobalId,'BSA_OUTLINE')
    line((0,-L),(0,L),tee.GlobalId,'BSA_PIPE_AXIS');line((0,0),(B,0),tee.GlobalId,'BSA_PIPE_AXIS')
    rows.append(dict(name=tee.Name,guid=tee.GlobalId,kind='tee',bore_m=inner,outside_m=2*R,length_m='',note='Synthetic intersecting-cylinder tee; main span %.3f m, branch %.3f m'%(2*L,B)))
    for pipe in sorted(f.by_type('IfcPipeSegment'),key=lambda x:x.Name):
        ports={p.Name:p for p in system.get_ports(pipe)}
        endpoints=[inverse@placement.get_local_placement(ports[name].ObjectPlacement)[:,3] for name in ('in','out')]
        if any(abs(p[1])>1e-8 for p in endpoints):raise ValueError('nonplanar assembly unsupported')
        a,b=[np.array([p[0],p[2]]) for p in endpoints];length=float(np.linalg.norm(b-a));direction=(b-a)/length;normal=np.array([-direction[1],direction[0]])
        line(a,b,pipe.GlobalId,'BSA_PIPE_AXIS')
        for sign in (-1,1):line(a+sign*R*normal,b+sign*R*normal,pipe.GlobalId,'BSA_OUTLINE')
        line(b-R*normal,b+R*normal,pipe.GlobalId,'BSA_OUTLINE')
        rows.append(dict(name=pipe.Name,guid=pipe.GlobalId,kind='pipe',bore_m=inner,outside_m=2*R,length_m=length,note='Straight butt-ended stub'))
    bottom=min(min(a[1],b[1]) for a,b,_,_ in expected)-.08
    for i,row in enumerate(rows):
        label=f"{row['name']} | ID {inner*1000:.1f} / OD {2*R*1000:.1f} mm"
        if row['length_m']!='':label+=f" | L {row['length_m']*1000:.1f} mm"
        ent=msp.add_text(label,dxfattribs={'insert':(-.3,bottom-i*.045),'height':.025,'layer':'BSA_LABEL'});ent.set_xdata('BSA_IFC',[(1000,row['guid'])])
    msp.add_text('LOCAL X/Z | synthetic geometry | no installation detail',dxfattribs={'insert':(-.3,bottom-4*.045),'height':.02,'layer':'BSA_LABEL'})
    out.mkdir(parents=True);path=out/'segments.dxf';doc.saveas(path)
    saved=ezdxf.readfile(path);actual=[(tuple(e.dxf.start),tuple(e.dxf.end),e.get_xdata('BSA_IFC')[0].value,e.dxf.layer) for e in saved.modelspace().query('LINE')]
    if expected!=actual or saved.units!=6:raise ValueError('saved diagram geometry/identity mismatch')
    if any(digest(p)!=before[str(p)] for p in paths):raise ValueError('source changed during drawing')
    with (out/'schedule.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(inputs=before,geometry_checks=checks['checks'],rows=rows,local_to_world=placement_matrix(spec).tolist(),line_count=len(actual),saved_geometry_identity_pass=True,design_accepted=False,scope='Local X/Z synthetic tee and pipe outside outlines with centreline axes; no sockets, supports, insulation or installation drawing acceptance')
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()};(out/'tee-drawing.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','tee-spec','assembly-spec','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();print(json.dumps(run(a.model,a.tee_spec,a.assembly_spec,a.out),indent=2))
