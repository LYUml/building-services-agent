import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.spatial_air_allocation import prepare,verify as verify_allocation
from bsa.spatial_air_balance import prepare as balance_spaces
from tests import test_spatial_air_balance as balance_fixtures

ROOT=Path(__file__).resolve().parents[1]


class SpatialAirAllocationTests(unittest.TestCase):
    def setUp(self):
        fixture=balance_fixtures.SpatialAirBalanceTests();fixture.setUp();self.producer=fixture.producer
        self.balance={'calculation':balance_spaces(fixture.producer,fixture.basis)}
        self.basis={'Room':dict(terminals=[dict(id='A',center_m=[1,3],unit='m',classification='design_choice',source='Explicit synthetic point choice')],turndown=dict(value=.4,unit='1',classification='assumed',source='Synthetic ratio'))}

    def test_single_terminal_inherits_maximum_minimum_and_source_classifications(self):
        r=prepare(self.balance,self.producer,self.basis);row=r['rooms']['Room']['allocation']['terminals'][0]
        self.assertEqual(row['maximum_flow_L_s'],self.balance['calculation']['totals']['supply_flow_L_s'])
        self.assertAlmostEqual(row['minimum_flow_L_s'],float(Decimal(str(row['maximum_flow_L_s']))*Decimal('.4')),places=12)
        self.assertEqual(r['rooms']['Room']['design_basis']['terminals'][0]['classification'],'design_choice')
        self.assertEqual(r['rooms']['Room']['design_basis']['turndown']['classification'],'assumed')
        self.assertFalse(r['ADPI_verified']);self.assertFalse(r['installed_geometry_verified'])

    def test_area_flow_overrides_unknown_sources_and_outside_point_reject(self):
        for kind in ('flow','source','point','unit','turndown'):
            changed=copy.deepcopy(self.basis)
            if kind=='flow':changed['Room']['maximum_flow_L_s']=100
            elif kind=='source':changed['Room']['terminals'][0]['source']=''
            elif kind=='point':changed['Room']['terminals'][0]['center_m']=[4,3]
            elif kind=='unit':changed['Room']['terminals'][0]['unit']='mm'
            else:changed['Room']['turndown']['value']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):prepare(self.balance,self.producer,changed)

    def test_multiple_terminals_conserve_full_room_flow_and_area(self):
        self.basis['Room']['terminals'].append(dict(self.basis['Room']['terminals'][0],id='B',center_m=[4,1]))
        r=prepare(self.balance,self.producer,self.basis)['rooms']['Room']['allocation']
        self.assertAlmostEqual(sum(t['maximum_flow_L_s'] for t in r['terminals']),self.balance['calculation']['totals']['supply_flow_L_s'])
        self.assertAlmostEqual(sum(t['allocated_load_area_m2'] for t in r['terminals']),14)
        self.assertEqual(r['allocation']['uncovered_area_m2'],0)


class SpatialAirAllocationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        source=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](cls.root/'source')
        cls.plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](cls.root/'inputs',ifc_source=source,tolerances=dict(length_tolerance_m=1e-6,area_tolerance_m2=1e-8),air_balance=True,terminal_allocation=True)
        # Only a synthetic source-hash/dispatch control,not official source bytes.
        pdf=cls.plan.parent/'sources/emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC RULE SOURCE CONTROL')
        pack=cls.plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(pdf);pack.write_text(json.dumps(data))

    def execute(self,name,**kwargs):
        out=self.root/name;r=execute(self.plan,out,**kwargs);self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out);return r,out

    def test_whole_model_handoff_and_disabled_gates(self):
        r,out=self.execute('native',module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        self.assertEqual(r['tasks']['terminal-allocation']['status'],'pass');self.assertEqual(r['tasks']['review']['status'],'pending')
        a=verify_allocation(out/'terminal-allocation')['calculation'];self.assertEqual(a['terminal_count'],3);self.assertAlmostEqual(a['maximum_flow_L_s'],870.4);self.assertAlmostEqual(a['minimum_flow_L_s'],348.16)
        disabled,folder=self.execute('disabled',module_providers={'recognition':'ifcopenshell.polygon-spaces'},disabled_module_providers=['ifcopenshell.polygon-spaces'])
        self.assertEqual(disabled['tasks']['terminal-allocation']['status'],'pending');self.assertEqual(disabled['tasks']['independent-electrical']['status'],'pass')
        self.assertFalse((folder/'terminal-allocation/terminal-allocation.json').exists())

    def test_rewritten_terminal_flow_rejects_replay(self):
        _,out=self.execute('mutated',module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        path=out/'terminal-allocation/terminal-allocation.json';data=json.loads(path.read_text());room=next(iter(data['calculation']['rooms'].values()));room['allocation']['terminals'][0]['maximum_flow_L_s']+=1;path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'source replay'):verify_allocation(out/'terminal-allocation')

    @unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit MOOSAS runtime required')
    def test_provider_replacement_preserves_all_terminal_allocations(self):
        _,native=self.execute('comparison-native',module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        _,moosas=self.execute('comparison-moosas',module_runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps'))
        self.assertEqual(verify_allocation(native/'terminal-allocation')['calculation'],verify_allocation(moosas/'terminal-allocation')['calculation'])
