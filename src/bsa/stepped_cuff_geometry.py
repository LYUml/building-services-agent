"""Nominal stepped sleeve and two bondline proxies; no fabrication approval."""
import math


def build(model, context, *, upstream_outside_diameter_m,
          downstream_outside_diameter_m, half_length_m, minimum_wall_m,
          assumed_bondline_m):
    vals = (upstream_outside_diameter_m, downstream_outside_diameter_m,
            half_length_m, minimum_wall_m, assumed_bondline_m)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in vals):
        raise ValueError('Explicit finite positive SI sleeve dimensions required')
    a, b = upstream_outside_diameter_m/2, downstream_outside_diameter_m/2
    if not a < b or half_length_m <= max(minimum_wall_m, assumed_bondline_m):
        raise ValueError('Increasing outside step and finite overlap required')
    f, wall, lap = assumed_bondline_m, minimum_wall_m, half_length_m
    outside = b+f+wall

    def representation(polygons):
        solids = []
        for polygon in polygons:
            pts = [model.create_entity('IfcCartesianPoint', Coordinates=(float(r), float(z)))
                   for r, z in [*polygon, polygon[0]]]
            curve = model.create_entity('IfcPolyline', Points=pts)
            profile = model.create_entity('IfcArbitraryClosedProfileDef', ProfileType='AREA', OuterCurve=curve)
            pos = model.create_entity('IfcAxis2Placement3D',
                Location=model.create_entity('IfcCartesianPoint', Coordinates=(0., 0., 0.)))
            axis = model.create_entity('IfcAxis1Placement',
                Location=model.create_entity('IfcCartesianPoint', Coordinates=(0., 0., 0.)),
                Axis=model.create_entity('IfcDirection', DirectionRatios=(0., 1., 0.)))
            solids.append(model.create_entity('IfcRevolvedAreaSolid', SweptArea=profile,
                Position=pos, Axis=axis, Angle=2*math.pi))
        rep = model.create_entity('IfcShapeRepresentation', ContextOfItems=context,
            RepresentationIdentifier='Body', RepresentationType='SweptSolid', Items=solids)
        return model.create_entity('IfcProductDefinitionShape', Representations=[rep])

    sleeve = representation([[(a+f, -lap), (outside, -lap), (outside, lap),
        (b+f, lap), (b+f, 0.), (a+f, 0.)]])
    bondlines = representation([[(a, -lap), (a+f, -lap), (a+f, 0.), (a, 0.)],
        [(b, 0.), (b+f, 0.), (b+f, lap), (b, lap)]])
    return sleeve, bondlines
