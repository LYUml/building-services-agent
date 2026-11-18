import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import ezdxf
from bsa.air_terminal_drawing import from_workflow, inspect
from bsa.cli import digest


class TerminalDrawingTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new();self.doc.units=6
        self.layers=dict(supply='duct',vav='vav',terminal='terminal',flex='flex')
        self.tree=dict(root='R',sections=[dict(id='A',**{'from':'R','to':'VA'}),dict(id='B',**{'from':'R','to':'VB'})],leaf_terminals=dict(VA=['TA'],VB=['TB']),basis='Synthetic test')
        self.allocation=dict(terminals=[dict(id='TA',center_m=[2,1],maximum_flow_L_s=100),dict(id='TB',center_m=[2,-1],maximum_flow_L_s=100)])
        self.binding=dict(sections={})
        m=self.doc.modelspace()
        for sid,node,y in [('A','VA',1),('B','VB',-1)]:
            m.add_line((0,0),(1,y),dxfattribs=dict(layer='duct'))
            m.add_circle((1,y),.1,dxfattribs=dict(layer='vav'))
            m.add_line((1,y),(2,y),dxfattribs=dict(layer='flex'))
            m.add_lwpolyline([(1.9,y-.1),(2.1,y-.1),(2.1,y+.1),(1.9,y+.1)],close=True,dxfattribs=dict(layer='terminal'))
            self.binding['sections'][sid]=dict(from_node='R',to_node=node,from_m=[0,0,0],to_m=[1,y,0])

    def check(self):
        return inspect(self.doc,self.allocation,self.tree,self.binding,self.layers)

    def test_actual_geometry_and_reversed_lines(self):
        for e in self.doc.modelspace().query('LINE'):
            e.dxf.start,e.dxf.end=e.dxf.end,e.dxf.start
        r=self.check()
        self.assertEqual(r['terminal_count'],2)
        self.assertEqual([row['section'] for row in r['rigid_sections']], ['A', 'B'])
        self.assertEqual([row['from_node'] for row in r['rigid_sections']], ['R', 'R'])
        self.assertEqual([row['saved_from_m'] for row in r['rigid_sections']], [[0, 0, 0], [0, 0, 0]])
        self.assertEqual([row['saved_to_m'] for row in r['rigid_sections']], [[1, 1, 0], [1, -1, 0]])
        for row in r['rigid_sections']:
            self.assertAlmostEqual(row['saved_plan_length_m'], 2**0.5)
        self.assertAlmostEqual(r['maximum_plan_length_m'],1)
        self.assertEqual([route['saved_plan_length_m'] for group in r['groups'] for route in group['routes']],
                         [1.0, 1.0])
        self.assertFalse(r['design_accepted'])

    def test_equal_length_translation_is_visible_in_saved_section_coordinates(self):
        from ezdxf.math import Matrix44

        baseline = self.check()
        shift = 0.25
        for entity in self.doc.modelspace():
            entity.transform(Matrix44.translate(shift, 0, 0))
        for section in self.binding['sections'].values():
            section['from_m'][0] += shift
            section['to_m'][0] += shift
        for terminal in self.allocation['terminals']:
            terminal['center_m'][0] += shift
        revised = self.check()
        for old, new in zip(baseline['groups'], revised['groups'], strict=True):
            self.assertEqual(new['saved_vav_center_m'][0] - old['saved_vav_center_m'][0], shift)
            self.assertEqual(new['routes'][0]['saved_terminal_center_m'][0]
                             - old['routes'][0]['saved_terminal_center_m'][0], shift)

        for old, new in zip(baseline['rigid_sections'], revised['rigid_sections'], strict=True):
            self.assertEqual(old['section'], new['section'])
            self.assertEqual(old['saved_plan_length_m'], new['saved_plan_length_m'])
            for key in ('saved_from_m', 'saved_to_m'):
                self.assertEqual(new[key][0] - old[key][0], shift)
                self.assertEqual(new[key][1:], old[key][1:])

    def test_disconnected_rigid_node_reports_both_sections_and_gap(self):
        first, second = self.doc.modelspace().query('LINE[layer=="duct"]')
        second.dxf.start = (0.25, 0, 0)
        self.binding['sections']['B']['from_m'] = [0.25, 0, 0]
        with self.assertRaisesRegex(ValueError, 'Disconnected rigid node R') as error:
            self.check()
        diagnostic = str(error.exception)
        self.assertIn(f'section A (handle {first.dxf.handle}) at (0.0, 0.0, 0.0) m', diagnostic)
        self.assertIn(f'section B (handle {second.dxf.handle}) at (0.25, 0.0, 0.0) m, gap 0.25 m', diagnostic)

    def test_collapsed_rigid_section_cannot_match_a_collapsed_binding(self):
        line = self.doc.modelspace().query('LINE[layer=="duct"]')[0]
        line.dxf.end = line.dxf.start
        self.binding['sections']['A']['to_m'] = [0, 0, 0]
        with self.assertRaisesRegex(ValueError, f'Rigid section A .*{line.dxf.handle}.*no distinct planar endpoints'):
            self.check()

    def test_saved_flex_and_symbol_must_agree_with_each_other(self):
        circle = self.doc.modelspace().query('CIRCLE')[0]
        flex = self.doc.modelspace().query('LINE[layer=="flex"]')[0]
        circle.dxf.center = (1 + 8e-9, 1, 0)
        flex.dxf.start = (1 - 8e-9, 1, 0)
        with self.assertRaisesRegex(ValueError, f'Flex handle {flex.dxf.handle}.*VA.*1.6e-08 m'):
            self.check()

    def test_shared_node_rejects_drift_across_individually_close_sections(self):
        first, _ = self.doc.modelspace().query('LINE[layer=="duct"]')
        first.dxf.start = (8e-9, 0, 0)
        self.tree['sections'].append({'id': 'C', 'from': 'R', 'to': 'VC'})
        self.tree['leaf_terminals']['VC'] = ['TC']
        self.allocation['terminals'].append(dict(id='TC', center_m=[-2, 1], maximum_flow_L_s=100))
        self.binding['sections']['C'] = dict(from_node='R', to_node='VC', from_m=[0, 0, 0], to_m=[-1, 1, 0])
        self.doc.modelspace().add_line((-8e-9, 0), (-1, 1), dxfattribs=dict(layer='duct'))
        with self.assertRaisesRegex(ValueError, 'gap 1.6e-08 m'):
            self.check()

    def test_displaced_terminal_endpoint_reports_vav_side_candidate(self):
        line = next(entity for entity in self.doc.modelspace().query('LINE')
                    if entity.dxf.layer == 'flex' and entity.dxf.end.y == 1)
        line.dxf.end = (2.25, 1, 0)
        with self.assertRaisesRegex(ValueError, 'saved lines at terminal TA: none') as error:
            self.check()
        self.assertIn(f'unmatched lines at VAV VA: {line.dxf.handle} to (2.25, 1.0, 0.0) m (0.25 m from TA)',
                      str(error.exception))

    def test_inherited_report_requires_final_integrity_before_write(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        runs.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=runs) as temporary:
            root = Path(temporary).resolve()
            workflow = root / 'workflow'

            def save(path, data):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding='utf-8')

            drawing = workflow / 'native/reopened/source-export.dxf'
            drawing.parent.mkdir(parents=True)
            self.doc.saveas(drawing)
            project = root / 'ducts.json'
            save(project, {'tree': self.tree})
            save(root / 'binding.json', self.binding)
            save(workflow / 'allocation/allocation.json', self.allocation)
            save(workflow / 'schedule/results.json', {'input_sha256': digest(project)})
            tasks = [dict(id='allocation', kind='air_allocation'),
                     dict(id='schedule', kind='duct_schedule', depends_on='allocation', project='ducts.json'),
                     dict(id='sheet', kind='duct_sheet', depends_on='schedule', binding='binding.json'),
                     dict(id='native', kind='duct_sheet_native', depends_on='sheet')]
            plan = root / 'plan.json'
            save(plan, {'tasks': tasks})
            report = dict(inputs={str(path): digest(path) for path in (plan, project, root / 'binding.json')},
                          artifact_hashes={path.relative_to(workflow).as_posix(): digest(path)
                                           for path in workflow.rglob('*') if path.is_file()},
                          tasks={task['id']: dict(kind=task['kind'], status='pass') for task in tasks})
            save(workflow / 'workflow.json', report)
            output = root / 'review.json'
            with patch('bsa.workflow.verify', side_effect=[{'integrity_pass': True}, {'integrity_pass': False}]):
                with self.assertRaisesRegex(ValueError, 'Workflow changed during terminal review'):
                    from_workflow(plan, workflow, 'native', output, layers=self.layers)
            self.assertFalse(output.exists())
            with patch('bsa.workflow.verify', return_value={'integrity_pass': True}):
                result = from_workflow(plan, workflow, 'native', output, layers=self.layers)
            self.assertTrue(result['workflow_integrity_pass'])
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), result)
            command = [sys.executable, '-m', 'bsa.cli', 'delivery', 'verify-terminal-connections',
                       'plan.json', 'workflow', 'native', '--out', 'cli.json']
            for key, value in self.layers.items():
                command.extend((f'--{key}-layer', value))
            completed = subprocess.run(command, cwd=root, env={**os.environ, 'BSA_PROJECT_ROOT': str(root)},
                                       capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout), result)
            if importlib.util.find_spec('mcp'):
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client

                async def check_stdio():
                    params = StdioServerParameters(command=sys.executable, args=['-m', 'bsa.mcp_server'],
                                                   cwd=str(root), env={**os.environ, 'BSA_PROJECT_ROOT': str(root)})
                    arguments = dict(plan='plan.json', workflow='workflow', native_task='native', out='mcp.json',
                                     **{f'{key}_layer': value for key, value in self.layers.items()})
                    async with stdio_client(params) as streams:
                        async with ClientSession(*streams) as session:
                            await session.initialize()
                            response = await session.call_tool('bsa_verify_terminal_connections', arguments)
                            self.assertFalse(response.isError, response.content)
                            self.assertEqual(response.structuredContent, result)

                asyncio.run(check_stdio())
            del report['artifact_hashes']['native/reopened/source-export.dxf']
            save(workflow / 'workflow.json', report)
            command[command.index('--out') + 1] = 'unbound.json'
            failed = subprocess.run(command, cwd=root, env={**os.environ, 'BSA_PROJECT_ROOT': str(root)},
                                    capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2, failed.stderr)
            self.assertIn('missing from the verified workflow evidence', failed.stderr)
            self.assertFalse((root / 'unbound.json').exists())

    def test_same_counts_and_flows_wrong_membership(self):
        self.tree['leaf_terminals']=dict(VA=['TB'],VB=['TA'])
        wrong = next(line for line in self.doc.modelspace().query('LINE')
                     if line.dxf.layer == 'flex' and line.dxf.end.y == -1)
        with self.assertRaisesRegex(ValueError, 'correspondence for VAV VA to terminal TB') as error:
            self.check()
        self.assertIn(f'saved lines at terminal TB: {wrong.dxf.handle}', str(error.exception))
        self.assertIn('declared VAV centres: VB', str(error.exception))

    def test_disconnected_flex(self):
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='flex')
        e.dxf.start=(1.01,1,0)
        with self.assertRaisesRegex(ValueError,'correspondence'):self.check()

    def test_extra_geometry_and_nonplanar_symbol(self):
        e=self.doc.modelspace().add_line((9,9),(10,10),dxfattribs=dict(layer='FLEX'))
        with self.assertRaisesRegex(ValueError,'Unbound') as error:
            self.check()
        self.assertIn(f'flex (1): {e.dxf.handle} from (9.0, 9.0, 0.0) to (10.0, 10.0, 0.0) m',
                      str(error.exception))
        self.doc.modelspace().delete_entity(e)
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='terminal')
        e.dxf.elevation=.1
        with self.assertRaisesRegex(ValueError,'planar'):self.check()

    def test_scoped_layers_cannot_alias_by_case(self):
        self.layers['vav'] = 'FLEX'
        with self.assertRaisesRegex(ValueError, 'Four distinct scoped layers'):
            self.check()

    def test_displaced_terminal_symbol_reports_candidate(self):
        from ezdxf.math import Matrix44

        symbol = self.doc.modelspace().query('LWPOLYLINE')[0]
        symbol.transform(Matrix44.translate(0.25, 0, 0))
        with self.assertRaisesRegex(ValueError, 'terminal TA') as error:
            self.check()
        self.assertIn(f'candidate handle {symbol.dxf.handle} at (2.25, 1.0, 0.0) m, deviation 0.25 m',
                      str(error.exception))

    def test_shifted_group_and_duplicate_symbol(self):
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='vav')
        before=e.dxf.center;e.dxf.center=(1.1,1,0)
        with self.assertRaisesRegex(ValueError,'correspondence') as error:
            self.check()
        self.assertIn(f'candidate handle {e.dxf.handle} at (1.1, 1.0, 0.0) m, deviation 0.1 m',
                      str(error.exception))
        e.dxf.center=before
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='terminal')
        self.doc.modelspace().add_entity(e.copy())
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.check()
