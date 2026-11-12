import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.air_load import UNITS
from bsa.spatial_air_balance import prepare,verify as verify_balance
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context

ROOT=Path(__file__).resolve().parents[1]


class SpatialAirBalanceTests(unittest.TestCase):
    def setUp(self):
        frame=dict(id='synthetic',kind='source-world-si',length_unit='m',georeferenced=False)
        self.producer=dict(execution=dict(status='completed'),payload_schema='bsa.spatial-polygons/1',payload=dict(schema='bsa.spatial-polygons/1',coordinate_frame=frame,units=dict(length='m',area='m2'),point_grid_m=None,source_geometry_matches=True,simulation_ready=False,design_accepted=False,spaces=[dict(id='Room',recognized_id='native',boundary_vertices=[[0,0],[5,0],[5,2],[2,2],[2,4],[0,4],[0,0]],floor_area_m2=14,height_m=3,floor_elevation_m=0)]))
        values=dict(cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
        self.basis={'Room':{k:dict(value=v,unit=UNITS[k],classification='assumed',source='Explicit synthetic numerical control') for k,v in values.items()}}

    def test_source_area_and_independent_decimal_balance(self):
        r=prepare(self.producer,self.basis);room=r['room_balances']['Room']
        expected=Decimal(14)*Decimal(200)*Decimal('.8')/(Decimal('1.25')*Decimal(1000)*Decimal(10))*1000
        self.assertAlmostEqual(room['supply_flow_L_s'],float(expected),places=12)
        self.assertEqual(room['inputs']['area']['classification'],'geometry-derived')
        self.assertEqual(room['inputs']['area']['value'],14)
        self.assertFalse(r['room_sensible_load_verified']);self.assertFalse(r['simulation_executed']);self.assertFalse(r['design_accepted'])
        self.assertNotIn('area',self.basis['Room'])

    def test_replacement_area_missing_space_and_nonarea_geometry_class_reject(self):
        with self.assertRaisesRegex(ValueError,'every source space'):prepare(self.producer,{})
        changed=copy.deepcopy(self.basis);changed['Room']['area']=dict(value=1000,unit='m2',classification='given',source='Replacement')
        with self.assertRaisesRegex(ValueError,'replacement area'):prepare(self.producer,changed)
        changed=copy.deepcopy(self.basis);changed['Room']['density']['classification']='geometry-derived'
        with self.assertRaises(ValueError):prepare(self.producer,changed)

    def test_unexecuted_geometry_and_wrong_flow_units_reject(self):
        self.producer['execution']['status']='unavailable'
        with self.assertRaisesRegex(ValueError,'Completed'):prepare(self.producer,self.basis)
        self.producer['execution']['status']='completed';self.basis['Room']['temperature_difference']['unit']='degC absolute'
        with self.assertRaises(ValueError):prepare(self.producer,self.basis)


class SpatialAirBalanceWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        source=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](cls.root/'source')
        cls.plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](cls.root/'inputs',ifc_source=source,tolerances=dict(length_tolerance_m=1e-6,area_tolerance_m2=1e-8),air_balance=True)
        # Source hashing control only;not official code bytes.
        pdf=cls.plan.parent/'sources/emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC RULE SOURCE CONTROL')
        pack=cls.plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(pdf);pack.write_text(json.dumps(data))

    def execute(self,name,**kwargs):
        out=self.root/name;r=execute(self.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},**kwargs)
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        return r,out

    def test_native_inheritance_units_totals_and_pending_acceptance(self):
        r,out=self.execute('native')
        self.assertEqual(r['tasks']['air-balance']['status'],'pass');self.assertEqual(r['tasks']['review']['status'],'pending')
        report=verify_balance(out/'air-balance');calculation=report['calculation']
        self.assertEqual(calculation['units']['power'],'kW thermal')
        self.assertAlmostEqual(calculation['totals']['supply_flow_L_s'],870.4,places=10)
        self.assertEqual(calculation['totals']['total_cooling_kW_thermal'],13.6)
        self.assertEqual(len(r['requirements']),5);self.assertFalse(calculation['room_sensible_load_verified'])

    def test_disabled_geometry_gates_air_balance_only(self):
        r,out=self.execute('disabled',disabled_module_providers=['ifcopenshell.polygon-spaces'])
        self.assertEqual(r['tasks']['air-balance']['status'],'pending');self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')
        self.assertFalse((out/'air-balance/air-balance.json').exists())

    def test_air_balance_external_project_requires_host_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder).resolve();shutil.copytree(self.plan.parent,project/'inputs')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(project)}):
                out=project/'workflow';plan=project/'inputs/plan.json'
                r=execute(plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'})
                self.assertEqual(r['tasks']['air-balance']['status'],'pass');context(plan,out);verify_balance(out/'air-balance')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaisesRegex(ValueError,'selected workspace'):verify_balance(out/'air-balance')

    def test_stripped_method_pins_and_rewritten_totals_reject(self):
        _,out=self.execute('tampered');path=out/'air-balance/air-balance.json';original=json.loads(path.read_text())
        changed=copy.deepcopy(original);changed['inputs'].pop(str(ROOT/'src/bsa/air_load.py'));path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'Complete'):verify_balance(out/'air-balance')
        changed=copy.deepcopy(original);changed['calculation']['totals']['supply_flow_L_s']+=1;path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'source replay'):verify_balance(out/'air-balance')

    @unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit MOOSAS runtime required')
    def test_geometry_provider_replacement_preserves_air_balance(self):
        _,native=self.execute('comparison-native')
        moosas=self.root/'comparison-moosas';r=execute(self.plan,moosas,module_runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps'))
        self.assertEqual(r['tasks']['air-balance']['status'],'pass');context(self.plan,moosas)
        self.assertEqual(verify_balance(native/'air-balance')['calculation'],verify_balance(moosas/'air-balance')['calculation'])
