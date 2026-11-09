"""Bind native CAD diagnostics to saved source-product IFC alignment without waiving mesh failures."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import ifcopenshell
from ifcopenshell.util.placement import get_local_placement
from ifcopenshell.util.unit import calculate_unit_scale
from .product_alignment import load_bundle, aligned_placement
from .product_ports import mesh
from .cad_intake import METRES_PER_UNIT
from .cad_joint import run as native_joint
from .native_cad import DEFAULT_EXE
from .cli import digest
from .engine import ProjectError


def relative_basis(fixed, moving, unit_scale):
    aligned_placement(fixed,moving,0)  # Require proper rigid input frames.
    if not math.isfinite(unit_scale) or unit_scale<=0:raise ProjectError('positive CAD unit scale required')
    relative=np.linalg.inv(fixed)@moving
    if not np.allclose(relative[:3,2],[0,0,1],atol=1e-9,rtol=0):
        raise ProjectError('native adapter requires relative Z-axis rotation')
    return relative[:3,3]/unit_scale, math.degrees(math.atan2(relative[1,0],relative[0,0]))


def source_dwg(inputs):
    reports=[Path(p) for p in inputs if Path(p).name=='cad-ifc.json']
    if len(reports)!=1:raise ProjectError('one pinned source conversion required')
    r=json.loads(reports[0].read_text())
    if r.get('geometry_conversion_pass') is not True:raise ProjectError('passing source conversion required')
    candidates=[Path(p) for p,h in r['inputs'].items() if Path(p).suffix.lower()=='.dwg' and h==r['basis']['drawing_sha256']]
    if len(candidates)!=1:raise ProjectError('unique source drawing required')
    path=candidates[0]
    if inputs.get(str(path))!=digest(path):raise ProjectError('source drawing not bound to placement')
    return path,r['basis']['insunits']


def run(alignment,junction,connector,out,exe=DEFAULT_EXE):
    alignment,junction,connector,out=[Path(p).resolve() for p in (alignment,junction,connector,out)]
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents or p in out.parents for p in (alignment,junction,connector)):
        raise ProjectError('new separate repository output required')
    report_path=alignment/'alignment.json';path=alignment/'alignment.ifc'
    r=json.loads(report_path.read_text())
    if r.get('model_alignment_pass') is not True or digest(path)!=r['ifc_sha256']:
        raise ProjectError('intact passing model alignment required')
    if any(digest(Path(p))!=h for p,h in r['inputs'].items()):raise ProjectError('alignment input changed')
    _,j,ji=load_bundle(junction,'junction');_,c,ci=load_bundle(connector,'connector')
    if any(r['inputs'].get(p)!=h for p,h in {**ji,**ci}.items()):raise ProjectError('placement bundles differ from alignment inputs')
    saved=ifcopenshell.open(str(path))
    if calculate_unit_scale(saved)!=1 or {x.GlobalId for x in saved.by_type('IfcElement')}!={j.GlobalId,c.GlobalId}:
        raise ProjectError('alignment units or product coverage mismatch')
    sj,sc=saved.by_guid(j.GlobalId),saved.by_guid(c.GlobalId)
    for original,current in ((j,sj),(c,sc)):
        ov,of=mesh(original);cv,cf=mesh(current)
        if not np.array_equal(of,cf) or not np.allclose(ov,cv,atol=1e-10,rtol=0):raise ProjectError('saved local product geometry differs from source')
    jf,cf=get_local_placement(sj.ObjectPlacement),get_local_placement(sc.ObjectPlacement)
    if not np.allclose(jf,get_local_placement(j.ObjectPlacement),atol=1e-10,rtol=0) or not np.allclose(cf,r['connector_transform'],atol=1e-10,rtol=0):
        raise ProjectError('saved product placement differs from alignment')
    fixed,fu=source_dwg(ji);moving,mu=source_dwg(ci)
    if fu!=mu:raise ProjectError('native source units differ')
    translation,angle=relative_basis(jf,cf,METRES_PER_UNIT[fu])
    basis={'source':'Derived from hash-bound saved IFC alignment; diagnostic comparison only',
           'fixed_sha256':digest(fixed),'moving_sha256':digest(moving),'insunits':fu,
           'translation_drawing_units':translation.tolist(),'rotation_z_degrees':angle}
    before={str(report_path):digest(report_path),str(path):digest(path),**r['inputs']}
    out.mkdir(parents=True);bp=out/'native-basis.json';bp.write_text(json.dumps(basis,indent=2),encoding='utf-8')
    native=native_joint(fixed,moving,bp,out/'native',exe)
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('alignment sources changed during native check')
    result={'inputs':before,'native_report_sha256':digest(out/'native/joint.json'),
            'ifc_geometry_and_placement_binding_pass':True,'native_clear':native['native_clear'],
            'mesh_calculated_checks_pass':r['calculated_checks_pass'],
            'mesh_overlap_m3':r['material_overlap_m3'],'native_intersection_volume_m3':native['intersection_volume_m3'],
            'status':'comparison_requires_engineering_review','design_accepted':False,
            'scope':'Same source bodies and saved relative placement; native kernel versus tessellated intersection. No mesh waiver or installed-joint approval.'}
    (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('alignment');p.add_argument('junction');p.add_argument('connector');p.add_argument('--out',required=True);p.add_argument('--autocad',default=str(DEFAULT_EXE))
    a=p.parse_args();r=run(a.alignment,a.junction,a.connector,a.out,a.autocad)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['native_clear'] and r['mesh_calculated_checks_pass'] else 2)
