"""Saved straight hollow IFC segments to a traceable schedule and projected schematic."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError

AXES = {'X': 0, 'Y': 1, 'Z': 2}


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) != {'projection_axes', 'annotation_height_m', 'source'}:
        raise ProjectError('explicit projection axes, annotation height and source required')
    axes = settings['projection_axes']
    if not isinstance(axes, list) or len(axes) != 2 or any(not isinstance(a,str) or a not in AXES for a in axes) or axes[0] == axes[1]:
        raise ProjectError('two distinct X/Y/Z projection axes required')
    height = settings['annotation_height_m']
    if type(height) not in (int, float) or not math.isfinite(height) or not .001 <= height <= 1:
        raise ProjectError('annotation height must be 0.001 to 1 metre')
    if not isinstance(settings['source'], str) or not settings['source'].strip():
        raise ProjectError('drawing settings source required')
    return settings


def extract(path):
    import numpy as np
    import ifcopenshell
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    import ifcopenshell.util.unit as unit
    source_hash = digest(Path(path))
    model = ifcopenshell.open(str(path))
    projects = model.by_type('IfcProject')
    if len(projects) != 1 or not projects[0].UnitsInContext:
        raise ProjectError('one project with explicit length units required')
    units = [u for u in projects[0].UnitsInContext.Units if getattr(u, 'UnitType', None) == 'LENGTHUNIT']
    if len(units) != 1:
        raise ProjectError('one explicit length unit required')
    base = units[0]; seen = set()
    while base.is_a('IfcConversionBasedUnit'):
        if base.id() in seen:
            raise ProjectError('cyclic length unit')
        seen.add(base.id()); base = base.ConversionFactor.UnitComponent
    if not base.is_a('IfcSIUnit') or base.Name != 'METRE':
        raise ProjectError('length unit must resolve to SI metres')
    factor = unit.calculate_unit_scale(model)
    if not math.isfinite(factor) or factor <= 0:
        raise ProjectError('positive known length unit required')
    segments = model.by_type('IfcPipeSegment') + model.by_type('IfcDuctSegment')
    guids = [r.GlobalId for r in model.by_type('IfcRoot')]
    if len(set(guids)) != len(guids):
        raise ProjectError('duplicate IFC identity')
    rows = []; errors = []
    for obj in sorted(segments, key=lambda o:o.GlobalId):
        try:
            bodies = [r for r in obj.Representation.Representations if r.RepresentationIdentifier == 'Body'] if obj.Representation else []
            if len(bodies) != 1 or bodies[0].RepresentationType != 'SweptSolid' or len(bodies[0].Items) != 1:
                raise ProjectError('one direct swept Body required; envelopes/mapped/compound shapes unsupported')
            solid = bodies[0].Items[0]
            if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcCircleHollowProfileDef'):
                raise ProjectError('explicit circular hollow extrusion required')
            profile = solid.SweptArea
            outer = 2*profile.Radius*factor
            inner = 2*(profile.Radius-profile.WallThickness)*factor
            length = solid.Depth*factor
            if not all(math.isfinite(v) for v in (outer, inner, length)) or not 0 < inner < outer or length <= 0:
                raise ProjectError('positive straight hollow dimensions required')
            direction = np.asarray(solid.ExtrudedDirection.DirectionRatios, dtype=float)
            if not np.all(np.isfinite(direction)) or np.linalg.norm(direction) == 0:
                raise ProjectError('finite extrusion direction required')
            direction /= np.linalg.norm(direction)
            if abs(direction[0]) > 1e-9 or abs(direction[1]) > 1e-9 or direction[2] <= 0:
                raise ProjectError('normal positive profile extrusion required')
            if not obj.ObjectPlacement or not solid.Position:
                raise ProjectError('explicit product and solid placement required')
            matrix = placement.get_local_placement(obj.ObjectPlacement) @ placement.get_axis2placement(solid.Position)
            if not np.all(np.isfinite(matrix)) or not np.allclose(matrix[:3,:3].T @ matrix[:3,:3], np.eye(3), atol=1e-9):
                raise ProjectError('finite rigid placement required')
            local = [0., 0., 0., 1.]
            if profile.Position:
                local[:2] = profile.Position.Location.Coordinates
            a = (matrix @ np.asarray(local))[:3]*factor
            end = np.asarray(local); end[:3] += direction*solid.Depth
            b = (matrix @ end)[:3]*factor
            ports = system.get_ports(obj)
            sinks = [p for p in ports if p.FlowDirection == 'SINK']
            sources = [p for p in ports if p.FlowDirection == 'SOURCE']
            if len(ports) != 2 or len(sinks) != 1 or len(sources) != 1:
                raise ProjectError('one placed sink and source port required')
            points = []
            for port in (sinks[0], sources[0]):
                if not port.ObjectPlacement:
                    raise ProjectError('explicit port placement required')
                points.append(placement.get_local_placement(port.ObjectPlacement)[:3,3]*factor)
            if not (np.allclose(points[0], a, atol=1e-8, rtol=0) and np.allclose(points[1], b, atol=1e-8, rtol=0) or
                    np.allclose(points[1], a, atol=1e-8, rtol=0) and np.allclose(points[0], b, atol=1e-8, rtol=0)):
                raise ProjectError('saved ports do not match actual profile endpoints')
            props = element.get_psets(obj).get('BSA_DesignInputs', {})
            for key, value in (('InternalDiameter_m', inner), ('OutsideDiameter_m', outer)):
                if key not in props:
                    continue
                saved = props.get(key)
                if type(saved) not in (int,float) or not math.isclose(saved, value, abs_tol=1e-9, rel_tol=1e-9):
                    raise ProjectError('saved metre diameter metadata differs from actual profile')
            if 'Source' in props and (not isinstance(props['Source'], str) or not props['Source'].strip()):
                raise ProjectError('saved segment provenance required')
            rows.append(dict(guid=obj.GlobalId, name=obj.Name or '', ifc_class=obj.is_a(),
                             system_guids=[s.GlobalId for s in system.get_element_systems(obj)],
                             source=props.get('Source', 'Declared saved IFC profile/placement geometry; source SHA256 '+source_hash),
                             missing_diameter_metadata=[key for key in ('InternalDiameter_m','OutsideDiameter_m') if key not in props],
                             inner_diameter_m=inner, outside_diameter_m=outer,
                             length_m=length, start_world_m=points[0].tolist(), end_world_m=points[1].tolist(),
                             sink_port_guid=sinks[0].GlobalId, source_port_guid=sources[0].GlobalId,
                             analytic_wall_volume_m3=math.pi*(outer**2-inner**2)*length/4))
        except (ProjectError, ValueError, AttributeError, TypeError, RuntimeError) as exc:
            errors.append(dict(guid=obj.GlobalId, name=obj.Name, reason=str(exc)))
    excluded = [dict(guid=e.GlobalId, name=e.Name, ifc_class=e.is_a()) for e in model.by_type('IfcElement')
                if not e.is_a('IfcPipeSegment') and not e.is_a('IfcDuctSegment')]
    return dict(ifcopenshell_version=ifcopenshell.version, source_length_unit_to_m=factor,
                segment_count=len(segments), segments=rows, unsupported_segments=errors,
                excluded_non_segment_elements=excluded, calculated_checks_pass=bool(rows) and not errors)


def draw(rows, settings, out):
    import ezdxf
    axes = [AXES[a] for a in settings['projection_axes']]; height = settings['annotation_height_m']
    doc = ezdxf.new('R2018'); doc.header['$INSUNITS'] = 6
    doc.appids.new('BSA_IFC')
    for name, color in (('BSA_PIPE_AXIS',4), ('BSA_LABEL',7), ('BSA_LEADER',8)):
        doc.layers.new(name, dxfattribs={'color':color})
    ms = doc.modelspace(); projected = []
    for row in rows:
        a,b = [[point[i] for i in axes] for point in (row['start_world_m'], row['end_world_m'])]
        row['projected_length_m'] = math.dist(a,b)
        if row['projected_length_m'] <= 1e-9:
            raise ProjectError('end-on segment cannot be represented as a centreline in this projection')
        projected.append((row,a,b))
    label_x = max(p[0] for _,a,b in projected for p in (a,b)) + 4*height
    last_y = -math.inf; entities=[]; svg=[]; labels=[]
    for row,a,b in sorted(projected, key=lambda item:sum(p[1] for p in item[1:])/2):
        middle = [(a[i]+b[i])/2 for i in (0,1)]
        label_y = max(middle[1], last_y+2*height); last_y=label_y
        label = f"{row['name']} ID {row['inner_diameter_m']*1000:g} / OD {row['outside_diameter_m']*1000:g} mm; L {row['length_m']:g} m"
        labels.append((label_y,label))
        for entity in (ms.add_line(a,b,dxfattribs={'layer':'BSA_PIPE_AXIS'}),
                       ms.add_line(middle,[label_x-height,label_y],dxfattribs={'layer':'BSA_LEADER'}),
                       ms.add_text(label,dxfattribs={'height':height,'insert':(label_x,label_y),'layer':'BSA_LABEL'})):
            entity.set_xdata('BSA_IFC',[(1000,row['guid'])]);entities.append((entity.dxf.handle,row['guid']))
        svg.extend([f'<line x1="{a[0]}" y1="{-a[1]}" x2="{b[0]}" y2="{-b[1]}" stroke="black" stroke-width="{height/10}"/>',
                    f'<line x1="{middle[0]}" y1="{-middle[1]}" x2="{label_x-height}" y2="{-label_y}" stroke="gray" stroke-width="{height/20}"/>',
                    f'<text x="{label_x}" y="{-label_y}" font-size="{height}">{html.escape(label)}</text>'])
    points = [p for _,a,b in projected for p in (a,b)]
    xmin=min(p[0] for p in points)-3*height
    titles=[' / '.join(settings['projection_axes'])+' projected centrelines; coordinate unit m',
            'Labels show true length; NOT installation geometry']
    title_y=min(p[1] for p in points)-2*height
    for i,title in enumerate(titles):
        y=title_y-i*1.8*height
        ms.add_text(title,dxfattribs={'height':height,'insert':(xmin+height,y),'layer':'BSA_LABEL'})
        svg.append(f'<text x="{xmin+height}" y="{-y}" font-size="{height}">{html.escape(title)}</text>')
    ymin=min([-p[1] for p in points]+[-y for y,_ in labels])-2*height
    ymax=-title_y+3.8*height
    width=max(label_x+max(len(text) for _,text in labels)*height*.65,
              xmin+height+max(map(len,titles))*height*.65)-xmin+2*height
    doc.saveas(out/'segments.dxf')
    reopened=ezdxf.readfile(out/'segments.dxf')
    for handle,guid in entities:
        saved=reopened.entitydb[handle];original=doc.entitydb[handle]
        if saved.get_xdata('BSA_IFC')[0].value != guid:
            raise ProjectError('saved DXF identity mismatch')
        if saved.dxftype()=='LINE':
            if not saved.dxf.start.isclose(original.dxf.start,rel_tol=0,abs_tol=1e-9) or not saved.dxf.end.isclose(original.dxf.end,rel_tol=0,abs_tol=1e-9):
                raise ProjectError('saved DXF endpoints mismatch')
        elif saved.dxf.text!=original.dxf.text or not saved.dxf.insert.isclose(original.dxf.insert,rel_tol=0,abs_tol=1e-9):
            raise ProjectError('saved DXF annotation mismatch')
    if len(reopened.modelspace().query('LINE[layer=="BSA_PIPE_AXIS"]')) != len(rows):
        raise ProjectError('saved DXF segment count mismatch')
    (out/'preview.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" font-family="monospace" viewBox="{xmin} {ymin} {width} {ymax-ymin}">'+''.join(svg)+'</svg>',encoding='utf-8')


def run(ifc, settings_path, out):
    ifc, settings_path, out = [Path(p).resolve() for p in (ifc, settings_path, out)]
    if any(out == p or out in p.parents for p in (ifc,settings_path)):
        raise ProjectError('output must not contain source inputs')
    before = {str(p):digest(p) for p in (ifc,settings_path)}
    settings = validate_settings(json.loads(settings_path.read_text(encoding='utf-8-sig')))
    result = extract(ifc); out.mkdir(parents=True,exist_ok=False)
    if result['calculated_checks_pass']:
        try: draw(result['segments'],settings,out)
        except ProjectError as exc:
            result['calculated_checks_pass']=False; result['drawing_error']=str(exc)
    with (out/'segments.csv').open('w',newline='',encoding='utf-8') as stream:
        fields=['guid','name','ifc_class','inner_diameter_m','outside_diameter_m','length_m','analytic_wall_volume_m3','start_world_m','end_world_m','source']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(result['segments'])
    result.update(inputs=before,settings=settings,inputs_unchanged=all(digest(Path(p))==h for p,h in before.items()),
                  design_accepted=False,scope='saved direct hollow pipe/duct profiles and directed ports; projected centreline schematic only',
                  pending=['native DWG reopen and printed scale/visual acceptance','equipment, fittings, insulation and installation drawings','product provenance and complete engineering acceptance'])
    if not result['inputs_unchanged']:raise ProjectError('source changed during IFC drawing extraction')
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ifc',type=Path)
    parser.add_argument('--settings',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.ifc,args.settings,args.out)
    print(json.dumps({k:result[k] for k in ('segment_count','calculated_checks_pass','design_accepted')}))
    return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
