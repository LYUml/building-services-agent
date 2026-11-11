import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute
from bsa.modules import run,verify_result
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class BoundAirModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-bound-analysis-plan.json','modular/bound-air-authoring.json','modular/bound-air-budget.json','modular/bound-air-brief.md','rectangular-air/straight-wall.json','rectangular-air/binding-project.json','rectangular-air/binding.json','rectangular-air/undersized-wall.json'):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/'examples'/name).read_bytes())
        self.plan=self.root/'modular-bound-analysis-plan.json'

    def template_change(self,change):
        path=self.root/'rectangular-air/binding-project.json';data=json.loads(path.read_text());change(data);path.write_text(json.dumps(data))
        request=self.root/'modular/bound-air-budget.json';r=json.loads(request.read_text());r['sources']['project']['sha256']=digest(path);request.write_text(json.dumps(r))

    def test_saved_geometry_bound_and_same_existing_pressure_budget(self):
        from bsa.rectangular_binding import run as legacy
        out=self.root/'run';result=execute(self.plan,out);m=verify_result(out/'budget/exchange/result.json')
        self.assertEqual([r['status'] for r in result['tasks'].values()],['pass','pass','pending']);self.assertTrue(m['payload']['geometry_bound'])
        bound=json.loads((out/'budget/exchange/bound/network-input.json').read_text());self.assertEqual(bound['segments'][0]['length_m'],2)
        old=legacy(self.root/'rectangular-air/binding-project.json',self.root/'rectangular-air/straight-wall.json',self.root/'rectangular-air/binding.json',self.root/'legacy')
        old_analysis=json.loads((self.root/'legacy/analysis/network.json').read_text())
        self.assertAlmostEqual(m['payload']['required_source_total_pressure_pa'],old_analysis['required_source_total_pressure_pa'])
        self.assertEqual(digest(out/'model/native/model.ifc'),m['payload']['model']['sha256']);self.assertTrue(old['saved_ifc_geometry_match'])
        folder=out/'budget/exchange';path=folder/'bound/network-binding.json';data=json.loads(path.read_text());data['calculated_checks_pass']=False;path.write_text(json.dumps(data))
        m['artifacts']['bound/network-binding.json']=digest(path);m['payload']['binding']['sha256']=digest(path);(folder/'result.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Derived input/result binding'):verify_result(folder/'result.json')

    def test_bound_numerical_failure_keeps_geometry_evidence_and_blocks_review(self):
        self.template_change(lambda p:p['supply'].update(total_pressure_pa=0));out=self.root/'low';r=execute(self.plan,out);m=verify_result(out/'budget/exchange/result.json')
        self.assertEqual(m['execution']['status'],'completed');self.assertEqual(m['payload']['status'],'fail');self.assertTrue(m['payload']['geometry_bound'])
        self.assertEqual(r['tasks']['budget']['status'],'fail');self.assertEqual(diagnose(self.plan,out)['tasks'][2]['blocked_by'],['budget'])

    def test_duplicate_geometry_and_disabled_upstream_do_not_produce_success(self):
        out=self.root/'disabled';r=execute(self.plan,out,disabled_module_providers=['ifcopenshell.bim-authoring'])
        self.assertTrue(all(t['status']=='pending' for t in r['tasks'].values()));self.assertFalse((out/'budget').exists())
        self.template_change(lambda p:p['segments'][0].update(length_m=99));out=self.root/'duplicate';r=execute(self.plan,out)
        m=verify_result(out/'budget/exchange/result.json');self.assertEqual(m['execution']['status'],'failed');self.assertIsNone(m['payload'])

    def test_mismatching_native_geometry_rejects_and_tampering_detected(self):
        out=self.root/'baseline';execute(self.plan,out);materialized=json.loads((out/'budget/request.json').read_text())
        sources={k:(out/'budget'/row['path']).resolve() for k,row in materialized['sources'].items()};sources['model']=self.root/'rectangular-air/undersized-wall.json'
        request=self.root/'direct.json';materialized['sources']={k:dict(path=str(p.relative_to(self.root)),sha256=digest(p)) for k,p in sources.items()};request.write_text(json.dumps(materialized))
        result=run(request,'fluids.rectangular-ifc-budget',self.root/'mismatch');self.assertEqual(result['execution']['status'],'failed');self.assertIsNone(result['payload'])
        # Change a real hollow profile while preserving its metadata and ports.
        import ifcopenshell
        original=out/'model/native/model.ifc';native=ifcopenshell.open(str(original));duct=native.by_type('IfcDuctSegment')[0]
        body=next(r for r in duct.Representation.Representations if r.RepresentationIdentifier=='Body')
        body.Items[0].SweptArea.XDim*=.8;changed=self.root/'wrong-profile.ifc';native.write(str(changed))
        sources['model']=self.root/'rectangular-air/straight-wall.json';sources['ifc']=changed
        materialized['sources']={k:dict(path=str(p.relative_to(self.root)),sha256=digest(p)) for k,p in sources.items()};request.write_text(json.dumps(materialized))
        result=run(request,'fluids.rectangular-ifc-budget',self.root/'wrong-profile')
        self.assertEqual(result['execution']['status'],'failed');self.assertIsNone(result['payload'])
        (out/'budget/exchange/bound/verified-model.ifc').write_text('Changed native file')
        with self.assertRaises(ValueError):verify_result(out/'budget/exchange/result.json')
