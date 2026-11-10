import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from shapely.geometry import box,mapping
from bsa.air_load import UNITS
from bsa.cli import digest
from bsa.workflow import execute,verify,validate_plan
from bsa.engine import ProjectError

class AllocationLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        boundary=self.root/'boundary.json';boundary.write_text(json.dumps(mapping(box(0,0,10,4))))
        brief=self.root/'brief.md';brief.write_text('Allocate and look up terminal throws.\n')
        catalogue=self.root/'catalogue.json';catalogue.write_text(json.dumps(dict(rows=[dict(flow_L_s=1,T025_m=1),dict(flow_L_s=2000,T025_m=8)])))
        values=dict(area=100,cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
        self.allocation=dict(boundary='boundary.json',boundary_sha256=digest(boundary),geometry_basis='Synthetic metres',terminals=[dict(id='A',center_m=[1,2]),dict(id='B',center_m=[5,2])],load_inputs={k:dict(value=v,unit=UNITS[k],source='Synthetic assumption',classification='assumed') for k,v in values.items()},turndown=.4)
        self.lookup=dict(catalogue='catalogue.json',catalogue_sha256=digest(catalogue),basis='Synthetic lookup; not ADPI',terminals=[dict(id=k,characteristic_lengths_m=dict(east=2)) for k in ('A','B')])
        self.plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[dict(id='allocation',kind='air_allocation',project='allocation.json'),dict(id='lookup',kind='terminal_throw',project='lookup.json',depends_on='allocation')],requirements=[dict(id='R'+str(i),passage='P001',quote='Allocate and look up terminal throws.',task=t,acceptance='Numerical result only; design review pending') for i,t in enumerate(('allocation','lookup'))])
    def run_plan(self,name):
        for filename,data in [('allocation.json',self.allocation),('lookup.json',self.lookup),('plan.json',self.plan)]:
            (self.root/filename).write_text(json.dumps(data))
        return execute(self.root/'plan.json',self.root/name)
    def test_layout_changes_propagate_without_replacement_flows(self):
        for right,fraction in [(5,.3),(7,.4)]:
            self.allocation['terminals'][1]['center_m']=[right,2]
            r=self.run_plan(str(right));self.assertEqual(r['tasks']['lookup']['status'],'pass')
            folder=self.root/str(right)
            result=json.loads((folder/'lookup/terminal-results.json').read_text())
            cases=result['terminals'][0]['directions']['east']['cases']
            self.assertAlmostEqual(cases['maximum']['flow_L_s'],1280*fraction)
            self.assertAlmostEqual(cases['minimum']['flow_L_s'],1280*fraction*.4)
            self.assertIn(str(folder/'allocation/allocation.json'),result['inputs'])
            self.assertTrue(verify(folder)['integrity_pass'])
            self.assertFalse(r['design_accepted'])
    def test_failed_source_blocks_lookup_and_replacement_is_rejected(self):
        self.allocation['terminals'][1]['center_m']=[50,2]
        r=self.run_plan('bad');self.assertEqual(r['tasks']['lookup']['status'],'pending')
        self.assertFalse((self.root/'bad/lookup').exists())
        self.allocation['terminals'][1]['center_m']=[5,2]
        self.lookup['turndown']=.5
        r=self.run_plan('override');self.assertEqual(r['tasks']['lookup']['status'],'fail')
        self.assertIn('cannot be overridden',r['tasks']['lookup']['scope'])
        del self.lookup['turndown'];self.lookup['terminals'][0]['id']='missing'
        r=self.run_plan('identity');self.assertEqual(r['tasks']['lookup']['status'],'fail')
        self.assertIn('identities',r['tasks']['lookup']['scope'])
    def test_changed_producer_rejected_before_lookup_output(self):
        from bsa.terminal_throw import run as original
        def tamper(*args,**kwargs):
            kwargs['allocation_path'].write_text('{}')
            return original(*args,**kwargs)
        with patch('bsa.terminal_throw.run',side_effect=tamper):r=self.run_plan('tamper')
        self.assertEqual(r['tasks']['lookup']['status'],'fail')
        self.assertIn('hash mismatch',r['tasks']['lookup']['scope'])
        self.assertFalse((self.root/'tamper/lookup').exists())

