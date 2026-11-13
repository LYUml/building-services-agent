"""Human-readable component/port/path schedules from existing verified native analysis."""
import argparse
import html
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element as element
from . import source_fitting_data as fitting
from .cli import digest
from .workspace import allowed


def build_tables(case,data,identities,absorbed):
    products={p['guid']:p for p in case['products']}
    if len(products)!=len(case['products']) or set(products)!=set(identities):
        raise ValueError('Exact unique native component identity coverage required')
    tags={guid:f'N{i:03d}' for i,guid in enumerate(sorted(products),1)}
    straights={r['guid']:r for r in case['straight_sections']}
    end_studies={r['product_guid']:r for r in data.get('transition_end_straight_study',[])}
    ports=[];components=[];paths=[]
    for guid in sorted(products):
        owned=sorted([(key,row) for key,row in case['port_flows'].items() if row['owner_guid']==guid])
        incoming=math.fsum(r['flow_m3_s'] for _,r in owned if r['direction']=='SINK')
        outgoing=math.fsum(r['flow_m3_s'] for _,r in owned if r['direction']=='SOURCE')
        if not owned or not math.isclose(incoming,outgoing,rel_tol=1e-10,abs_tol=1e-12):
            raise ValueError('Owned component port coverage and flow continuity required')
        p=products[guid];straight=straights.get(guid);transition=p.get('transition_geometry');bend=p.get('elbow_geometry')
        length=straight['length_m'] if straight else transition['quantities']['total_length_m'] if transition else bend['quantities']['bend_centerline_arc_length_m'] if bend else None
        length_basis='saved extrusion' if straight else 'saved transition axial extent' if transition else 'saved circular Axis arc' if bend else 'no unique route length assigned'
        components.append(dict(tag=tags[guid],guid=guid,**identities[guid],port_count=len(owned),
            source_sections=sorted({r['source_section'] for _,r in owned}),
            inherited_inlet_design_flow_m3_s=incoming,model_path_length_m=length,model_length_basis=length_basis,
            separate_straight_friction_pa=straight['straight_friction_Pa'] if straight else None,
            separate_developed_end_study_pa=end_studies.get(guid,{}).get('developed_flow_study_friction_Pa')))
        for port,row in owned:
            ports.append(dict(component_tag=tags[guid],component_guid=guid,port_guid=port,direction=row['direction'],
                source_section=row['source_section'],source_node=row['source_node'],
                model_clear_width_m=row['width_m'],model_clear_height_m=row['height_m'],
                inherited_design_flow_m3_s=row['flow_m3_s'],flow_classification=row['classification'],
                calculated_velocity_m_s=row['actual_velocity_m_s'],calculated_velocity_pressure_pa=row['actual_velocity_pressure_Pa'],
                boundary=port in case['boundary_ports']))
    if len(ports)!=len(case['port_flows']):raise ValueError('Every native port must have exactly one scheduled owner')
    seen=set()
    for r in data['data_requests']:
        key=tuple(r[k] for k in ('product_guid','inlet_port_guid','outlet_port_guid'))
        if key in seen or key[0] not in tags or any(case['port_flows'][port]['owner_guid']!=key[0] for port in key[1:]):
            raise ValueError('Unique owned directed fitting path required')
        seen.add(key);value=r['recorded_table_result']
        paths.append(dict(component_tag=tags[key[0]],component_guid=key[0],inlet_port_guid=key[1],outlet_port_guid=key[2],
            status=r['status'],conditional_coefficient=value['coefficient'] if value else None,
            conditional_signed_contribution_pa=value['signed_tabulated_contribution_Pa'] if value else None,
            reference_port_guid=value['reference_port_guid'] if value else None,
            source_location=value['citation_location'] if value else None,
            applicability_note=value['applicability_note'] if value else None,
            required_evidence=r['required_evidence'],physical_applicability_verified=False))
    return dict(components=components,ports=ports,fitting_paths=paths,absorbed_source_sections=absorbed,
        internal_compound_source_flows=case.get('internal_compound_source_flows',[]),
        original_requirement_ids=case['original_requirement_ids'],pressure_budget_complete=False,design_accepted=False,
        scope='Saved model geometry and inherited design flows; source scale, nominal-clear-size, elevation, gauge and air assumptions remain. Separate conditional friction/table studies are not complete path pressure or fan duty.')


