"""Saved-DXF reconstruction tests; synthetic manifest is not native host evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.hvac_report import connection_summary


class ConnectionSummaryTests(unittest.TestCase):
    def setUp(self):
        from tests.test_air_terminal_drawing import TerminalDrawingTests
        fixture=TerminalDrawingTests();fixture.setUp();self.fixture=fixture
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.directory=self.root/'workflow'
        self.drawing=self.directory/'native/reopened/source-export.dxf'
        self.drawing.parent.mkdir(parents=True);fixture.doc.saveas(self.drawing)
        def save(path,value):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value),encoding='utf-8');return path
        self.save=save
        allocation=save(self.directory/'allocation/allocation.json',fixture.allocation)
        project=save(self.root/'ducts.json',dict(tree=fixture.tree))
        binding=save(self.root/'binding.json',fixture.binding)
        schedule=save(self.directory/'ducts/results.json',dict(input_sha256=digest(project)))
        self.paths=[allocation,self.directory/'lookup/terminal-results.json',schedule]
        self.workflow=dict(inputs={str(p):digest(p) for p in (project,binding)},tasks={name:dict(kind=kind,status='pass') for name,kind in [('native','duct_sheet_native'),('sheet','duct_sheet'),('ducts','duct_schedule'),('allocation','air_allocation')]})
        save(self.directory/'workflow.json',self.workflow)
        self.record=fixture.check()|dict(inputs={str(p):digest(p) for p in (self.drawing,allocation,project,binding)},layers=fixture.layers,
            workflow_sha256=digest(self.directory/'workflow.json'),schedule_sha256=digest(schedule),lineage=['native','sheet','ducts','allocation'])
        self.review=self.root/'review.json'

    def summarize(self):
        self.save(self.review,self.record)
        return connection_summary(self.directory,self.workflow,self.paths,self.review)

    def test_saved_geometry_summary(self):
        summary=self.summarize()
        self.assertIn('2 terminals, 2 groups and 2 rigid sections',summary)
        self.assertIn('1.000 m',summary)
        self.assertIn('does not verify physical ports',summary)

    def test_forged_review_counts(self):
        self.record['terminal_count']=999
        with self.assertRaisesRegex(ValueError,'differs from saved geometry'):self.summarize()

    def test_changed_geometry_even_with_rewritten_review_hash(self):
        line=next(e for e in self.fixture.doc.modelspace() if e.dxf.layer=='flex')
        line.dxf.end=(20,20,0);self.fixture.doc.saveas(self.drawing)
        self.record['inputs'][str(self.drawing)]=digest(self.drawing)
        with self.assertRaisesRegex(ValueError,'correspondence'):self.summarize()

    def test_other_workflow_and_failed_ancestry(self):
        self.record['workflow_sha256']='other'
        with self.assertRaisesRegex(ValueError,'another workflow'):self.summarize()
        self.record['workflow_sha256']=digest(self.directory/'workflow.json')
        self.workflow['tasks']['native']['status']='pending'
        with self.assertRaisesRegex(ValueError,'Passing'):self.summarize()

    def test_replaced_binding_source(self):
        binding=next(p for p in self.workflow['inputs'] if p.endswith('binding.json'))
        self.workflow['inputs'][binding]='other'
        with self.assertRaisesRegex(ValueError,'outside workflow'):self.summarize()
