import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.plumbing_pump_binding import run
from bsa.workflow import execute, passages, verify

ROOT = Path(__file__).resolve().parents[1]


class PlumbingPumpBindingTests(unittest.TestCase):
    def test_native_capacity_failures_and_binding_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for name in ('network.json', 'curve.json', 'binding.json'):
                shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name, root/name)
            pdf = root/'wsd-tr-2026-04.pdf'; pdf.write_bytes(b'SYNTHETIC UNIT TEST SOURCE')
            pack = json.loads((ROOT/'regulations/hk/plumbing-pumps-2026.11.09/pack.json').read_text())
            pack['sources']['wsd_tr_2026_04']['sha256'] = digest(pdf)
            (root/'pack.json').write_text(json.dumps(pack))
            def check(name):return run(root/'network.json', root/'curve.json', root/'binding.json', root/'pack.json', root, root/name)
            result = check('positive')
            self.assertEqual(result['status'], 'pass')
            self.assertFalse(result['design_accepted'])
            point = json.loads((root/'positive/pump/pump.json').read_text())['operating_point']['flow_m3_s']
            bound = json.loads((root/'positive/bound-facts.json').read_text())
            self.assertEqual(bound['sump_pump']['available_pumping_capacity']['value'], point)
            brief = root/'brief.md'; brief.write_text('Synthetic capacity calculation and gated independent rerun.')
            row = passages(brief)[0]
            task = dict(kind='plumbing_pump_regulations', project='network.json', curve='curve.json', basis='binding.json', pack='pack.json', sources='.')
            tasks = [dict(task, id='capacity'), dict(task, id='recheck', requires_pass=['capacity'])]
            plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief), passage_dispositions={row['id']:'requirement'}, tasks=tasks,
                        requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
            plan_file = root/'plan.json'; plan_file.write_text(json.dumps(plan))
            workflow = execute(plan_file, root/'workflow_pass')
            self.assertTrue(workflow['execution_pass'])
            self.assertTrue(verify(root/'workflow_pass')['integrity_pass'])
            original = json.loads((root/'binding.json').read_text())
            bad = json.loads(json.dumps(original)); bad['regulatory_basis']['sump_pump']['available_pumping_capacity'] = {'value': 100}
            (root/'binding.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ProjectError, 'overridden'):check('override')
            bad = json.loads(json.dumps(original)); bad['connection']['tank_id'] = 'WRONG'
            (root/'binding.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ProjectError, 'tank identity'):check('identity')
            # Native flow can be numerically valid yet insufficient for the design target.
            network = json.loads((root/'network.json').read_text())
            network['nodes'][-1]['demand_m3_s'] = .0015
            (root/'network.json').write_text(json.dumps(network))
            (root/'binding.json').write_text(json.dumps(original))
            with self.assertRaisesRegex(ProjectError, 'design demand'):check('mismatch')
            original['regulatory_basis']['sump_pump']['tank_design_outflow']['value'] = .0015
            (root/'binding.json').write_text(json.dumps(original))
            result = check('insufficient')
            self.assertEqual(result['status'], 'fail')
            self.assertFalse(result['hydraulic_checks_pass'])
            self.assertFalse(result['supported_checks_pass'])
            self.assertEqual(result['regulatory_checks']['checks'][0]['status'], 'review_required')
            workflow = execute(plan_file, root/'workflow_fail')
            self.assertEqual(workflow['tasks']['capacity']['status'], 'fail')
            self.assertEqual(workflow['tasks']['recheck']['status'], 'pending')
            self.assertFalse((root/'workflow_fail/recheck').exists())
            self.assertFalse(verify(root/'workflow_pass')['integrity_pass'])
            curve = json.loads((root/'curve.json').read_text())
            for p in curve['points']:p['total_pressure_rise_pa'] *= .1
            (root/'curve.json').write_text(json.dumps(curve))
            result = check('no_intersection')
            self.assertEqual(result['status'], 'fail')
            self.assertIsNone(result['regulatory_checks'])
            self.assertFalse((root/'no_intersection/bound-facts.json').exists())
