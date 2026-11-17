"""Nearest-centre design allocation; not a prediction of diffuser air coverage."""
import math
from shapely import voronoi_polygons, union_all
from shapely.geometry import MultiPoint, Point, mapping, shape


def allocate(boundary, terminals, given_load_area_m2):
    """Inputs use planar metres; preserve supplied area separately from geometry."""
    space = shape(boundary)
    if space.geom_type not in ('Polygon', 'MultiPolygon') or not space.is_valid or space.is_empty or not math.isfinite(space.area) or space.area <= 0:
        raise ValueError('Valid positive polygonal service boundary required')
    if type(given_load_area_m2) not in (int, float) or not math.isfinite(given_load_area_m2) or given_load_area_m2 <= 0:
        raise ValueError('Explicit positive load area required')
    if not terminals:
        raise ValueError('At least one terminal required')
    ids, points = set(), []
    for terminal in terminals:
        name, xy = terminal['id'], terminal['center_m']
        if not isinstance(name, str) or not name.strip() or name in ids:
            raise ValueError('Unique terminal IDs required')
        if len(xy) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in xy):
            raise ValueError('Finite planar metre coordinates required')
        if tuple(xy) in points or not space.contains(Point(xy)):
            raise ValueError('Distinct terminal centres inside service space required')
        ids.add(name)
        points.append(tuple(xy))
    cells = [space] if len(points)==1 else list(voronoi_polygons(MultiPoint(points), extend_to=space.envelope, ordered=True).geoms)
    if len(cells) != len(terminals):
        raise ValueError('Voronoi cell identity count differs')
    clipped = [cell.intersection(space) for cell in cells]
    merged = union_all(clipped)
    gap = merged.symmetric_difference(space).area
    overlap = sum(cell.area for cell in clipped) - merged.area
    tolerance = max(1e-9, space.area*1e-10)
    if gap > tolerance or abs(overlap) > tolerance:
        raise ValueError('Service cells do not partition boundary')
    rows = []
    for terminal, cell in zip(terminals, clipped):
        if cell.is_empty or not cell.covers(Point(terminal['center_m'])):
            raise ValueError('Cell does not contain its terminal')
        rows.append(dict(id=terminal['id'], center_m=terminal['center_m'],
                         geometric_area_m2=cell.area,
                         allocated_load_area_m2=given_load_area_m2*cell.area/space.area,
                         geometry=mapping(cell)))
    return dict(terminals=rows, net_geometry_area_m2=space.area,
                given_load_area_m2=given_load_area_m2, uncovered_area_m2=gap,
                overlap_area_m2=overlap,
                scope='Nearest-centre design allocation; not measured coverage, heat-load distribution or ADPI characteristic length',
                design_accepted=False)


def allocate_explicit(boundary, terminals, given_load_area_m2, service_cells, basis):
    """Clip declared cells with Shapely; never infer coverage from the partition."""
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError('Explicit service partition design basis required')
    space = shape(boundary)
    if space.geom_type not in ('Polygon', 'MultiPolygon') or not space.is_valid or space.is_empty or not math.isfinite(space.area) or space.area <= 0:
        raise ValueError('Valid positive polygonal service boundary required')
    if type(given_load_area_m2) not in (int, float) or not math.isfinite(given_load_area_m2) or given_load_area_m2 <= 0:
        raise ValueError('Explicit positive load area required')
    if not terminals or not isinstance(service_cells, dict):
        raise ValueError('Terminals and ID-bound service cells required')
    ids, points, clipped = set(), set(), []
    for terminal in terminals:
        name, xy = terminal['id'], terminal['center_m']
        if not isinstance(name, str) or not name.strip() or name in ids:
            raise ValueError('Unique terminal IDs required')
        if len(xy) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in xy):
            raise ValueError('Finite planar metre coordinates required')
        if tuple(xy) in points or not space.contains(Point(xy)):
            raise ValueError('Distinct terminal centres inside service space required')
        if name not in service_cells:
            raise ValueError('Exactly one declared service cell per terminal required')
        cell = shape(service_cells[name])
        if cell.geom_type not in ('Polygon', 'MultiPolygon') or not cell.is_valid or cell.is_empty or not math.isfinite(cell.area) or cell.area <= 0:
            raise ValueError('Valid positive polygonal service cell required')
        cell = cell.intersection(space)
        if cell.is_empty or cell.area <= 0 or not cell.covers(Point(xy)):
            raise ValueError('Cell does not contain its terminal')
        clipped.append(cell)
        ids.add(name)
        points.add(tuple(xy))
    if set(service_cells) != ids:
        raise ValueError('Exactly one declared service cell per terminal required')
    merged = union_all(clipped)
    gap = merged.symmetric_difference(space).area
    overlap = math.fsum(cell.area for cell in clipped) - merged.area
    tolerance = max(1e-9, space.area*1e-10)
    if gap > tolerance or abs(overlap) > tolerance:
        raise ValueError('Service cells do not partition boundary')
    rows = [dict(id=t['id'], center_m=list(t['center_m']), geometric_area_m2=c.area,
                 allocated_load_area_m2=given_load_area_m2*c.area/space.area,
                 geometry=mapping(c)) for t, c in zip(terminals, clipped)]
    return dict(terminals=rows, net_geometry_area_m2=space.area,
                given_load_area_m2=given_load_area_m2, uncovered_area_m2=gap,
                overlap_area_m2=overlap, basis=basis,
                scope='Explicit clipped service-cell design allocation; not measured coverage, spatial load or ADPI acceptance',
                design_accepted=False)
