import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ezdxf

from bsa.cli import digest
from bsa.duct_junction_review import inspect, from_workflow

ROOT = Path(__file__).resolve().parents[1]


class DuctJunctionReviewTests(unittest.TestCase):
    def fixture(self, units=6, reverse=False):
        doc = ezdxf.new(); doc.units = units; factor = 1000 if units == 4 else 1
        points = dict(R=[-2, 0, 0], J=[0, 0, 0], P=[2, 0, 0], Q=[4, 0, 0], L=[4, 2, 0], B=[0, 2, 0])
        edges = []; rows = []; entries = {}; flows = {}
        for sid, a, b, q, w, h in [('S0', 'R', 'J', .5, .6, .3), ('S1', 'J', 'P', .3, .4, .2), ('S2', 'J', 'B', .2, .2, .1), ('S3', 'P', 'Q', .3, .2, .1), ('S4', 'Q', 'L', .3, .2, .1)]:
            x, y = (b, a) if reverse else (a, b)
            line = doc.modelspace().add_line([v*factor for v in points[x]], [v*factor for v in points[y]])
            entries[sid] = dict(line_handle=line.dxf.handle, from_node=x, to_node=y, from_m=points[x], to_m=points[y])
            edges.append(dict(id=sid, **{'from': a, 'to': b}))
            rows.append(dict(id=sid, inputs=dict(width_m=w, height_m=h, flow_m3_s=q), calculation={'computed': True}, failures=[]))
            flows[sid] = q*1000
        schedule = dict(status='pass', sections=rows, flow_aggregation=dict(root='R', sections=edges, section_flow_L_s=flows,
            leaf_flow_L_s={'B': 200, 'L': 300}, total_flow_L_s=500, topology_pass=True, flow_conserved=True, basis='Synthetic explicit tree'))
        return doc, schedule, dict(basis='Synthetic line binding', sections=entries)

    def test_source_classification_units_reversed_lines_and_angles(self):
        for units, reverse in ((6, False), (4, True)):
            doc, schedule, binding = self.fixture(units, reverse)
            result = inspect(doc, schedule, binding)
            nodes = {n['node']: n for n in result['nodes']}
            self.assertEqual(nodes['J']['connection_requirement'], 'unequal_section_tee_required')
            self.assertEqual(nodes['P']['connection_requirement'], 'transition_required')
            self.assertEqual(nodes['Q']['connection_requirement'], 'elbow_required')
            self.assertEqual(sorted(round(p['outward_angle_deg']) for p in nodes['J']['pair_angles']), [90, 90, 180])
            self.assertTrue(all(r['source_centreline_length_m'] == 2 for n in nodes.values() for r in n['incidents']))
            self.assertEqual(nodes['J']['incoming_flow_L_s'], 500)
            self.assertEqual(nodes['J']['outgoing_flow_L_s'], 500)
            self.assertFalse(result['design_accepted'])
            self.assertTrue(all(n['fitting_authored'] is False for n in result['nodes']))
        doc, schedule, binding = self.fixture()
        for row in schedule['sections']: row['inputs'].update(width_m=.2, height_m=.1)
        result = inspect(doc, schedule, binding)
        self.assertEqual(result['counts']['equal_section_tee_candidate'], 1)
        self.assertEqual(result['counts']['straight_continuation'], 1)

    def test_rejects_stale_geometry_bad_topology_and_flow(self):
        for case in ('geometry', 'flow', 'conservation', 'coverage', 'disconnected', 'failed', 'dimension', 'leaf', 'cycle'):
            doc, schedule, binding = self.fixture()
            if case == 'geometry': doc.entitydb[binding['sections']['S0']['line_handle']].dxf.start = (-3, 0, 0)
            elif case == 'flow': schedule['flow_aggregation']['section_flow_L_s']['S0'] = 499
            elif case == 'conservation': schedule['flow_aggregation']['flow_conserved'] = False
            elif case == 'coverage': schedule['sections'].append(copy.deepcopy(schedule['sections'][0]))
            elif case == 'disconnected': binding['sections']['S1']['from_m'] = [.001, 0, 0]
            elif case == 'failed': schedule['sections'][0]['failures'] = ['No feasible size']
            elif case == 'dimension': schedule['sections'][0]['inputs']['height_m'] = True
            elif case == 'leaf': schedule['flow_aggregation']['leaf_flow_L_s'] = {'B': 200}
            else: schedule['flow_aggregation']['sections'][0]['to'] = 'R'
            with self.subTest(case=case), self.assertRaises(ValueError): inspect(doc, schedule, binding)

    def _check_inherited_inputs_and_immutable_workflow(self,directory):
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            root = Path(tmp).resolve(); run = root/'workflow'; (run/'native/reopened').mkdir(parents=True); (run/'sizing').mkdir()
            doc, schedule, binding = self.fixture(); doc.saveas(run/'native/reopened/source-export.dxf')
            source = root/'source.json'; source.write_text('{}'); schedule['input_sha256'] = digest(source)
            (root/'binding.json').write_text(json.dumps(binding)); (run/'sizing/results.json').write_text(json.dumps(schedule))
            tasks = [dict(id='sizing', kind='duct_schedule', project='source.json'), dict(id='sheet', kind='duct_sheet', depends_on='sizing', binding='binding.json'), dict(id='native', kind='duct_sheet_native', depends_on='sheet')]
            plan = root/'plan.json'; plan.write_text(json.dumps(dict(tasks=tasks)))
            report = dict(inputs={str(plan): digest(plan)}, tasks={t['id']: {'status': 'pass'} for t in tasks})
            (run/'workflow.json').write_text(json.dumps(report))
            with patch('bsa.workflow.verify', return_value={'integrity_pass': True}):
                result = from_workflow(plan, run, 'native', root/'review.json')
                self.assertEqual(result['lineage'], ['native', 'sheet', 'sizing'])
                self.assertEqual(result['inputs'][str(root/'binding.json')], digest(root/'binding.json'))
                with self.assertRaisesRegex(ValueError, 'outside immutable'): from_workflow(plan, run, 'native', run/'review.json')
                report['tasks']['sizing']['status'] = 'pending'; (run/'workflow.json').write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError, 'Passing native'): from_workflow(plan, run, 'native', root/'pending.json')
                report['tasks']['sizing']['status'] = 'pass'; (run/'workflow.json').write_text(json.dumps(report))
                source.write_text('{"changed": true}')
                with self.assertRaisesRegex(ValueError, 'Schedule/project'): from_workflow(plan, run, 'native', root/'changed.json')
            with patch('bsa.workflow.verify', return_value={'integrity_pass': False}):
                with self.assertRaisesRegex(ValueError, 'changed'): from_workflow(plan, run, 'native', root/'stale.json')

    def test_inherited_inputs_and_immutable_workflow(self):
        self._check_inherited_inputs_and_immutable_workflow(ROOT/'runs')

    def test_host_selected_external_review(self):
        import os
        with tempfile.TemporaryDirectory() as parent:
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':parent}):
                self._check_inherited_inputs_and_immutable_workflow(parent)
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaisesRegex(ValueError,'outside immutable'):
                    from_workflow(Path(parent)/'plan.json',Path(parent)/'workflow','native',Path(parent)/'denied.json')
