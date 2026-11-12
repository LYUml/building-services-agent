"""Trusted code registry;documents cannot supply import paths or commands."""


def get_provider(id):
    if id=='fluids.native-stub-friction':
        from . import stub_friction
        return stub_friction
    if id=='ifcopenshell.polygon-spaces':
        from . import ifc_polygon_spaces
        return ifc_polygon_spaces
    if id=='moosas.ifc-room-recognition':
        from . import moosas_ifc_recognition
        return moosas_ifc_recognition
    if id=='moosas.surface-room-recognition':
        from . import moosas_recognition
        return moosas_recognition
    if id=='bsa.classified-air-allocation':
        from . import air_allocation
        return air_allocation
    if id=='bsa.source-requirements':
        from . import requirements
        return requirements
    if id=='bsa.electrical-path-rules':
        from . import electrical_rules
        return electrical_rules
    if id=='bsa.single-phase-circuits':
        from . import electrical_circuits
        return electrical_circuits
    if id=='bsa.hvac-water-rules':
        from . import water_rules
        return water_rules
    if id=='wntr.ifc-steady':
        from . import epanet_ifc_water
        return epanet_ifc_water
    if id=='wntr.epanet-steady':
        from . import epanet_water
        return epanet_water
    if id=='fluids.rectangular-ifc-budget':
        from . import rectangular_ifc_air
        return rectangular_ifc_air
    if id=='fluids.rectangular-air-budget':
        from . import rectangular_air
        return rectangular_air
    if id=='ifcopenshell.bim-authoring':
        from . import ifc_authoring
        return ifc_authoring
    if id=='ifcopenshell.box-spaces':
        from . import ifc_boxes
        return ifc_boxes
    if id=='moosas.box-space-exchange':
        from . import moosas_exchange
        return moosas_exchange
    raise ValueError('Unknown registered module provider: '+str(id))
