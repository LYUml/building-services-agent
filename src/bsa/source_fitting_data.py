"""Reuse source-linked bounded fitting tables on the complete represented native network."""
import argparse
import copy
import json
import importlib.metadata
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.system as system
import numpy as np
from . import source_network_analysis as analysis,duct_fitting_data as tables
from . import duct_transition_quantities as quantities
from . import duct_elbow_quantities as elbow_quantities
from . import transition_straight_friction
from .cli import digest
from .workspace import allowed


def native_case(model,case):
    """Canonical native profiles, not rounded mesh values or widened table bounds."""
    case=copy.deepcopy(case);products={p['guid']:p for p in case['products']};rho=case['air']['density_kg_m3']
    for obj in model.by_type('IfcDistributionElement'):
        body=obj.Representation.Representations[0].Items[0];canonical=False
        bend=None
        if obj.is_a('IfcDuctFitting') and obj.PredefinedType=='TRANSITION':
            owned=system.get_ports(obj);incoming=[p for p in owned if p.FlowDirection=='SINK'];outgoing=[p for p in owned if p.FlowDirection=='SOURCE']
            if len(incoming)!=1 or len(outgoing)!=1:raise ValueError('One native transition flow path required')
            products[obj.GlobalId]['transition_geometry']=quantities.calculate(obj,incoming[0].Name,outgoing[0].Name);canonical=True
        elif obj.is_a('IfcDuctFitting') and obj.PredefinedType=='BEND':
            owned=system.get_ports(obj);incoming=[p for p in owned if p.FlowDirection=='SINK'];outgoing=[p for p in owned if p.FlowDirection=='SOURCE']
            if len(incoming)!=1 or len(outgoing)!=1:raise ValueError('One native bend flow path required')
            bend=elbow_quantities.calculate(obj,incoming[0].Name,outgoing[0].Name,case['port_flows'][incoming[0].GlobalId]['flow_m3_s'],case['air']);products[obj.GlobalId]['elbow_geometry']=bend;canonical=True
        elif obj.is_a('IfcDuctFitting') and obj.PredefinedType=='JUNCTION' and body.is_a('IfcBooleanResult') and body.SecondOperand.is_a('IfcBooleanResult') and body.SecondOperand.FirstOperand.is_a('IfcExtrudedAreaSolid'):canonical=True
        if canonical:
            for port in system.get_ports(obj):
                w,h=bend['inlet_section_m'] if bend else analysis.local.section_at_port(obj,port);row=case['port_flows'][port.GlobalId]
                if not np.allclose([w,h],[row['width_m'],row['height_m']],atol=1e-8,rtol=0):raise ValueError('Native literal profiles differ from independently recovered material cap')
                velocity=row['flow_m3_s']/(w*h);row.update(width_m=w,height_m=h,actual_velocity_m_s=velocity,actual_velocity_pressure_Pa=rho*velocity**2/2,
                    fitting_query_geometry_basis='Exact saved local profile/ring dimensions checked against native mesh material caps; table bounds are not enlarged or snapped')
    return case


def evaluate(directory,basis):
    case=json.loads((directory/'analysis.json').read_text());source=Path(case['source']);model=ifcopenshell.open(str(source/'Supply Network.ifc'));case=native_case(model,case);data,pins=tables.prepare(basis);result=tables.calculate(model,case,data)
    result.update(original_requirement_ids=case['original_requirement_ids'],source_analysis=str(directory),source_basis=str(basis),original_analysis_unchanged=True,complete_network=False)
    result['transition_end_straight_study']=[transition_straight_friction.calculate(r,case['air'])
        for r in result['data_requests'] if r['transition_geometry'] is not None]
    return result,pins


def methods():
    import scipy.interpolate._rgi as rgi
    if importlib.metadata.version('scipy')!='1.18.1':raise ValueError('Pinned SciPy 1.18.1 required')
    return [Path(__file__),Path(analysis.__file__),Path(tables.__file__),Path(quantities.__file__),Path(elbow_quantities.__file__),Path(transition_straight_friction.__file__),Path(transition_straight_friction.duct_equivalent.__file__),Path(rgi.__file__)]


def run(directory,basis,out):
    directory,basis,out=[Path(p).resolve() for p in (directory,basis,out)]
    if not all(allowed(p) for p in (directory,basis,out)) or out.exists() or out.is_relative_to(directory) or directory.is_relative_to(out) or out==basis or out in basis.parents:raise ValueError('Fresh selected workspace outside immutable analysis/source required')
    analysis.verify(directory);_,source_pins=tables.prepare(basis);pins={str(p):digest(p) for p in [directory/'analysis.json',*methods()]}|source_pins;result,fresh=evaluate(directory,basis)
    if fresh!=source_pins or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Fitting data source/method changed')
    out.mkdir(parents=True);result['inputs']=pins;(out/'fitting-data.json').write_text(json.dumps(result,indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    record=json.loads((out/'fitting-data.json').read_text());directory=Path(record['source_analysis']);basis=Path(record['source_basis'])
    if not all(allowed(p) for p in (directory,basis)):raise ValueError('Selected source analysis/basis required')
    analysis.verify(directory);fresh,source_pins=evaluate(directory,basis);pins={str(p):digest(p) for p in [directory/'analysis.json',*methods()]}|source_pins
    if record['inputs']!=pins or any(record.get(k)!=v for k,v in fresh.items()):raise ValueError('Full-network fitting table/native replay differs')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Fitting data source changed during replay')
    return dict(integrity_pass=True,unique_fitting_paths=fresh['unique_fitting_paths'],calculated_table_paths=fresh['calculated_table_paths'],unsupplied_table_paths=fresh['unsupplied_table_paths'],pressure_budget_complete=False,design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('analysis');a.add_argument('basis');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.analysis,a.basis,a.out) if a.command=='run' else verify(a.out);print(json.dumps({k:r[k] for k in (('unique_fitting_paths','calculated_table_paths','unsupplied_table_paths','pressure_budget_complete','design_accepted') if a.command=='run' else r)},indent=2));raise SystemExit(2)
