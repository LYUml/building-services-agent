import copy
import json
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.terminal_performance import calculate,run
from tests import test_allocation_lookup as fixtures


class TerminalPerformanceTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.AllocationLookupTests();fixture.setUp();self.addCleanup(fixture.temp.cleanup)
        self.fixture=fixture;self.root=fixture.root
        self.source=self.root/'manufacturer.txt';self.source.write_text('Synthetic original performance source')
        self.rows=[dict(flow_L_s=1,T025_m=1,static_pressure_Pa=1,total_pressure_Pa=2,NC=None,NC_qualifier='less than 10'),
            dict(flow_L_s=2000,T025_m=8,static_pressure_Pa=100,total_pressure_Pa=200,NC=40,NC_qualifier='catalogue value')]
        old=dict(source_sha256=digest(self.source),model='Synthetic terminal',rows=self.rows)
        (self.root/'catalogue.json').write_text(json.dumps(old))
        fixture.lookup['catalogue_sha256']=digest(self.root/'catalogue.json')
        fixture.run_plan('workflow')
        self.catalogue=self.root/'performance-catalogue.json';self.catalogue.write_text(json.dumps(old))
        self.settings=self.root/'settings.json';self.spec=dict(source=self.source.name,source_sha256=digest(self.source),
            catalogue=self.catalogue.name,catalogue_sha256=digest(self.catalogue),conditions='Synthetic no-damper condition <not verified>')
        self.save_settings()

    def save_settings(self):self.settings.write_text(json.dumps(self.spec))
    def execute(self):return run(self.root/'plan.json',self.root/'workflow','lookup',self.settings,self.root/'output')

    def test_analytical_pressure_interpolation_preserves_nc_reference_semantics(self):
        c=calculate(self.rows,1000.5)
        self.assertEqual(c['static_pressure_Pa'],50.5);self.assertEqual(c['total_pressure_Pa'],101)
        self.assertIsNone(c['NC']);self.assertEqual(c['nc_status'],'not_interpolated')
        self.assertIsNone(c['nc_catalogue_rows'][0]['NC']);self.assertEqual(c['nc_catalogue_rows'][0]['qualifier'],'less than 10')
        exact=calculate(self.rows,2000);self.assertEqual(exact['NC'],40);self.assertEqual(len(exact['nc_catalogue_rows']),1)

    def test_outside_not_clamped_and_invalid_pressure_rejected(self):
        for q in (.5,2001):
            c=calculate(self.rows,q);self.assertEqual(c['status'],'outside_catalogue');self.assertIsNone(c['static_pressure_Pa'])
        for key,value in (('total_pressure_Pa',0),('static_pressure_Pa',True),('NC',float('nan')),('NC_qualifier','')):
            rows=copy.deepcopy(self.rows);rows[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):calculate(rows,100)

    def test_inherited_flow_pairs_source_pins_and_html_escape(self):
        result=self.execute();self.assertEqual(len(result['terminals']),2)
        original=json.loads((self.root/'workflow/lookup/terminal-results.json').read_text())
        self.assertEqual(result['terminals'][0]['cases']['minimum']['flow_L_s'],original['terminals'][0]['directions']['east']['cases']['minimum']['flow_L_s'])
        self.assertIn(str(self.source),result['inputs']);self.assertFalse(result['fan_pressure_complete'])
        self.assertIn('&lt;not verified&gt;',(self.root/'output/index.html').read_text())
        with self.assertRaises(ValueError):self.execute()

    def test_changed_source_and_different_original_rows_reject_before_output(self):
        self.source.write_text('Changed source')
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse((self.root/'output').exists())
        self.source.write_text('Synthetic original performance source')
        data=json.loads(self.catalogue.read_text());data['rows'][0]['T025_m']=2
        self.catalogue.write_text(json.dumps(data));self.spec['catalogue_sha256']=digest(self.catalogue);self.save_settings()
        with self.assertRaisesRegex(ValueError,'row differs'):self.execute()
        self.assertFalse((self.root/'output').exists())

    def test_mid_calculation_source_change_rejects(self):
        def change(*args):
            self.source.write_text('Changed during calculation')
            return calculate(*args)
        with patch('bsa.terminal_performance.calculate',side_effect=change),self.assertRaisesRegex(ValueError,'changed during'):
            self.execute()
        self.assertFalse((self.root/'output').exists())

    def test_failed_original_lookup_cannot_supply_operating_points(self):
        self.fixture.allocation['load_inputs']['cooling_allowance']['value']=20000
        self.fixture.run_plan('failed-workflow')
        with self.assertRaisesRegex(ValueError,'passing terminal lookup'):
            run(self.root/'plan.json',self.root/'failed-workflow','lookup',self.settings,self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_source_document_correspondence_is_required(self):
        data=json.loads(self.catalogue.read_text());data['source_sha256']='wrong'
        self.catalogue.write_text(json.dumps(data));self.spec['catalogue_sha256']=digest(self.catalogue);self.save_settings()
        with self.assertRaisesRegex(ValueError,'same source document'):self.execute()
