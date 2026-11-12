"""Explicit typed IFC4 scenario properties using the existing IfcOpenShell API."""
import math
from .engine import ProjectError

CONTRACTS={
    'power_kw':('IfcPowerMeasure',('SI','POWERUNIT','WATT','KILO')),
    'voltage':('IfcElectricVoltageMeasure',('SI','ELECTRICVOLTAGEUNIT','VOLT',None)),
    'current':('IfcElectricCurrentMeasure',('SI','ELECTRICCURRENTUNIT','AMPERE',None)),
    'pressure':('IfcPressureMeasure',('SI','PRESSUREUNIT','PASCAL',None)),
    'flow':('IfcVolumetricFlowRateMeasure',('DERIVED','VOLUMETRICFLOWRATEUNIT',((('SI','LENGTHUNIT','METRE',None),3),(('SI','TIMEUNIT','SECOND',None),-1)))),
    'ratio':('IfcRatioMeasure',None),'text':('IfcText',None),'identifier':('IfcIdentifier',None)}


def unit_signature(unit):
    if unit is None:return None
    if unit.is_a('IfcSIUnit'):return ('SI',unit.UnitType,unit.Name,unit.Prefix)
    if unit.is_a('IfcDerivedUnit'):return ('DERIVED',unit.UnitType,tuple(sorted((unit_signature(e.Unit),e.Exponent) for e in unit.Elements)))
    raise ProjectError('Explicit supported SI scenario unit required')


def inspect(model,obj,name,records):
    sets=[r.RelatingPropertyDefinition for r in obj.IsDefinedBy if r.is_a('IfcRelDefinesByProperties') and r.RelatingPropertyDefinition.is_a('IfcPropertySet') and r.RelatingPropertyDefinition.Name==name]
    if len(sets)!=1:raise ProjectError('Exactly one typed scenario property set required')
    props=sets[0].HasProperties
    if len(props)!=len(records) or {p.Name for p in props}!=set(records):raise ProjectError('Scenario property coverage differs')
    for prop in props:
        expected,kind=records[prop.Name];datatype,unit=CONTRACTS[kind]
        if not prop.is_a('IfcPropertySingleValue') or prop.NominalValue is None or prop.NominalValue.is_a()!=datatype or unit_signature(prop.Unit)!=unit:
            raise ProjectError('Scenario measure type or explicit unit differs: '+prop.Name)
        actual=prop.NominalValue.wrappedValue
        if isinstance(expected,str):equal=actual==expected
        else:equal=type(actual) in (int,float) and math.isfinite(actual) and math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-12)
        if not equal:raise ProjectError('Scenario property value differs: '+prop.Name)
    return dict(property_count=len(props),typed_values_pass=True,explicit_units_pass=True)


def add(model,obj,name,records):
    import ifcopenshell.api as api
    for val,kind in records.values():
        if kind not in CONTRACTS or (kind in ('text','identifier') and not isinstance(val,str)) or (kind not in ('text','identifier') and (type(val) not in (int,float) or not math.isfinite(val))):raise ProjectError('Finite typed scenario property required')
    if any(r.RelatingPropertyDefinition.Name==name for r in obj.IsDefinedBy if r.is_a('IfcRelDefinesByProperties')):raise ProjectError('Scenario namespace already exists; preserve original properties')
    units={kind:model.create_entity('IfcSIUnit',UnitType=signature[1],Name=signature[2],Prefix=signature[3]) for kind,(_,signature) in CONTRACTS.items() if signature is not None and signature[0]=='SI'}
    metre=model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Name='METRE');second=model.create_entity('IfcSIUnit',UnitType='TIMEUNIT',Name='SECOND')
    units['flow']=model.create_entity('IfcDerivedUnit',Elements=[model.create_entity('IfcDerivedUnitElement',Unit=metre,Exponent=3),model.create_entity('IfcDerivedUnitElement',Unit=second,Exponent=-1)],UnitType='VOLUMETRICFLOWRATEUNIT')
    pset=api.run('pset.add_pset',model,product=obj,name=name)
    api.run('pset.edit_pset',model,pset=pset,properties={key:model.create_entity(CONTRACTS[kind][0],val) for key,(val,kind) in records.items()})
    for prop in pset.HasProperties:prop.Unit=units.get(records[prop.Name][1])
    inspect(model,obj,name,records)
    return pset
