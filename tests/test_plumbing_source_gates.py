import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import regulatory_source_bindings

ROOT = Path(__file__).resolve().parents[1]


class PlumbingSourceGateTests(unittest.TestCase):
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
