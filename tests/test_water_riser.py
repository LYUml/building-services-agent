"""Independent vertical water/electrical reuse acceptance fixtures."""
import importlib.util
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('ifcopenshell', 'manifold3d', 'fluids')), 'requires water/IFC/clash runtimes')
class IndependentWaterRiserTests(unittest.TestCase):
    def test_independent_brief_to_selected_saved_model_and_electrical_drawing(self):
        from bsa.workflow import execute, verify
        import ezdxf
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.util.shape
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'run'
            result = execute(ROOT/'examples/water-riser/plan.json', out)
            self.assertTrue(result['execution_pass'])
            self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(out)['integrity_pass'])
            design = json.loads((out/'water/model-design.json').read_text())
            self.assertEqual(design['selected']['choices'], {'RISER': 'D32'})
            self.assertEqual(design['original_candidate_count'], 4)
            self.assertFalse(design['baseline_analysis']['calculated_checks_pass'])
            self.assertTrue(design['saved_ifc_resize_checks_pass'])
            self.assertTrue(design['stable_object_port_ids_match'])
            analysis = json.loads((out/'water/selected-coordination/analysis/network.json').read_text())
            segment = analysis['segments'][0]
            # Independent dimensional checks: Q/A, rho*g*dz, and pressure budget.
            velocity = .001/(math.pi*.032**2/4)
            self.assertAlmostEqual(segment['velocity_m_s'], velocity, places=10)
            self.assertAlmostEqual(segment['elevation_pressure_pa'], 998*9.80665*5, places=7)
            self.assertAlmostEqual(segment['minor_pa'], 3*998*velocity**2/2, places=7)
            self.assertAlmostEqual(analysis['required_source_total_pressure_pa'],
                                   100000+998*9.80665*5+segment['dissipative_loss_pa'], places=7)
            self.assertAlmostEqual(analysis['nodes'][1]['total_pressure_pa'],
                                   180000-998*9.80665*5-segment['dissipative_loss_pa'], places=7)
            native = ifcopenshell.open(str(out/'water/selected-coordination/bim/model.ifc'))
            settings = ifcopenshell.geom.settings()
            from bsa.circular_geometry import configure
            configure(settings)
            pipes = native.by_type('IfcPipeSegment')
            self.assertEqual(len(pipes), 2)
            for pipe in pipes:
                shape = ifcopenshell.geom.create_shape(settings, pipe)
                volume = ifcopenshell.util.shape.get_volume(shape.geometry)
                self.assertAlmostEqual(volume, math.pi*(.04**2-.032**2)*2.5/4,
                                       delta=1e-6)
            qa = json.loads((out/'qa/clash.json').read_text())
            self.assertTrue(qa['calculated_checks_pass'])
            self.assertEqual(qa['physical_element_count'], 4)
            self.assertEqual(len(qa['outside_region_checks']), 3)
            electrical = json.loads((out/'electrical/calculations.json').read_text())
            circuits = {c['id']:c for c in electrical['circuits']}
            self.assertAlmostEqual(circuits['PUMP-SUPPLY']['design_current_a'], 750/.85/230)
            self.assertAlmostEqual(circuits['SERVICE-LIGHTS']['connected_electrical_kw'], .036)
            drawing = ezdxf.readfile(out/'electrical/devices.dxf')
            self.assertEqual(len(drawing.modelspace().query('CIRCLE')), 3)
            self.assertEqual(drawing.header['$INSUNITS'], 6)

    def test_inadequate_supply_retains_failed_model_and_blocks_dependent_qa(self):
        from bsa.workflow import execute, verify
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT/'examples/water-riser', root/'inputs')
            path = root/'inputs/network.json'
            data = json.loads(path.read_text())
            data['supply']['total_pressure_pa'] = 140000
            data['sources']['test'] += ' Negative test revision: supply reduced to 140 kPa.'
            path.write_text(json.dumps(data))
            result = execute(root/'inputs/plan.json', root/'run')
            self.assertEqual(result['tasks']['electrical']['status'], 'pass')
            self.assertEqual(result['tasks']['water']['status'], 'fail')
            self.assertEqual(result['tasks']['qa']['status'], 'pending')
            self.assertTrue((root/'run/water/baseline-bim/model.ifc').is_file())
            self.assertFalse((root/'run/water/selected-coordination').exists())
            self.assertTrue(verify(root/'run')['integrity_pass'])


if __name__ == '__main__':
    unittest.main()
