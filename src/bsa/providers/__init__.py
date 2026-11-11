"""Trusted code registry;documents cannot supply import paths or commands."""


def get_provider(id):
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
