"""Bind the same electrical/CAD/IFC device positions to IES-backed Radiance."""
import argparse
import copy
import json
import math
from pathlib import Path
import shutil
from .cli import digest
from .engine import ProjectError


def prepare(electrical,geometry,optical,root):
    from .coordination import compile_model
    from .lighting import validate,ies_metadata
    root=Path(root).resolve()
    compile_model(electrical,geometry)
    if not isinstance(optical,dict) or optical.get('coordinate_reference')!='world; offsets from electrical XY centre and envelope bottom Z':
        raise ProjectError('explicit common world coordinate/photometric offset reference required')
    if set(optical)!={'coordinate_reference','sources','space','reflectances','photometry','sensors','targets','simulation','power_check'}:
        raise ProjectError('unsupported or missing optical binding fields')
    sources=optical['sources']
    if not isinstance(sources,dict) or not sources or any(not isinstance(v,str) or not v.strip() for v in sources.values()):raise ProjectError('optical source descriptions required')
    def sourced(row):
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or row['source'] not in sources:raise ProjectError('known optical source required')
    spaces={s['id']:s for s in geometry['spaces']}
    if not isinstance(optical['space'],str) or optical['space'] not in spaces:raise ProjectError('selected optical space must exist in shared geometry')
    space=spaces[optical['space']];origin=space['origin_m']
    envelope={d['id']:d for d in geometry['devices'] if d['space']==optical['space'] and d['ifc_class']=='IfcLightFixture'}
    if not envelope:raise ProjectError('selected space contains no explicit light fixtures')
    electrical_devices={d['id']:d for d in electrical['devices']}
    photometry=optical['photometry']
    if not isinstance(photometry,list):raise ProjectError('photometry assignments required')
    assigned={}
    for row in photometry:
        sourced(row)
        if set(row)!={'id','ies','yaw_deg','maintenance_factor','origin_offset_m','source'}:raise ProjectError('photometry assignments cannot repeat positions or power')
        if not isinstance(row['id'],str) or row['id'] in assigned:raise ProjectError('unique photometry device IDs required')
        offset=row['origin_offset_m']
        if not isinstance(offset,list) or len(offset)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in offset):raise ProjectError('three finite world-axis photometric offsets required')
        assigned[row['id']]=row
    if set(assigned)!=set(envelope):raise ProjectError('photometry must cover exactly the shared light fixtures in the selected space')
    power=optical['power_check'];sourced(power)
    tolerance=power.get('absolute_tolerance_w')
    if set(power)!={'absolute_tolerance_w','source'} or type(tolerance) not in (int,float) or not math.isfinite(tolerance) or tolerance<0:
        raise ProjectError('explicit nonnegative nominal-power match tolerance required')
    reflect=optical['reflectances'];sourced(reflect)
    if set(reflect)!={'wall','floor','ceiling','source'}:raise ProjectError('explicit room reflectances required')
    merged={f'optical/{k}':v for k,v in sources.items()}
    merged['shared-room']=geometry['sources'][space['source']]+'; reflectance: '+sources[reflect['source']]
    project=dict(name=electrical['name']+' - bound optical model',sources=merged,
        room=dict(size_m=space['size_m'],wall_reflectance=reflect['wall'],floor_reflectance=reflect['floor'],ceiling_reflectance=reflect['ceiling'],source='shared-room'),
        luminaires=[],sensors=[],targets=copy.deepcopy(optical['targets']),simulation=copy.deepcopy(optical['simulation']))
    for key in ('targets','simulation'):
        sourced(project[key]);project[key]['source']='optical/'+project[key]['source']
    bindings=[]
    for id,row in assigned.items():
        d=electrical_devices[id];e=envelope[id];offset=row['origin_offset_m']
        world=[d['x_m']+offset[0],d['y_m']+offset[1],e['z_m']+offset[2]]
        project['luminaires'].append(dict(id=id,position_m=[v-o for v,o in zip(world,origin)],ies=row['ies'],
            yaw_deg=row['yaw_deg'],maintenance_factor=row['maintenance_factor'],source='optical/'+row['source']))
        bindings.append(dict(id=id,circuit=d['circuit'],electrical_kw=d['electrical_kw'],photometric_origin_world_m=world,
            offset_world_m=offset,envelope_z_m=e['z_m']))
    if not isinstance(optical['sensors'],list):raise ProjectError('world sensor positions required')
    for s in optical['sensors']:
        sourced(s)
        if set(s)!={'id','position_m','source'}:raise ProjectError('explicit world sensor positions only')
        xyz=s['position_m']
        if not isinstance(xyz,list) or len(xyz)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz):raise ProjectError('finite world sensor coordinates required')
        project['sensors'].append(dict(id=s['id'],position_m=[v-o for v,o in zip(xyz,origin)],source='optical/'+s['source']))
    paths=validate(project,root)
    for binding in bindings:
        row=assigned[binding['id']];meta=ies_metadata((root/row['ies']).resolve())
        watts=electrical_devices[binding['id']]['electrical_kw']*1000
        if abs(meta['input_watts']-watts)>tolerance:raise ProjectError('IES nominal input watts differ from shared electrical input for '+binding['id'])
        binding.update(ies_sha256=meta['sha256'],ies_input_watts=meta['input_watts'],power_tolerance_w=tolerance)
    return project,paths,bindings,origin


