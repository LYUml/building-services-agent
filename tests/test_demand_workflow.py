import json
from pathlib import Path
import tempfile
import unittest
from bsa.workflow import execute,verify
from bsa.cli import digest


class DemandWorkflowTests(unittest.TestCase):
    def test_calculated_unknown_rejected_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def save(name,value):
                p=root/name;p.write_text(json.dumps(value),encoding='utf-8');return p
            source=root/'basis.txt';source.write_text('Synthetic demand test, not engineering source')
            refs={'basis.txt':digest(source)}
            p=save('probability.json',dict(inputs={k:dict(value=v,unit='L/s' if k=='fixture_flow_L_s' else '1',classification='assumed',source='Synthetic') for k,v in dict(count=100,operating_probability=.01,fixture_flow_L_s=.1,exceedance_probability=.01).items()},model_facts=dict(identical_appliances=True,independent_use=True),basis='Synthetic independent appliances',references=refs))
            du=dict(fixtures=[dict(id='A',count=4,DU_per_fixture=2,source='Synthetic',classification='assumed')],frequency_factor=dict(value=.5,source='Synthetic',classification='assumed'),model_facts=dict(connected_inventory_verified=True,frequency_classification_verified=True),basis='Synthetic connected fixtures',references=refs)
            save('du.json',du)
            brief=root/'brief.md';brief.write_text('Calculate demand and retain downstream engineering review.\n')
            tasks=[dict(id='water',kind='plumbing_demand',project=p.name),dict(id='drain',kind='discharge_demand',project='du.json'),dict(id='review',kind='manual',requires_pass=['water','drain'],description='Engineering review pending')]
            plan=save('plan.json',dict(version=1,brief=brief.name,brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,requirements=[dict(id='R'+str(i),passage='P001',quote='Calculate demand and retain downstream engineering review.',task=t['id'],acceptance='Scoped numerical evidence; engineering acceptance pending') for i,t in enumerate(tasks)]))
            r=execute(plan,root/'calculated');self.assertEqual(r['tasks']['water']['status'],'pass');self.assertEqual(r['tasks']['drain']['status'],'pass');self.assertFalse(r['design_accepted']);self.assertTrue(verify(root/'calculated')['integrity_pass'])
            du['model_facts']['connected_inventory_verified']=None;save('du.json',du)
            r=execute(plan,root/'unknown');self.assertEqual(r['tasks']['drain']['status'],'pending');self.assertEqual(r['tasks']['review']['status'],'pending')
            du['model_facts']['connected_inventory_verified']=False;save('du.json',du)
            r=execute(plan,root/'rejected');self.assertEqual(r['tasks']['drain']['status'],'fail');self.assertEqual(r['tasks']['review']['status'],'pending')
            source.write_text('Changed source');self.assertFalse(verify(root/'rejected')['integrity_pass'])
