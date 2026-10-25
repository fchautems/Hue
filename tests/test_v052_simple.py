"""v0.5.2 : courbe simple, persistance et API, sans perdre le profil personnalisé."""
import copy
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from hue_simple_profile import DEFAULT_SIMPLE_PROFILE, simple_brightness_at, validate_simple_profile
import hue_web
from hue_web import HueServer
from test_v05 import ThreeLamps


class SimpleCurveTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'settings.json'
        self.bridge=ThreeLamps()
        self.server=HueServer(self.bridge,self.path,logging.getLogger('test_v052'))
        self.server.poll()

    def test_defaults_preserve_custom_and_manual(self):
        previous=self.server.profile('light-1')
        info=self.server.simple_profile('light-1')
        self.assertEqual(info['type'],'custom')
        self.assertEqual(info['params'],DEFAULT_SIMPLE_PROFILE)
        self.assertEqual(self.server.profile('light-1'),previous)
        self.assertEqual(self.server.state()['auto_count'],0)

    def test_set_simple_preserves_custom_and_other_lamps(self):
        old=self.server.profile('light-1')
        self.server.set_simple_profile('light-1',DEFAULT_SIMPLE_PROFILE)
        self.assertEqual(self.server.profile('light-1'),old)
        self.assertEqual(self.server.simple_profile('light-1')['type'],'simple')
        self.assertEqual(self.server.simple_profile('light-0')['type'],'custom')
        self.assertEqual(self.server.state()['auto_count'],0)
        stored=json.loads(self.path.read_text())
        self.assertEqual(stored['profiles']['light-1'],old)
        self.assertEqual(stored['simple_profiles']['light-1'],DEFAULT_SIMPLE_PROFILE)
        self.assertEqual(stored['profile_types']['light-1'],'simple')

    def test_simple_only_commands_auto_lamp_and_uses_correct_time(self):
        self.server.set_simple_profile('light-1',DEFAULT_SIMPLE_PROFILE)
        self.server.set_light_mode('light-1','auto')
        self.server.set_clock_mode('accelere')
        self.server.set_sim({'minute': 600,'running':False})
        self.server.automate()
        self.assertEqual(len(self.bridge.calls),1)
        self.assertEqual(self.bridge.calls[0][0],'light/light-1')
        self.assertAlmostEqual(self.bridge.calls[0][1]['dimming']['brightness'],simple_brightness_at(DEFAULT_SIMPLE_PROFILE,600),places=2)
        self.assertEqual(self.server.state()['lights'][1]['target'],simple_brightness_at(DEFAULT_SIMPLE_PROFILE,600))

    def test_off_lamp_stays_off(self):
        self.server.set_simple_profile('light-1',DEFAULT_SIMPLE_PROFILE)
        self.server.set_light_mode('light-1','auto')
        self.bridge.lights[1]['on']['on']=False
        self.server.poll()
        self.server.automate()
        self.assertEqual(self.bridge.calls,[])

    def test_restore_after_reboot(self):
        self.server.set_simple_profile('light-2',DEFAULT_SIMPLE_PROFILE)
        self.server.set_light_mode('light-2','auto')
        restored=HueServer(self.bridge,self.path,logging.getLogger('test_v052_reboot'))
        restored.poll()
        self.assertEqual(restored.simple_profile('light-2')['type'],'simple')
        self.assertEqual(restored.simple_profile('light-2')['params'],DEFAULT_SIMPLE_PROFILE)
        self.assertEqual(restored.state()['lights'][2]['control_mode'],'auto')

    def test_switching_types_keeps_both_profiles(self):
        self.server.set_simple_profile('light-0',DEFAULT_SIMPLE_PROFILE)
        original=self.server.profile('light-0')
        self.server.set_profile_type('light-0','custom')
        self.assertEqual(self.server.simple_profile('light-0')['type'],'custom')
        self.assertEqual(self.server.profile('light-0'),original)
        self.server.set_profile_type('light-0','simple')
        self.assertEqual(self.server.simple_profile('light-0')['type'],'simple')
        new_points=[{'minute':0,'brightness':11},{'minute':720,'brightness':87}]
        self.server.set_profile('light-0',new_points)
        self.assertEqual(self.server.simple_profile('light-0')['type'],'custom')
        self.assertEqual(self.server.profile('light-0'),new_points)
        self.assertEqual(self.server.simple_profile('light-0')['params'],DEFAULT_SIMPLE_PROFILE)

    def test_invalid_cannot_touch_disk_or_active_mode(self):
        before=self.path.read_bytes()
        for invalid in ({'wake':10},dict(DEFAULT_SIMPLE_PROFILE,wake=790),dict(DEFAULT_SIMPLE_PROFILE,max_brightness=9)):
            with self.assertRaises(ValueError): self.server.set_simple_profile('light-0',invalid)
        with self.assertRaises(ValueError): self.server.set_profile_type('light-0','autre')
        with self.assertRaises(ValueError): self.server.set_simple_profile('absent',DEFAULT_SIMPLE_PROFILE)
        self.assertEqual(self.path.read_bytes(),before)


class SimpleCurveHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.before=hue_web.controller
        self.bridge=ThreeLamps()
        hue_web.controller=HueServer(self.bridge,Path(self.temp.name)/'settings.json',logging.getLogger('test_v052_api'))
        hue_web.controller.poll()
        self.addCleanup(lambda:setattr(hue_web,'controller',self.before))
        self.client=TestClient(hue_web.app)
        self.addCleanup(self.client.close)

    def test_http_simple_and_custom(self):
        path='/api/profile/simple/light-1'
        res=self.client.get(path)
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()['data']['type'],'custom')
        self.assertEqual(self.client.put(path,json={'params':DEFAULT_SIMPLE_PROFILE}).status_code,200)
        self.assertEqual(self.client.get(path).json()['data']['type'],'simple')
        self.assertEqual(self.client.post('/api/profile/type/light-1',json={'type':'custom'}).status_code,200)
        self.assertEqual(self.client.get(path).json()['data']['type'],'custom')
        self.assertEqual(self.client.get('/api/profile/light-1').json()['data'],hue_web.controller.profile('light-1'))
        self.assertEqual(self.client.post('/api/profile/type/light-1',json={'type':'garbage'}).status_code,400)
        self.assertEqual(self.client.put(path,json={'params':{'min_brightness':-1}}).status_code,400)

if __name__=='__main__': unittest.main()
