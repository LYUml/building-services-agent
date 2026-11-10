import unittest
import ezdxf
import numpy as np
from bsa.cad_text_layout import place_outward,check_dimension_box,audit_graphics,text_box
from bsa.engine import ProjectError


class CadTextLayoutTests(unittest.TestCase):
    def test_cardinal_and_oblique_whole_box_placement(self):
        for vector in ([1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[-1,-1],[1,-1]):
            doc=ezdxf.new();normal=np.array(vector,dtype=float);normal/=np.linalg.norm(normal)
            tangent=np.array([-normal[1],normal[0]])
            entity=doc.modelspace().add_text('Straight L=2.000000 m',dxfattribs={'height':.04})
            place_outward(entity,[0.,1.],normal,.04)
            check_dimension_box(entity,[0.,1.],normal,.04)
            doc.modelspace().add_line(np.array([0.,1.])-tangent,np.array([0.,1.])+tangent)
            self.assertTrue(audit_graphics(doc,.04)['text_graphics_checks_pass'])

    def test_legacy_left_normal_crosses_vertical_route(self):
        doc=ezdxf.new();entity=doc.modelspace().add_text('Straight L=2.000000 m',dxfattribs={'height':.04,'insert':(-.08,1.)})
        doc.modelspace().add_line((.16,0.),(.16,2.))
        with self.assertRaisesRegex(ProjectError,'intersects'):audit_graphics(doc,.04)
        with self.assertRaisesRegex(ProjectError,'differs'):check_dimension_box(entity,[0.,1.],[-1.,0.],.04)

    def test_left_label_stays_entirely_left(self):
        doc=ezdxf.new();entity=doc.modelspace().add_text('Straight L=2.000000 m',dxfattribs={'height':.04})
        place_outward(entity,[0.,1.],[-1.,0.],.04)
        self.assertLess(text_box(entity)[2],-.079)

    def test_overlapping_text_boxes_rejected(self):
        doc=ezdxf.new()
        for _ in range(2):doc.modelspace().add_text('label',dxfattribs={'height':.04})
        with self.assertRaisesRegex(ProjectError,'overlap'):audit_graphics(doc,.04)

    def test_conservative_arc_bounds_reject_unproven_clearance(self):
        doc=ezdxf.new();doc.modelspace().add_arc((0.,0.),1.,0.,90.)
        doc.modelspace().add_text('a',dxfattribs={'height':.04,'insert':(.1,.1)})
        with self.assertRaisesRegex(ProjectError,'arc bounds'):audit_graphics(doc,.04)

    def test_device_label_association_controls(self):
        from bsa.cad_text_layout import audit_label_associations
        doc=ezdxf.new();a=doc.modelspace().add_text('A',dxfattribs={'height':.1})
        b=doc.modelspace().add_text('B',dxfattribs={'height':.1,'insert':(3,0)})
        anchors={'A':[0,0],'B':[3,0]}
        self.assertTrue(audit_label_associations([a,b],anchors,1,.01)['association_screen_pass'])
        a.dxf.insert=(2.8,0)
        with self.assertRaises(ProjectError):audit_label_associations([a,b],anchors,1,.01)
        with self.assertRaises(ProjectError):audit_label_associations([b],anchors,1,.01)
        with self.assertRaises(ProjectError):audit_label_associations([b,b],anchors,1,.01)
