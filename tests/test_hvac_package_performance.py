import json
from unittest import TestCase
from unittest.mock import patch
from bsa.hvac_package import run
from bsa.cli import digest
from tests import test_terminal_performance as fixtures


class PackagePerformanceTests(TestCase):
    def setUp(self):
        f=fixtures.TerminalPerformanceTests();f.setUp();self.addCleanup(f.fixture.temp.cleanup)
        self.root=f.root;self.settings=f.settings;self.source=f.source
        self.font=self.root/'font.ttf';self.font.write_text('Mock renderer only;no PDF authored')

    def package(self,out,report=None,settings=True):
        # Real source-bound workflow/performance calculation;PDF/report plumbing
        # mocked explicitly. Native CAD and real PDF are checked in actual replay.
        with patch('bsa.hvac_report.run',side_effect=report or (lambda *a,**kw:dict(scope='Mock report plumbing'))),patch('bsa.hvac_report_pdf.run',return_value=dict(scope='Mock PDF plumbing;no PDF')):
            return run(self.root/'plan.json',out,font=self.font,terminal_performance=self.settings if settings else None)

    def test_real_stage_inherits_flow_and_enters_package_links_and_hashes(self):
        out=self.root/'package';result=self.package(out)
        self.assertEqual(result['stage_errors'],{})
        self.assertEqual(len(result['stages']['terminal_performance']['terminals']),2)
        self.assertEqual(result['artifact_hashes'][str((out/'terminal-performance/performance.json').relative_to(out))],digest(out/'terminal-performance/performance.json'))
        self.assertIn('terminal-performance/index.html',(out/'index.html').read_text())
        self.assertIn(str(self.source),result['terminal_performance_configuration_inputs'])
        self.assertFalse(result['design_accepted'])
        omitted=self.package(self.root/'omitted',settings=False)
        self.assertNotIn('terminal_performance',omitted['stages'])

    def test_late_source_mutation_suppresses_package_manifest(self):
        def mutate(*a,**kw):self.source.write_text('Changed after performance');return dict(scope='Mock report')
        out=self.root/'mutated'
        with self.assertRaisesRegex(ValueError,'Terminal performance settings/source changed'):self.package(out,report=mutate)
        self.assertFalse((out/'package.json').exists())

    def test_stage_error_retained_and_no_success_link(self):
        out=self.root/'failed'
        with patch('bsa.terminal_performance.run',side_effect=ValueError('Controlled source correspondence failure')):
            result=self.package(out)
        self.assertEqual(result['status'],'incomplete');self.assertIn('terminal_performance',result['stage_errors'])
        self.assertNotIn('terminal-performance/index.html',(out/'index.html').read_text())

    def test_invalid_settings_reject_before_workflow_creation(self):
        self.source.write_text('Changed before execution');out=self.root/'invalid'
        with self.assertRaisesRegex(ValueError,'source hash'):self.package(out)
        self.assertFalse(out.exists())
