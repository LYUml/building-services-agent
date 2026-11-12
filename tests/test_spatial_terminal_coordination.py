import copy
import json
import unittest
from bsa.spatial_terminal_ifc import run as author
from bsa.spatial_terminal_coordination import run,verify,classify
from tests import test_spatial_terminal_performance as fixtures

class SpatialTerminalCoordinationTests(unittest.TestCase):
    def test_overlapping_added_terminals_fail_and_removed_findings_reject(self):
        f=fixtures.SpatialTerminalPerformanceTests();f.setUp();self.addCleanup(f.temp.cleanup)
        path=f.plan.parent/'terminal-design-basis.json';bases=json.loads(path.read_text());room=next(iter(bases.values()));first=room['terminals'][0];second=copy.deepcopy(first);second['id']+='B';second['center_m'][0]+=.05;room['terminals'].append(second);path.write_text(json.dumps(bases))
        products=f.plan.parent/'performance-selections.json';selections=json.loads(products.read_text());selections[second['id']]=copy.deepcopy(selections[first['id']]);products.write_text(json.dumps(selections))
        out,_=f.run_workflow();performance=out/'terminal-performance/terminal-performance.json';result=json.loads(performance.read_text());basis=f.root/'ifc-basis.json';basis.write_text(json.dumps({name:dict(size_m=dict(value=[.6,.6,.1],unit='m',source='Synthetic overlapping envelope control',classification='design_choice'),bottom_above_floor_m=dict(value=2.7,unit='m',source='Synthetic elevation',classification='assumed')) for name in result['calculation']['terminals']}))
        model=f.root/'terminal-model';author(performance,basis,model)
        policy=f.root/'policy.json';policy.write_text(json.dumps(dict(scope='all represented non-feature non-virtual IfcElements',sources={'test':'Synthetic50mm clearance control;not regulation'},source='test',minimum_clearance_m=.05,intersection_tolerance_m=.0001,contact_tolerance_m=.0001,overlap_volume_tolerance_m3=1e-10,maximum_boolean_pairs=1000,allowed_contacts=[])))
        target=f.root/'coordination';r=run(model/'terminal-ifc.json',policy,target);self.assertEqual(verify(target)['summary']['status'],'fail');self.assertGreater(len(r['summary']['partitions']['terminal_terminal']['intersections']),0);self.assertFalse(r['design_accepted'])
        record=target/'terminal-coordination.json';r['calculation']['intersections']=[];r['summary']['status']='pass';record.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'native replay'):verify(target)

    def test_existing_only_findings_still_fail_whole_model(self):
        report=dict(terminals=[dict(guid='new')]);hit=dict(pair=['oldA','oldB'])
        raw=dict(elements=[dict(guid='new')],intersections=[hit],clearance_violations=[],checks=dict(no_intersections=False),calculated_checks_pass=False)
        r=classify(report,raw);self.assertEqual(r['status'],'fail');self.assertEqual(r['partitions']['existing_existing']['intersections'],[hit])
