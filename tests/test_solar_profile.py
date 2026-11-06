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
from hue_simple_profile import simple_brightness_at, validate_simple_profile
from hue_rgb import DEFAULT_RGB_PHASES, rgb_at, hsv_to_xy
from datetime import datetime

class SolarProfileTests(unittest.TestCase):
    def draft(self, **kw):
        args=dict(day=date(2026,6,21),latitude=46.46,longitude=6.22,tz='Europe/Zurich',wake=420,bed=1350)
        args.update(kw)
        return draft_profile(**args)
    def test_bounded_smooth_samples_and_seasons(self):
        summer=self.draft();winter=self.draft(day=date(2026,12,21))
        for d in [summer,winter,self.draft(latitude=89)]:
            p=d['params'];self.assertEqual(p['wake'],420);self.assertEqual(p['bed'],1350)
            self.assertTrue(450<=p['morning_end']<=p['evening_start']<=1320)
            self.assertEqual(len(d['samples']),97)
            self.assertTrue(all(10<=s['brightness']<=85 for s in d['samples']))
            self.assertEqual(d['samples'][0]['brightness'],10)
        self.assertNotEqual(summer['params'],winter['params'])

    def test_reported_day_follows_solar_anchors_without_two_or_three_hour_caps(self):
        times={'sunrise':datetime(2026,11,6,7,23),'sunset':datetime(2026,11,6,17,13)}
        with patch('hue_solar_profile.solar_times',return_value=times):
            p=self.draft(wake=315)['params']
        self.assertEqual((p['wake'],p['morning_end'],p['evening_start'],p['bed']),
                         (315,443,1033,1350))
        self.assertEqual(p['transition_shape'],'asymmetric')

    def test_asymmetric_shape_rises_early_and_dims_late_without_overshoot(self):
        p=self.draft(wake=315)['params']
        smooth={k:v for k,v in p.items() if k!='transition_shape'}
        mid_morning=(p['wake']+p['morning_end'])/2
        mid_evening=(p['evening_start']+p['bed'])/2
        self.assertGreater(simple_brightness_at(p,mid_morning),simple_brightness_at(smooth,mid_morning))
        self.assertGreater(simple_brightness_at(p,mid_evening),simple_brightness_at(smooth,mid_evening))
        levels=[simple_brightness_at(p,m) for m in range(1440)]
        self.assertTrue(all(p['min_brightness']<=b<=p['max_brightness'] for b in levels))
        rise=levels[p['wake']:p['morning_end']+1]
        fall=levels[p['evening_start']:p['bed']+1]
        self.assertTrue(all(a<=b for a,b in zip(rise,rise[1:])))
        self.assertTrue(all(a>=b for a,b in zip(fall,fall[1:])))
        self.assertEqual(self.draft()['colors'],DEFAULT_RGB_PHASES)
        self.assertEqual(rgb_at(DEFAULT_RGB_PHASES,p,p['bed']),DEFAULT_RGB_PHASES['night'])

    def test_sun_outside_personal_rhythm_keeps_valid_order_and_explains_adjustment(self):
        for wake,bed in [(420,1350),(900,1200),(60,300)]:
            d=self.draft(wake=wake,bed=bed)
            validate_simple_profile(d['params'])
            self.assertTrue(d['timing_note'])

    def test_applied_profile_commands_same_brightness_as_state_and_preserves_shape_after_restart(self):
        from test_v05 import ThreeLamps
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'s.json';bridge=ThreeLamps()
            bridge.lights[0]['color']={'xy':{'x':.3,'y':.3}}
            server=HueServer(bridge,path,logging.getLogger('solar-apply'))
            server.poll();server.set_light_mode('light-0','auto')
            server.apply_solar_draft('light-0',self.draft(wake=315))
            server.set_clock_mode('accelere');server.set_sim({'minute':1150,'running':False})
            server.automate()
            command=bridge.calls[-1][1]
            self.assertEqual(command['dimming']['brightness'],server.state()['lights'][0]['target'])
            self.assertEqual(command['color']['xy'],hsv_to_xy(rgb_at(DEFAULT_RGB_PHASES,server.settings['simple_profiles']['light-0'],1150)))
            server.poll()
            self.assertEqual(server.state()['lights'][0]['brightness'],server.state()['lights'][0]['target'])
            restarted=HueServer(bridge,path,logging.getLogger('solar-restart'))
            self.assertEqual(restarted.settings['simple_profiles']['light-0']['transition_shape'],'asymmetric')

    def test_unrecognized_transition_shape_rejected(self):
        p=self.draft()['params']
        for bad in ['unknown',True,{},None]:
            with self.subTest(shape=bad),self.assertRaises(ValueError):
                validate_simple_profile(dict(p,transition_shape=bad))
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

    def test_draft_route_is_read_only_and_validates_rhythm(self):
        from fastapi.testclient import TestClient
        import hue_web
        with patch.object(hue_web, 'controller', None):
            http=TestClient(hue_web.app)
            response=http.get('/api/solar/draft', params=dict(day='2026-06-21',wake=420,bed=1350))
            self.assertEqual(response.status_code,200)
            self.assertEqual(len(response.json()['data']['samples']),97)
            self.assertEqual(http.get('/api/solar/draft',params=dict(day='2026-06-21',wake=1350,bed=420)).status_code,400)
