"""Declared four-outlet lined chamber candidate using native IFC CSG primitives.

The body combines metal and liner occupied volume. It is not a manufacturer
fabrication model, separate-material takeoff or a pressure-loss correlation.
"""
import math
import numpy as np
from ifcopenshell.util.shape_builder import ShapeBuilder
from .product_alignment import aligned_placement


def build(model, context, frame, *, width_m, height_m, length_m, metal_m,
          liner_m, collar_outside_diameter_m, projection_m, stations_m):
    values = (width_m, height_m, length_m, metal_m, liner_m,
              collar_outside_diameter_m, projection_m, *stations_m)
    if len(stations_m) != 2 or any(type(v) not in (int, float) or
            not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Explicit positive SI dimensions and two outlet stations required')
    f = np.asarray(frame, dtype=float)
    aligned_placement(f, np.eye(4), 0)
    t = metal_m+liner_m
    radius = collar_outside_diameter_m/2
    if min(width_m, height_m, length_m) <= 2*t or radius <= metal_m:
        raise ValueError('Positive chamber and collar bores required')
    if 2*radius >= height_m or not radius < stations_m[0] < stations_m[1] < length_m-radius:
        raise ValueError('Collar envelopes must remain within side panels')
    if stations_m[1]-stations_m[0] <= 2*radius:
        raise ValueError('Distinct nonintersecting outlet collars required')
    builder = ShapeBuilder(model)

    def extrude(profile, start, axis, reference, depth):
        return builder.extrude(profile, magnitude=depth,
            position=f[:3, 3]+f[:3, :3]@np.asarray(start),
            position_z_axis=f[:3, :3]@np.asarray(axis),
            position_x_axis=f[:3, :3]@np.asarray(reference))

    def box(w, h, start, depth):
        profile = model.create_entity('IfcRectangleProfileDef', ProfileType='AREA', XDim=w, YDim=h)
        return extrude(profile, start, (1., 0., 0.), (0., 1., 0.), depth)

    def circle(r, start, sign, depth):
        profile = model.create_entity('IfcCircleProfileDef', ProfileType='AREA', Radius=r)
        return extrude(profile, start, (0., sign, 0.), (1., 0., 0.), depth)

    def combine(items, operator):
        result = items[0]
        for item in items[1:]:
            result = model.create_entity('IfcBooleanResult', Operator=operator,
                FirstOperand=result, SecondOperand=item)
        return result

    # Overshoot is only a Boolean construction margin, not installed length.
    eps = .01
    outside = [box(width_m, height_m, (0., 0., 0.), length_m)]
    air = [box(width_m-2*t, height_m-2*t, (-eps, 0., 0.), length_m-t+eps)]
    for x in stations_m:
        for sign in (-1., 1.):
            start = (x, sign*(width_m/2-t-eps), 0.)
            outside.append(circle(radius, start, sign, projection_m+t+eps))
            air.append(circle(radius-metal_m, start, sign, projection_m+t+2*eps))
    body = combine([combine(outside, 'UNION'), combine(air, 'UNION')], 'DIFFERENCE')
    representation = model.create_entity('IfcShapeRepresentation', ContextOfItems=context,
        RepresentationIdentifier='Body', RepresentationType='CSG', Items=[body])
    return model.create_entity('IfcProductDefinitionShape', Representations=[representation])
