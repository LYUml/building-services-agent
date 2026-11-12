import json
import unittest
from pathlib import Path
from bsa.spatial_terminal_ifc import run as author
from bsa.spatial_terminal_preview import run,verify
from tests import test_spatial_terminal_ifc as fixtures

class SpatialTerminalPreviewTests(unittest.TestCase):
    def test_complete_foreground_context_and_image_tampering(self):
        fixture=fixtures.SpatialTerminalIFCTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        source=fixture.f.root/'preview-model';model=author(fixture.source,fixture.basis,source)
        out=fixture.f.root/'preview';r=run(source/'terminal-ifc.json',out);verify(out)
        self.assertEqual(len(r['bindings']),3);self.assertEqual(set(r['preview']['element_labels']),{t['guid'] for t in model['terminals']})
        self.assertEqual(len(r['preview']['context_element_guids']),5);self.assertEqual(r['preview']['ports'],[]);self.assertFalse(r['design_accepted'])
        image=out/'overview/preview.png';image.write_bytes(image.read_bytes()+b'tampered')
        with self.assertRaisesRegex(ValueError,'output pins'):verify(out)
