"""Synthetic controls; real recorded-source integration is a separate private run."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.lighting_audit.calculate import calculate,verify_sources,validate_project
from bsa.lighting_audit import runtime
from bsa.providers import get_provider
from bsa.engineering_data.inputs import project_parameters
from bsa.engineering_data.quantities import quantity
from bsa.cli import digest
from bsa.modules import run,verify_result
from bsa.engineering_data.module_bridge import export,verify

ROOT=Path(__file__).resolve().parents[1]


def project():
    def fact(v,u,p,role='design'):
        return dict(value=v,unit=u,classification='declared',basis='Synthetic source control',source=dict(role=role,pointer=p))
    return dict(schema='bsa.lighting-source-project/1',title='Synthetic audit control',room_id='office',
        expected_header='Synthetic room',summary_pages=[2,3],density_display_decimals=2,
        fixture_count=fact(2,'count','/count'),auxiliary_allowance=fact(5,'W electrical','/allowance'),
        annotation_area=fact(80,'m2','/area'),products=[dict(id='P',input_power=fact(20,'W electrical','/power'),
        source_product=dict(role='design',pointer='/product'))],fixtures=[dict(id=n,product_id='P') for n in ('L1','L2')])


def summary():
    return dict(room_scene_header='Synthetic room',area_m2=100,measurements=[dict(metric='lighting_power_density',
        value=.4,unit='W/m2',calculation_surface='space',page=3)],warnings=[],excerpt_sha256='a'*64)


class LightingSourceTests(unittest.TestCase):
    def test_body_allowance_and_area_bases_stay_separate(self):
        r=calculate(project(),summary())
        self.assertEqual(r['totals']['luminaire_input_W'],40)
        self.assertEqual(r['totals']['budget_input_W'],45)
        self.assertEqual(r['totals']['annotation_budget_density_W_m2'],45/80)
        self.assertEqual(r['status'],'pass')
        self.assertFalse(r['native_calculation_executed'])
        self.assertEqual(r['regulatory_compliance'],'not_established')

    def test_mixed_products_count_actual_fixture_ids(self):
        p=project();second=copy.deepcopy(p['products'][0]);second['id']='Q';second['input_power']['value']=30
        p['products'].append(second);p['fixtures'][1]['product_id']='Q'
        s=summary();s['measurements'][0]['value']=.5
        self.assertEqual(calculate(p,s)['totals']['luminaire_input_W'],50)

    def test_mismatch_fails_and_surface_cannot_be_substituted(self):
        s=summary();s['measurements'][0]['value']=.45
        self.assertEqual(calculate(project(),s)['status'],'fail')
        s['measurements'][0]['calculation_surface']='task'
        with self.assertRaises(ValueError):calculate(project(),s)

    def test_duplicate_product_fixture_and_count_reject(self):
        for mode in ('product','fixture','count'):
            p=project()
            if mode=='product':p['products']*=2
            elif mode=='fixture':p['fixtures'][1]['id']='L1'
            else:p['fixture_count']['value']=3
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_project(p)

    def test_parameters_have_owned_electrical_units_and_explicit_unmapped_pages(self):
        rows,coverage=project_parameters(project(),'separate-project','bsa.lighting-source-audit/1')
        self.assertEqual(len(rows),4)
        self.assertIn('/summary_pages/0',coverage['unmapped_numeric_pointers'])
        self.assertEqual(next(r for r in rows if r['name']=='input_power')['quantity']['dimension'],'electrical_real_power')
        self.assertNotEqual(quantity(1,'W electrical/m2','/x')['dimension'],quantity(1,'W thermal/m2','/x')['dimension'])

    def fixture(self,root):
        def save(name,data):
            (root/name).write_text(json.dumps(data),encoding='utf-8')
        save('project.json',project());save('layout.json',dict(fixture_count=2,fixtures=[dict(id=n,product_order_code='P') for n in ('L1','L2')]))
        (root/'native.pdf').write_bytes(b'synthetic not a PDF; reader is explicitly mocked')
        save('metrics.json',dict(pdf_sha256=digest(root/'native.pdf')))
        save('design.json',dict(count=2,allowance=5,area=80,power=20,product='P',bindings=dict(fixtures=dict(sha256=digest(root/'layout.json')),core_results=dict(sha256=digest(root/'metrics.json')))))
        save('area.json',{})
        roles=dict(project='project.json',layout='layout.json',design='design.json',native_metrics='metrics.json',native_report='native.pdf',area_evidence='area.json')
        request=dict(schema='bsa.module-request/1',project_id='synthetic-lighting',scenario_id='baseline',capability='analysis.lighting.source-power-audit',
            coordinate_frame=dict(id='declared-frame',kind='source-world-si',length_unit='m',georeferenced=False),
            sources={k:dict(path=v,sha256=digest(root/v)) for k,v in roles.items()})
        save('request.json',request)
        return request

    def test_missing_host_reader_is_unavailable_not_empty_success(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp,patch.dict('os.environ',{'BSA_DIALUX_TOOLKIT_ROOT':''}):
            root=Path(tmp);self.fixture(root)
            r=run(root/'request.json','bsa.lighting-source-power',root/'unavailable')
            self.assertEqual(r['execution']['status'],'unavailable');self.assertIsNone(r['payload'])
            verify_result(root/'unavailable/result.json')

    def test_provider_export_replays_and_rejects_coherently_rehashed_calculation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp,patch.object(runtime,'configuration',return_value=(None,None,{})),patch.object(runtime,'read_summary',return_value=(summary(),{})):
            root=Path(tmp);self.fixture(root)
            r=run(root/'request.json','bsa.lighting-source-power',root/'analysis')
            self.assertEqual(r['execution']['status'],'completed')
            export(root/'analysis/result.json',root/'data',include_inputs=True)
            checked=verify(root/'data');self.assertEqual(checked['entity_count'],4)
            self.assertEqual(checked['input_parameter_count'],4)
            audit=root/'analysis/analysis/audit.json';d=json.loads(audit.read_text());d['totals']['budget_input_W']=0
            audit.write_text(json.dumps(d),encoding='utf-8');r['artifacts']['analysis/audit.json']=digest(audit)
            r['payload']['report']['sha256']=digest(audit)
            (root/'analysis/result.json').write_text(json.dumps(r),encoding='utf-8')
            with self.assertRaises(ValueError):verify_result(root/'analysis/result.json')

    def test_source_fact_cannot_drift_behind_normalized_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);request=self.fixture(root)
            provider=get_provider('bsa.lighting-source-power');paths={k:root/v['path'] for k,v in request['sources'].items()}
            provider.sources(paths)
            p=json.loads((root/'project.json').read_text());p['auxiliary_allowance']['value']=6
            (root/'project.json').write_text(json.dumps(p),encoding='utf-8')
            with self.assertRaises(ValueError):provider.sources(paths)

    def test_workflow_keeps_common_inputs_and_manual_acceptance(self):
        from bsa.workflow import execute,verify as verify_workflow
        from bsa.engineering_data.context import create
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp,patch.object(runtime,'configuration',return_value=(None,None,{})),patch.object(runtime,'read_summary',return_value=(summary(),{})):
            root=Path(tmp);request=self.fixture(root)
            ctx=create('Synthetic workflow control','baseline',root/'context.json')
            request.update(project_id=ctx['project_id'],scenario_id=ctx['scenario_id'])
            (root/'request.json').write_text(json.dumps(request),encoding='utf-8')
            text='Reconcile source power, export data and retain separate review.'
            (root/'brief.md').write_text(text,encoding='utf-8')
            tasks=[dict(id='analysis',kind='module_analysis',request='request.json',provider='bsa.lighting-source-power'),
                dict(id='data',kind='engineering_data',depends_on='analysis',include_inputs=True),
                dict(id='review',kind='manual',requires_pass=['data'],description='Separate native and engineering acceptance')]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(root/'brief.md'),project_context='context.json',
                passage_dispositions=dict(P001='requirement'),tasks=tasks,
                requirements=[dict(id='R'+str(i),passage='P001',quote=text,task=t['id'],acceptance='Separate review') for i,t in enumerate(tasks)])
            (root/'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            r=execute(root/'plan.json',root/'run')
            self.assertEqual({k:v['status'] for k,v in r['tasks'].items()},dict(analysis='pass',data='pass',review='pending'))
            self.assertTrue(verify_workflow(root/'run')['integrity_pass'])
            self.assertTrue(all(v['acceptance_status']=='pending review' for v in r['requirements']))
            from bsa.changes.core import checkpoint,impact,REUSABLE_PROVIDERS
            checkpoint(root/'run',root/'checkpoint')
            primary=json.loads((root/'project.json').read_text());primary['auxiliary_allowance']['value']=15
            design=json.loads((root/'design.json').read_text());design['allowance']=15
            for filename,data in [('project.json',primary),('design.json',design)]:
                (root/filename).write_text(json.dumps(data),encoding='utf-8')
            for role in ('project','design'):request['sources'][role]['sha256']=digest(root/request['sources'][role]['path'])
            (root/'request.json').write_text(json.dumps(request),encoding='utf-8')
            delta=impact(root/'checkpoint')['tasks']['analysis']['parameter_changes']
            self.assertEqual(delta['total_changes'],1)
            self.assertEqual(delta['changes'][0]['name'],'auxiliary_allowance')
            self.assertEqual(delta['changes'][0]['delta_si'],10)
            self.assertNotIn('bsa.lighting-source-power',REUSABLE_PROVIDERS)
            current=execute(root/'plan.json',root/'current')
            self.assertEqual(current['tasks']['analysis']['status'],'pass')
            updated=json.loads((root/'current/analysis/analysis/audit.json').read_text())
            self.assertEqual(updated['totals']['budget_input_W'],55)
