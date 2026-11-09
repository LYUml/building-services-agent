import json
from pathlib import Path
import shutil
import tempfile
import unittest
import ifcopenshell
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, validate_plan, verify

ROOT = Path(__file__).resolve().parents[1]


class SelectedPumpWorkflowTests(unittest.TestCase):
    def test_inherited_screen_revision_ids_and_no_feasible_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for name in ('model.json', 'project.json', 'binding.json', 'regulatory-bases.json'):
                shutil.copyfile(ROOT/'examples/circulation-ifc'/name, root/name)
            for name in ('pump-catalogue.json', 'thermal-duty.json'):
                shutil.copyfile(ROOT/'examples/hvac-circulation'/name, root/name)
            shutil.copyfile(ROOT/'examples/ids/pump-selection.ids', root/'pump.ids')
            catalogue = json.loads((root/'pump-catalogue.json').read_text())
            catalogue['candidates'] = catalogue['candidates'][-1:]
            catalogue['candidates'][0]['head_curve'] = [[0, 7], [.005, .1]]
            (root/'pump-catalogue.json').write_text(json.dumps(catalogue))
            pdf = root/'emsd-bec-2024.pdf'; pdf.write_bytes(b'SYNTHETIC TEST SOURCE, NOT OFFICIAL REGULATORY EVIDENCE')
            pack = json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
            pack['sources']['emsd_bec_2024']['sha256'] = digest(pdf)
            (root/'pack.json').write_text(json.dumps(pack))
            brief = root/'brief.md'; brief.write_text('Model, screen and record a synthetic selected pump, then verify its information and hydraulics.')
            row = passages(brief)[0]
            tasks = [dict(id='model', kind='bim', project='model.json'),
                     dict(id='bound', kind='water_coordination', project='project.json', binding='binding.json', depends_on='model'),
                     dict(id='screen', kind='circulation_pump_design', depends_on='bound', catalogue='pump-catalogue.json', thermal_basis='thermal-duty.json', rule_basis='regulatory-bases.json', pack='pack.json', sources='.'),
                     dict(id='selected', kind='selected_pump_ifc', depends_on='screen'),
                     dict(id='combined', kind='ifc_circulation_checks', depends_on='selected', thermal_basis='thermal-duty.json', rule_basis='regulatory-bases.json', pack='pack.json', sources='.'),
                     dict(id='information', kind='ids_check', depends_on='selected', ids='pump.ids'),
                     dict(id='water', kind='water_network', depends_on='screen', requires_pass=['information', 'combined'])]
            plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
                        passage_dispositions={row['id']: 'requirement'}, tasks=tasks,
                        requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
            file = root/'plan.json'; file.write_text(json.dumps(plan))
            result = execute(file, root/'positive')
            self.assertTrue(result['execution_pass'], result['tasks'])
            self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            from bsa.workflow_status import diagnose
            self.assertTrue(diagnose(file, root/'positive')['execution_pass'])
            selected = root/'positive/selected'
            ids = json.loads((root/'positive/information/ids-check.json').read_text())
            self.assertEqual(ids['inputs'][str(selected/'selected-model.ifc')], digest(selected/'selected-model.ifc'))
            revised = json.loads((selected/'selected-template.json').read_text())
            self.assertEqual(revised['pumps'][0]['head_curve'], [[0, 7], [.005, .1]])
            original = ifcopenshell.open(str(root/'positive/bound/model.ifc'))
            updated = ifcopenshell.open(str(selected/'selected-model.ifc'))
            for cls in ('IfcDistributionElement', 'IfcDistributionPort'):
                self.assertEqual({o.GlobalId for o in original.by_type(cls)}, {o.GlobalId for o in updated.by_type(cls)})
            # Inherited scenario and model revision cannot be replaced by caller files.
            for index, key, value in ((2, 'project', 'project.json'), (3, 'ifc', 'positive/bound/model.ifc')):
                tasks[index][key] = value; file.write_text(json.dumps(plan))
                with self.assertRaises(ProjectError):validate_plan(file)
                del tasks[index][key]
            file.write_text(json.dumps(plan))
            catalogue['candidates'][0]['head_curve'] = [[0, .01], [.005, .001]]
            (root/'pump-catalogue.json').write_text(json.dumps(catalogue))
            self.assertFalse(verify(root/'positive')['integrity_pass'])
            result = execute(file, root/'negative')
            self.assertEqual(result['tasks']['screen']['status'], 'fail')
            for name in ('selected', 'combined', 'information', 'water'):
                self.assertEqual(result['tasks'][name]['status'], 'pending')
                self.assertFalse((root/'negative'/name).exists())
