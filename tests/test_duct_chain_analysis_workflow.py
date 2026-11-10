import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.workflow import execute, passages, validate_plan
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]


class DuctChainAnalysisWorkflowTests(unittest.TestCase):
    def test_incomplete_pressure_blocks_release_and_wrong_model_gates_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); brief = root/'brief.md'; brief.write_text('Compute source-bound chain analysis and retain incomplete pressure acceptance before release.')
            project = root/'source.json'; project.write_text('{}'); row = passages(brief)[0]
            tasks = [dict(id='chain', kind='duct_fitting_chain', project='source.json'), dict(id='analysis', kind='duct_chain_analysis', depends_on='chain'),
                dict(id='release', kind='ifc_preview', depends_on='chain', requires_pass=['analysis'], guid='0fL6ph7XD7AQ7ccJ8qPaHr')]
            def save():
                plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief), passage_dispositions={row['id']: 'requirement'}, tasks=tasks,
                    requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
                path = root/'plan.json'; path.write_text(json.dumps(plan)); return path
            path = save()
            # State/gate control only. Actual saved geometry and source binding
            # execute separately without these mocks on the real private plan.
            with patch('bsa.duct_fitting_chain.source_files', return_value={project}), patch('bsa.duct_fitting_chain.run', return_value={'chain_checks_pass': True, 'scope': 'unit stage control'}), patch('bsa.duct_chain_analysis.run', return_value=dict(pressure_budget_complete=False, scope='incomplete pressure', missing_fitting_path_losses=[{}])):
                result = execute(path, root/'pending')
                self.assertEqual(result['tasks']['analysis']['status'], 'pending')
                self.assertEqual(result['tasks']['release']['status'], 'pending')
                self.assertFalse((root/'pending/release').exists()); self.assertFalse(result['design_accepted'])
                tasks[1]['flow_m3_s'] = 1; save()
                with self.assertRaisesRegex(ProjectError, 'replacement'): validate_plan(path)
                del tasks[1]['flow_m3_s']
                tasks.insert(1, dict(id='other', kind='duct_fitting_chain', project='source.json')); tasks[-1]['depends_on'] = 'other'; save()
                with self.assertRaisesRegex(ProjectError, 'different model'): validate_plan(path)
