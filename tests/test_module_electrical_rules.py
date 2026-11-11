import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.modules import run as analyse
from bsa.module_electrical_rules import run,verify,METRIC

ROOT=Path(__file__).resolve().parents[1]


class ModuleElectricalRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        request=json.loads((ROOT/'examples/modular/electrical-request.json').read_text())
        project=ROOT/'examples/electrical-paths/project.json';request['sources']['project']=dict(path=os.path.relpath(project,cls.root),sha256=digest(project))
        path=cls.root/'request.json';path.write_text(json.dumps(request));analyse(path,'bsa.single-phase-circuits',cls.root/'module');cls.producer=cls.root/'module/result.json'

    def setUp(self):
        self.case=self.root/self._testMethodName;self.case.mkdir()
        self.topology=self.case/'topology.json';self.topology.write_bytes((ROOT/'examples/electrical-paths/topology.json').read_bytes())
        basis=json.loads((ROOT/'examples/regulations-hk/project.json').read_text());basis['facts'].pop(METRIC)
        self.basis=self.case/'basis.json';self.basis.write_text(json.dumps(basis))
        # Synthetic source-byte control only;actual official-file replay is separate.
        pack=json.loads((ROOT/'regulations/hk/2026.11.08/pack.json').read_text());source=self.case/'emsd-wiring-2025.pdf';source.write_bytes(b'SYNTHETIC RULE CONTROL')
        pack['sources']['emsd_wiring_2025']['sha256']=digest(source);self.pack=self.case/'pack.json';self.pack.write_text(json.dumps(pack))

    def assess(self,name):return run(self.producer,self.topology,self.basis,self.pack,self.case,self.case/name)

    def test_full_paths_include_feeders_and_override_rejects(self):
        r=self.assess('pass');verify(self.case/'pass');self.assertEqual(r['status'],'pass')
        paths=json.loads((self.case/'pass/path-calculation.json').read_text())['paths']
        self.assertTrue(all(p['total_voltage_drop_v']>p['branch_voltage_drop_v'] for p in paths))
        self.assertEqual(len(r['assessment']['checks']),2);self.assertFalse(r['design_accepted'])
        basis=json.loads(self.basis.read_text());basis['facts'][METRIC]=dict(value=0,unit='percent_of_nominal_supply_voltage',source='Forged override');self.basis.write_text(json.dumps(basis))
        with self.assertRaisesRegex(ValueError,'cannot be overridden'):self.assess('override')
        self.assertFalse((self.case/'override').exists())

    def test_exceeded_unknown_and_missing_source_stay_distinct(self):
        topology=json.loads(self.topology.read_text());original=copy.deepcopy(topology);topology['feeders'][0]['route_length_m']=300;self.topology.write_text(json.dumps(topology))
        self.assertEqual(self.assess('exceeded')['status'],'fail');verify(self.case/'exceeded')
        self.topology.write_text(json.dumps(original));basis=json.loads(self.basis.read_text());basis['facts']['normal_service']['value']=None;self.basis.write_text(json.dumps(basis))
        self.assertEqual(self.assess('unknown')['status'],'pending');verify(self.case/'unknown')
        (self.case/'emsd-wiring-2025.pdf').unlink();self.assertEqual(self.assess('missing')['status'],'pending');verify(self.case/'missing')

    def test_coherently_rehashed_bound_fact_change_rejects(self):
        self.assess('original');folder=self.case/'original';p=folder/'bound-projects.json';bound=json.loads(p.read_text());bound['C1']['facts'][METRIC]['value']=0;p.write_text(json.dumps(bound))
        path=folder/'electrical-module-rules.json';report=json.loads(path.read_text());report['artifacts'][p.name]=digest(p);path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'bound path/facts differ'):verify(folder)
