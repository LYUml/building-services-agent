import json
import math
from pathlib import Path
import tempfile
import unittest

from bsa.cli import digest
from bsa.raster_chart_points import run as points_run
from bsa.round_duct_chart_check import run,ROOT
from tests import test_raster_chart_points as raster_tests


class RoundDuctChartCheckTests(unittest.TestCase):
    def fixture(self,root):
        project,data=raster_tests.RasterChartPointsTests().fixture(root)
        data['axes']=dict(x=dict(quantity='Air quantity',unit='L/s'),y=dict(quantity='Friction gradient',unit='Pa/m'))
        project.write_text(json.dumps(data));points_run(project,root/'points')
        record=root/'points/points.json'
        air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009)
        basis=dict(points_project=project.name,points_result='points/points.json',points_result_sha256=digest(record),air=air,
            air_basis={key:dict(classification='assumed',basis='Synthetic trial property, not source acceptance') for key in air},
            diameters=[dict(point_id='P1',diameter_m=.5,source_label='Synthetic500mm',identity_observation='Test coordinate, not a real labelled source curve')])
        path=root/'basis.json';path.write_text(json.dumps(basis));return path,basis

    def test_actual_engine_residual_and_mismatch_retention(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);path,basis=self.fixture(root);result=run(path,root/'comparison')
            row=result['points'][0];d=.5;q=row['manual_point']['x']/1000
            velocity=4*q/(math.pi*d*d);rho=1.2;mu=1.81e-5
            f=row['equation_gradient_Pa_m']*2*d/(rho*velocity*velocity)
            re=rho*velocity*d/mu
            residual=1/math.sqrt(f)+2*math.log10(.00009/(3.7*d)+2.51/(re*math.sqrt(f)))
            self.assertLess(abs(residual),1e-10)
            self.assertFalse(row['endpoint_ranges_overlap'])
            self.assertNotEqual(row['center_relative_difference'],0)
            self.assertFalse(result['curve_identity_verified']);self.assertFalse(result['design_accepted'])
            with self.assertRaises(ValueError):run(path,root/'comparison')

    def test_forged_points_with_updated_declared_hash_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);path,basis=self.fixture(root);record=root/'points/points.json'
            data=json.loads(record.read_text());data['points'][0]['y']*=2;record.write_text(json.dumps(data))
            basis['points_result_sha256']=digest(record);path.write_text(json.dumps(basis))
            with self.assertRaisesRegex(ValueError,'current source replay'):run(path,root/'comparison')
            self.assertFalse((root/'comparison').exists())

    def test_missing_duplicate_and_invalid_diameter_interpretations_reject(self):
        for case in ('missing','duplicate','negative','no_basis'):
            with self.subTest(case=case),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                root=Path(folder);path,basis=self.fixture(root)
                if case=='missing':basis['diameters'][0]['point_id']='other'
                elif case=='duplicate':basis['diameters']*=2
                elif case=='negative':basis['diameters'][0]['diameter_m']=-1
                else:basis['air_basis']['viscosity_Pa_s']['basis']=''
                path.write_text(json.dumps(basis))
                with self.assertRaises(ValueError):run(path,root/'comparison')
                self.assertFalse((root/'comparison').exists())

    def test_source_changed_after_points_rejects_without_comparison(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);path,basis=self.fixture(root);(root/'source.txt').write_text('Changed source')
            with self.assertRaises(ValueError):run(path,root/'comparison')
            self.assertFalse((root/'comparison').exists())

    def test_incompatible_axis_units_are_not_silently_converted(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);path,basis=self.fixture(root);project=root/'project.json'
            data=json.loads(project.read_text());data['axes']['x']['unit']='m3/s';project.write_text(json.dumps(data))
            points_run(project,root/'other-points');record=root/'other-points/points.json'
            basis.update(points_result='other-points/points.json',points_result_sha256=digest(record));path.write_text(json.dumps(basis))
            with self.assertRaisesRegex(ValueError,'requires L/s and Pa/m'):run(path,root/'comparison')
            self.assertFalse((root/'comparison').exists())

    def test_comparison_cannot_write_inside_saved_point_results(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);path,basis=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'outside saved point results'):run(path,root/'points/nested')
            self.assertFalse((root/'points/nested').exists())


if __name__=='__main__':unittest.main()
