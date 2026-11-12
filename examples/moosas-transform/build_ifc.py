"""Create an original synthetic saved IFC fixture using existing native adapters."""
import argparse
from pathlib import Path
from bsa.bim import run as author

ROOT=Path(__file__).resolve().parents[2]


def build(out):
    import ifcopenshell
    import ifcopenshell.api
    out=Path(out).resolve()
    if out.exists():raise ValueError('New native fixture directory required')
    author(ROOT/'examples/thermal-ifc/bim.json',out/'original-boxes')
    model=ifcopenshell.open(str(out/'original-boxes/model.ifc'))
    space=next(s for s in model.by_type('IfcSpace') if s.Name=='Office')
    body=next(r for r in space.Representation.Representations if r.RepresentationIdentifier=='Body')
    ring=[(0.,0.),(5.,0.),(5.,2.),(2.,2.),(2.,4.),(0.,4.),(0.,0.)]
    curve=model.create_entity('IfcPolyline',Points=[model.create_entity('IfcCartesianPoint',Coordinates=p) for p in ring])
    profile=model.create_entity('IfcArbitraryClosedProfileDef',ProfileType='AREA',OuterCurve=curve)
    axis=model.create_entity('IfcAxis2Placement3D',Location=model.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)))
    solid=model.create_entity('IfcExtrudedAreaSolid',SweptArea=profile,Position=axis,ExtrudedDirection=model.create_entity('IfcDirection',DirectionRatios=(0.,0.,1.)),Depth=3.)
    body.Items=(solid,);body.RepresentationType='SweptSolid'
    pset=ifcopenshell.api.run('pset.add_pset',model,product=space,name='BSA_DesignInputs')
    ifcopenshell.api.run('pset.edit_pset',model,pset=pset,properties=dict(GeometryScope='Explicit synthetic concave profile fixture;not the original box envelope',Source='Original14m2L-shaped room test declaration;not measured architecture'))
    path=out/'polygonal-spaces.ifc';model.write(str(path));return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    print(build(parser.parse_args().out))
