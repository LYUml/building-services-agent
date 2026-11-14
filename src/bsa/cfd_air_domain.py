"""Export supported saved native duct air solids for an external CFD mesher.

Only source-native difference solids and sharp hollow rectangular swept profiles
are supported. This does not mesh, solve or accept a pressure-loss model.
"""
import math
import ifcopenshell.geom
from ifcopenshell.util import unit


def air_item(model, solid):
    lengths = [u for assignment in model.by_type('IfcUnitAssignment')
               for u in assignment.Units if getattr(u, 'UnitType', None) == 'LENGTHUNIT']
    if (model.schema != 'IFC4' or len(lengths) != 1
            or not lengths[0].is_a('IfcSIUnit') or lengths[0].Name != 'METRE'
            or lengths[0].Prefix is not None
            or not math.isclose(unit.calculate_unit_scale(model), 1., abs_tol=1e-12, rel_tol=0)):
        raise ValueError('Explicit metre IFC4 source required')
    if solid.is_a('IfcBooleanResult') and solid.Operator == 'DIFFERENCE':
        # Void operands may overshoot end caps for wall construction. Clip them
        # to the actual outside envelope before exporting a closed fluid solid.
        return model.create_entity('IfcBooleanResult', Operator='INTERSECTION',
            FirstOperand=solid.SecondOperand, SecondOperand=solid.FirstOperand)
    if not (solid.is_a('IfcExtrudedAreaSolid') or solid.is_a('IfcRevolvedAreaSolid')):
        raise ValueError('Unsupported source duct air primitive')
    if solid.is_a('IfcRevolvedAreaSolid'):
        angles = [u for assignment in model.by_type('IfcUnitAssignment')
                  for u in assignment.Units if getattr(u, 'UnitType', None) == 'PLANEANGLEUNIT']
        if len(angles) != 1 or not angles[0].is_a('IfcSIUnit') or angles[0].Name != 'RADIAN' or angles[0].Prefix is not None:
            raise ValueError('Explicit unscaled radian source revolution required')
        if not math.isfinite(solid.Angle) or not 0 < solid.Angle <= 2*math.pi:
            raise ValueError('Positive finite source revolution up to one turn required')
    elif not math.isfinite(solid.Depth) or solid.Depth <= 0:
        raise ValueError('Positive finite source extrusion depth required')
    p = solid.SweptArea
    if not p.is_a('IfcRectangleHollowProfileDef') or any(
            v not in (None, 0) for v in (p.InnerFilletRadius, p.OuterFilletRadius)):
        raise ValueError('Explicit sharp hollow rectangular profile required')
    w, h = p.XDim-2*p.WallThickness, p.YDim-2*p.WallThickness
    if not all(math.isfinite(v) and v > 0 for v in (w, h, p.WallThickness)):
        raise ValueError('Finite positive source bore and wall required')
    profile = model.create_entity('IfcRectangleProfileDef', ProfileType='AREA',
        Position=p.Position, XDim=w, YDim=h)
    if solid.is_a('IfcExtrudedAreaSolid'):
        return model.create_entity('IfcExtrudedAreaSolid', SweptArea=profile,
            Position=solid.Position, ExtrudedDirection=solid.ExtrudedDirection, Depth=solid.Depth)
    return model.create_entity('IfcRevolvedAreaSolid', SweptArea=profile,
        Position=solid.Position, Axis=solid.Axis, Angle=solid.Angle)


def serialized_brep(model, product):
    """Use a scratch file: only its in-memory representation is replaced."""
    bodies = [r for r in product.Representation.Representations if r.RepresentationIdentifier == 'Body']
    if len(bodies) != 1 or len(bodies[0].Items) != 1:
        raise ValueError('One source-native body item required')
    air = air_item(model, bodies[0].Items[0])
    rep = model.create_entity('IfcShapeRepresentation', ContextOfItems=bodies[0].ContextOfItems,
        RepresentationIdentifier='Body', RepresentationType='CSG' if air.is_a('IfcBooleanResult') else 'SweptSolid',
        Items=[air])
    product.Representation = model.create_entity('IfcProductDefinitionShape', Representations=[rep])
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    settings.set('iterator-output', ifcopenshell.ifcopenshell_wrapper.SERIALIZED)
    shape = ifcopenshell.geom.create_shape(settings, product)
    return shape.geometry.brep_data
