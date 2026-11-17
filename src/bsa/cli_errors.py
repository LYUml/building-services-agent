"""Actionable setup hints for known missing imports, without installing anything."""
EXTRAS={
    'rectpack':'drawing-layout','textalloc':'drawing-labels',
    'ifcopenshell':'bim','openstudio':'energy','fluids':'network',
    'shapely':'spatial','trimesh':'section','mcp':'mcp','PIL':'mcp',
    'reportlab':'reports','pypdf':'drawing','jsonschema':'modules',
    'tomlkit':'codex-setup',
}


def missing_dependency(error):
    name=error.name
    extra=EXTRAS.get(name)
    message='Required Python module is unavailable: '+(name or str(error))+'.'
    if extra:
        message+=f' Install the {extra} extra in the same environment: python -m pip install -e ".[{extra}]".'
        message+=' Then run bsa doctor --extra '+extra+'.'
    elif name=='ezdxf':message+=' Install this checkout in the same environment: python -m pip install -e .'
    else:message+=' Check the selected adapter runtime requirements; no installation profile was inferred.'
    return dict(message=message,missing_module=name,suggested_extra=extra)
