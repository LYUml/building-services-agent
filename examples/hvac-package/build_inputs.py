"""Create independent synthetic HVAC inputs; never a real equipment selection."""
import argparse
import json
from pathlib import Path
import ezdxf
from bsa.cli import digest
from bsa.air_load import UNITS
from bsa.workflow import validate_plan


def build(output):
    root=Path(output).resolve()
    if root.exists():raise ValueError('New example input directory required')
    root.mkdir(parents=True)
    def save(name,data):
        p=root/name;p.write_text(json.dumps(data,indent=2),encoding='utf-8');return p
    brief='Demonstrate synthetic airflow allocation, terminal lookup, duct sizing, saved native drawing and reporting; retain full engineering acceptance as pending.'
    (root/'brief.md').write_text(brief+'\n',encoding='utf-8')
    boundary=save('boundary.json',dict(type='Polygon',coordinates=[[[-8,-3],[0,-3],[0,3],[-8,3],[-8,-3]]]))
    terminals=[dict(id=tid,center_m=[x,y]) for tid,x,y in [('T1',-6,-1.5),('T2',-2,-1.5),('T3',-6,1.5),('T4',-2,1.5)]]
    values=dict(area=48,cooling_allowance=80,sensible_fraction=.85,density=1.2,specific_heat=1006,temperature_difference=10)
    save('allocation.json',dict(boundary=boundary.name,boundary_sha256=digest(boundary),geometry_basis='Synthetic 8 by 6 metre rectangle; equal-area partition assumption',terminals=terminals,
         load_inputs={k:dict(value=v,unit=UNITS[k],source='Independent synthetic demonstration assumption; not coursework or regulation',classification='assumed') for k,v in values.items()},turndown=.5))
    catalogue=save('catalogue.json',dict(basis='Fictional demonstration data; no manufacturer or product claim',rows=[dict(flow_L_s=20,T025_m=1),dict(flow_L_s=120,T025_m=4)]))
    save('lookup.json',dict(catalogue=catalogue.name,catalogue_sha256=digest(catalogue),basis='Synthetic interpolation exercise; assumed L=2 m, no ADPI acceptance',terminals=[dict(id=t['id'],characteristic_lengths_m=dict(east=2,west=2)) for t in terminals]))
    nodes=dict(ROOT=[-9,0,0],J=[-4,0,0],VA=[-4,-1.5,0],VB=[-4,1.5,0])
    edges=[dict(id=s,**{'from':a,'to':b}) for s,a,b in [('M','ROOT','J'),('A','J','VA'),('B','J','VB')]]
    tree=dict(root='ROOT',sections=edges,leaf_terminals=dict(VA=['T1','T2'],VB=['T3','T4']),basis='Synthetic three-section tree and two groups')
    save('ducts.json',dict(basis='Synthetic finite size grid and trial limits; not manufacturer selection',air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009),tree=tree,
         sections=[dict(id=e['id'],candidate_basis='Synthetic square/rectangular grid',candidates=[dict(id=f'{w}x{h}',width_m=w,height_m=h) for w,h in [(.15,.15),(.2,.2),(.25,.2),(.3,.25),(.4,.3)]],limits=dict(actual_velocity_m_s=5.5,friction_Pa_m=2,aspect_ratio=3)) for e in edges]))
    doc=ezdxf.new();doc.units=6;m=doc.modelspace()
    layers=dict(supply='DEMO_DUCT',vav='DEMO_VAV',terminal='DEMO_TERMINAL',flex='DEMO_FLEX')
    for layer in [*layers.values(),'DEMO_ROOM','DEMO_TEXT','DEMO_TABLE']:doc.layers.new(layer)
    def text(value,x,y,layer='DEMO_TEXT',height=.25):
        return m.add_text(value,dxfattribs=dict(insert=(x,y),height=height,layer=layer))
    m.add_lwpolyline([(-8,-3),(0,-3),(0,3),(-8,3)],close=True,dxfattribs=dict(layer='DEMO_ROOM'))
    text('SYNTHETIC HVAC WORKFLOW DEMONSTRATION',-8,8,height=.4)
    text('Fictional inputs and catalogue. Not an engineering design.',-8,7.2)
    text('Centreline diagram. Physical ports and installation remain unverified.',-8,6.6)
    bindings={};columns=[1,3.2,5.5,9.5,12.4]
    for x,value in zip(columns,['Section','L/s','Size mm','m/s','Pa/m']):text(value,x,5,'DEMO_TABLE')
    for i,e in enumerate(edges):
        a,b=nodes[e['from']],nodes[e['to']]
        line=m.add_line(a,b,dxfattribs=dict(layer=layers['supply']))
        cells=[text(value,x,4-i*.8,'DEMO_TABLE') for x,value in zip(columns,[e['id'],'pending','pending','pending','pending'])]
        bindings[e['id']]=dict(line_handle=line.dxf.handle,from_m=a,to_m=b,from_node=e['from'],to_node=e['to'],cells=[dict(handle=c.dxf.handle,expected_text=c.dxf.text) for c in cells])
        text(e['id'],(a[0]+b[0])/2+.15,(a[1]+b[1])/2+.15)
    centers={t['id']:t['center_m'] for t in terminals}
    for leaf,members in tree['leaf_terminals'].items():
        a=nodes[leaf];m.add_circle(a,.12,dxfattribs=dict(layer=layers['vav']));text(leaf,a[0]+.2,a[1]+.3)
        for tid in members:
            x,y=centers[tid]
            m.add_line(a,(x,y,0),dxfattribs=dict(layer=layers['flex']))
            m.add_lwpolyline([(x-.2,y-.2),(x+.2,y-.2),(x+.2,y+.2),(x-.2,y+.2)],close=True,dxfattribs=dict(layer=layers['terminal']))
            text(tid,x-.2,y+.35)
    ref=m.add_line((-8,-4),(2,-4),dxfattribs=dict(layer='DEMO_TABLE'))
    text('10 m reference = 100 mm at 1:100',-8,-4.6)
    source=root/'source.dxf';doc.saveas(source)
    save('binding.json',dict(source_sha256=digest(source),basis='Synthetic source entities with explicit node identity',sections=bindings))
    save('native.json',dict(layers=[*layers.values(),'DEMO_ROOM','DEMO_TEXT','DEMO_TABLE'],sheet=dict(source='Synthetic A4 demonstration',paper='A4',window_drawing_units=[-10,-5,16,10],scale_denominator=100,reference_handle=ref.dxf.handle,pdf_tolerance_mm=.2)))
    save('review.json',dict(native_task='native',layers=layers))
    tasks=[dict(id='allocation',kind='air_allocation',project='allocation.json'),dict(id='lookup',kind='terminal_throw',project='lookup.json',depends_on='allocation'),dict(id='ducts',kind='duct_schedule',project='ducts.json',depends_on='allocation'),dict(id='sheet',kind='duct_sheet',drawing='source.dxf',binding='binding.json',depends_on='ducts'),dict(id='native',kind='duct_sheet_native',settings='native.json',depends_on='sheet'),dict(id='engineering',kind='manual',description='Synthetic exercise; real sources, products, ADPI, installation, jurisdiction and engineering acceptance not established')]
    plan=save('plan.json',dict(version=1,brief='brief.md',brief_sha256=digest(root/'brief.md'),passage_dispositions={'P001':'requirement'},tasks=tasks,requirements=[dict(id='R'+str(i+1),passage='P001',quote=brief,task=t['id'],acceptance='Verify scoped evidence; full engineering acceptance remains pending') for i,t in enumerate(tasks)]))
    validate_plan(plan)
    return plan


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True)
    print(build(p.parse_args().out))
