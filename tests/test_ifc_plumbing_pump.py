import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_plumbing_pump import verify_producer
from bsa.workflow import execute, passages, validate_plan, verify

ROOT = Path(__file__).resolve().parents[1]


class IFCPlumbingPumpTests(unittest.TestCase):
    def test_actual_model_inheritance_and_reconstruction_rejects_tamper(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for name, target in (('route-template.json','network.json'), ('route-model.json','model.json'), ('route-binding.json','binding.json')):
                shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name, root/target)
            for name, target in (('curve.json','curve.json'), ('binding.json','basis.json')):
                shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name, root/target)
            pdf = root/'wsd-tr-2026-04.pdf'; pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            pack = json.loads((ROOT/'regulations/hk/plumbing-pumps-2026.11.09/pack.json').read_text())
            pack['sources']['wsd_tr_2026_04']['sha256'] = digest(pdf)
            (root/'pack.json').write_text(json.dumps(pack))
            brief = root/'brief.md'; brief.write_text('Bind synthetic saved route geometry to pump capacity checks.')
            row = passages(brief)[0]
            tasks = [dict(id='route', kind='network_coordination', project='network.json', model='model.json', binding='binding.json'),
                     dict(id='capacity', kind='plumbing_pump_regulations', depends_on='route', curve='curve.json', basis='basis.json', pack='pack.json', sources='.'),
                     dict(id='pump', kind='pump_operating_point', depends_on='route', curve='curve.json', requires_pass=['capacity'])]
            plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief), passage_dispositions={row['id']:'requirement'}, tasks=tasks,
                        requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
            file = root/'plan.json'; file.write_text(json.dumps(plan))
            result = execute(file, root/'run')
            self.assertTrue(result['execution_pass'], result['tasks'])
            self.assertTrue(verify(root/'run')['integrity_pass'])
            fields = {b['field'] for b in result['regulatory_source_bindings'] if b['consumer']=='pump'}
            self.assertEqual(fields, {'network_template', 'network_model', 'network_binding', 'pump_curve'})
            report = json.loads((root/'run/capacity/plumbing-pump-checks.json').read_text())
            self.assertTrue(report['saved_ifc_binding']['saved_geometry_reconciled'])
            self.assertEqual(report['saved_ifc_binding']['network_sha256'], digest(root/'run/route/network-input.json'))
            for key in ('project', 'model', 'binding', 'ifc', 'producer'):
                tasks[1][key] = 'network.json'; file.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ProjectError, 'replacements forbidden'):validate_plan(file)
                del tasks[1][key]
            file.write_text(json.dumps(plan))
            original_bytes = (root/'network.json').read_bytes()
            insufficient = json.loads(original_bytes)
            insufficient['supply']['total_pressure_pa'] = 1
            (root/'network.json').write_text(json.dumps(insufficient))
            failed = execute(file, root/'failed_route')
            self.assertEqual(failed['tasks']['route']['status'], 'fail')
            self.assertEqual(failed['tasks']['capacity']['status'], 'pending')
            self.assertFalse((root/'failed_route/capacity').exists())
            (root/'network.json').write_bytes(original_bytes)
            # Edit both generated data and its manifest: reconstruction must still reject it.
            generated = root/'run/route/network-input.json'
            changed = json.loads(generated.read_text()); changed['segments'][0]['length_m'] += 1
            generated.write_text(json.dumps(changed))
            manifest = root/'run/route/network-binding.json'; data = json.loads(manifest.read_text())
            data['artifacts']['network-input.json'] = digest(generated); manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError, 'source reconstruction'):
                verify_producer(root/'run/route', root/'network.json', root/'model.json', root/'binding.json')
            self.assertFalse(verify(root/'run')['integrity_pass'])
