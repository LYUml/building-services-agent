import json
from pathlib import Path
import tempfile
import unittest
from bsa.energy import build,validate
from bsa.engine import ProjectError
from bsa.sizing_humidity import audit,audit_idf,validate as validate_humidity

ROOT=Path(__file__).resolve().parents[1]


class SizingHumidityTests(unittest.TestCase):
    def setUp(self):
        import openstudio as os
        self.os=os;self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=json.loads((ROOT/'examples/sizing-humidity/project.json').read_text())
        self.metadata=build(validate(self.project),12,self.root)
        self.model=os.model.Model.load(os.path(str(self.root/'model.osm'))).get()

    def test_saved_osm_and_idf_cover_all_zones(self):
        result=self.metadata['sizing_humidity_audit']
        self.assertTrue(result['saved_osm_checks_pass']);self.assertTrue(result['saved_idf_checks_pass'])
        self.assertEqual(result['zone_count'],2)

    def test_changed_schedule_and_operating_override_rejected(self):
        z=self.model.getThermalZones()[0]
        schedule=z.sizingZone().zoneHumidistatDehumidificationSetPointSchedule().get().to_ScheduleConstant().get()
        schedule.setValue(55)
        with self.assertRaisesRegex(ProjectError,'RH differs'):audit(self.model,self.project['sizing_humidity'])
        schedule.setValue(50);z.setZoneControlHumidistat(self.os.model.ZoneControlHumidistat(self.model))
        with self.assertRaisesRegex(ProjectError,'overriding'):audit(self.model,self.project['sizing_humidity'])

    def test_native_method_tampering_rejected(self):
        p=self.root/'bad.idf';p.write_text((self.root/'model.idf').read_text().replace('Sensible And Latent Load','Sensible Load Only No Latent Load'))
        with self.assertRaisesRegex(ProjectError,'latent sizing method'):audit_idf(p,self.metadata['sizing_humidity_audit']['zones'],self.project['sizing_humidity'])

    def test_invalid_percent_deadband_and_annual_use_rejected(self):
        for value in (0,100,True,float('nan'),49):
            bad=dict(self.project['sizing_humidity'],dehumidification_rh_percent=value)
            with self.subTest(value=value),self.assertRaises(ProjectError):validate_humidity(bad)
        with self.assertRaisesRegex(ProjectError,'design-day workflows only'):validate(self.project,require_design_days=False)
