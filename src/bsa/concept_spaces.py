"""Independent saved IFC concept-space/storey inspection using existing native box QA."""
import json
import math
import uuid
from .engine import ProjectError


def inspect_spaces(model,source):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    import ifcopenshell.util.unit as unit_util
    import ifcopenshell.util.placement as placement
    import numpy as np
    from .bim import validate,CONCEPT_SCOPE
    from .box_geometry import box_mesh
    from .circular_geometry import configure
    p=validate(source)
    if p['geometry_scope']!=CONCEPT_SCOPE:raise ProjectError('explicit concept space scope required')
    if len(model.by_type('IfcSpace'))!=len(p['spaces']) or len(model.by_type('IfcBuildingStorey'))!=len(p['storeys']) or model.by_type('IfcDistributionElement') or model.by_type('IfcDistributionSystem') or not math.isclose(unit_util.calculate_unit_scale(model),1):raise ProjectError('exact metre concept-space/storey coverage without MEP required')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    records=[];namespace=uuid.UUID(p['project_uuid']) if p.get('project_uuid') else None
    for row in p['spaces']:
        objects=[o for o in model.by_type('IfcSpace') if o.Name==row['id']]
        if len(objects)!=1:raise ProjectError('unique saved concept space required')
        obj=objects[0];shape=ifcopenshell.geom.create_shape(settings,obj)
        verts=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
        lo,size,volume=box_mesh(verts,faces)
        if len(obj.Decomposes)!=1:raise ProjectError('unique concept-space storey required')
        parent=obj.Decomposes[0].RelatingObject
        metadata=element.get_psets(obj).get('BSA_DesignInputs',{})
        level=next(s for s in p['storeys'] if s['id']==row['storey'])
        if not np.allclose(lo,row['origin_m'],atol=1e-7,rtol=0) or not np.allclose(size,row['size_m'],atol=1e-7,rtol=0) or not parent.is_a('IfcBuildingStorey') or parent.Name!=row['storey'] or not math.isclose(parent.Elevation,level['elevation_m'],abs_tol=1e-8,rel_tol=0):raise ProjectError('saved concept space/storey geometry differs')
        if len(parent.Decomposes)!=1 or not parent.Decomposes[0].RelatingObject.is_a('IfcBuilding'):raise ProjectError('concept storey must aggregate under building')
        parent_data=element.get_psets(parent).get('BSA_DesignInputs',{})
        if parent_data.get('Source')!=p['sources'][level['source']] or parent_data.get('InputID')!=level['id'] or parent_data.get('ConceptHeight_m')!=level['height_m']:raise ProjectError('saved concept storey provenance differs')
        matrix=placement.get_local_placement(parent.ObjectPlacement);expected_matrix=np.eye(4);expected_matrix[2,3]=level['elevation_m']
        if not np.allclose(matrix,expected_matrix,atol=1e-8,rtol=0):raise ProjectError('saved concept storey placement differs')
        expected=ifcopenshell.guid.compress(uuid.uuid5(namespace,json.dumps(['IfcSpace',row['id']],ensure_ascii=False,separators=(',',':'))).hex) if namespace else obj.GlobalId
        if namespace and parent.GlobalId!=ifcopenshell.guid.compress(uuid.uuid5(namespace,json.dumps(['IfcBuildingStorey',row['storey']],ensure_ascii=False,separators=(',',':'))).hex):raise ProjectError('saved concept storey identity differs')
        if metadata.get('Source')!=p['sources'][row['source']] or metadata.get('InputID')!=row['id'] or metadata.get('GeometryScope')!=CONCEPT_SCOPE or metadata.get('FloorAreaBasis')!=p['floor_area_basis'] or obj.GlobalId!=expected:raise ProjectError('saved concept provenance/identity differs')
        records.append(dict(id=row['id'],guid=obj.GlobalId,storey=parent.Name,origin_m=lo.tolist(),size_m=size.tolist(),gross_footprint_area_m2=float(size[0]*size[1]),volume_m3=volume))
    return records