def render(data):
    def text(v):return html.escape('Pending' if v is None else format(v,'.6g') if isinstance(v,float) else str(v))
    def table(headers,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+text(h)+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+text(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table></div>'
    def kind(r):return r['predefined_type'] or {'IfcDuctSegment':'Duct segment','IfcDuctFitting':'Duct fitting'}.get(r['ifc_class'],r['ifc_class'])
    components=[[r['tag'],r['name'],', '.join(r['source_sections']),kind(r),r['port_count'],r['inherited_inlet_design_flow_m3_s'],r['model_path_length_m'],r['model_length_basis']] for r in data['components']]
    ports=[[r['component_tag'],r['port_guid'],r['source_section'],r['direction'],r['model_clear_width_m'],r['model_clear_height_m'],r['inherited_design_flow_m3_s'],r['calculated_velocity_m_s'],r['calculated_velocity_pressure_pa'],r['flow_classification']] for r in data['ports']]
    paths=[[r['component_tag'],r['inlet_port_guid'],r['outlet_port_guid'],r['reference_port_guid'],r['status'],r['conditional_coefficient'],r['conditional_signed_contribution_pa'],r['source_location']] for r in data['fitting_paths']]
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Supply Network Parameter Schedule</title><style>body{font:15px/1.5 Arial;color:#21343d;max-width:1300px;margin:30px auto;padding:20px}.notice{padding:16px;background:#fff2d5;border-left:5px solid #9a6500}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;border:1px solid #ccd5d9;text-align:left}th{background:#edf2f5}h2{margin-top:32px}</style><h1>Supply Network Parameter Schedule</h1><p class="notice">Source-model geometry and inherited preliminary design flows. Physical scale, nominal-clear-size interpretation, elevation, gauge and air conditions retain their recorded assumptions. Conditional numbers need applicability review; missing values stay pending. Complete pressure, fan duty and engineering acceptance remain unresolved.</p><p>'+str(len(data['components']))+' components; '+str(len(data['ports']))+' owned ports; '+str(len(data['fitting_paths']))+' directed fitting paths; '+str(len(data['original_requirement_ids']))+' original requirements retained.</p><p>Displayed numbers use six significant figures; the numerical schedule retains full precision.</p><p>Absorbed source sections retained as compound obligations: '+text(', '.join(data['absorbed_source_sections']))+'. Model GUIDs remain in the <a href="Network Parameter Schedule.json">source-linked numerical schedule</a>. N-tags are stable for this model identity set; drawing tag placement is a separate review.</p><h2 id="components">Components</h2>'+table(['Tag','Model name','Source sections','Type','Ports','Inherited inlet flow m3/s','Model length m','Length basis'],components)+'<h2 id="ports">Owned port parameters</h2>'+table(['Tag','Port model ID','Source section','Direction','Model width m','Model height m','Design flow m3/s','Calculated velocity m/s','Calculated velocity pressure Pa','Flow classification'],ports)+'<h2 id="fitting-paths">Directed fitting queries</h2><p>Signed table contributions preserve the actual reference port. Separate straight/end studies are kept in the numerical schedule and are not added here. Null values mean pending evidence, not zero loss.</p>'+table(['Tag','Inlet model ID','Outlet model ID','Reference model ID','Recorded status','Conditional K','Conditional signed Pa','Source location'],paths)+'</html>'


def evaluate(directory):
    data=json.loads((directory/'fitting-data.json').read_text());source=Path(data['source_analysis']);case=json.loads((source/'analysis.json').read_text())
    model_path=Path(case['source'])/'Supply Network.ifc';model=ifcopenshell.open(str(model_path));case=fitting.native_case(model,case)
    identities={o.GlobalId:dict(name=o.Name or '',ifc_class=o.is_a(),predefined_type=getattr(o,'PredefinedType',None),source_properties=element.get_psets(o)) for o in model.by_type('IfcDistributionElement')}
    network=Path(case['source'])/'network.json';absorbed=json.loads(network.read_text())['fit']['absorbed_straight_sections']
    return build_tables(case,data,identities,absorbed),{str(p):digest(p) for p in [directory/'fitting-data.json',source/'analysis.json',model_path,network,Path(__file__),Path(fitting.__file__)]}|data['inputs']


def run(directory,out):
    directory,out=Path(directory).resolve(),Path(out).resolve()
    if not allowed(directory) or not allowed(out) or out.exists() or out.is_relative_to(directory) or directory.is_relative_to(out):raise ValueError('Fresh selected schedule workspace outside immutable fitting analysis required')
    fitting.verify(directory);data,pins=evaluate(directory)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Schedule source changed')
    out.mkdir(parents=True);(out/'Network Parameter Schedule.json').write_text(json.dumps(data,indent=2));(out/'index.html').write_text(render(data),encoding='utf-8')
    record=dict(source_fitting_analysis=str(directory),inputs=pins,artifacts={p.name:digest(p) for p in out.iterdir() if p.is_file()},design_accepted=False)
    (out/'schedule.json').write_text(json.dumps(record,indent=2));return data


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected schedule workspace required')
    record=json.loads((out/'schedule.json').read_text());source=Path(record['source_fitting_analysis'])
    if not allowed(source):raise ValueError('Host-selected fitting analysis required')
    fitting.verify(source);data,pins=evaluate(source)
    if record['inputs']!=pins or set(record['artifacts'])!={'Network Parameter Schedule.json','index.html'}:raise ValueError('Schedule source or artifact coverage differs')
    if any(digest(out/name)!=sha for name,sha in record['artifacts'].items()) or data!=json.loads((out/'Network Parameter Schedule.json').read_text()) or render(data)!=(out/'index.html').read_text(encoding='utf-8'):
        raise ValueError('Source-reconstructed schedule differs')
    return dict(integrity_pass=True,components=len(data['components']),ports=len(data['ports']),fitting_paths=len(data['fitting_paths']),design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.out) if a.command=='run' else verify(a.out)
    summary=dict(components=len(r['components']),ports=len(r['ports']),fitting_paths=len(r['fitting_paths']),design_accepted=False) if a.command=='run' else r
    print(json.dumps(summary,indent=2));raise SystemExit(2)