def run(project,geometry_path,optical_path,out,radiance_bin):
    from .coordination import run as coordinate
    from .lighting import run as simulate
    project,geometry_path,optical_path,out=(p.resolve() for p in (project,geometry_path,optical_path,out))
    electrical=json.loads(project.read_text(encoding='utf-8-sig'));geometry=json.loads(geometry_path.read_text(encoding='utf-8-sig'))
    derived,ies_paths,bindings,origin=prepare(electrical,geometry,json.loads(optical_path.read_text(encoding='utf-8-sig')),optical_path.parent)
    inputs={project,geometry_path,optical_path}|ies_paths
    if any(out==p or out in p.parents for p in inputs):raise ProjectError('output must not contain any source')
    before={str(p):digest(p) for p in inputs}
    out.mkdir(parents=True,exist_ok=False)
    common=coordinate(project,geometry_path,out/'shared')
    photo_dir=out/'photometry';photo_dir.mkdir()
    for i,f in enumerate(derived['luminaires']):
        src=(optical_path.parent/f['ies']).resolve();dest=photo_dir/f'fixture-{i:04}.ies'
        shutil.copyfile(src,dest)
        if digest(dest)!=digest(src):raise ProjectError('photometry copy differs from source')
        f['ies']=dest.relative_to(out).as_posix()
    path=out/'lighting-input.json';path.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    light=simulate(path,out/'lighting',radiance_bin)
    for binding,fixture in zip(bindings,derived['luminaires']):
        world=[v+o for v,o in zip(fixture['position_m'],origin)]
        if any(abs(a-b)>1e-8 for a,b in zip(world,binding['photometric_origin_world_m'])):raise ProjectError('bound lighting coordinate transform mismatch')
    unchanged=all(digest(Path(p))==sha for p,sha in before.items())
    result=dict(inputs=before,inputs_unchanged=unchanged,bindings=bindings,room_origin_world_m=origin,
        common_coordination_checks_pass=common['coordination_checks_pass'],lighting_checks_pass=light['calculated_checks_pass'],
        calculated_checks_pass=unchanged and common['calculated_checks_pass'] and light['calculated_checks_pass'],design_accepted=False,
        scope='Shared electrical/CAD/IFC light IDs and positions with explicit photometric origin offsets, IES power metadata checks and local-room Radiance transform',
        pending=['physical photometric reference and manufacturer data review','actual obstructions and room fidelity','full photometric/electrical/code acceptance'])
    result['artifacts']={f.relative_to(out).as_posix():digest(f) for f in out.rglob('*') if f.is_file()}
    (out/'lighting-binding.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not unchanged:raise ProjectError('bound source inputs changed')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--geometry',type=Path,required=True)
    p.add_argument('--optical',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--radiance-bin',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.geometry,a.optical,a.out,a.radiance_bin)
    print(json.dumps({k:r[k] for k in ('common_coordination_checks_pass','lighting_checks_pass','calculated_checks_pass','design_accepted')}))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
