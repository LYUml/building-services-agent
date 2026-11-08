"""Conservative planar leader routing; graphic clearances are not service clearances."""
import heapq
import itertools
import math
from .engine import ProjectError

EPS = 1e-10
MAX_NODES = 20000


def inside(p, box):
    return box[0]+EPS < p[0] < box[2]-EPS and box[1]+EPS < p[1] < box[3]-EPS


def crosses(a, b, box):
    """Positive segment extent inside an open rectangle; touching its boundary is allowed."""
    low, high = 0., 1.
    for i in (0, 1):
        delta = b[i]-a[i]
        if abs(delta) < EPS:
            if not box[i]+EPS < a[i] < box[i+2]-EPS:
                return False
        else:
            ends = sorted(((box[i]-a[i])/delta, (box[i+2]-a[i])/delta))
            low, high = max(low, ends[0]), min(high, ends[1])
    return high-low > EPS and inside([(a[i]+(low+high)/2*(b[i]-a[i])) for i in (0, 1)], box)


def expand(box, margin):
    return [box[0]-margin, box[1]-margin, box[2]+margin, box[3]+margin]


def clear(a, b, boxes):
    return not any(crosses(a, b, box) for box in boxes)


def path(start, end, boxes, height, maximum_x=None):
    if any(inside(p, box) for p in (start, end) for box in boxes):
        return None
    # Prefer vertical departure so a leader need not run along a horizontal pipe.
    for corner in ([start[0], end[1]], [end[0], start[1]]):
        if clear(start, corner, boxes) and clear(corner, end, boxes):
            return simplify([start, corner, end])
    xs = sorted({start[0], end[0]} | {b[i] for b in boxes for i in (0, 2)})
    if maximum_x is not None:xs=[x for x in xs if x<=maximum_x+EPS]
    ys = sorted({start[1], end[1]} | {b[i] for b in boxes for i in (1, 3)})
    if len(xs)*len(ys) > MAX_NODES:
        raise ProjectError('annotation visibility grid exceeds explicit node budget')
    nodes = {(i, j): [x, y] for i, x in enumerate(xs) for j, y in enumerate(ys)
             if not any(inside([x, y], b) for b in boxes)}
    first = (xs.index(start[0]), ys.index(start[1])); last = (xs.index(end[0]), ys.index(end[1]))
    queue = [(0., first, -1)]; costs = {(first, -1): 0.}; previous = {}
    while queue:
        cost, node, direction = heapq.heappop(queue); state = (node, direction)
        if cost != costs[state]:
            continue
        if node == last:
            result = [nodes[node]]
            while state in previous:
                state = previous[state]; result.append(nodes[state[0]])
            return simplify(list(reversed(result)))
        for dx, dy, axis in ((0, 1, 1), (0, -1, 1), (1, 0, 0), (-1, 0, 0)):
            other = (node[0]+dx, node[1]+dy)
            if other not in nodes or not clear(nodes[node], nodes[other], boxes):
                continue
            value = cost+math.dist(nodes[node], nodes[other])+(height if direction not in (-1, axis) else 0)
            next_state = (other, axis)
            if value < costs.get(next_state, math.inf):
                costs[next_state] = value; previous[next_state] = (node, direction)
                heapq.heappush(queue, (value, other, axis))
    return None


def simplify(points):
    result = []
    for p in points:
        p = list(p)
        if result and math.dist(result[-1], p) < EPS:
            continue
        if len(result) >= 2:
            a, b = result[-2:]
            if abs((b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0])) < EPS:
                result.pop()
        result.append(p)
    return result


