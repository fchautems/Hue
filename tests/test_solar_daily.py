import copy
from datetime import datetime
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from hue_web import HueServer
from hue_solar_profile import DEFAULT_SOLAR_CONFIG, validate_solar_config, draft_profile
from hue_rgb import hsv_to_xy, rgb_at
from test_v05 import ThreeLamps


class DailySolarTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'settings.json'
        self.bridge = ThreeLamps()
        self.bridge.lights[0]['color'] = {'xy': {'x': .3, 'y': .3}}
        self.server = HueServer(self.bridge, self.path, logging.getLogger('solar-daily'))
        self.server.poll()
        self.config = dict(DEFAULT_SOLAR_CONFIG, wake=315)
        self.instant = datetime(2026,11,6,20,0,tzinfo=ZoneInfo('Europe/Zurich'))
        self.clock = patch.object(self.server, '_solar_now', side_effect=lambda _: self.instant)
        self.clock.start();self.addCleanup(self.clock.stop)

    def test_daily_seasons_cache_and_restart_without_reapplying_or_writing(self):
        s=self.server;before=copy.deepcopy(s.settings)
        s.set_solar_profile('light-0',self.config)
        persisted=self.path.read_bytes()
        with patch('hue_web.draft_profile', wraps=draft_profile) as calc:
            for day in [(2026,11,6),(2026,11,7),(2027,6,21),(2027,12,21)]:
                self.instant=self.instant.replace(year=day[0],month=day[1],day=day[2])
                expected=draft_profile(self.instant.date(),**self.config)['params']
                self.assertEqual(s._effective_simple('light-0'),expected)
                s._effective_simple('light-0')
            self.assertEqual(calc.call_count,4,'one calculation per date/config')
        self.assertEqual(self.path.read_bytes(),persisted,'no daily settings writes')
        self.assertEqual(before['simple_profiles'],s.settings['simple_profiles'])
        self.assertEqual(before['profiles'],s.settings['profiles'])
        rebooted=HueServer(self.bridge,self.path,logging.getLogger('solar-reboot'))
        with patch.object(rebooted,'_solar_now',return_value=self.instant):
            self.assertEqual(rebooted._effective_simple('light-0'),s._effective_simple('light-0'))
        self.assertEqual(rebooted.settings['profile_types']['light-0'],'solar')

    def test_dst_and_local_day_not_host_timezone(self):
        s=self.server;s.set_solar_profile('light-0',self.config)
        for instant in ['2027-03-28T01:30:00+01:00','2027-03-28T03:30:00+02:00',
                        '2027-10-31T02:30:00+02:00','2027-10-31T02:30:00+01:00',
                        '2027-01-01T00:05:00+01:00']:
            self.instant=datetime.fromisoformat(instant)
            self.assertEqual(s._effective_simple('light-0'),draft_profile(self.instant.date(),**self.config)['params'])
            self.assertEqual(s._profile_minute('light-0',0),self.instant.hour*60+self.instant.minute)
        s.set_clock_mode('accelere')
        self.assertEqual(s._profile_minute('light-0',720),720)

    def test_actual_command_matches_state_and_colors_and_respects_off_manual_vacation(self):
        s=self.server;s.set_solar_profile('light-0',self.config)
        self.assertEqual(self.bridge.calls,[])
        s.automate();self.assertEqual(self.bridge.calls,[],'manual stays manual')
        s.set_light_mode('light-0','auto');s.automate()
        command=self.bridge.calls[-1][1];target=s.state()['lights'][0]['target']
        self.assertEqual(command['dimming']['brightness'],target)
        expected=rgb_at(s.settings['rgb_profiles']['light-0'],s._effective_simple('light-0'),1200)
        self.assertEqual(command['color']['xy'],hsv_to_xy(expected))
        for off,vacation in [(True,False),(False,True)]:
            self.bridge.calls.clear();s.lights[0]['on']['on']=not off
            s.vacation.update(enabled=vacation,light_ids=['light-0'])
            s._automate_locked();self.assertEqual(self.bridge.calls,[])

    def test_save_failure_rolls_back_and_simple_switch_is_reversible(self):
        s=self.server;before=copy.deepcopy(s.settings)
        with patch.object(s,'save',side_effect=OSError('disk')):
            with self.assertRaises(OSError):s.set_solar_profile('light-0',self.config)
        self.assertEqual(s.settings,before)
        s.set_solar_profile('light-0',self.config);s.set_profile_type('light-0','simple')
        self.assertEqual(s.settings['solar_profiles']['light-0'],self.config)
        s.set_solar_profile('light-0',self.config)
        self.assertEqual(s.settings['profile_types']['light-0'],'solar')

    def test_full_copy_keeps_daily_behavior_and_rgb_save_preserves_solar(self):
        s=self.server;s.set_solar_profile('light-0',self.config)
        s.copy_profile('light-0','light-1')
        self.assertEqual(s.settings['solar_profiles']['light-1'],self.config)
        self.assertEqual(s.settings['profile_types']['light-1'],'solar')
        self.assertFalse(s.settings['rgb_auto_enabled']['light-1'])
        rgb=s.rgb_profile('light-0')
        data={k:rgb[k] for k in ['mode','colors','simple_params','manual']};data['mode']='auto'
        data['colors']['evening']={'h':25,'s':80}
        s.save_rgb_profile('light-0',data)
        self.assertEqual(s.settings['profile_types']['light-0'],'solar')
        self.assertEqual(s.settings['solar_profiles']['light-0'],self.config)
        self.assertEqual(s.settings['rgb_profiles']['light-0']['evening'],{'h':25,'s':80})

    def test_validation_and_api_date_cannot_be_saved_as_activation(self):
        for delta in [dict(day='2026-11-06'),dict(latitude=float('nan')),dict(latitude=True),
                      dict(tz='Unknown/Place'),dict(wake=True),dict(low=90),dict(bed=100)]:
            with self.subTest(delta=delta),self.assertRaises(ValueError):validate_solar_config(dict(self.config,**delta))
        from fastapi.testclient import TestClient
        import hue_web
        with patch.object(hue_web,'controller',self.server):
            http=TestClient(hue_web.app)
            self.assertEqual(http.put('/api/profile/solar/light-0',json={'config':self.config}).status_code,200)
            self.assertEqual(http.get('/api/profile/solar/light-0').json()['data']['config'],self.config)
            before=self.path.read_bytes();self.bridge.calls.clear()
            r=http.get('/api/solar/draft',params=dict(self.config,day='2027-06-21',uid='light-0'))
            self.assertEqual(r.status_code,200)
            self.assertEqual(self.path.read_bytes(),before);self.assertEqual(self.bridge.calls,[])
            self.assertEqual(http.put('/api/profile/solar/light-0',json={'config':self.config,'day':'2027-06-21'}).status_code,400)
