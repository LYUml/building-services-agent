"""Scoped native two-solid Boolean with sourced rigid placement and INSBASE compensation."""
import argparse
import json
import math
from pathlib import Path
import shutil
import numpy as np
import ezdxf
from .cad_intake import export_dwg, METRES_PER_UNIT
from .cad_ifc import mass_properties
from .cli import digest
from .engine import ProjectError
from .native_cad import DEFAULT_EXE, execute, lisp_string as q


def insertion(base, translation, angle):
    if np.shape(base)!=(3,) or np.shape(translation)!=(3,) or not np.isfinite(base).all() or not np.isfinite(translation).all():
        raise ProjectError('finite three-coordinate base and translation required')
    if isinstance(angle,list) or isinstance(angle,np.ndarray):
        rotation=np.asarray(angle,dtype=float)
        if rotation.shape!=(3,3) or not np.isfinite(rotation).all() or not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-10,rtol=0) or not math.isclose(np.linalg.det(rotation),1,abs_tol=1e-10,rel_tol=0):
            raise ProjectError('proper rigid rotation matrix required')
    else:
        if type(angle) not in (int,float) or not math.isfinite(angle):
            raise ProjectError('finite Z rotation required')
        a=math.radians(angle)
        rotation=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1.]])
    return np.array(translation)+rotation@base, rotation


def read_dxf(path, units):
    doc=ezdxf.readfile(path);audit=doc.audit()
    if audit.errors or audit.fixes or doc.units!=units:
        raise ProjectError('clean native DXF with declared units required')
    return doc


def native(exe, copy, script, body):
    guard=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {q(copy)}))'
    setup='(setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "OSMODE" 0) (setvar "ATTREQ" 0) (setvar "LUPREC" 8) (setvar "LUNITS" 2) (command "_.UCS" "_World") '
    script.write_text(f'(if {guard} (progn {setup}{body}) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n',encoding='ascii')
    execute(exe,copy,script,script.with_suffix('.log'),120)


