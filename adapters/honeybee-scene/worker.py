# SPDX-License-Identifier: AGPL-3.0-only
"""Local Honeybee scene conversion; never launches Radiance or claims annual metrics."""
import json
from importlib import metadata
from pathlib import Path
import sys
import math
import honeybee_radiance
from honeybee.model import Model
from honeybee.room import Room
from honeybee.aperture import Aperture
from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D
from honeybee_radiance.modifier.material.plastic import Plastic
from honeybee_radiance.modifier.material.glass import Glass
from honeybee_radiance.writer import model_to_rad


def run(packet,out):
    packet,out=Path(packet),Path(out);p=json.loads(packet.read_text(encoding='utf-8'))
    pins=json.loads((Path(__file__).parent/'dependencies.json').read_text(encoding='utf-8'))
    versions={r['name']:metadata.version(r['name']) for r in pins}
    if any(versions[r['name']]!=r['version'] for r in pins):raise ValueError('Honeybee dependency versions differ from pins')
    s=p['settings'];rooms=[]
    for row in p['spaces']:
        w,d,h=row['size_m'];room=Room.from_box(row['id'],w,d,h,origin=Point3D(*row['origin_m']))
        room.user_data=dict(source=row['source'],ifc_sha256=p['ifc_sha256'])
        rooms.append(room)
    Room.solve_adjacency(rooms,tolerance=.000001)
    known={r.identifier:r for r in rooms}
    mods={role:Plastic.from_single_reflectance('BSA_'+role,value) for role,value in s['reflectance'].items()}
    glass=Glass.from_single_transmittance('BSA_course_baseline_glazing',s['visible_transmittance'])
    for room in rooms:
        for face in room.faces:
            role='floor' if str(face.type)=='Floor' else 'ceiling' if str(face.type)=='RoofCeiling' else 'wall'
            face.properties.radiance.modifier=mods[role]
    for w in p['windows']:
        room=known[w['zone']];axis=0 if w['face'].startswith('X') else 1;sign=1 if w['face'].endswith('+') else -1
        matches=[f for f in room.faces if str(f.type)=='Wall' and math.isclose(f.normal[axis],sign,abs_tol=1e-8)]
        if len(matches)!=1:raise ValueError('exact native-derived Honeybee wall required')
        ap=Aperture(w['id'],Face3D(tuple(Point3D(*v) for v in w['vertices_m'])))
        ap.properties.radiance.modifier=glass;ap.user_data=dict(source=w['source']);matches[0].add_aperture(ap)
    model=Model('BSA_concept_scene',rooms=rooms,units='Meters',tolerance=.000001)
    for room in rooms:
        grid=room.properties.radiance.generate_sensor_grid(s['grid_spacing_m'],offset=s['sensor_height_m'],remove_out=True)
        if grid is None:raise ValueError('sensor generation failed')
        model.properties.radiance.add_sensor_grid(grid)
    errors=model.check_all(raise_exception=False,all_ext_checks=True)
    if errors:raise ValueError('Honeybee scene validation failed: '+str(errors))
    out.mkdir(parents=True,exist_ok=False)
    file=out/'model.hbjson';file.write_text(json.dumps(model.to_dict(),indent=2),encoding='utf-8')
    saved=Model.from_dict(json.loads(file.read_text(encoding='utf-8')))
    if saved.check_all(raise_exception=False,all_ext_checks=True):raise ValueError('saved Honeybee model validation failed')
    expected_rooms={r['id']:r for r in p['spaces']}
    expected_windows={w['id']:w for w in p['windows']}
    seen_windows=set();adjacent_faces=0
    for room in saved.rooms:
        row=expected_rooms[room.identifier]
        if not math.isclose(room.volume,math.prod(row['size_m']),abs_tol=1e-6) or not math.isclose(room.floor_area,row['size_m'][0]*row['size_m'][1],abs_tol=1e-6):raise ValueError('saved room area/volume differs')
        for face in room.faces:
            if str(face.boundary_condition)=='Surface':adjacent_faces+=1
            role='floor' if str(face.type)=='Floor' else 'ceiling' if str(face.type)=='RoofCeiling' else 'wall'
            if not math.isclose(face.properties.radiance.modifier.average_reflectance,s['reflectance'][role],abs_tol=1e-8):raise ValueError('saved opaque optical property differs')
            for ap in face.apertures:
                w=expected_windows[ap.identifier];seen_windows.add(ap.identifier)
                actual=sorted(tuple(round(v,7) for v in point) for point in ap.geometry.vertices)
                expected=sorted(tuple(round(v,7) for v in point) for point in w['vertices_m'])
                if w['zone']!=room.identifier or actual!=expected or not math.isclose(ap.properties.radiance.modifier.average_transmissivity,Glass.transmissivity_from_transmittance(s['visible_transmittance']),abs_tol=1e-10):raise ValueError('saved aperture identity/vertices/optical property differs')
    if seen_windows!=set(expected_windows) or adjacent_faces!=2*len(p['adjacency']):raise ValueError('saved aperture/adjacency coverage differs')
    source={r['id']:r for r in p['spaces']};audits=[]
    for grid in saved.properties.radiance.sensor_grids:
        row=source[grid.room_identifier];lo=row['origin_m'];size=row['size_m']
        expected=round(size[0]/s['grid_spacing_m'])*round(size[1]/s['grid_spacing_m'])
        # This adapter only accepts integer-cell rectangular grids; no guessed edge rules.
        if any(not math.isclose(v/s['grid_spacing_m'],round(v/s['grid_spacing_m']),abs_tol=1e-8) for v in size[:2]) or len(grid.sensors)!=expected:raise ValueError('saved sensor coverage differs from source grid')
        for sensor in grid.sensors:
            if any(not math.isclose(v,e,abs_tol=1e-8) for v,e in zip(sensor.dir,(0,0,1))) or not math.isclose(sensor.pos[2],lo[2]+s['sensor_height_m'],abs_tol=1e-8) or not all(lo[k]<sensor.pos[k]<lo[k]+size[k] for k in (0,1)):raise ValueError('saved sensor location/direction differs')
        positions={tuple(round(v,7) for v in sensor.pos) for sensor in grid.sensors}
        expected_positions={(round(lo[0]+(i+.5)*s['grid_spacing_m'],7),round(lo[1]+(j+.5)*s['grid_spacing_m'],7),round(lo[2]+s['sensor_height_m'],7)) for i in range(round(size[0]/s['grid_spacing_m'])) for j in range(round(size[1]/s['grid_spacing_m']))}
        if positions!=expected_positions:raise ValueError('saved exact grid positions differ')
        grid.to_file(str(out/'grids'),mkdir=True)
        audits.append(dict(room=grid.room_identifier,count=len(grid.sensors),height_m=s['sensor_height_m'],spacing_m=s['grid_spacing_m'],upward=True))
    aperture_area=sum(a.area for r in saved.rooms for f in r.faces for a in f.apertures)
    if not math.isclose(aperture_area,p['window_area_m2'],abs_tol=1e-6):raise ValueError('saved aperture area differs')
    rad,materials=model_to_rad(saved)
    (out/'scene.rad').write_text(rad,encoding='utf-8');(out/'materials.rad').write_text(materials,encoding='utf-8')
    # Independently read the exported primitive records and verify punched areas.
    tokens=' '.join(line.split('#',1)[0] for line in rad.splitlines()).split();index=0;primitives={}
    faces={f.identifier:f for room in saved.rooms for f in room.faces}
    while index<len(tokens):
        modifier,kind,name=tokens[index:index+3];index+=3;arguments=[]
        for group in range(3):
            count=int(tokens[index]);index+=1;arguments.append(tokens[index:index+count]);index+=count
        if kind!='polygon' or name in primitives or modifier not in {'BSA_floor','BSA_ceiling','BSA_wall','BSA_course_baseline_glazing'}:raise ValueError('unexpected exported scene primitive/material')
        coords=list(map(float,arguments[2]));points=[coords[i:i+3] for i in range(0,len(coords),3)]
        origin=points[0];local=[[v[k]-origin[k] for k in range(3)] for v in points];cross=[0.,0.,0.]
        for a,b in zip(local,local[1:]+local[:1]):
            for k in range(3):cross[k]+=a[(k+1)%3]*b[(k+2)%3]-a[(k+2)%3]*b[(k+1)%3]
        area=math.sqrt(sum(v*v for v in cross))/2
        if name in expected_windows:
            w=expected_windows[name];expected=w['width_m']*w['height_m']
            if modifier!='BSA_course_baseline_glazing' or sorted(tuple(round(v,7) for v in p) for p in points)!=sorted(tuple(round(v,7) for v in p) for p in w['vertices_m']):raise ValueError('exported aperture vertices differ')
        else:
            face=faces[name];expected=face.area-sum(a.area for a in face.apertures)
        if not math.isclose(area,expected,abs_tol=1e-6):raise ValueError('exported punched polygon area differs')
        primitives[name]=area
    if len(primitives)!=6*len(saved.rooms)+len(expected_windows) or not set(expected_windows)<=set(primitives):raise ValueError('exported polygon coverage differs')
    report=dict(exported_adjacent_face_offset_m=2*saved.tolerance,rad_polygon_count=len(primitives),exported_punched_area_checks_pass=True,runtime=versions,optical_conversion=dict(source_visible_transmittance=s['visible_transmittance'],saved_glass_transmissivity=glass.average_transmissivity,upstream_approximate_inverse_transmittance=glass.average_transmittance,verification='Exact forward Honeybee conversion; upstream inverse uses a 0.01 secant tolerance and is diagnostic only'),rooms=len(saved.rooms),apertures=sum(len(f.apertures) for r in saved.rooms for f in r.faces),aperture_area_m2=aperture_area,sensors=audits,sensor_count=sum(r['count'] for r in audits),geometry_checks_pass=True,simulation_executed=False,solver_ready=False,design_accepted=False,pending=['actual site/weather/neighbor shading and ground','wall/frame/reveal detail and clear air-volume interpretation','exterior optical assumptions and scene completeness','Radiance runtime and actual annual sDA/ASE/view glare verification'])
    (out/'scene.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':print(json.dumps(run(sys.argv[1],sys.argv[2])))
