import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest

from bsa.engineering_handoff import verify
from bsa.workflow import validate_plan
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
SOURCES=ROOT/'runs/hk-coupled-official-refresh'


@unittest.skipUnless((SOURCES/'emsd-wiring-2025.pdf').is_file(),'requires pinned official EMSD source cache')
class CoupledHKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name);execute=runpy.run_path(str(ROOT/'scripts/run_coupled_handoff_demo.py'))['execute']
        cls.positive=execute(cls.root/'positive',hk_sources=SOURCES)
        cls.long=execute(cls.root/'long',native=True,autocad='not-started.exe',hk_sources=SOURCES,hk_control='long-feeder')
        cls.unknown=execute(cls.root/'unknown',native=True,autocad='not-started.exe',hk_sources=SOURCES,hk_control='unknown-scope')

    def test_official_source_checks_original_baseline_and_preserves_phase_identity(self):
        root=self.root/'positive';checked=verify(root/'engineering-run')
        self.assertEqual(checked['task_statuses']['hk-rules'],'pass')
        self.assertEqual(checked['task_statuses']['drawing'],'pass')
        self.assertEqual(checked['task_statuses']['review'],'pending')
        original=json.loads((ROOT/'examples/water-riser/electrical.json').read_text())
        self.assertEqual(json.loads((root/'electrical.json').read_text()),original)
        rules=json.loads((root/'engineering-run/workflow/hk-rules/electrical-regulation-checks.json').read_text())
        paths=json.loads((root/'engineering-run/workflow/hk-rules/calculation/electrical-paths.json').read_text())
        self.assertEqual({row['phase'] for row in paths['feeders']},{'L1','L2'})
        pump=next(row for row in paths['branch_calculation']['circuits'] if row['id']=='PUMP-SUPPLY')
        self.assertAlmostEqual(pump['design_current_a'],750/.85/230)
        self.assertTrue(rules['branch_checks_pass']);self.assertTrue(rules['supported_regulation_checks_pass'])
        self.assertEqual(rules['regulatory_compliance'],'not_established');self.assertFalse(rules['design_accepted'])

    def test_long_feeder_and_unknown_applicability_block_model_and_native_release(self):
        for name,expected in [('long','review_required'),('unknown','pending')]:
            with self.subTest(name=name):
                root=self.root/name;checked=verify(root/'engineering-run')
                self.assertEqual(checked['task_statuses']['hk-rules'],'pending')
                self.assertTrue(all(checked['task_statuses'][task]=='pending' for task in ('coupled','coupled-qa','drawing','native','review')))
                self.assertFalse((root/'engineering-run/workflow/coupled/model.ifc').exists())
                self.assertFalse((root/'engineering-run/workflow/native').exists())
                rules=json.loads((root/'engineering-run/workflow/hk-rules/electrical-regulation-checks.json').read_text())
                self.assertTrue(rules['branch_checks_pass'])
                self.assertEqual(rules['circuit_checks']['PUMP-SUPPLY']['checks'][0]['status'],expected)

    def test_lower_operating_project_cannot_replace_baseline_beneath_rule_gate(self):
        root=self.root/'positive';plan=json.loads((root/'engineering-plan.json').read_text())
        source=json.loads((root/'electrical.json').read_text())
        operating=json.loads((root/'engineering-run/workflow/coupled/pump-electrical.json').read_text())['record']['operating_electrical_kw']
        source['devices'][0]['electrical_kw']=operating
        (root/'wrong-project.json').write_text(json.dumps(source))
        changed=copy.deepcopy(plan);next(task for task in changed['tasks'] if task['id']=='coupled')['project']='wrong-project.json'
        path=root/'wrong-plan.json';path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ProjectError,'checks different project bytes'):validate_plan(path)


if __name__=='__main__':unittest.main()
