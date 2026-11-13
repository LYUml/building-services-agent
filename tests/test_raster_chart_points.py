import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from bsa.cli import digest
from bsa.raster_chart_points import run,ROOT


class RasterChartPointsTests(unittest.TestCase):
    def fixture(self,root):
        image=root/'chart.png';Image.new('RGB',(1001,1001),'white').save(image)
        source=root/'source.txt';source.write_text('Synthetic coordinate calibration; no actual curve.')
        data=dict(source=dict(path=source.name,sha256=digest(source),locator='Synthetic coordinate axes'),image=dict(path=image.name,sha256=digest(image)),axes=dict(x=dict(quantity='Synthetic x',unit='1'),y=dict(quantity='Synthetic y',unit='1')),
            calibration=dict(x1=dict(pixel=[0,1000],value=20),x2=dict(pixel=[1000,1000],value=200000),
                y1=dict(pixel=[0,1000],value=.1),y2=dict(pixel=[0,0],value=100),x_scale='log10',y_scale='log10'),
            pixel_uncertainty=2,checks=[dict(pixel=[250,750],expected=[200,10**-.25]),dict(pixel=[750,250],expected=[20000,10**1.25])],
            points=[dict(id='P1',pixel=[500,500],series='coordinate probe',interpretation='Synthetic calibration only')])
        project=root/'project.json';project.write_text(json.dumps(data));return project,data

    def test_pinned_upstream_log_axes_and_pixel_bounds(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);project,data=self.fixture(root);before=digest(project)
            result=run(project,root/'out');row=result['points'][0]
            self.assertAlmostEqual(row['x'],2000);self.assertAlmostEqual(row['y'],10**.5)
            self.assertLess(row['x_range'][0],2000);self.assertGreater(row['x_range'][1],2000)
            self.assertLess(row['y_range'][0],10**.5);self.assertGreater(row['y_range'][1],10**.5)
            self.assertTrue(result['axis_tick_checks_pass']);self.assertFalse(result['curve_identity_verified']);self.assertFalse(result['design_accepted'])
            self.assertEqual(before,digest(project));self.assertTrue((root/'out/points.csv').is_file())
            with self.assertRaisesRegex(ValueError,'New output'):run(project,root/'out')

    def test_invalid_calibration_or_points_create_no_output(self):
        for case in ('tick','nonpositive_log','rotated','outside','duplicate','nan','excess_uncertainty','no_held_ticks','missing_units'):
            with self.subTest(case=case),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                root=Path(folder);project,data=self.fixture(root)
                if case=='tick':data['checks'][0]['expected'][0]=900
                elif case=='nonpositive_log':data['calibration']['x1']['value']=0
                elif case=='rotated':data['calibration']['x2']['pixel'][1]=999
                elif case=='outside':data['points'][0]['pixel']=[1001,500]
                elif case=='duplicate':data['points']*=2
                elif case=='nan':data['pixel_uncertainty']=float('nan')
                elif case=='excess_uncertainty':data['pixel_uncertainty']=600
                elif case=='missing_units':data['axes']['x']['unit']=''
                else:data['checks']=[dict(pixel=[0,1000],expected=[20,.1]),dict(pixel=[1000,0],expected=[200000,100])]
                project.write_text(json.dumps(data))
                with self.assertRaises(ValueError):run(project,root/'out')
                self.assertFalse((root/'out').exists())

    def test_source_change_upstream_change_and_unselected_workspace_reject(self):
        for case in ('source','upstream','workspace'):
            with self.subTest(case=case),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                root=Path(folder);project,data=self.fixture(root)
                if case=='source':(root/'source.txt').write_text('Changed')
                with patch('bsa.raster_chart_points.UPSTREAM_SHA256','0'*64) if case=='upstream' else patch('bsa.raster_chart_points.allowed',return_value=case!='workspace'):
                    with self.assertRaises(ValueError):run(project,root/'out')
                self.assertFalse((root/'out').exists())

    def test_linear_reversed_axes_and_clipped_uncertainty(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);project,data=self.fixture(root)
            data['calibration'].update(x_scale='linear',y_scale='linear')
            data['calibration']['x1']['value']=100;data['calibration']['x2']['value']=0
            data['calibration']['y1']['value']=0;data['calibration']['y2']['value']=100
            data['checks']=[dict(pixel=[250,750],expected=[75,25]),dict(pixel=[750,250],expected=[25,75])]
            data['points'][0]['pixel']=[0,1000];project.write_text(json.dumps(data))
            row=run(project,root/'out')['points'][0]
            self.assertEqual(row['x'],100);self.assertEqual(row['y'],0)
            self.assertEqual(row['x_range'][1],100);self.assertEqual(row['y_range'][0],0)


if __name__=='__main__':unittest.main()
