"""Native kernel eligibility, fallback and unchanged source-mesh checks."""
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import patch,call

from bsa.circular_geometry import native_shape


class Item:
    def __init__(self,kind,*,closed=True,arity=3,voids=False):
        self.kind=kind;self.Closed=closed;self.CoordIndex=[tuple(range(1,arity+1))]
        self.Faces=[SimpleNamespace(is_a=lambda:'IfcIndexedPolygonalFaceWithVoids' if voids else 'IfcIndexedPolygonalFace',CoordIndex=tuple(range(1,arity+1)))]
    def is_a(self,kind=None):return self.kind==kind if kind else self.kind


def obj(item,openings=()):
    body=SimpleNamespace(RepresentationIdentifier='Body',RepresentationType='Tessellation',Items=[item])
    return SimpleNamespace(Representation=SimpleNamespace(Representations=[body]),HasOpenings=openings)


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'Requires pinned IFC runtime')
class NativeKernelTests(unittest.TestCase):
    def test_only_direct_closed_triangle_sets_use_fast_kernel(self):
        for kind in ('IfcPolygonalFaceSet','IfcTriangulatedFaceSet'):
            source=obj(Item(kind));settings=object();sentinel=object()
            with self.subTest(kind=kind),patch('ifcopenshell.geom.create_shape',return_value=sentinel) as engine:
                self.assertIs(native_shape(settings,source),sentinel)
                engine.assert_called_once_with(settings,source,geometry_library='cgal-simple')

    def test_other_representations_openings_and_polygon_voids_keep_original_kernel(self):
        cases=[obj(Item('IfcExtrudedAreaSolid')),obj(Item('IfcPolygonalFaceSet',closed=False)),
            obj(Item('IfcPolygonalFaceSet',arity=4)),obj(Item('IfcPolygonalFaceSet',voids=True)),
            obj(Item('IfcPolygonalFaceSet'),openings=[object()]),SimpleNamespace(Representation=None)]
        for source in cases:
            with self.subTest(source=source),patch('ifcopenshell.geom.create_shape',return_value='original') as engine:
                self.assertEqual(native_shape('settings',source),'original')
                engine.assert_called_once_with('settings',source)

    def test_unavailable_conversion_falls_back_without_accepting_failure(self):
        source=obj(Item('IfcPolygonalFaceSet'))
        with patch('ifcopenshell.geom.create_shape',side_effect=[RuntimeError('Unavailable kernel'),'original']) as engine:
            self.assertEqual(native_shape('settings',source),'original')
            self.assertEqual(engine.call_args_list,[call('settings',source,geometry_library='cgal-simple'),call('settings',source)])
        with patch('ifcopenshell.geom.create_shape',side_effect=RuntimeError('Both unavailable')) as engine:
            with self.assertRaises(RuntimeError):native_shape('settings',source)
            self.assertEqual(engine.call_count,2)
        with patch('ifcopenshell.geom.create_shape',side_effect=ValueError('Invalid caller')) as engine:
            with self.assertRaises(ValueError):native_shape('settings',source)
            self.assertEqual(engine.call_count,1)

    def test_actual_native_route_matches_original_kernel_under_same_checks(self):
        import ifcopenshell.geom
        from bsa.ifc_route_drawing import extract
        from tests import test_ifc_route_drawing
        fixture=test_ifc_route_drawing.RouteDrawingTests
        with patch('ifcopenshell.geom.create_shape',wraps=ifcopenshell.geom.create_shape) as engine:
            fixture.setUpClass();self.addCleanup(fixture.tearDownClass)
        self.assertEqual(engine.call_count,3)
        self.assertEqual(sum(c.kwargs.get('geometry_library')=='cgal-simple' for c in engine.call_args_list),1)
        with patch('bsa.circular_geometry.native_shape',side_effect=lambda settings,product:ifcopenshell.geom.create_shape(settings,product)):
            original=extract(fixture.ifc,fixture.model,fixture.settings)
        observed=fixture.result['pieces']
        def compare(a,b):
            self.assertEqual(type(a),type(b))
            if type(a) in (int,float):self.assertAlmostEqual(a,b,delta=1e-12)
            elif isinstance(a,dict):
                self.assertEqual(set(a),set(b))
                for key in a:compare(a[key],b[key])
            elif isinstance(a,list):
                self.assertEqual(len(a),len(b))
                for x,y in zip(a,b):compare(x,y)
            else:self.assertEqual(a,b)
        compare(original,observed)
        self.assertTrue(all(r['native_wall_checks']['closed_mesh'] for r in observed))
