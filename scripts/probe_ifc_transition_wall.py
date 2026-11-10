"""Research centred transition wall via existing upstream shapes and native Boolean."""
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
import manifold3d as m
from ifcopenshell.util.shape_builder import ShapeBuilder

from probe_ifc_transition import run as outer_probe
from bsa.cli import digest
from bsa.circular_geometry import verify_closed_wall
from bsa.cad_ifc import mesh_properties
from bsa.solid_clash import from_mesh
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


def run(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out==ROOT or out.exists():raise ValueError('New repository research output required')
    out.mkdir(parents=True)
    outer=outer_probe(out/'outer')
    source=out/'outer/transition-probe.ifc';source_sha=digest(source)
    model=ifcopenshell.open(str(source));builder=ShapeBuilder(model)
    fitting=model.by_type('IfcDuctFitting')[0]
    original=fitting.Representation.Representations[0]
    section_offset=.005;extension=.0001
    segments=[]
    for name,width,height in [('Synthetic inner start',.6-2*section_offset,.3-2*section_offset),
                              ('Synthetic inner end',.4-2*section_offset,.2-2*section_offset)]:
        segment=api.run('root.create_entity',model,ifc_class='IfcDuctSegment',name=name)
        profile=model.create_entity('IfcRectangleProfileDef',ProfileType='AREA',XDim=width,YDim=height)
        material=model.create_entity('IfcMaterialProfileSet',MaterialProfiles=[model.create_entity('IfcMaterialProfile',Profile=profile)])
        model.create_entity('IfcRelAssociatesMaterial',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[segment],RelatingMaterial=material)
        segments.append(segment)
    inner,parameters=builder.mep_transition_shape(*segments,.1+extension,.1+extension,angle=30,profile_offset=(0.,0.))
    if inner is None or not math.isclose(parameters['transition_length'],outer['upstream_parameters']['transition_length'],abs_tol=1e-12):
        raise ValueError('Inner and outer transition stations differ')
    builder.translate(inner,(0.,0.,-extension))
    def brep(representation):
        if len(representation.Items)!=1 or not representation.Items[0].is_a('IfcPolygonalFaceSet'):
            raise ValueError('Expected single upstream polygonal transition shape')
        item=representation.Items[0]
        return builder.faceted_brep(item.Coordinates.CoordList,[[i-1 for i in face.CoordIndex] for face in item.Faces])
    difference=model.create_entity('IfcBooleanResult',Operator='DIFFERENCE',FirstOperand=brep(original),SecondOperand=brep(inner))
    representation=model.create_entity('IfcShapeRepresentation',ContextOfItems=original.ContextOfItems,
        RepresentationIdentifier='Body',RepresentationType='CSG',Items=[difference])
    fitting.Representation.Representations=(representation,)
    api.run('geometry.remove_representation',model,representation=original)
    api.run('geometry.remove_representation',model,representation=inner)
    fitting.Name='Synthetic centred transition section-offset wall research'
    api.run('geometry.edit_object_placement',model,product=fitting,matrix=np.eye(4),is_si=True)
    target=out/'transition-wall-probe.ifc';model.write(str(target))
    saved=ifcopenshell.open(str(target))
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(saved,logger,express_rules=True)
    if logger.statements:raise ValueError('Saved probe schema/EXPRESS validation issues: '+str(logger.statements))
    shape=ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(),saved.by_guid(fitting.GlobalId))
    vertices=np.asarray(shape.geometry.verts).reshape((-1,3));faces=np.asarray(shape.geometry.faces).reshape((-1,3))
    def prismoid(w0,h0,w1,h1,length):
        return length*(2*w0*h0+2*w1*h1+w0*h1+w1*h0)/6
    taper=outer['upstream_parameters']['transition_length'];length=.2+taper
    inner_volume=.1*(.59*.29+.39*.19)+prismoid(.59,.29,.39,.19,taper)
    expected=outer['independent_filled_envelope_volume_m3']-inner_volume
    volume,error,euler=verify_closed_wall(vertices,faces,expected)
    mass=mesh_properties(vertices,faces)
    solid=from_mesh((vertices,faces));probe=m.Manifold.cube((.1,.1,length+.2),center=True).translate((0.,0.,length/2))
    overlap=solid^probe
    if overlap.status()!=m.Error.NoError or abs(overlap.volume())>1e-12:raise ValueError('Centre through-bore probe intersects material')
    outer_model=ifcopenshell.open(str(source));outer_shape=ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(),outer_model.by_guid(fitting.GlobalId))
    outer_v=np.asarray(outer_shape.geometry.verts).reshape((-1,3));outer_f=np.asarray(outer_shape.geometry.faces).reshape((-1,3))
    rejected=False
    try:verify_closed_wall(outer_v,outer_f,expected)
    except ProjectError:rejected=True
    if not rejected:raise ValueError('Filled-envelope negative control was accepted')
    if digest(source)!=source_sha:raise ValueError('Original upstream probe changed')
    result=dict(upstream='IfcOpenShell0.8.5 ShapeBuilder transition and faceted_brep; native IFC Boolean DIFFERENCE',
                versions={name:importlib.metadata.version(name) for name in ('ifcopenshell','manifold3d','numpy')},
                builder_sha256=outer['builder_sha256'],saved_schema_express_issue_count=len(logger.statements),
                section_plane_offset_m=section_offset,offset_is_not_constant_sheet_normal_thickness=True,
                inner_numerical_end_extension_m=extension,transition_length_m=taper,
                independent_material_volume_m3=expected,native_material_volume_m3=volume,relative_volume_error=error,
                euler_characteristic=euler,one_connected_closed_material=True,centre_through_bore_overlap_m3=overlap.volume(),
                filled_outer_negative_control_rejected=rejected,bounds_m=mass['bounds'].tolist(),
                port_count=len(saved.by_type('IfcDistributionPort')),source_ifc_sha256=source_sha,
                ifc_sha256=digest(target),script_sha256=digest(Path(__file__)),production_adapter=False,design_accepted=False,
                scope='Synthetic centred section-plane offset wall only; not constant sheet-normal thickness, product geometry, ports, pressure losses or accepted assembly')
    (out/'probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    result=run(parser.parse_args().out)
    print(json.dumps({k:result[k] for k in ('native_material_volume_m3','euler_characteristic','centre_through_bore_overlap_m3','filled_outer_negative_control_rejected','design_accepted')}))
