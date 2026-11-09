import unittest
import ezdxf
import numpy as np
from bsa.connector_ports import anchors
from bsa.engine import ProjectError


class ConnectorAnchorTests(unittest.TestCase):
    def fixture(self):
        d=ezdxf.new();ms=d.modelspace();line=ms.add_line((0,-10,0),(0,10,0))
        points=[ms.add_point((0,y,0)) for y in (-1,1)]
        b={'axis_line_handle':line.dxf.handle,'ports':[{'id':str(i),'source':'Synthetic source node','point_handle':p.dxf.handle,'axis_endpoint':side} for i,(p,side) in enumerate(zip(points,('start','end')))]}
        return d,b,points

    def test_saved_node_positions_and_opposing_axes(self):
        d,b,_=self.fixture();frames,_=anchors(d,b,.001)
        self.assertTrue(np.allclose(frames['0'][:3,3],[0,-.001,0]))
        self.assertTrue(np.allclose(frames['1'][:3,3],[0,.001,0]))
        self.assertTrue(np.allclose(frames['0'][:3,2],[0,-1,0]))
        self.assertTrue(np.allclose(frames['1'][:3,2],[0,1,0]))

    def test_wrong_side_duplicate_and_off_axis_reject(self):
        for change in ('side','duplicate','off_axis','outside'):
            d,b,pts=self.fixture()
            if change=='side':b['ports'][0]['axis_endpoint']='end'
            elif change=='duplicate':b['ports'][1]['point_handle']=pts[0].dxf.handle
            elif change=='off_axis':pts[1].dxf.location=(1,1,0)
            else:pts[1].dxf.location=(0,11,0)
            with self.assertRaises(ProjectError):anchors(d,b,.001)

    def test_paper_space_and_wrong_entity_reject(self):
        d,b,_=self.fixture();p=d.paperspace().add_point((0,1,0));b['ports'][1]['point_handle']=p.dxf.handle
        with self.assertRaises(ProjectError):anchors(d,b,.001)
        b['ports'][1]['point_handle']=b['axis_line_handle']
        with self.assertRaises(ProjectError):anchors(d,b,.001)
