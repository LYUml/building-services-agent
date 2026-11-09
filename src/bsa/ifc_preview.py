"""Saved IFC single-element multi-view preview; never drawing/design acceptance."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape as shape
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
from .cli import digest
from .engine import ProjectError


def extract(path, guid):
    f = ifcopenshell.open(str(path)); obj = f.by_guid(guid)
    if not obj.is_a('IfcElement') or not obj.Representation:
        raise ProjectError('selected represented IFC element required')
    settings = ifcopenshell.geom.settings(); settings.set('use-world-coords', True)
    body = ifcopenshell.geom.create_shape(settings, obj)
    vertices = shape.get_vertices(body.geometry); faces = shape.get_faces(body.geometry)
    if not len(vertices) or not len(faces) or len(faces) > 200000 or not np.isfinite(vertices).all():
        raise ProjectError('finite nonempty mesh of at most 200000 triangles required')
    scale = unit.calculate_unit_scale(f)
    if not np.isfinite(scale) or scale <= 0: raise ProjectError('positive finite IFC length scale required')
    ports = []
    for p in sorted(system.get_ports(obj), key=lambda x: x.GlobalId):
        if p.ObjectPlacement is None: raise ProjectError('port placement missing')
        matrix = placement.get_local_placement(p.ObjectPlacement)
        axis = matrix[:3, 2]
        if not np.isfinite(matrix).all() or not np.isclose(np.linalg.norm(axis), 1):
            raise ProjectError('finite unit port axis required')
        ports.append(dict(guid=p.GlobalId, name=p.Name, position_m=(matrix[:3, 3]*scale).tolist(), axis=axis.tolist()))
    if len(ports) > 12: raise ProjectError('preview supports at most twelve port labels')
    return vertices, faces, ports, [e.GlobalId for e in f.by_type('IfcElement') if e.GlobalId != guid]


def run(ifc, guid, out):
    ifc, out = Path(ifc).resolve(), Path(out).resolve()
    if out.exists() or out == ifc or out in ifc.parents: raise ProjectError('new separate output directory required')
    versions = {n: importlib.metadata.version(n) for n in ('ifcopenshell', 'matplotlib', 'numpy')}
    if versions != {'ifcopenshell':'0.8.5','matplotlib':'3.11.2','numpy':'2.5.4'}:
        raise ProjectError('pinned preview dependencies required')
    before = digest(ifc); vertices, faces, ports, omitted = extract(ifc, guid)
    centre = (vertices.min(axis=0)+vertices.max(axis=0))/2
    span = float(np.ptp(vertices, axis=0).max())
    if span <= 0: raise ProjectError('nonzero model extent required')
    arrow_length = span*.22
    points = [vertices]
    for p in ports:
        pt = np.array(p['position_m']); axis = np.array(p['axis'])
        points.append(np.array([pt, pt+axis*arrow_length*1.25]))
    cloud = np.concatenate(points)-centre
    radius = float(np.abs(cloud).max())*1.12
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 11), layout=None)
    colours = plt.get_cmap('tab10')
    for i, (title, elev, azim) in enumerate((('Isometric',25,-55),('XY / looking down Z',90,-90),
                                            ('XZ / looking along Y',0,-90),('YZ / looking along X',0,0)), 1):
        ax = fig.add_subplot(2, 2, i, projection='3d', proj_type='ortho', computed_zorder=False)
        ax.add_collection3d(Poly3DCollection((vertices-centre)[faces], facecolors='#9bb5c9', shade=True,
                                           linewidth=0, alpha=1, antialiased=False, zorder=1))
        for j, p in enumerate(ports):
            pt = np.array(p['position_m'])-centre; direction = np.array(p['axis'])*arrow_length
            ax.scatter(*pt, color=colours(j%10), s=28, depthshade=False, zorder=10)
            ax.quiver(*pt, *direction, color=colours(j%10), arrow_length_ratio=.2, linewidth=2, zorder=10)
            ax.text(*(pt+direction*1.15), str(j+1), color=colours(j%10), fontsize=11, zorder=11)
        for setter in (ax.set_xlim, ax.set_ylim, ax.set_zlim): setter(-radius, radius)
        ax.set_box_aspect((1,1,1)); ax.view_init(elev=elev, azim=azim)
        ax.set_title(title); ax.set_xlabel('X offset (m)'); ax.set_ylabel('Y offset (m)'); ax.set_zlabel('Z offset (m)')
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis): axis.set_ticks(np.linspace(-radius*.8, radius*.8, 5))
        if i > 1:
            hidden = {2:ax.zaxis, 3:ax.yaxis, 4:ax.xaxis}[i]
            hidden.set_ticks([]); hidden.set_label_text('')
        ax.tick_params(labelsize=7)
    fig.suptitle('Saved IFC body and port axes — geometric preview', fontsize=15)
    labels = [f'{i+1}: {(p["name"] or p["guid"])[:32]}' for i,p in enumerate(ports)]
    legend = '\n'.join(' | '.join(labels[i:i+3]) for i in range(0,len(labels),3)) or 'No attached ports'
    fig.text(.05,.06,legend,fontsize=9,va='bottom')
    fig.text(.05,.025,f'World origin for displayed offsets: {np.round(centre,6).tolist()} m\nAxis arrows are illustrative; no flow, joint, installation or design acceptance.',fontsize=8)
    fig.subplots_adjust(left=.02,right=.95,bottom=.12,top=.92,wspace=.08,hspace=.12)
    out.mkdir(parents=True)
    try: fig.savefig(out/'preview.png',dpi=150)
    finally: plt.close(fig)
    if digest(ifc) != before: raise ProjectError('source IFC changed during preview')
    result = dict(ifc=str(ifc), ifc_sha256=before, guid=guid, vertices=len(vertices), triangles=len(faces),
                  ports=ports, omitted_element_guids=omitted, display_origin_m=centre.tolist(),
                  world_bounds_m=[vertices.min(axis=0).tolist(),vertices.max(axis=0).tolist()],
                  arrow_length_m=arrow_length, runtime=versions, preview_sha256=digest(out/'preview.png'),
                  visual_review='pending', design_accepted=False,
                  scope='Selected saved element only; opaque mesh with overlay port markers, not a hidden-line or installation drawing')
    (out/'preview.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ifc');p.add_argument('guid');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.ifc,a.guid,a.out);print(json.dumps(r,indent=2))
