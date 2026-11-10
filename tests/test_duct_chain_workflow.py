import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.workflow import execute, passages, validate_plan
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]


class DuctChainWorkflowTests(unittest.TestCase):
    def test_failed_chain_blocks_saved_ifc_reader_and_replacements_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); brief = root/'brief.md'; brief.write_text('Compose a scoped source-bound chain and inspect its saved model.')
            project = root/'source.json'; project.write_text('{}'); row = passages(brief)[0]
            tasks = [dict(id='chain', kind='duct_fitting_chain', project='source.json'),
                dict(id='preview', kind='ifc_preview', depends_on='chain', guid='0fL6ph7XD7AQ7ccJ8qPaHr')]
            plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief), passage_dispositions={row['id']: 'requirement'}, tasks=tasks,
                requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
            path = root/'plan.json'; path.write_text(json.dumps(plan))
            # This control verifies orchestration only; native geometry is tested
            # separately and the real source workflow executes without these mocks.
            with patch('bsa.duct_fitting_chain.source_files', return_value={project}), patch('bsa.duct_fitting_chain.run', return_value=dict(chain_checks_pass=False, reason='source span overrun')):
                result = execute(path, root/'failed')
                self.assertEqual(result['tasks']['chain']['status'], 'fail')
                self.assertEqual(result['tasks']['preview']['status'], 'pending')
                self.assertFalse((root/'failed/preview').exists())
                self.assertFalse(result['design_accepted'])
                tasks[0]['ifc'] = 'replacement.ifc'; path.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ProjectError, 'replacement'): validate_plan(path)
