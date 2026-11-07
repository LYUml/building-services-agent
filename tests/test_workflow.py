import json
from pathlib import Path
import tempfile
import unittest
from bsa.workflow import intake,validate_plan,execute,passages,verify
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def test_tracked_example_plans_keep_source_hashes(self):
        count=0
        for path in (ROOT/'examples').rglob('*.json'):
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            if isinstance(data,dict) and data.get('version')==1 and 'brief_sha256' in data:
                self.assertEqual(digest(path.parent/data['brief']),data['brief_sha256'],str(path))
                validate_plan(path);count+=1
        self.assertGreaterEqual(count,5)

    def fixture(self,folder):
        root=Path(folder)
        brief=root/"brief.md";brief.write_text("# Test\n\nCalculate and draw the three-light circuit.\n",encoding="utf-8")
        project=root/"project.json"
        project.write_bytes((ROOT/"examples/office-electrical/project.json").read_bytes())
        p=dict(version=1,brief="brief.md",brief_sha256=digest(brief),
            passage_dispositions={"P001":"context","P002":"requirement"},
            tasks=[dict(id="electrical",kind="electrical",project="project.json")],
            requirements=[dict(id="R1",passage="P002",quote="Calculate and draw the three-light circuit.",task="electrical",acceptance="Calculation and three editable symbols")])
        plan=root/"plan.json";plan.write_text(json.dumps(p),encoding="utf-8")
        return brief,plan,p

    def test_intake_preserves_line_evidence(self):
        with tempfile.TemporaryDirectory() as f:
            brief,plan,p=self.fixture(f)
            r=intake(brief,Path(f)/"intake.json")
            self.assertEqual(r["passages"][1]["start_line"],3)
            self.assertEqual(r["brief_sha256"],digest(brief))
            self.assertEqual(r["requirements"],[])

    def test_execution_does_not_claim_acceptance(self):
        with tempfile.TemporaryDirectory() as f:
            brief,plan,p=self.fixture(f)
            r=execute(plan,Path(f)/"run")
            self.assertTrue(r["inputs_unchanged"])
            self.assertTrue(r["execution_pass"])
            self.assertFalse(r["design_accepted"])
            self.assertEqual(r["requirements"][0]["acceptance_status"],"pending review")
            self.assertIn("electrical/devices.dxf",r["requirements"][0]["evidence"])
            self.assertTrue(verify(Path(f)/"run")["integrity_pass"])
            (Path(f)/"run/electrical/devices.dxf").write_text("tampered")
            checked=verify(Path(f)/"run")
            self.assertFalse(checked["integrity_pass"])
            self.assertIn("artifact changed",checked["issues"][0])

    def test_stale_source_missing_coverage_and_fabricated_quote_rejected(self):
        for change in (lambda p:p.update(brief_sha256="0"*64),
                       lambda p:p["passage_dispositions"].pop("P002"),
                       lambda p:p["requirements"][0].update(quote="Invented requirement"),
                       lambda p:p["tasks"][0].update(project="../elsewhere.json"),
                       lambda p:p["tasks"][0].update(id="../escape")):
            with tempfile.TemporaryDirectory() as f:
                brief,plan,p=self.fixture(f);change(p)
                plan.write_text(json.dumps(p),encoding="utf-8")
                with self.assertRaises(ProjectError):validate_plan(plan)

    def test_missing_native_tool_stays_pending(self):
        with tempfile.TemporaryDirectory() as f:
            brief,plan,p=self.fixture(f)
            p["tasks"].append(dict(id="cad",kind="native_cad",depends_on="electrical"))
            p["requirements"].append(dict(id="R2",passage="P002",quote="draw",task="cad",acceptance="native verification"))
            plan.write_text(json.dumps(p),encoding="utf-8")
            r=execute(plan,Path(f)/"run")
            self.assertEqual(r["tasks"]["cad"]["status"],"pending")
            self.assertFalse(r["execution_pass"])

if __name__=="__main__":unittest.main()
