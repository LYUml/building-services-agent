"""Real upstream IDS execution and workflow release gates on synthetic IFC."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import ifcopenshell
import ifcopenshell.api
from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, validate_plan, verify

ROOT = Path(__file__).resolve().parents[1]


class IDSWorkflowTests(unittest.TestCase):
    def test_native_pass_failure_gate_and_source_integrity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            shutil.copyfile(ROOT/'examples/ids/pump-selection.ids', root/'requirements.ids')
            shutil.copyfile(ROOT/'examples/circulation-ifc/model.json', root/'model.json')
            author(root/'model.json', root/'authored')
            model = ifcopenshell.open(str(root/'authored/model.ifc'))
            for pump in model.by_type('IfcPump'):
                pset = ifcopenshell.api.run('pset.add_pset', model, product=pump, name='BSA_ScreenedPumpCurve')
                ifcopenshell.api.run('pset.edit_pset', model, pset=pset, properties={
                    key: 'SYNTHETIC presence-only test value' for key in
                    ('CandidateId', 'HeadCurve_m3_s_m', 'ScreeningReportSHA256', 'Source')})
            model.write(str(root/'present.ifc'))
            brief = root/'brief.md'
            brief.write_text('Check pump information before downstream checks.', encoding='utf-8')
            row = passages(brief)[0]
            tasks = [dict(id='information', kind='ids_check', ids='requirements.ids', ifc='present.ifc'),
                     dict(id='downstream', kind='ids_check', ids='requirements.ids', ifc='present.ifc', requires_pass=['information'])]
            plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
                        passage_dispositions={row['id']: 'requirement'}, tasks=tasks,
                        requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
            file = root/'plan.json'
            file.write_text(json.dumps(plan))
            result = execute(file, root/'positive')
            self.assertTrue(result['execution_pass'])
            self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            check = json.loads((root/'positive/information/ids-check.json').read_text())
            self.assertEqual(check['requirements_checked'], 4)
            self.assertEqual(check['inputs'][str(root/'present.ifc')], digest(root/'present.ifc'))
            # Inherited model has none of the required properties. Engine still exits 0.
            tasks.insert(0, dict(id='author', kind='bim', project='model.json'))
            plan['requirements'].append(dict(id='author', passage=row['id'], quote=row['text'], task='author', acceptance=row['text']))
            tasks[1].pop('ifc'); tasks[1]['depends_on'] = 'author'
            file.write_text(json.dumps(plan))
            result = execute(file, root/'negative')
            self.assertEqual(result['tasks']['author']['status'], 'pass')
            self.assertEqual(result['tasks']['information']['status'], 'fail')
            self.assertEqual(result['tasks']['downstream']['status'], 'pending')
            self.assertFalse((root/'negative/downstream').exists())
            check = json.loads((root/'negative/information/ids-check.json').read_text())
            self.assertEqual(check['engine_exit_code'], 0)
            self.assertEqual(check['requirements_failed'], 4)
            self.assertEqual(check['inputs'][str(root/'negative/author/model.ifc')], digest(root/'negative/author/model.ifc'))
            self.assertTrue(verify(root/'negative')['integrity_pass'])
            # No input replacement is allowed for inherited IFC checks.
            tasks[1]['ifc'] = 'present.ifc'; file.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError, 'exactly one'):
                validate_plan(file)
            tasks[1].pop('ifc'); file.write_text(json.dumps(plan))
            with patch('bsa.bim.run', side_effect=ProjectError('synthetic upstream failure')):
                result = execute(file, root/'upstream-failure')
            self.assertNotEqual(result['tasks']['author']['status'], 'pass')
            self.assertEqual(result['tasks']['information']['status'], 'pending')
            self.assertFalse((root/'upstream-failure/information').exists())
            (root/'requirements.ids').write_text('changed')
            self.assertFalse(verify(root/'negative')['integrity_pass'])

    def test_no_applicable_pump_cannot_pass(self):
        from bsa.ids_check import run
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            empty = ifcopenshell.file(schema='IFC4')
            empty.write(str(root/'empty.ifc'))
            result = run(ROOT/'examples/ids/pump-selection.ids', root/'empty.ifc', root/'check')
            self.assertFalse(result['calculated_checks_pass'])
