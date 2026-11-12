import copy
import json
import runpy
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.spatial_terminal_performance import verify as verify_performance

ROOT=Path(__file__).resolve().parents[1]

class SpatialTerminalPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        source=self.root/'source.txt';source.write_text('Synthetic performance control;not a manufacturer selection')
        rows=[dict(flow_L_s=q,T025_m=q/100,static_pressure_Pa=q/10,total_pressure_Pa=q/5,NC=None,NC_qualifier='less than 10') for q in (10,1000)]
        catalogue=self.root/'catalogue.json';catalogue.write_text(json.dumps(dict(source_sha256=digest(source),model='Synthetic terminal',locator='Synthetic two-row table',damper=False,rows=rows)))
        self.settings=self.root/'settings.json';self.settings.write_text(json.dumps(dict(source=source.name,source_sha256=digest(source),catalogue=catalogue.name,catalogue_sha256=digest(catalogue),conditions='Synthetic only')))
        ifc=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](self.root/'ifc')
        self.plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](self.root/'inputs',ifc_source=ifc,tolerances=dict(length_tolerance_m=1e-6,area_tolerance_m2=1e-8),air_balance=True,terminal_allocation=True,performance_settings=self.settings)
        pdf=self.plan.parent/'sources/emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC RULE SOURCE CONTROL')
        pack=self.plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(pdf);pack.write_text(json.dumps(data))

    def run_workflow(self,**kwargs):
        out=self.root/'workflow';record=execute(self.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},**kwargs)
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        return out,record

    def test_exact_inheritance_interpolation_and_replay_tamper(self):
        out,record=self.run_workflow();self.assertEqual(record['tasks']['terminal-performance']['status'],'pass')
        result=verify_performance(out/'terminal-performance');allocation=json.loads((out/'terminal-allocation/terminal-allocation.json').read_text())
        for room in allocation['calculation']['rooms'].values():
            for terminal in room['allocation']['terminals']:
                cases=result['calculation']['terminals'][terminal['id']]['cases']
                for name in ('maximum','minimum'):
                    q=terminal[name+'_flow_L_s'];self.assertEqual(cases[name]['flow_L_s'],q)
                    self.assertAlmostEqual(cases[name]['T025_m'],q/100)
                    self.assertAlmostEqual(cases[name]['total_pressure_Pa'],q/5)
                    self.assertIsNone(cases[name]['NC']);self.assertEqual(cases[name]['nc_status'],'not_interpolated')
        self.assertFalse(result['calculation']['ADPI_verified'])
        path=out/'terminal-performance/terminal-performance.json';data=copy.deepcopy(result);next(iter(data['calculation']['terminals'].values()))['cases']['maximum']['total_pressure_Pa']+=1;path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'source replay'):verify_performance(path.parent)

    def test_outside_catalogue_pending_not_clamped(self):
        folder=self.plan.parent/'performance-source';path=folder/'catalogue.json';data=json.loads(path.read_text());data['rows'][-1]['flow_L_s']=100;path.write_text(json.dumps(data))
        settings=folder/'settings.json';spec=json.loads(settings.read_text());spec['catalogue_sha256']=digest(path);settings.write_text(json.dumps(spec))
        out,record=self.run_workflow();self.assertEqual(record['tasks']['terminal-performance']['status'],'pending')
        result=verify_performance(out/'terminal-performance')['calculation'];self.assertGreater(result['outside_catalogue_cases'],0)
        for terminal in result['terminals'].values():
            self.assertIsNone(terminal['cases']['maximum']['T025_m']);self.assertIsNone(terminal['cases']['maximum']['total_pressure_Pa'])
        self.assertEqual(record['tasks']['independent-electrical']['status'],'pass')

    def test_disabled_geometry_gates_performance(self):
        out,record=self.run_workflow(disabled_module_providers=['ifcopenshell.polygon-spaces'])
        self.assertEqual(record['tasks']['terminal-performance']['status'],'pending');self.assertFalse((out/'terminal-performance/terminal-performance.json').exists())
        self.assertEqual(record['tasks']['independent-electrical']['status'],'pass')

    def test_replacement_flow_and_missing_product_reject(self):
        from bsa.spatial_terminal_performance import selections
        path=self.plan.parent/'performance-selections.json';data=json.loads(path.read_text());original=copy.deepcopy(data)
        next(iter(data.values()))['maximum_flow_L_s']=42;path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'replacement flows'):selections(path)
        data=original;data.pop(next(iter(data)));path.write_text(json.dumps(data))
        out,record=self.run_workflow()
        self.assertEqual(record['tasks']['terminal-performance']['status'],'fail')
        self.assertFalse((out/'terminal-performance/terminal-performance.json').exists())
