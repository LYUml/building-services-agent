import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell

from bsa.rectangular_tee import run,inspect,validate
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class RectangularTeeTests(unittest.TestCase):
    def source(self):
        return json.loads((ROOT/'examples/rectangular-tee/project.json').read_text())

    def test_native_material_ports_rigid_placement_and_rejected_changes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for case in ('identity','rotated'):
                data=self.source()
                if case=='rotated':
                    data['placement'].update(origin_m=[12,-7,4],rotation=[[0,0,1],[0,1,0],[-1,0,0]])
                    data.update(internal_width_m=.5,internal_height_m=.25,wall_thickness_m=.004,main_half_length_m=.75,branch_length_m=.65)
                project=root/(case+'.json');project.write_text(json.dumps(data))
                before=digest(project);result=run(project,root/case)
                self.assertEqual(digest(project),before)
                self.assertTrue(result['geometry_checks_pass']);self.assertFalse(result['design_accepted'])
                self.assertEqual(result['checks']['euler_characteristic'],-2)
                self.assertEqual(result['checks']['bore_probe_overlap_m3'],[0,0])
                self.assertAlmostEqual(result['checks']['native_material_volume_m3'],.0087195 if case=='identity' else .010997344,places=12)
                model_path=root/case/'rectangular-tee.ifc'
                for mutation in ('inner_width','port','filled'):
                    model=ifcopenshell.open(str(model_path));obj=model.by_type('IfcDuctFitting')[0]
                    wall=obj.Representation.Representations[0].Items[0]
                    if mutation=='inner_width':wall.SecondOperand.FirstOperand.SweptArea.XDim+=.001
                    elif mutation=='port':next(p for p in model.by_type('IfcDistributionPort') if p.Name=='main-a').FlowDirection='SOURCE'
                    else:wall.Operator='UNION'
                    bad=root/(case+'-'+mutation+'.ifc');model.write(str(bad))
                    with self.assertRaises(ValueError):inspect(bad,data)

    def test_invalid_source_geometry_and_frames(self):
        for changes in [dict(wall_thickness_m=0),dict(internal_width_m=True),dict(main_half_length_m=.1),dict(source='')]:
            with self.assertRaises(ValueError):validate(self.source()|changes)
        data=self.source();data['placement']['rotation']=[[-1,0,0],[0,1,0],[0,0,1]]
        with self.assertRaises(ValueError):validate(data)
        data=self.source();data['port_directions']={name:'SOURCE' for name in data['port_directions']}
        with self.assertRaises(ValueError):validate(data)
