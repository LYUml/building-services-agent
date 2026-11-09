"""Place a converted CAD fitting and bind model ports to explicit source LINE ends."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import numpy as np
import ezdxf
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.shape
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.element as element
import manifold3d as manifold
from .cad_ifc import mass_properties, mesh_properties, compare
from .cad_intake import METRES_PER_UNIT
from .cad_passage import validate as validate_probes
from .cli import digest
from .engine import ProjectError
from .solid_clash import from_mesh
from .tee_geometry import stable_guid, placement_matrix


def frame(point, axis):
    axis = np.asarray(axis, dtype=float); axis /= np.linalg.norm(axis)
    seed = np.eye(3)[np.argmin(abs(axis))]
    x = np.cross(seed, axis); x /= np.linalg.norm(x)
    result = np.eye(4); result[:3, 0] = x; result[:3, 1] = np.cross(axis, x)
    result[:3, 2] = axis; result[:3, 3] = point
    return result


def anchors(doc, ports, probes, scale):
    if not isinstance(ports, list) or len(ports) != 3:
        raise ProjectError('three explicit junction ports required')
    result = {}; used = set(); passage = {p['id']: p for p in probes if p['role'] == 'passage'}
    for p in ports:
        if not isinstance(p, dict) or set(p) != {'id', 'source', 'line_handle', 'endpoint', 'passage_id'}:
            raise ProjectError('exact port anchor fields required')
        if any(not isinstance(p[k], str) or not p[k].strip() for k in p):
            raise ProjectError('port source and identities required')
        if p['id'] in result or p['endpoint'] not in ('start', 'end') or p['passage_id'] not in passage:
            raise ProjectError('unique port with endpoint and passage reference required')
        line = doc.entitydb.get(p['line_handle'])
        if line is None or line.dxftype() != 'LINE' or line not in doc.modelspace():
            raise ProjectError('selected source model-space LINE missing')
        end = np.array(getattr(line.dxf, p['endpoint']), dtype=float)
        other = np.array(getattr(line.dxf, 'end' if p['endpoint'] == 'start' else 'start'), dtype=float)
        direction = end-other
        if not np.isfinite(direction).all() or np.linalg.norm(direction) <= 0:
            raise ProjectError('finite nondegenerate source centreline required')
        position = tuple(end.tolist())
        if position in used: raise ProjectError('duplicate port anchor position')
        used.add(position)
        probe = passage[p['passage_id']]
        start, finish = np.array(probe['start']), np.array(probe['end'])
        axis = finish-start; length = np.linalg.norm(axis); axis = axis/length
        distance = np.dot(end-start, axis)
        if (distance < 0 or distance > length or np.linalg.norm(end-start-distance*axis)*scale > 1e-8
                or abs(abs(np.dot(direction/np.linalg.norm(direction), axis))-1) > 1e-9):
            raise ProjectError('port must lie on the linked clear probe axis and axial span')
        result[p['id']] = frame(end*scale, direction)
    return result


def mesh(obj, world=False):
    settings = ifcopenshell.geom.settings(); settings.set('use-world-coords', world)
    shape = ifcopenshell.geom.create_shape(settings, obj)
    return (np.array(ifcopenshell.util.shape.get_vertices(shape.geometry), copy=True),
            np.array(ifcopenshell.util.shape.get_faces(shape.geometry), copy=True))


def run(producer, basis_path, out):
    if {k: importlib.metadata.version(k) for k in ('ifcopenshell', 'manifold3d', 'ezdxf')} != {
        'ifcopenshell': '0.8.5', 'manifold3d': '3.5.4', 'ezdxf': '1.4.5'}:
        raise ProjectError('verified pinned geometry runtimes required')
    producer, basis_path, out = [Path(p).resolve() for p in (producer, basis_path, out)]
    report_path = producer/'cad-ifc.json'; report = json.loads(report_path.read_text())
    b = json.loads(basis_path.read_text(encoding='utf-8-sig'))
    if not isinstance(b, dict) or set(b) != {'source', 'placement', 'system_name', 'passage_basis', 'ports'}:
        raise ProjectError('exact sourced placement/port basis required')
    if any(not isinstance(b[k], str) or not b[k].strip() for k in ('source', 'system_name', 'passage_basis')):
        raise ProjectError('placement/system and passage sources required')
    transform = placement_matrix(b)
    probe_path = (basis_path.parent/b['passage_basis']).resolve()
    probes = json.loads(probe_path.read_text(encoding='utf-8-sig')); validate_probes(probes)
    if not report.get('geometry_conversion_pass'): raise ProjectError('passing CAD conversion required')
    before = {str(p): digest(p) for p in (report_path, basis_path, probe_path)}
    for name, expected in report['artifacts'].items():
        p = (producer/name).resolve()
        if not p.is_relative_to(producer) or digest(p) != expected:
            raise ProjectError('converted producer artifact changed')
        before[str(p)] = expected
    for name, expected in report['inputs'].items():
        p = Path(name)
        if digest(p) != expected: raise ProjectError('original conversion input changed')
        before[str(p)] = expected
    if any(k not in report['artifacts'] for k in ('fitting.ifc', 'intake/source-export.dxf', 'solid.mpr')):
        raise ProjectError('required source/geometry artifacts missing')
    if probes['drawing_sha256'] != report['basis']['drawing_sha256'] or probes['solid_handle'].upper() != report['basis']['solid_handle'].upper() or probes['insunits'] != report['basis']['insunits']:
        raise ProjectError('passage basis must bind the same source CAD solid and units')
    doc = ezdxf.readfile(producer/'intake/source-export.dxf'); audit = doc.audit()
    if audit.errors or audit.fixes or doc.units != probes['insunits']:
        raise ProjectError('source CAD units/audit failed')
    scale = METRES_PER_UNIT[doc.units]
    port_frames = anchors(doc, b['ports'], probes['probes'], scale)
    f = ifcopenshell.open(str(producer/'fitting.ifc'))
    if len(f.by_type('IfcElement')) != 1 or len(f.by_type('IfcPipeFitting')) != 1 or f.by_type('IfcDistributionPort'):
        raise ProjectError('one unconnected converted fitting required')
    obj = f.by_type('IfcPipeFitting')[0]
    if obj.GlobalId != report['guid'] or obj.GlobalId != stable_guid(report['basis'], 'IfcPipeFitting', report['basis']['id']):
        raise ProjectError('converted identity mismatch')
    if not np.allclose(placement.get_local_placement(obj.ObjectPlacement), np.eye(4), atol=1e-12, rtol=0):
        raise ProjectError('converted source must use the local definition frame')
    v, faces = mesh(obj); original = mesh_properties(v, faces)
    native = mass_properties((producer/'solid.mpr').read_text())
    reference = {'volume': native['volume']*scale**3, 'bounds': native['bounds']*scale, 'centroid': native['centroid']*scale}
    if not all(compare(original, reference, report['basis']['linear_tolerance_m'], report['basis']['relative_volume_tolerance']).values()):
        raise ProjectError('converted body no longer reconciles to native source')
    for local in port_frames.values():
        normal, point = local[:3, 2], local[:3, 3]
        if abs(float(np.dot(point, normal)-np.max(v@normal))) > report['basis']['linear_tolerance_m']:
            raise ProjectError('port anchor must lie on the outward body support plane')
    if (out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or out.is_relative_to(producer)
            or producer.is_relative_to(out) or any(out == p or out in p.parents for p in (basis_path, probe_path))):
        raise ProjectError('new repository output outside source bundle required')
    # Preserve the original tessellation verbatim; only add placement/ports/group.
    source_rep = obj.Representation.Representations[0].Items[0]
    if not source_rep.is_a('IfcTriangulatedFaceSet'): raise ProjectError('source tessellation required')
    coords, indices = source_rep.Coordinates.CoordList, source_rep.CoordIndex
    api.run('geometry.edit_object_placement', f, product=obj, matrix=transform, is_si=True)
    group = api.run('root.create_entity', f, ifc_class='IfcDistributionSystem', name=b['system_name'])
    group.GlobalId = stable_guid(report['basis'], 'IfcDistributionSystem', b['system_name'])
    api.run('system.assign_system', f, products=[obj], system=group)
    for name, local in port_frames.items():
        port = api.run('system.add_port', f, element=obj); port.Name = name; port.FlowDirection = 'SOURCEANDSINK'
        port.GlobalId = stable_guid(report['basis'], 'IfcDistributionPort', report['basis']['id'], name)
        api.run('geometry.edit_object_placement', f, product=port, matrix=transform@local, is_si=True)
        ps = api.run('pset.add_pset', f, product=port, name='BSA_CADAnchor')
        definition = next(p for p in b['ports'] if p['id'] == name)
        api.run('pset.edit_pset', f, pset=ps, properties={'Source': definition['source'], 'LineHandle': definition['line_handle'],
            'Endpoint': definition['endpoint'], 'SourceDXFSHA256': digest(producer/'intake/source-export.dxf'),
            'Scope': 'Source centreline anchor; physical joint compatibility unverified'})
    out.mkdir(parents=True); target = out/'placed-fitting.ifc'; f.write(str(target))
    saved = ifcopenshell.open(str(target)); product = saved.by_guid(obj.GlobalId)
    saved_rep = product.Representation.Representations[0].Items[0]
    actual_ports = {p.Name: p for p in system.get_ports(product)}
    checks = {'tessellation_preserved': saved_rep.Coordinates.CoordList == coords and saved_rep.CoordIndex == indices,
              'placement': bool(np.allclose(placement.get_local_placement(product.ObjectPlacement), transform, atol=1e-9, rtol=0)),
              'port_coverage': set(actual_ports) == set(port_frames) and len(saved.by_type('IfcDistributionPort')) == 3,
              'system_membership': {s.GlobalId for s in system.get_element_systems(product)} == {group.GlobalId}}
    for name, local in port_frames.items():
        port = actual_ports[name]
        source_port = next(p for p in b['ports'] if p['id'] == name)
        metadata = element.get_psets(port).get('BSA_CADAnchor', {})
        checks['port_'+name] = (port.GlobalId == stable_guid(report['basis'], 'IfcDistributionPort', report['basis']['id'], name)
            and port.FlowDirection == 'SOURCEANDSINK'
            and metadata.get('LineHandle') == source_port['line_handle'] and metadata.get('Endpoint') == source_port['endpoint']
            and metadata.get('Source') == source_port['source']
            and metadata.get('SourceDXFSHA256') == digest(producer/'intake/source-export.dxf')
            and bool(np.allclose(placement.get_local_placement(port.ObjectPlacement), transform@local, atol=1e-9, rtol=0)))
    world, wf = mesh(product, world=True); expected_world = v@transform[:3, :3].T+transform[:3, 3]
    checks.update({'world_'+k: value for k, value in compare(mesh_properties(world, wf), mesh_properties(expected_world, faces), 1e-8, 1e-8).items()})
    body = from_mesh((world, wf)); probe_results = []
    for p in probes['probes']:
        start, finish = np.array(p['start'])*scale, np.array(p['end'])*scale
        probe = manifold.Manifold.cylinder(float(np.linalg.norm(finish-start)), p['radius']*scale, circular_segments=128)
        probe = probe.transform((transform@frame(start, finish-start))[:3, :])
        common = body^probe
        if common.status() != manifold.Error.NoError: raise ProjectError('saved IFC probe Boolean failed')
        volume = common.volume()
        if not math.isfinite(volume) or volume < 0: raise ProjectError('invalid saved IFC intersection volume')
        passed = volume <= 1e-12 if p['role'] == 'passage' else volume > 1e-12
        probe_results.append({'id': p['id'], 'role': p['role'], 'intersection_m3': volume, 'pass': passed})
    checks['saved_ifc_passages_and_wall_control'] = all(p['pass'] for p in probe_results)
    if any(digest(Path(p)) != h for p, h in before.items()): raise ProjectError('product source changed')
    result = {'inputs': before, 'basis': b, 'guid': obj.GlobalId, 'checks': checks, 'probes': probe_results,
              'probe_numerics': {'circular_segments': 128, 'intersection_volume_tolerance_m3': 1e-12},
              'product_ports_pass': all(checks.values()), 'design_accepted': False,
              'pending': ['physical joint and pipe compatibility', 'external system connections', 'viewer and installation review',
                          'hydraulic and regulatory applicability'], 'ifc_sha256': digest(target)}
    (out/'product-ports.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('producer'); p.add_argument('basis'); p.add_argument('--out', required=True)
    a = p.parse_args(); r = run(a.producer, a.basis, a.out)
    print(json.dumps({'checks': r['checks'], 'probes': r['probes'], 'design_accepted': False}, indent=2))
    raise SystemExit(0 if r['product_ports_pass'] else 2)
