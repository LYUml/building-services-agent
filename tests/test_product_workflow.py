import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, verify, validate_plan

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    brief = root/'brief.md'; brief.write_text('Convert the selected source body and locate its model ports.\n')
    (root/'source.dwg').write_bytes(b'Synthetic placeholder; no engine execution permitted')
    (root/'convert.json').write_text('{}')
    (root/'place.json').write_text(json.dumps({'passage_basis': 'probes.json'}))
    (root/'probes.json').write_text('{}')
    plan = {'version': 1, 'brief': 'brief.md', 'brief_sha256': digest(brief),
            'passage_dispositions': {'P001': 'requirement'},
            'tasks': [{'id': 'convert', 'kind': 'cad_ifc', 'drawing': 'source.dwg', 'basis': 'convert.json'},
                      {'id': 'place', 'kind': 'product_ports', 'depends_on': 'convert', 'basis': 'place.json'}],
            'requirements': [{'id': 'R1', 'passage': 'P001', 'quote': brief.read_text().strip(),
                              'task': 'place', 'acceptance': 'Source-linked model ports; engineering acceptance remains separate'},
                             {'id': 'R2', 'passage': 'P001', 'quote': brief.read_text().strip(),
                              'task': 'convert', 'acceptance': 'Source-bound native geometry conversion'}]}
    path = root/'plan.json'; path.write_text(json.dumps(plan)); return path, plan


class ProductWorkflowTests(unittest.TestCase):
    def test_missing_engine_blocks_both_and_tracks_nested_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); path, _ = fixture(root)
            r = execute(path, root/'run')
            self.assertIn(str(root/'probes.json'), r['inputs'])
            for task in ('convert', 'place'):
                self.assertEqual(r['tasks'][task]['status'], 'pending')
                self.assertFalse((root/'run'/task).exists())
            self.assertTrue(verify(root/'run')['integrity_pass'])
            page=root/'run/index.html'
            original=page.read_bytes();page.write_bytes(original+b'changed')
            self.assertFalse(verify(root/'run')['integrity_pass'])
            page.write_bytes(original)
            (root/'probes.json').write_text('{"changed":true}')
            self.assertFalse(verify(root/'run')['integrity_pass'])

    def test_failed_producer_blocks_ports(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); path, _ = fixture(root)
            r = execute(path, root/'run', autocad=root/'missing.exe')
            self.assertEqual(r['tasks']['convert']['status'], 'fail')
            self.assertEqual(r['tasks']['place']['status'], 'pending')
            self.assertFalse((root/'run/place').exists())

    def test_replacement_or_wrong_parent_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); path, plan = fixture(root)
            for extra in ({'ifc': 'source.dwg'}, {'producer': 'elsewhere'}, {'depends_on': 'missing'}):
                plan['tasks'][1] = {'id': 'place', 'kind': 'product_ports', 'depends_on': 'convert', 'basis': 'place.json', **extra}
                path.write_text(json.dumps(plan))
                with self.assertRaises(ProjectError): validate_plan(path)

    def test_nested_input_cannot_escape_plan_root(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); path, _ = fixture(root)
            (root/'place.json').write_text(json.dumps({'passage_basis': '../outside.json'}))
            with self.assertRaises(ProjectError): validate_plan(path)
