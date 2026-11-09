import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import regulatory_source_bindings

ROOT = Path(__file__).resolve().parents[1]


class PlumbingSourceGateTests(unittest.TestCase):
    def test_derived_gate_rejects_explicit_replacement(self):
        root = ROOT/'examples/hk-plumbing-pumps'
        tasks = [dict(id='route', kind='network_coordination', project='route-template.json', model='route-model.json', binding='route-binding.json'),
                 dict(id='check', kind='plumbing_pump_regulations', depends_on='route', curve='curve.json', basis='binding.json'),
                 dict(id='pump', kind='pump_operating_point', project='network.json', curve='curve.json', requires_pass=['check'])]
        with self.assertRaisesRegex(ProjectError, 'same inherited network'):
            regulatory_source_bindings(tasks, root)
        del tasks[-1]['project']; tasks[-1]['depends_on'] = 'route'
        rows = regulatory_source_bindings(tasks, root)
        self.assertIn('network_model', {r['field'] for r in rows})

    def test_direct_transitive_and_curve_correspondence(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for name in ('network.json', 'curve.json', 'binding.json'):
                shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name, root/name)
            checked = dict(id='checked', kind='plumbing_pump_regulations', project='network.json', curve='curve.json', basis='binding.json')
            tasks = [checked, dict(id='review', kind='manual', requires_pass=['checked']),
                     dict(id='pump', kind='pump_operating_point', project='network.json', curve='curve.json', requires_pass=['review'])]
            rows = regulatory_source_bindings(tasks, root)
            self.assertEqual({r['field'] for r in rows if r['consumer']=='pump'}, {'network', 'pump_curve'})
            changed = json.loads((root/'curve.json').read_text()); changed['points'][0]['total_pressure_rise_pa'] += 1000
            (root/'other-curve.json').write_text(json.dumps(changed))
            tasks[-1]['curve'] = 'other-curve.json'
            with self.assertRaisesRegex(ProjectError, 'different pump_curve'):
                regulatory_source_bindings(tasks, root)
            tasks[-1]['curve'] = 'curve.json'
            changed = json.loads((root/'network.json').read_text()); changed['segments'][0]['length_m'] = 10
            (root/'other-network.json').write_text(json.dumps(changed))
            tasks[-1]['project'] = 'other-network.json'
            with self.assertRaisesRegex(ProjectError, 'different network'):
                regulatory_source_bindings(tasks, root)
            # The same check repeated downstream must not swap its tank/configuration basis.
            changed = json.loads((root/'binding.json').read_text()); changed['connection']['tank_id'] = 'OTHER'
            (root/'other-binding.json').write_text(json.dumps(changed))
            tasks[-1] = dict(checked, id='recheck', basis='other-binding.json', requires_pass=['review'])
            with self.assertRaisesRegex(ProjectError, 'different plumbing_basis'):
                regulatory_source_bindings(tasks, root)
            # Identical source bytes at a different path are explicitly permitted.
            shutil.copyfile(root/'binding.json', root/'same-binding.json')
            tasks[-1]['basis'] = 'same-binding.json'
            rows = regulatory_source_bindings(tasks, root)
            self.assertEqual({r['field'] for r in rows if r['consumer']=='recheck'}, {'network', 'pump_curve', 'plumbing_basis'})

    def test_pump_set_role_binding_and_substitution(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for name in ('pump-set.json','network.json','curve.json','binding.json'):
                shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name,root/name)
            curve=json.loads((root/'curve.json').read_text())
            curve['points'][0]['total_pressure_rise_pa']+=1000
            (root/'standby.json').write_text(json.dumps(curve))
            data=json.loads((root/'pump-set.json').read_text())
            data['pumps'][1]['curve']='standby.json'
            (root/'pump-set.json').write_text(json.dumps(data))
            tasks=[dict(id='set',kind='plumbing_pump_set',project='pump-set.json',basis='binding.json'),
                   dict(id='review',kind='manual',requires_pass=['set']),
                   dict(id='pump',kind='pump_operating_point',project='network.json',curve='standby.json',
                        pump_role='standby',requires_pass=['review'])]
            rows=regulatory_source_bindings(tasks,root)
            self.assertEqual({r['field'] for r in rows},{'network','pump_curve'})
            self.assertTrue(all(r['pump_role']=='standby' for r in rows))
            tasks[-1]['curve']='curve.json'
            with self.assertRaisesRegex(ProjectError,'different standby pump_curve'):
                regulatory_source_bindings(tasks,root)
            tasks[-1]['curve']='standby.json'
            del tasks[-1]['pump_role']
            with self.assertRaisesRegex(ProjectError,'explicit pump_role'):
                regulatory_source_bindings(tasks,root)
            tasks[-1]=dict(id='pipe',kind='water_pipe_regulations',project='network.json',
                           pump_role='standby',requires_pass=['review'])
            self.assertEqual(regulatory_source_bindings(tasks,root)[0]['field'],'network')
            net=json.loads((root/'network.json').read_text());net['segments'][0]['length_m']+=1
            (root/'changed.json').write_text(json.dumps(net));tasks[-1]['project']='changed.json'
            with self.assertRaisesRegex(ProjectError,'different standby network'):
                regulatory_source_bindings(tasks,root)
            tasks[-1]['requires_pass']=[]
            with self.assertRaisesRegex(ProjectError,'upstream pump-set gate'):
                regulatory_source_bindings(tasks,root)