def run(fixed, moving, basis_path, out, exe=DEFAULT_EXE):
    fixed,moving,basis_path,out,exe=[Path(p).resolve() for p in (fixed,moving,basis_path,out,exe)]
    b=json.loads(basis_path.read_text(encoding='utf-8-sig'))
    required={'source','fixed_sha256','moving_sha256','insunits','translation_drawing_units'}
    if not isinstance(b,dict) or set(b) not in (required|{'rotation_z_degrees'},required|{'rotation'}) or not isinstance(b['source'],str) or not b['source'].strip():
        raise ProjectError('exact sourced joint basis required')
    if type(b['insunits']) is not int or b['insunits'] not in METRES_PER_UNIT:
        raise ProjectError('declared supported units required')
    orientation=b['rotation'] if 'rotation' in b else b['rotation_z_degrees']
    insertion([0,0,0],b['translation_drawing_units'],orientation)
    hashes={str(p):digest(p) for p in (fixed,moving,basis_path)}
    if hashes[str(fixed)]!=b['fixed_sha256'] or hashes[str(moving)]!=b['moving_sha256']:
        raise ProjectError('source DWG hash mismatch')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents for p in (fixed,moving,basis_path)):
        raise ProjectError('new repository output separate from inputs required')
    out.mkdir(parents=True)
    docs=[read_dxf(export_dwg(p,out/name,exe),b['insunits']) for p,name in ((fixed,'fixed-intake'),(moving,'moving-intake'))]
    for doc in docs:
        if len(list(doc.modelspace().query('3DSOLID')))!=1 or list(doc.modelspace().query('INSERT')):
            raise ProjectError('each input must contain one model-space solid and no block references')
    point,rotation=insertion(list(docs[1].header.get('$INSBASE',(0,0,0))),b['translation_drawing_units'],orientation)
    # A unique copied name prevents existing block definitions from replacing the import.
    imported=out/'BSA_NATIVE_JOINT_IMPORT.dwg'
    if imported.stem in docs[0].blocks:raise ProjectError('reserved import block already exists')
    shutil.copyfile(moving,imported);copy=out/'fixed-copy.dwg';shutil.copyfile(fixed,copy)
    handle=list(docs[1].modelspace().query('3DSOLID'))[0].dxf.handle
    native(exe,imported,out/'source-mass.scr',f'(command "_.MASSPROP" (handent {q(handle)}) "" "_Y" {q(out/"source.mpr")})')
    coord=lambda values:q(','.join(format(float(x),'.17g') for x in values))
    body=f'(command "_.UCS" "_3point" "0,0,0" {coord(rotation[:,0])} {coord(rotation[:,1])}) '
    # Specify uniform scale and angle before the point: source blocks differ in
    # whether post-point prompts ask for one scale or separate X/Y scales.
    body+=f'(command "_.-INSERT" {q(imported)} "_Scale" "1" "_Rotate" "0" {coord(rotation.T@point)}) (setq block (entlast)) (command "_.UCS" "_World") '
    body+=f'(command "_.DXFOUT" {q(out/"inserted.dxf")} "16") (command "_.EXPLODE" block "") '
    body+='(setq ss (ssget "_X" (list (cons 0 "3DSOLID") (cons 410 "Model")))) '
    fixed_handle=list(docs[0].modelspace().query('3DSOLID'))[0].dxf.handle
    body+=f'(if (= (sslength ss) 2) (progn (setq other (ssname ss 0)) (if (= other (handent {q(fixed_handle)})) (setq other (ssname ss 1))) '
    body+=f'(command "_.MASSPROP" other "" "_Y" {q(out/"moved.mpr")}) (command "_.DXFOUT" {q(out/"before.dxf")} "16") '
    body+=f'(command "_.INTERSECT" ss "") (command "_.DXFOUT" {q(out/"intersection.dxf")} "16") '
    body+='(setq result (ssget "_X" (list (cons 0 "3DSOLID") (cons 410 "Model")))) '
    body+=f'(if result (command "_.MASSPROP" result "" "_Y" {q(out/"intersection.mpr")}))))'
    native(exe,copy,out/'joint.scr',body)
    inserted=read_dxf(out/'inserted.dxf',b['insunits']);refs=list(inserted.modelspace().query('INSERT'))
    if len(refs)!=1:raise ProjectError('one inserted block required')
    ref=refs[0]
    matrix=ref.matrix44()
    actual_origin=np.array(matrix.transform((0,0,0)))
    actual_rotation=np.column_stack([np.array(matrix.transform(v))-actual_origin for v in np.eye(3)])
    if not np.allclose(actual_origin,point,atol=1e-9,rtol=0) or not np.allclose(actual_rotation,rotation,atol=1e-9,rtol=0):
        raise ProjectError('native insertion transform mismatch')
    source=mass_properties((out/'source.mpr').read_text());moved=mass_properties((out/'moved.mpr').read_text())
    if not math.isclose(source['volume'],moved['volume'],rel_tol=1e-7,abs_tol=1e-7) or not np.allclose(moved['centroid'],rotation@source['centroid']+b['translation_drawing_units'],atol=1e-7,rtol=0):
        raise ProjectError('native moved body volume/centroid mismatch')
    counts=[len(list(read_dxf(out/name,b['insunits']).modelspace().query('3DSOLID'))) for name in ('before.dxf','intersection.dxf')]
    if counts[0]!=2 or counts[1] not in (0,1):raise ProjectError('unexpected Boolean solid counts')
    if any(digest(Path(p))!=h for p,h in hashes.items()) or digest(copy)!=hashes[str(fixed)] or digest(imported)!=hashes[str(moving)]:
        raise ProjectError('source or isolated copy changed')
    result={'inputs':hashes,'basis':b,'insertion_point_drawing_units':point.tolist(),'solid_counts_before_after':counts,
            'native_clear':counts[1]==0,'intersection_volume_m3':mass_properties((out/'intersection.mpr').read_text())['volume']*METRES_PER_UNIT[b['insunits']]**3 if counts[1] else None,
            'native_transform_and_mass_checks_pass':True,'design_accepted':False,
            'scope':'Two native solids, explicit rigid placement; kernel tolerance applies. No IFC equivalence, mesh waiver or installation acceptance.',
            'artifacts':{p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}}
    (out/'joint.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('fixed');p.add_argument('moving');p.add_argument('basis');p.add_argument('--out',required=True);p.add_argument('--autocad',default=str(DEFAULT_EXE))
    a=p.parse_args();r=run(a.fixed,a.moving,a.basis,a.out,a.autocad)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['native_clear'] else 2)
