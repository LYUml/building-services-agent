import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.workflow import execute, validate_plan, verify
from bsa.engine import ProjectError
from tests import test_drainage_stack_demand as demand_fixture


class StackWorkflowTests(unittest.TestCase):
    def test_inherited_identity_gates_unknowns_and_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def save(name, value):
                path = root/name
                path.write_text(json.dumps(value), encoding='utf-8')
                return path
            source = root/'source.txt'
            source.write_text('Synthetic test basis, not official source')
            sha = digest(source)
            fixture = demand_fixture.StackDemandTests(); fixture.setUp()
            spec, basis = fixture.project, fixture.basis
            spec.update(references={source.name: sha}, official_reference=source.name)
            basis['references'] = {source.name: sha}
            save('connections.json', spec); save('basis.json', basis)
            brief = root/'brief.txt'; brief.write_text('Bind the same fixture inventory to stack demand.\n')
            tasks = [dict(id='connections', kind='drainage_connections', project='connections.json'),
                     dict(id='demand', kind='drainage_stack_demand', depends_on='connections', basis='basis.json'),
                     dict(id='review', kind='manual', requires_pass=['demand'], description='Whole design review pending')]
            plan_data = dict(version=1, brief=brief.name, brief_sha256=digest(brief),
                             passage_dispositions={'P001': 'requirement'}, tasks=tasks,
                             requirements=[dict(id='R'+str(i), passage='P001', quote='Bind the same fixture inventory to stack demand.',
                                                task=t['id'], acceptance='Scoped method check only') for i,t in enumerate(tasks)])
            plan = save('plan.json', plan_data)
            with patch('bsa.drainage_connections.OFFICIAL_SHA256', sha):
                result = execute(plan, root/'positive')
                self.assertEqual(result['tasks']['demand']['status'], 'pass')
                actual = json.loads((root/'positive/demand/stack-demand.json').read_text())
                self.assertEqual(actual['calculation']['total_DU'], 2)
                self.assertTrue(verify(root/'positive')['integrity_pass'])
                basis['full_stack_inventory_verified'] = None; save('basis.json', basis)
                result = execute(plan, root/'unknown_inventory')
                self.assertEqual(result['tasks']['demand']['status'], 'pending')
                basis['full_stack_inventory_verified'] = True; save('basis.json', basis)
                spec['fixtures'][1]['connected_to_stack'] = True; save('connections.json', spec)
                result = execute(plan, root/'bad_connection')
                self.assertEqual(result['tasks']['connections']['status'], 'fail')
                self.assertEqual(result['tasks']['demand']['status'], 'pending')
                self.assertFalse((root/'bad_connection/demand').exists())
                spec['fixtures'][1]['connected_to_stack'] = False; save('connections.json', spec)
                from bsa.drainage_connections import run as real_run
                def corrupt(project, output):
                    result = real_run(project, output)
                    data = json.loads(output.read_text()); data['inventory_source'] = 'Tampered'
                    output.write_text(json.dumps(data), encoding='utf-8')
                    return result
                with patch('bsa.drainage_connections.run', side_effect=corrupt):
                    result = execute(plan, root/'corrupt')
                self.assertEqual(result['tasks']['demand']['status'], 'fail')
                self.assertTrue(verify(root/'corrupt')['integrity_pass'])
            tasks[1]['project'] = 'connections.json'; save('plan.json', plan_data)
            with self.assertRaises(ProjectError): validate_plan(plan)
            del tasks[1]['project']; tasks[1]['depends_on'] = 'review'; save('plan.json', plan_data)
            with self.assertRaises(ProjectError): validate_plan(plan)
            source.write_text('Changed basis')
            self.assertFalse(verify(root/'positive')['integrity_pass'])
