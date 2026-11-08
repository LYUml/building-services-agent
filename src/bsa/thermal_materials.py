"""Explicit opaque layer authoring and saved-OSM source reconciliation."""
import math
from .engine import ProjectError

ROLES=('exterior_wall','roof','floor','interzone')
ROUGHNESS={'VeryRough','Rough','MediumRough','MediumSmooth','Smooth','VerySmooth'}
COMMON={'name','source','type','roughness','thermal_absorptance','solar_absorptance','visible_absorptance'}
MASSIVE={'thickness_m':'Thickness','conductivity_w_mk':'Conductivity','density_kg_m3':'Density','specific_heat_j_kgk':'SpecificHeat'}
RESISTANCE={'resistance_m2k_w':'ThermalResistance'}
OPTICAL={'thermal_absorptance':'ThermalAbsorptance','solar_absorptance':'SolarAbsorptance','visible_absorptance':'VisibleAbsorptance'}
VALIDATION_BASIS=dict(engine='EnergyPlus 25.2.0-cf7368216c',file='Energy+.idd',sha256='5f71380fdeb7d2456dbfb71913b90c40f87e109051c62c44f08577451974f44f',objects=['Material','Material:NoMass'],scope='input syntax/ranges only; not measured material or regulatory applicability')


def validate(config):
    if not isinstance(config,dict) or set(config)!=set(ROLES):raise ProjectError('four explicit opaque construction roles required')
    for role,assembly in config.items():
        if not isinstance(assembly,dict) or set(assembly)!={'source','layers'} or not isinstance(assembly['source'],str) or not assembly['source'].strip():raise ProjectError('opaque construction source and layers required')
        layers=assembly['layers']
        if not isinstance(layers,list) or not 1<=len(layers)<=10:raise ProjectError('one to ten outside-to-inside opaque layers required')
        for layer in layers:
            if not isinstance(layer,dict) or layer.get('type') not in ('massive','resistance'):raise ProjectError('explicit massive or resistance opaque layer required')
            physical=MASSIVE if layer['type']=='massive' else RESISTANCE
            if set(layer)!=COMMON|set(physical):raise ProjectError('exact opaque material fields required')
            if any(not isinstance(layer[key],str) or not layer[key].strip() for key in ('name','source')) or not isinstance(layer['roughness'],str) or layer['roughness'] not in ROUGHNESS:raise ProjectError('opaque material name/source/roughness required')
            for key in set(physical)|set(OPTICAL):
                v=layer[key]
                if type(v) not in (int,float) or not math.isfinite(v):raise ProjectError('finite opaque material properties required')
                if key in physical and (v<=0 or key=='specific_heat_j_kgk' and v<100 or key=='resistance_m2k_w' and v<.001):raise ProjectError('invalid opaque material physical property')
                if key in OPTICAL and (not 0<=v<=1 or key=='thermal_absorptance' and not 0<v<=.99999):raise ProjectError('invalid opaque material absorptance')
        try:
            resistance=math.fsum(l['thickness_m']/l['conductivity_w_mk'] if l['type']=='massive' else l['resistance_m2k_w'] for l in layers)
            capacity=math.fsum(l['thickness_m']*l['density_kg_m3']*l['specific_heat_j_kgk'] for l in layers if l['type']=='massive')
            if not math.isfinite(resistance) or resistance<=0 or not math.isfinite(1/resistance) or not math.isfinite(capacity):raise ValueError()
        except (ValueError,OverflowError,ZeroDivisionError) as exc:raise ProjectError('nonfinite opaque assembly properties') from exc
    return config


def author(model,config):
    import openstudio as os
    validate(config);constructions={}
    for role,assembly in config.items():
        materials=[]
        for i,layer in enumerate(assembly['layers']):
            material=os.model.StandardOpaqueMaterial(model) if layer['type']=='massive' else os.model.MasslessOpaqueMaterial(model)
            material.setName(f'BSA {role} layer {i+1}')
            material.additionalProperties().setFeature('Source',layer['source'])
            material.additionalProperties().setFeature('InputName',layer['name'])
            physical=MASSIVE if layer['type']=='massive' else RESISTANCE
            if not material.setRoughness(layer['roughness']):raise ProjectError('SDK rejected material roughness')
            for key,suffix in {**physical,**OPTICAL}.items():
                if not getattr(material,'set'+suffix)(layer[key]):raise ProjectError('SDK rejected material property: '+key)
            materials.append(material)
        for reverse in ((False,True) if role=='interzone' else (False,)):
            construction=os.model.Construction(model);construction.setName('BSA '+role+(' reverse' if reverse else ''))
            construction.additionalProperties().setFeature('Source',assembly['source'])
            vector=os.model.MaterialVector()
            for material in reversed(materials) if reverse else materials:vector.append(material)
            if not construction.setLayers(vector):raise ProjectError('SDK rejected opaque layer assembly')
            constructions[(role,reverse)]=construction
    return constructions


