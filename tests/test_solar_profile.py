import copy
from datetime import date
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from hue_solar_profile import draft_profile
from hue_web import HueServer
from test_server import FakeClient

class SolarProfileTests(unittest.TestCase):
    def draft(self, **kw):
        args=dict(day=date(2026,6,21),latitude=46.46,longitude=6.22,tz='Europe/Zurich',wake=420,bed=1350)
        args.update(kw)
        return draft_profile(**args)
    def test_bounded_smooth_samples_and_seasons(self):
        summer=self.draft();winter=self.draft(day=date(2026,12,21))
        for d in [summer,winter,self.draft(latitude=89)]:
            p=d['params'];self.assertEqual(p['wake'],420);self.assertEqual(p['bed'],1350)
            self.assertTrue(450<=p['morning_end']<=540)
            self.assertTrue(1170<=p['evening_start']<=1320)
            self.assertEqual(len(d['samples']),97)
            self.assertTrue(all(10<=s['brightness']<=85 for s in d['samples']))
            self.assertEqual(d['samples'][0]['brightness'],10)
        self.assertNotEqual(summer['params'],winter['params'])
    def test_invalid_rhythm(self):
        for kw in [dict(wake=1300,bed=300),dict(wake=True),dict(bed=450),dict(low=90,high=30)]:
            with self.assertRaises(ValueError):self.draft(**kw)
    def test_apply_preserves_modes_state_and_other_profiles(self):
        with TemporaryDirectory() as tmp:
            bridge=FakeClient();server=HueServer(bridge,Path(tmp)/'s.json',logging.getLogger('solar'))
            server.poll();before=copy.deepcopy(server.settings);vacation=copy.deepcopy(server.vacation)
            result=server.apply_solar_draft('light-a',self.draft())
            self.assertFalse(result['rgb_auto']);self.assertEqual(bridge.calls,[])
            for key in ['light_modes','manual_states','profiles','rgb_manual']:
                self.assertEqual(server.settings[key],before[key])
            self.assertEqual(server.vacation,vacation)
            server.lights[0]['color']={}
            self.assertTrue(server.apply_solar_draft('light-a',self.draft())['rgb_auto'])
            previous=copy.deepcopy(server.settings)
            with patch.object(server,'save',side_effect=OSError('disk')):
                with self.assertRaises(OSError):server.apply_solar_draft('light-a',self.draft(day=date(2026,12,21)))
            self.assertEqual(server.settings,previous)
