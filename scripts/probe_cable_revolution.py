"""Native IFC revolved circular cable envelope trial, with analytic checks."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import numpy as np
from bsa.cad_ifc import mesh_properties
from bsa.circular_geometry import configure,BOUNDS_TOLERANCE_M,VOLUME_RELATIVE_TOLERANCE
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase import ROOT


def run(out,radius=.3,envelope=.01):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository probe output required')
    if not 0<envelope<radius or not math.isfinite(radius+envelope):raise ProjectError('finite 0 < envelope radius < bend radius required')
    m=api.run('project.create_file',version='IFC4')
    project=api.run('root.create_entity',m,ifc_class='IfcProject',name='Synthetic quarter-circle solid cable trial')
    units=[api.run('unit.add_si_unit',m,unit_type=t) for t in ('LENGTHUNIT','PLANEANGLEUNIT')]
    api.run('unit.assign_unit',m,units=units)
    ctx=api.run('context.add_context',m,context_type='Model')
    body=api.run('context.add_context',m,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=ctx)
    cable=api.run('root.create_entity',m,ifc_class='IfcCableSegment',predefined_type='CABLESEGMENT',name='Synthetic 90 degree cable envelope')
    position=m.create_entity('IfcAxis2Placement3D',Location=m.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)))
    profile_position=m.create_entity('IfcAxis2Placement2D',Location=m.create_entity('IfcCartesianPoint',Coordinates=(float(radius),0.)))
    profile=m.create_entity('IfcCircleProfileDef',ProfileType='AREA',Position=profile_position,Radius=float(envelope))
    axis=m.create_entity('IfcAxis1Placement',Location=m.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)),Axis=m.create_entity('IfcDirection',DirectionRatios=(0.,1.,0.)))
    solid=m.create_entity('IfcRevolvedAreaSolid',SweptArea=profile,Position=position,Axis=axis,Angle=math.pi/2)
    representation=m.create_entity('IfcShapeRepresentation',ContextOfItems=body,RepresentationIdentifier='Body',RepresentationType='SweptSolid',Items=[solid])
    api.run('geometry.assign_representation',m,product=cable,representation=representation)
    api.run('geometry.edit_object_placement',m,product=cable,matrix=np.eye(4),is_si=True)
    out.mkdir(parents=True);path=out/'quarter-cable.ifc';m.write(str(path))
    reopened=ifcopenshell.open(str(path));logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(reopened,logger,express_rules=True)
    if logger.statements:raise ProjectError('native trial IFC schema/EXPRESS failed: '+str(logger.statements[:2]))
    settings=ifcopenshell.geom.settings();settings.set('use-world-coords',True);configure(settings)
    shape=ifcopenshell.geom.create_shape(settings,reopened.by_guid(cable.GlobalId))
    vertices=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
    observed=mesh_properties(vertices,faces)
    length=radius*math.pi/2;volume=math.pi*envelope**2*length
    centroid_radius=radius+envelope**2/(4*radius)
    centroid=np.array([centroid_radius*2/math.pi,0.,-centroid_radius*2/math.pi])
    bounds=np.array([[0.,-envelope,-radius-envelope],[radius+envelope,envelope,0.]])
    passed=bool(np.allclose(observed['bounds'],bounds,atol=BOUNDS_TOLERANCE_M,rtol=0) and np.allclose(observed['centroid'],centroid,atol=BOUNDS_TOLERANCE_M,rtol=0) and math.isclose(observed['volume'],volume,rel_tol=VOLUME_RELATIVE_TOLERANCE))
    result=dict(scope='Synthetic native quarter-circle solid envelope only; no installation, equipment, conductor selection or regulation acceptance',inputs=dict(bend_radius_m=radius,envelope_radius_m=envelope,angle_radians=math.pi/2,kind='assumption'),
        ifc_sha256=digest(path),schema_express_pass=True,analytic_arc_length_m=length,endpoint_chord_m=radius*math.sqrt(2),native_mesh_pass=True,
        native_volume_m3=observed['volume'],analytic_volume_m3=volume,native_centroid_m=observed['centroid'].tolist(),analytic_centroid_m=centroid.tolist(),native_bounds_m=observed['bounds'].tolist(),
        analytic_checks_pass=passed,versions={n:importlib.metadata.version(n) for n in ('ifcopenshell','manifold3d')},probe_sha256=digest(Path(__file__)),design_accepted=False)
    (out/'probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not passed:raise ProjectError('native circular revolution disagrees with analytic geometry')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--radius',type=float,default=.3);p.add_argument('--envelope',type=float,default=.01)
    a=p.parse_args();r=run(a.out,a.radius,a.envelope)
    print(json.dumps({k:r[k] for k in ('native_mesh_pass','analytic_checks_pass','analytic_arc_length_m','endpoint_chord_m','design_accepted')}))