def role_for(surface):
    if surface.outsideBoundaryCondition()=='Surface':
        peer=surface.adjacentSurface()
        if peer.empty():raise ProjectError('shared surface missing adjacent face')
        own=surface.space().get().thermalZone().get().nameString()
        other=peer.get().space().get().thermalZone().get().nameString()
        return 'interzone',own>other
    try:return {'Wall':'exterior_wall','RoofCeiling':'roof','Floor':'floor'}[surface.surfaceType()],False
    except KeyError as exc:raise ProjectError('unsupported opaque surface type') from exc


def assign(model,constructions):
    for surface in model.getSurfaces():
        if not surface.setConstruction(constructions[role_for(surface)]):raise ProjectError('SDK rejected surface construction')


def audit(model,config):
    """Compare every saved assigned layer to its source, including ordering."""
    validate(config);surface_rows=[];assemblies={}
    for role,assembly in config.items():
        layers=assembly['layers']
        resistance=math.fsum(l['thickness_m']/l['conductivity_w_mk'] if l['type']=='massive' else l['resistance_m2k_w'] for l in layers)
        capacity=math.fsum(l['thickness_m']*l['density_kg_m3']*l['specific_heat_j_kgk'] for l in layers if l['type']=='massive')
        assemblies[role]=dict(source=assembly['source'],layers=layers,layer_resistance_m2k_w=resistance,layer_conductance_w_m2k=1/resistance,areal_heat_capacity_j_m2k=capacity,scope='layers only; excludes surface films, thermal bridges and moisture')
    for surface in model.getSurfaces():
        role,reverse=role_for(surface);expected=config[role]['layers'][::-1] if reverse else config[role]['layers']
        saved=surface.construction()
        if saved.empty() or saved.get().to_Construction().empty():raise ProjectError('saved opaque construction missing')
        construction=saved.get().to_Construction().get()
        source=construction.additionalProperties().getFeatureAsString('Source')
        if source.empty() or source.get()!=config[role]['source']:raise ProjectError('saved construction provenance differs from source')
        if construction.numLayers()!=len(expected):raise ProjectError('saved opaque layer count differs from source')
        for material,layer in zip(construction.layers(),expected):
            actual=material.to_StandardOpaqueMaterial() if layer['type']=='massive' else material.to_MasslessOpaqueMaterial()
            if actual.empty():raise ProjectError('saved opaque material type differs from source')
            actual=actual.get();physical=MASSIVE if layer['type']=='massive' else RESISTANCE
            for feature,expected_value in (('Source',layer['source']),('InputName',layer['name'])):
                saved_value=actual.additionalProperties().getFeatureAsString(feature)
                if saved_value.empty() or saved_value.get()!=expected_value:raise ProjectError('saved material provenance differs from source')
            if actual.roughness()!=layer['roughness']:raise ProjectError('saved opaque roughness differs from source')
            for key,suffix in {**physical,**OPTICAL}.items():
                getter=suffix[0].lower()+suffix[1:]
                value=getattr(actual,getter)()
                if hasattr(value,'empty'):
                    if value.empty():raise ProjectError('saved opaque property missing: '+key)
                    value=value.get()
                if not math.isclose(value,layer[key],rel_tol=1e-9,abs_tol=1e-10):raise ProjectError('saved opaque property differs from source: '+key)
        surface_rows.append(dict(surface=surface.nameString(),zone=surface.space().get().thermalZone().get().nameString(),surface_type=surface.surfaceType(),boundary=surface.outsideBoundaryCondition(),area_m2=surface.grossArea(),net_opaque_area_m2=surface.netArea(),role=role,reversed_layers=reverse,construction=construction.nameString()))
    return dict(validation_basis=VALIDATION_BASIS,saved_layer_properties_match=True,assemblies=assemblies,surfaces=surface_rows,role_area_m2={role:math.fsum(s['area_m2'] for s in surface_rows if s['role']==role) for role in ROLES},role_net_opaque_area_m2={role:math.fsum(s['net_opaque_area_m2'] for s in surface_rows if s['role']==role) for role in ROLES},interzone_scope='original layer order assigned to lexically first zone; reversed on peer; pair areas counted twice')
