"""Exercise installed upstream transition geometry; research only, no duct wall claim."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.shape_builder as shape_builder
import numpy as np
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


def run(out,*,hollow_profile=False):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out==ROOT or out.exists():raise ValueError('New repository research output required')
    if importlib.metadata.version('ifcopenshell')!='0.8.5':raise ValueError('Pinned IfcOpenShell0.8.5 required')
    out.mkdir(parents=True)
    model=api.run('project.create_file',version='IFC4')
    api.run('root.create_entity',model,ifc_class='IfcProject',name='Synthetic upstream transition probe')
    unit=api.run('unit.add_si_unit',model,unit_type='LENGTHUNIT')
    api.run('unit.assign_unit',model,units=[unit])
    context=api.run('context.add_context',model,context_type='Model')
    api.run('context.add_context',model,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context)
    segments=[]
    for name,width,height in [('Synthetic start',.6,.3),('Synthetic end',.4,.2)]:
        segment=api.run('root.create_entity',model,ifc_class='IfcDuctSegment',name=name)
        profile=model.create_entity('IfcRectangleHollowProfileDef' if hollow_profile else 'IfcRectangleProfileDef',
                                    ProfileType='AREA',XDim=width,YDim=height,**({'WallThickness':.005} if hollow_profile else {}))
        item=model.create_entity('IfcMaterialProfile',Profile=profile)
        material=model.create_entity('IfcMaterialProfileSet',MaterialProfiles=[item])
        model.create_entity('IfcRelAssociatesMaterial',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[segment],RelatingMaterial=material)
        segments.append(segment)
    representation,parameters=shape_builder.ShapeBuilder(model).mep_transition_shape(*segments,.1,.1,angle=30,profile_offset=(0.,0.))
    if representation is None:raise ValueError('Upstream returned no transition representation')
    fitting=api.run('root.create_entity',model,ifc_class='IfcDuctFitting',predefined_type='TRANSITION',name='Synthetic transition surface probe')
    api.run('geometry.assign_representation',model,product=fitting,representation=representation)
    target=out/'transition-probe.ifc';model.write(str(target))
    saved=ifcopenshell.open(str(target));element=saved.by_guid(fitting.GlobalId)
    shape=ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(),element)
    vertices=np.asarray(shape.geometry.verts).reshape((-1,3))
    faces=np.asarray(shape.geometry.faces).reshape((-1,3))
    edges=np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True)
    triangles=vertices[faces]
    volume=abs(float(np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6))
    # Independent outer frustum expression for these similar centred rectangles.
    transition_length=parameters['transition_length']
    outer_volume=.1*.6*.3+.1*.4*.2+transition_length*(.6*.3+.4*.2+math.sqrt(.6*.3*.4*.2))/3
    report=dict(ifcopenshell_version='0.8.5',upstream='https://github.com/IfcOpenShell/IfcOpenShell',
                builder_sha256=digest(Path(shape_builder.__file__)),script_sha256=digest(Path(__file__)),
                synthetic_inputs=dict(start_profile_m=[.6,.3],end_profile_m=[.4,.2],start_length_m=.1,end_length_m=.1,angle_degrees=30),
                upstream_parameters={k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in parameters.items()},
                native_saved_geometry_executed=True,vertex_count=len(vertices),triangle_count=len(faces),
                boundary_edge_count=int(np.sum(counts==1)),nonmanifold_edge_count=int(np.sum(counts>2)),
                all_mesh_edges_have_two_faces=bool(np.all(counts==2)),
                bounds_m=[vertices.min(axis=0).tolist(),vertices.max(axis=0).tolist()],
                port_count=len(saved.by_type('IfcDistributionPort')),wall_thickness_supplied=hollow_profile,
                supplied_wall_thickness_m=.005 if hollow_profile else None,
                mesh_volume_m3=volume,independent_filled_envelope_volume_m3=outer_volume,
                matches_filled_outer_envelope=math.isclose(volume,outer_volume,rel_tol=1e-9,abs_tol=1e-10),
                ifc_sha256=digest(target),production_adapter=False,design_accepted=False,
                scope='Upstream transition representation probe only; no hollow wall material, physical ports, pressure loss, assembly or engineering acceptance')
    (out/'probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    parser.add_argument('--hollow-profile',action='store_true');args=parser.parse_args()
    report=run(args.out,hollow_profile=args.hollow_profile)
    print(json.dumps({k:report[k] for k in ('native_saved_geometry_executed','boundary_edge_count','port_count','matches_filled_outer_envelope','production_adapter','design_accepted')}))
