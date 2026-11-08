import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from bsa.engine import ProjectError
from bsa.ifc_native import run


class NativeTextWindowTests(unittest.TestCase):
    def test_straight_diagram_label_outside_window_rejected_before_cad(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);doc=ezdxf.new();doc.header['$INSUNITS']=6
            doc.layers.new('BSA_PIPE_AXIS');doc.appids.new('BSA_IFC')
            guid='14_Pcn3dHIEx82hnR2Z_vq'
            line=doc.modelspace().add_line((0,0),(1,0),dxfattribs={'layer':'BSA_PIPE_AXIS'})
            line.set_xdata('BSA_IFC',[(1000,guid)])
            doc.modelspace().add_text('CLIPPED LABEL',dxfattribs={'insert':(10,0),'height':.1})
            dxf=root/'diagram.dxf';doc.saveas(dxf)
            settings=root/'sheet.json';settings.write_text(json.dumps(dict(source='Synthetic clipping control',window_drawing_units=[-1,-1,2,2],scale_denominator=100,reference_ifc_guid=guid,pdf_tolerance_mm=.2)))
            with patch('bsa.ifc_native.execute') as execute,self.assertRaisesRegex(ProjectError,'annotation extents'):
                run(dxf,settings,root/'out',Path(sys.executable))
            execute.assert_not_called();self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