def geometry(row, axes, height):
    a, b = [[p[i] for i in axes] for p in (row['start_world_m'], row['end_world_m'])]
    ro = row['outside_diameter_m']/2
    if row['centreline_radius_m'] is None:
        length = math.dist(a, b); normal = [-(b[1]-a[1])/length, (b[0]-a[0])/length]
        if normal[0] < -EPS or abs(normal[0]) < EPS and normal[1] < 0:
            normal = [-v for v in normal]
        points = [[p[i]+sign*ro*normal[i] for i in (0, 1)] for p in (a, b) for sign in (-1, 1)]
        centre = [(a[i]+b[i])/2 for i in (0, 1)]
    else:
        c = row['projected_centre_m']; radius = row['centreline_radius_m']
        start, end = row['start_angle_deg'], row['end_angle_deg']; span = (end-start)%360
        angles = [start, end]+[v for v in (0, 90, 180, 270) if (v-start)%360 <= span+EPS]
        points = [[c[0]+r*math.cos(math.radians(t)), c[1]+r*math.sin(math.radians(t))]
                  for r in (radius-ro, radius+ro) for t in angles]
        theta = math.radians(start+span/2); normal = [math.cos(theta), math.sin(theta)]
        centre = [c[i]+radius*normal[i] for i in (0, 1)]
    box = [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]
    anchor = [centre[i]+ro*normal[i] for i in (0, 1)]
    distances = [((box[i+2]+height if normal[i] > 0 else box[i]-height)-anchor[i])/normal[i]
                 for i in (0, 1) if abs(normal[i]) > EPS]
    distance = max(distances)
    escape = [anchor[i]+distance*normal[i] for i in (0, 1)]
    return dict(guid=row['guid'], bounds_m=box, anchor_m=anchor, escape_m=escape, centre_m=centre)


def layout(rows, axes, height, obstacle_boxes=()):
    items = [geometry(row, axes, height) for row in rows]
    margin = height/2
    ordered = sorted(items, key=lambda item: (item['centre_m'][1], item['guid']))
    slots = []
    for item in ordered:
        slots.append(max(item['escape_m'][1], slots[-1]+2.2*height if slots else -math.inf))
    label_x = max([item['bounds_m'][2] for item in items]+[b[2] for b in obstacle_boxes])+4*height
    if len(items) <= 6:
        orders = sorted(itertools.permutations(ordered), key=lambda order: sum(abs(item['escape_m'][1]-y) for item, y in zip(order, slots)))[:128]
    else:
        orders = [tuple(ordered), tuple(reversed(ordered))]
    actual = {item['guid']: item['bounds_m'] for item in items}
    all_boxes=list(actual.values())+list(obstacle_boxes)
    top=max(b[3] for b in all_boxes)+4*height
    bottom=min(b[1] for b in all_boxes)-4*height-2.2*height*(len(items)-1)
    slot_sets=[slots,[top+i*2.2*height for i in range(len(items))],[bottom+i*2.2*height for i in range(len(items))]]
    assignments=((order,candidate_slots) for candidate_slots in slot_sets for order in orders)
    for attempt, (order,slots) in enumerate(assignments, 1):
        plans = {}; prior = []
        for item, y in zip(order, slots):
            guid = item['guid']; anchor, escape = item['anchor_m'], item['escape_m']
            other_boxes = [expand(box, margin) for key, box in actual.items() if key != guid]+[expand(b,margin) for b in obstacle_boxes]+prior
            if not clear(anchor, escape, other_boxes):
                break
            boxes = [expand(box, margin) for box in actual.values()]+[expand(b,margin) for b in obstacle_boxes]+prior
            tail = path(escape, [label_x-height, y], boxes, height,maximum_x=label_x-height)
            if tail is None:
                break
            points = [anchor]+tail
            plans[guid] = dict(**item, leader_points_m=points, label_position_m=[label_x, y])
            prior.extend(expand([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], margin)
                         for a, b in zip(points, points[1:]))
        else:
            return dict(scope='conservative OD-rectangle and prior-leader-box avoidance; own initial stub is an outward OD normal ray',
                        graphic_margin_m=margin, label_spacing_m=2.2*height, candidate_assignments_tested=attempt,
                        leader_body_checks_pass=True, leader_pair_checks_pass=True, pieces=list(plans.values()))
    raise ProjectError('annotation layout not proven: cannot route separate leaders outside conservative route obstacles')
