import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, validate_plan
from bsa.duct_fitting_data import prepare

ROOT = Path(__file__).resolve().parents[1]


class DuctFittingDataWorkflowTests(unittest.TestCase):
    def test_pending_data_blocks_release_and_changed_sources_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); brief = root/'brief.md'; brief.write_text('Review native fitting data before downstream pressure release.')
            project = root/'project.json'; project.write_text('{}'); document = root/'source.txt'; document.write_text('Synthetic coefficient control')
            basis = root/'basis.json'; basis.write_text(json.dumps(dict(sources=dict(test=dict(document='source.txt', sha256=digest(document), citation='Synthetic', edition='test')),
                tables=[dict(source_id='test', citation_location='fixture', classification='synthetic', applicability_note='No engineering acceptance',
                    friction_scope='local_dynamic_only', product_guid='fixture', geometry_sha256='0'*64, inlet_port_guid='a', outlet_port_guid='b', reference_port_guid='a',
                    axes=[dict(quantity='outlet_to_inlet_flow_ratio', values=[.1, .9])], coefficients=[1., 2.])])) )
            row = passages(brief)[0]
            tasks = [dict(id='chain', kind='duct_fitting_chain', project='project.json'),
                dict(id='data', kind='duct_fitting_data', depends_on='chain', basis='basis.json'),
                dict(id='release', kind='ifc_preview', depends_on='chain', requires_pass=['data'], guid='0fL6ph7XD7AQ7ccJ8qPaHr')]
            def save():
                path = root/'plan.json'; path.write_text(json.dumps(dict(version=1, brief='brief.md', brief_sha256=digest(brief), passage_dispositions={row['id']:'requirement'}, tasks=tasks,
                    requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks]))); return path
            # Gate control only. Actual native model/source execution is separate.
            with patch('bsa.duct_fitting_chain.source_files', return_value={project}), patch('bsa.duct_fitting_chain.run', return_value=dict(chain_checks_pass=True, scope='stage control')), patch('bsa.duct_fitting_data.run', return_value=dict(scope='Data require physical review', pressure_budget_complete=False)):
                path = save(); result = execute(path, root/'run')
                self.assertEqual(result['tasks']['data']['status'], 'pending')
                self.assertEqual(result['tasks']['release']['status'], 'pending'); self.assertFalse((root/'run/release').exists())
                original = json.loads(basis.read_text())
                for invalid in ('duplicate', 'axis', 'nonfinite', 'shape', 'boolean'):
                    altered = copy.deepcopy(original); table = altered['tables'][0]
                    if invalid == 'duplicate': altered['tables'].append(copy.deepcopy(table))
                    elif invalid == 'axis': table['axes'][0]['values'] = [.9, .1]
                    elif invalid == 'nonfinite': table['coefficients'][0] = float('nan')
                    elif invalid == 'shape': table['coefficients'] = [1.]
                    else: table['coefficients'][0] = True
                    basis.write_text(json.dumps(altered))
                    with self.subTest(invalid=invalid), self.assertRaises(ValueError): prepare(basis)
                basis.write_text(json.dumps(original))
                tasks[1]['flow_m3_s'] = .5
                with self.assertRaisesRegex(ProjectError, 'replacement'): validate_plan(save())
                del tasks[1]['flow_m3_s']
                tasks.insert(1, dict(id='other', kind='duct_fitting_chain', project='project.json')); tasks[-1]['depends_on']='other'
                with self.assertRaisesRegex(ProjectError, 'different model'): validate_plan(save())
                tasks.pop(1); tasks[-1]['depends_on']='chain'; save(); document.write_text('Changed source')
                with self.assertRaisesRegex(ValueError, 'hash'): validate_plan(path)
