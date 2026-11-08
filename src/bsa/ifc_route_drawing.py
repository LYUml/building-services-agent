"""Source-checked planar circular routes, including finite elbows, to editable DXF."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import uuid

from .cli import digest
from .engine import ProjectError
from . import circular_geometry as circular
from . import circular_elbow as elbow
from .ifc_drawing import validate_settings


def extract(ifc, source_model, settings):
    import numpy as np
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    import ifcopenshell.util.unit as unit
    from .bim import validate
    validate(source_model)
    validate_settings(settings)
    model = ifcopenshell.open(str(ifc))
    projects = model.by_type('IfcProject')
    if len(projects) != 1 or not projects[0].UnitsInContext:
        raise ProjectError('one route project with explicit metre units required')
    units = [u for u in projects[0].UnitsInContext.Units if getattr(u, 'UnitType', None) == 'LENGTHUNIT']
    if len(units) != 1 or not units[0].is_a('IfcSIUnit') or units[0].Name != 'METRE' or units[0].Prefix is not None or unit.calculate_unit_scale(model) != 1:
        raise ProjectError('source-checked route drawing currently requires explicit SI metres')
    roots = [r.GlobalId for r in model.by_type('IfcRoot')]
    if len(roots) != len(set(roots)):
        raise ProjectError('duplicate route IFC identity')
    physical = [o for o in model.by_type('IfcElement') if not o.is_a('IfcFeatureElement') and not o.is_a('IfcVirtualElement')]
    source = {d['id']: d for d in source_model['devices']}
    objects = {o.Name: o for o in physical}
    if len(objects) != len(physical) or set(objects) != set(source) or not objects:
        raise ProjectError('exact complete source/physical route element coverage required')
    namespace = uuid.UUID(source_model['project_uuid']) if source_model.get('project_uuid') else None
    def stable(cls, *keys):
        return ifcopenshell.guid.compress(uuid.uuid5(namespace, json.dumps([cls,*keys], ensure_ascii=False, separators=(',',':'))).hex)
    axes = [{'X':0,'Y':1,'Z':2}[a] for a in settings['projection_axes']]
    omitted_axis = next(i for i in range(3) if i not in axes)
    geom_settings = ifcopenshell.geom.settings()
    geom_settings.set(geom_settings.USE_WORLD_COORDS, True)
    circular.configure(geom_settings)
    rows = []
    for name, d in source.items():
        obj = objects[name]
        module = elbow if d.get('body_shape') == elbow.WALL else circular
        if d.get('body_shape') not in (elbow.WALL, circular.WALL) or obj.is_a() != d['ifc_class']:
            raise ProjectError('route drawing requires explicit supported straight or elbow walls')
        if namespace and obj.GlobalId != stable(d['ifc_class'], name):
            raise ProjectError('saved route object GUID differs from source namespace')
        props = element.get_psets(obj).get('BSA_DesignInputs', {})
        if props.get('InputID') != name or props.get('BodyShape') != d['body_shape'] or props.get('Source') != source_model['sources'][d['source']]:
            raise ProjectError('saved route identity/body/provenance differs from source')
        container = element.get_container(obj)
        if container is None or container.Name != d['space'] or {s.Name for s in system.get_element_systems(obj)} != {d['system']}:
            raise ProjectError('saved route space/system membership differs from source')
        spec = module.specification(d)
        shape = ifcopenshell.geom.create_shape(geom_settings, obj)
        vertices = np.asarray(shape.geometry.verts).reshape(-1,3)
        expected_bounds = np.asarray([d['origin_m'],np.asarray(d['origin_m'])+d['size_m']])
        if not len(vertices) or not np.isfinite(vertices).all() or not np.allclose([vertices.min(axis=0),vertices.max(axis=0)],expected_bounds,atol=circular.BOUNDS_TOLERANCE_M,rtol=0):
            raise ProjectError('saved route wall world bounds differ from source; ports alone do not prove body position')
        checks = module.verify(obj, d, shape)
        native_ports = system.get_ports(obj)
        ports = {p.Name:p for p in native_ports}
        if len(native_ports) != 2 or len(ports) != 2 or set(ports) != {p['id'] for p in d['ports']}:
            raise ProjectError('exact route port identities required')
        points = []
        for p in d['ports']:
            saved = ports[p['id']]
            if not saved.ObjectPlacement:
                raise ProjectError('saved route port placement required')
            matrix = placement.get_local_placement(saved.ObjectPlacement)
            if saved.FlowDirection != p['direction'] or not np.allclose(matrix[:3,3], np.asarray(d['origin_m'])+p['offset_m'], atol=1e-8, rtol=0) or not np.allclose(matrix[:3,2], spec['normals'][p['id']], atol=1e-8, rtol=0):
                raise ProjectError('saved route port direction/position/tangent differs from source')
            if namespace and saved.GlobalId != stable('IfcDistributionPort', name, p['id']):
                raise ProjectError('saved route port GUID differs from source namespace')
            if element.get_psets(saved).get('BSA_DesignInputs', {}).get('Source') != source_model['sources'][p['source']]:
                raise ProjectError('saved route port provenance differs from source')
            points.append(matrix[:3,3].tolist())
        row = dict(guid=obj.GlobalId, name=name, ifc_class=obj.is_a(), body_shape=d['body_shape'],
                   source=source_model['sources'][d['source']], inner_diameter_m=spec['inner_m'], outside_diameter_m=spec['outer_m'],
                   length_m=spec['length_m'], analytic_wall_volume_m3=spec['volume_m3'],
                   start_world_m=points[0], end_world_m=points[1], port_guids=[ports[p['id']].GlobalId for p in d['ports']],
                   native_wall_checks=checks, centreline_radius_m=None)
        if module is elbow:
            saved_length, ends, radius = elbow.saved_arc_length(obj)
            if not math.isclose(saved_length, spec['length_m'], abs_tol=1e-9):
                raise ProjectError('saved arc length differs from source')
            centre = spec['centre_m']
            if abs(spec['normal'][omitted_axis]) != 1:
                raise ProjectError('elbow plane must be parallel to selected drawing plane; oblique/end-on arc unsupported')
            row.update(centre_world_m=centre, centreline_radius_m=radius)
            a, b = [[p[i] for i in axes] for p in ends]
            c = [centre[i] for i in axes]
            angle = lambda p: math.degrees(math.atan2(p[1]-c[1],p[0]-c[0])) % 360
            start, end = angle(a), angle(b)
            if not math.isclose((end-start)%360, 90, abs_tol=1e-7):
                start, end = end, start
            if not math.isclose((end-start)%360, 90, abs_tol=1e-7):
                raise ProjectError('projected arc must preserve exact 90-degree circle')
            row.update(projected_centre_m=c, start_angle_deg=start, end_angle_deg=end, projected_length_m=saved_length)
        else:
            if abs(points[0][omitted_axis]-points[1][omitted_axis]) > 1e-8:
                raise ProjectError('route line must lie parallel to drawing plane')
            row['projected_length_m'] = math.dist(*[[p[i] for i in axes] for p in points])
        row['plane_coordinate_m'] = points[0][omitted_axis]
        rows.append(row)
    if max(r['plane_coordinate_m'] for r in rows)-min(r['plane_coordinate_m'] for r in rows) > 1e-8:
        raise ProjectError('one coplanar route required; separated levels must not overlap invisibly')
    return rows


def draw(rows, settings, out):
    import ezdxf
    from .cad_overlay import snapshot, reconcile
    axes = [{'X':0,'Y':1,'Z':2}[a] for a in settings['projection_axes']]
    height = settings['annotation_height_m']
    doc = ezdxf.new('R2018'); doc.header['$INSUNITS'] = 6
    doc.appids.new('BSA_IFC')
    for name, color in (('BSA_PIPE_AXIS',4),('BSA_PIPE_OUTLINE',7),('BSA_LABEL',7),('BSA_LEADER',8)):
        doc.layers.new(name, dxfattribs={'color':color})
    ms = doc.modelspace(); projected = []; svg = []
    for row in rows:
        a,b = [[p[i] for i in axes] for p in (row['start_world_m'],row['end_world_m'])]
        projected.extend([a,b])
    label_x = max(p[0] for p in projected)+4*height
    def add(entity, row):
        entity.set_xdata('BSA_IFC', [(1000,row['guid'])])
        return entity
    def line(a,b,layer,row):
        add(ms.add_line(a,b,dxfattribs={'layer':layer}),row)
        svg.append(f'<line x1="{a[0]}" y1="{-a[1]}" x2="{b[0]}" y2="{-b[1]}" stroke="black" stroke-width="{height/12}"/>')
    label_y = -math.inf
    for row in sorted(rows, key=lambda r:sum(p[axes[1]] for p in (r['start_world_m'],r['end_world_m']))/2):
        a,b = [[p[i] for i in axes] for p in (row['start_world_m'],row['end_world_m'])]
        if row['centreline_radius_m'] is None:
            line(a,b,'BSA_PIPE_AXIS',row)
            length = math.dist(a,b);normal = [-(b[1]-a[1])/length,(b[0]-a[0])/length]
            for sign in (-1,1):
                offset = [sign*row['outside_diameter_m']/2*n for n in normal]
                line([x+y for x,y in zip(a,offset)],[x+y for x,y in zip(b,offset)],'BSA_PIPE_OUTLINE',row)
            middle = [(x+y)/2 for x,y in zip(a,b)];detail = ''
            if normal[0] < -1e-9 or abs(normal[0]) < 1e-9 and normal[1] < 0:
                normal = [-n for n in normal]
        else:
            c = row['projected_centre_m'];radius = row['centreline_radius_m']
            start,end = row['start_angle_deg'],row['end_angle_deg']
            theta = math.radians(start+45)
            middle = [c[0]+radius*math.cos(theta),c[1]+radius*math.sin(theta)]
            for r, layer in ((radius,'BSA_PIPE_AXIS'),(radius-row['outside_diameter_m']/2,'BSA_PIPE_OUTLINE'),(radius+row['outside_diameter_m']/2,'BSA_PIPE_OUTLINE')):
                add(ms.add_arc(c,r,start,end,dxfattribs={'layer':layer}),row)
                p,q = [[c[0]+r*math.cos(math.radians(t)),c[1]+r*math.sin(math.radians(t))] for t in (start,end)]
                svg.append(f'<path d="M {p[0]} {-p[1]} A {r} {r} 0 0 0 {q[0]} {-q[1]}" fill="none" stroke="black" stroke-width="{height/12}"/>')
            detail = f"; R {radius*1000:g} mm; 90 deg"
            normal = [math.cos(theta),math.sin(theta)]
        anchor = [middle[i]+row['outside_diameter_m']/2*normal[i] for i in (0,1)]
        exit_point = [anchor[i]+height*normal[i] for i in (0,1)]
        label_y = max(exit_point[1],label_y+2.2*height)
        label = f"{row['name']} ID {row['inner_diameter_m']*1000:g}/OD {row['outside_diameter_m']*1000:g} mm; L {row['length_m']:.6f} m"+detail
        line(anchor,exit_point,'BSA_LEADER',row)
        line(exit_point,[label_x-height,label_y],'BSA_LEADER',row)
        add(ms.add_text(label,dxfattribs={'height':height,'insert':(label_x,label_y),'layer':'BSA_LABEL'}),row)
        svg.append(f'<text x="{label_x}" y="{-label_y}" font-size="{height}">{html.escape(label)}</text>')
    titles = [' / '.join(settings['projection_axes'])+f" route plane {rows[0]['plane_coordinate_m']:g} m; coordinates m",
              'Axis and OD outlines; generic geometry; product/installation acceptance pending']
    for i,title in enumerate(titles):
        x = min(p[0] for p in projected);y = min(p[1] for p in projected)-(3+i*1.8)*height
        ms.add_text(title,dxfattribs={'height':height,'insert':(x,y),'layer':'BSA_LABEL'})
        svg.append(f'<text x="{x}" y="{-y}" font-size="{height}">{html.escape(title)}</text>')
    path = out/'segments.dxf';doc.saveas(path)
    reconcile(snapshot(doc),path)
    saved = ezdxf.readfile(path)
    if saved.header['$INSUNITS'] != 6 or len(saved.modelspace().query('*[layer=="BSA_PIPE_AXIS"]')) != len(rows):
        raise ProjectError('saved route units/axis entity coverage mismatch')
    from .ifc_native import identity
    if identity(doc) != identity(saved):
        raise ProjectError('saved route IFC identity mismatch')
    from ezdxf import bbox
    bounds = bbox.extents(saved.modelspace());margin = 2*height
    lo,hi = bounds.extmin,bounds.extmax
    (out/'preview.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" font-family="monospace" viewBox="{lo.x-margin} {-hi.y-margin} {hi.x-lo.x+2*margin} {hi.y-lo.y+2*margin}">'+''.join(svg)+'</svg>',encoding='utf-8')


def run(ifc, source_model, settings_path, out):
    paths = [Path(p).resolve() for p in (ifc,source_model,settings_path)];out = Path(out).resolve()
    if any(out == p or out in p.parents for p in paths):
        raise ProjectError('route output must not contain sources')
    before = {str(p):digest(p) for p in paths}
    data = json.loads(paths[1].read_text(encoding='utf-8-sig'))
    settings = validate_settings(json.loads(paths[2].read_text(encoding='utf-8-sig')))
    rows = extract(paths[0], data, settings)
    out.mkdir(parents=True,exist_ok=False);draw(rows,settings,out)
    with (out/'segments.csv').open('w',newline='',encoding='utf-8') as f:
        fields = ['guid','name','ifc_class','inner_diameter_m','outside_diameter_m','length_m','centreline_radius_m','analytic_wall_volume_m3','source']
        writer = csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    if any(digest(Path(p)) != h for p,h in before.items()):
        raise ProjectError('route drawing source changed')
    result = dict(inputs=before,inputs_unchanged=True,settings=settings,pieces=rows,piece_count=len(rows),
                  calculated_checks_pass=True,design_accepted=False,
                  scope='source-checked coplanar circular route axes, true arcs and OD outlines; no manufacturer detail',
                  pending=['native DWG reopen and actual PDF visual review','product/joint/insulation/support detail','complete installation and engineering acceptance'])
    result['artifacts'] = {p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('ifc',type=Path)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--settings',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a = p.parse_args();r = run(a.ifc,a.model,a.settings,a.out)
    print(json.dumps({'piece_count':r['piece_count'],'calculated_checks_pass':True,'design_accepted':False}))


if __name__ == '__main__':main()
