import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.ifc_space_surfaces import prepare,run

ROOT=Path(__file__).resolve().parents[1]


class IfcSpaceSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](self.root/'native')

    def test_native_concave_spaces_complete_and_originals_unchanged(self):
        before=digest(self.source);r=run(self.source,self.root/'intake',length_tolerance_m=1e-6,area_tolerance_m2=1e-8)
        self.assertEqual(sorted(s['floor_area_m2'] for s in r['spaces']),[14,24,30])
        self.assertEqual(sorted(s['native_volume_m3'] for s in r['spaces']),[42,72,90])
        self.assertTrue(r['complete_saved_space_coverage']);self.assertEqual(digest(self.source),before)
        with self.assertRaisesRegex(ValueError,'new separate'):run(self.source,self.root/'intake',length_tolerance_m=1e-6,area_tolerance_m2=1e-8)

    def test_missing_body_and_tilted_space_reject_without_partial_output(self):
        import ifcopenshell
        for kind in ('missing-body','tilted'):
            model=ifcopenshell.open(str(self.source));space=next(s for s in model.by_type('IfcSpace') if s.Name=='Office')
            if kind=='missing-body':space.Representation=None
            else:space.ObjectPlacement.RelativePlacement.Axis=model.create_entity('IfcDirection',DirectionRatios=(0.,.2,1.))
            path=self.root/(kind+'.ifc');model.write(str(path))
            with self.assertRaises(ValueError):run(path,self.root/kind,length_tolerance_m=1e-6,area_tolerance_m2=1e-8)
            self.assertFalse((self.root/kind).exists())

    def test_profile_hole_is_not_filled(self):
        import ifcopenshell
        model=ifcopenshell.open(str(self.source));space=next(s for s in model.by_type('IfcSpace') if s.Name=='Office')
        solid=next(r for r in space.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0]
        ring=[(.5,.5),(1.,.5),(1.,1.),(.5,1.),(.5,.5)]
        hole=model.create_entity('IfcPolyline',Points=[model.create_entity('IfcCartesianPoint',Coordinates=p) for p in ring])
        solid.SweptArea=model.create_entity('IfcArbitraryProfileDefWithVoids',ProfileType='AREA',OuterCurve=solid.SweptArea.OuterCurve,InnerCurves=[hole])
        path=self.root/'hole.ifc';model.write(str(path))
        with self.assertRaisesRegex(ValueError,'holes'):prepare(path,length_tolerance_m=1e-6,area_tolerance_m2=1e-8)

    def test_curved_profile_rejects_instead_of_accepting_tessellation_as_polygon(self):
        import ifcopenshell
        model=ifcopenshell.open(str(self.source));space=next(s for s in model.by_type('IfcSpace') if s.Name=='Office')
        solid=next(r for r in space.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0]
        solid.SweptArea=model.create_entity('IfcCircleProfileDef',ProfileType='AREA',Radius=2.)
        path=self.root/'circle.ifc';model.write(str(path))
        with self.assertRaisesRegex(ValueError,'linear polygon'):prepare(path,length_tolerance_m=1e-6,area_tolerance_m2=1e-8)

    def test_native_millimetre_units_become_world_si_without_double_scaling(self):
        import ifcopenshell
        import ifcopenshell.util.unit
        model=ifcopenshell.util.unit.convert_file_length_units(ifcopenshell.open(str(self.source)),'MILLIMETER')
        path=self.root/'millimetres.ifc';model.write(str(path))
        _,_,audit=prepare(path,length_tolerance_m=1e-6,area_tolerance_m2=1e-8)
        self.assertEqual(audit['length_unit_scale_to_m'],.001)
        self.assertEqual(sorted(s['floor_area_m2'] for s in audit['spaces']),[14,24,30])

    @unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit MOOSAS runtime required')
    def test_full_ifc_to_common_recognition_and_changed_original_rejects(self):
        from bsa.modules import run as module,verify_result
        run(self.source,self.root/'intake',length_tolerance_m=1e-6,area_tolerance_m2=1e-8)
        result=module(self.root/'intake/request.json','moosas.surface-room-recognition',self.root/'recognized',runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps'))
        self.assertEqual(result['execution']['status'],'completed',result['execution'])
        verify_result(self.root/'recognized/result.json')
        self.assertEqual(sorted(s['floor_area_m2'] for s in result['payload']['spaces']),[14,24,30])
        self.assertIn(str(self.source.resolve()),result['inputs'])
        self.source.write_bytes(self.source.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'evidence changed'):verify_result(self.root/'recognized/result.json')

    @unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit MOOSAS runtime required')
    def test_rehashed_replacement_expectation_cannot_override_native_source(self):
        from bsa.modules import run as module
        run(self.source,self.root/'intake',length_tolerance_m=1e-6,area_tolerance_m2=1e-8)
        expected=self.root/'intake/space-expectations.json';data=json.loads(expected.read_text());data['expected'][0]['height_m']+=.2;expected.write_text(json.dumps(data))
        request=self.root/'intake/request.json';data=json.loads(request.read_text());data['sources']['expectations']['sha256']=digest(expected);request.write_text(json.dumps(data))
        result=module(request,'moosas.surface-room-recognition',self.root/'replaced',runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps'))
        self.assertEqual(result['execution']['status'],'failed');self.assertIsNone(result['payload'])
        self.assertIn('saved IFC source replay',result['execution']['diagnostics'][0]['message'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit MOOSAS runtime required')
    def test_unavailable_native_source_runtime_has_no_successful_payload(self):
        from bsa.modules import run as module,verify_result
        run(self.source,self.root/'intake',length_tolerance_m=1e-6,area_tolerance_m2=1e-8)
        with patch('bsa.ifc_space_surfaces.prepare',side_effect=ImportError('Synthetic unavailable native-source runtime control')):
            result=module(self.root/'intake/request.json','moosas.surface-room-recognition',self.root/'unavailable',runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps'))
        self.assertEqual(result['execution']['status'],'unavailable');self.assertIsNone(result['payload'])
        verify_result(self.root/'unavailable/result.json')
