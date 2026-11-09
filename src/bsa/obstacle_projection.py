"""Source-checked native generic obstacle boxes for explicit planar projection."""
import math
from pathlib import Path
import uuid
import numpy as np
from .cli import digest
from .engine import ProjectError
from .ifc_obstacles import prepare
from .ifc_drawing import AXES


def inputs(inventory):
    from . import box_geometry
    _, files = prepare(inventory)
    return files | {Path(__file__).resolve(), Path(box_geometry.__file__).resolve()}


def extract(ifc, inventory, axes):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import ifcopenshell.util.unit as unit
    from .box_geometry import box_mesh
    if not isinstance(axes, list) or len(axes)!=2 or any(not isinstance(a,str) or a not in AXES for a in axes) or axes[0]==axes[1]:
        raise ProjectError('two distinct projection axes required')
    indices=[AXES[a] for a in axes]
    depth=next(i for i in range(3) if i not in indices)
    inventory=Path(inventory).resolve();ifc=Path(ifc).resolve()
    rows,_=prepare(inventory)
    before={str(p):digest(p) for p in inputs(inventory)|{ifc}}
    model=ifcopenshell.open(str(ifc))
    projects=model.by_type('IfcProject')
    if model.schema!='IFC4' or len(projects)!=1 or not math.isclose(unit.calculate_unit_scale(model),1,abs_tol=1e-12,rel_tol=0):
        raise ProjectError('one metre IFC4 project required for obstacle projection')
    namespace=uuid.UUID(hex=ifcopenshell.guid.expand(projects[0].GlobalId))
    settings=ifcopenshell.geom.settings();settings.set('use-world-coords',True)
    for row in rows:
        name='COORDINATION_OBSTACLE_'+row['id']
        guid=ifcopenshell.guid.compress(uuid.uuid5(namespace,name).hex)
        matches=[o for o in model.by_type('IfcBuildingElementProxy') if o.GlobalId==guid and o.Name==name]
        if len(matches)!=1:raise ProjectError('exact source-linked obstacle identity required')
        obj=matches[0]
        props=element.get_psets(obj).get('BSA_CoordinationObstacle',{})
        expected=dict(InputID=row['id'],Source=row['source'],InventorySHA256=digest(inventory),**row['properties'])
        if any(props.get(k)!=v for k,v in expected.items()):raise ProjectError('saved obstacle provenance differs from source inventory')
        shape=ifcopenshell.geom.create_shape(settings,obj)
        low,size,volume=box_mesh(np.array(shape.geometry.verts).reshape(-1,3),np.array(shape.geometry.faces).reshape(-1,3))
        if not np.allclose(low,row['origin_m'],atol=1e-8,rtol=0) or not np.allclose(size,row['size_m'],atol=1e-8,rtol=0):
            raise ProjectError('native obstacle bounds differ from source inventory')
        high=low+size
        row.update(guid=guid,projected_bounds_m=[float(low[indices[0]]),float(low[indices[1]]),float(high[indices[0]]),float(high[indices[1]])],
                   depth_axis='XYZ'[depth],depth_interval_m=[float(low[depth]),float(high[depth])],native_volume_m3=volume)
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('obstacle projection inputs changed')
    return rows,before
