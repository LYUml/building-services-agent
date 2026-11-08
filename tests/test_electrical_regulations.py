import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.electrical_regulations import run
from bsa.workflow import execute, passages, verify

ROOT=Path(__file__).resolve().parents[1]


class ElectricalRegulationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for src,name in [('examples/electrical-paths/project.json','project.json'),('examples/electrical-paths/topology.json','topology.json'),('examples/regulations-hk/project.json','basis.json'),('regulations/hk/2026.11.08/pack.json','pack.json')]:
            (self.root/name).write_bytes((ROOT/src).read_bytes())
        self.official=self.root/'emsd-wiring-2025.pdf';self.official.write_bytes(b'SYNTHETIC TEST SOURCE NOT AN OFFICIAL PDF')
        self.edit('pack.json',lambda p:p['sources']['emsd_wiring_2025'].update(sha256=digest(self.official)))

    def edit(self,name,fn):
        path=self.root/name;data=json.loads(path.read_text());fn(data);path.write_text(json.dumps(data))

    def run_check(self):
        return run(*(self.root/n for n in ('project.json','topology.json','basis.json','pack.json')),self.root,self.root/'output')

    def test_fresh_calculation_replaces_supplied_metric(self):
        self.edit('basis.json',lambda p:p['facts']['installation_origin_to_fixed_equipment_voltage_drop'].update(value=999))
        r=self.run_check();self.assertEqual(r['status'],'pass')
        self.assertAlmostEqual(r['circuit_checks']['C1']['checks'][0]['value'],4.4/230*100)
        self.assertIn(str(self.official.resolve()),r['inputs'])
        self.assertFalse(r['design_accepted'])

    def test_branch_failure_is_not_cleared_by_passing_rule(self):
        self.edit('project.json',lambda p:p['circuits'][0].update(breaker_a=1))
        r=self.run_check();self.assertTrue(r['supported_regulation_checks_pass'])
        self.assertFalse(r['branch_checks_pass']);self.assertEqual(r['status'],'fail')

    def test_long_upstream_path_requires_review(self):
        self.edit('topology.json',lambda p:p['feeders'][0].update(route_length_m=300))
        r=self.run_check();self.assertTrue(r['branch_checks_pass'])
        self.assertEqual(r['status'],'pending')
        self.assertTrue(all(c['checks'][0]['status']=='review_required' for c in r['circuit_checks'].values()))

    def test_missing_source_stays_pending(self):
        self.official.unlink();r=self.run_check()
        self.assertEqual(r['status'],'pending');self.assertEqual(r['missing_sources'],[str(self.official.resolve())])

    def test_workflow_tracks_topology_and_blocks_false_execution_pass(self):
        self.edit('project.json',lambda p:p['circuits'][0].update(breaker_a=1))
        brief=self.root/'brief.md';brief.write_text('Calculate complete paths and check selected jurisdiction rules without clearing branch failures.')
        row=passages(brief)[0]
        plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},
                  tasks=[dict(id='check',kind='electrical_regulations',project='project.json',topology='topology.json',basis='basis.json',pack='pack.json',sources='.')],
                  requirements=[dict(id='R1',passage=row['id'],quote=row['text'],task='check',acceptance=row['text'])])
        path=self.root/'plan.json';path.write_text(json.dumps(plan))
        r=execute(path,self.root/'workflow');self.assertEqual(r['tasks']['check']['status'],'fail')
        self.assertFalse(r['execution_pass']);self.assertTrue(verify(self.root/'workflow')['integrity_pass'])
        self.edit('topology.json',lambda p:p['feeders'][0].update(route_length_m=1))
        self.assertFalse(verify(self.root/'workflow')['integrity_pass'])
