"""v0.6: integration tests for RGB settings, automatic and manual Hue commands."""
import copy
import json
import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
import hue_web
from hue_web import HueServer
from test_v05 import ThreeLamps
from hue_rgb import DEFAULT_RGB_PHASES
from hue_simple_profile import DEFAULT_SIMPLE_PROFILE

GAMUT = {'red':{'x':0.7,'y':0.3},'green':{'x':0.17,'y':0.7},'blue':{'x':0.15,'y':0.06}}


def payload(mode='auto'):
    return {'mode':mode,'colors':copy.deepcopy(DEFAULT_RGB_PHASES),
            'simple_params':copy.deepcopy(DEFAULT_SIMPLE_PROFILE),
            'manual':{'h':18,'s':85,'b':26}}


class RGBControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'hue_settings.json'
        self.bridge=ThreeLamps()
        for lamp in self.bridge.lights:
            lamp['color']={'xy':{'x':0.3,'y':0.3},'gamut':copy.deepcopy(GAMUT)}
        self.server=HueServer(self.bridge,self.path,logging.getLogger('test_v06'))
        self.server.poll()

    def test_no_rgb_enabled_for_existing_install(self):
        self.assertTrue(all(not x['rgb_auto'] for x in self.server.get_lights()))
        self.server.set_light_mode('light-1','auto')
        self.server.set_clock_mode('accelere');self.server.set_sim({'minute':700,'running':False})
        self.server.automate()
        self.assertTrue(self.bridge.calls)
        self.assertNotIn('color',self.bridge.calls[-1][1])

    def test_auto_uses_xy_without_switching_on(self):
        self.server.save_rgb_profile('light-1',payload('auto'))
        self.assertEqual(self.bridge.calls, [])
        self.assertEqual(self.server.get_lights()[1]['control_mode'],'auto')
        self.assertEqual(self.server.get_lights()[1]['profile_type'],'simple')
        self.server.set_clock_mode('accelere');self.server.set_sim({'minute':700,'running':False})
        self.server.automate()
        self.assertEqual([c[0] for c in self.bridge.calls],['light/light-1'])
        cmd=self.bridge.calls[-1][1]
        self.assertIn('dimming',cmd)
        self.assertIn('color',cmd)
        self.assertNotIn('on',cmd)
        self.assertIn('duration',cmd['dynamics'])

    def test_off_auto_never_relights(self):
        self.server.save_rgb_profile('light-1',payload())
        self.bridge.lights[1]['on']['on']=False;self.server.poll()
        self.server.automate()
        self.assertEqual(self.bridge.calls,[])

    def test_rgb_manual_applies_colour_and_brightness_together(self):
        self.server.save_rgb_profile('light-0',payload('manuel'))
        self.assertEqual([c[0] for c in self.bridge.calls],['light/light-0'])
        cmd=self.bridge.calls[0][1]
        self.assertEqual(cmd['dimming']['brightness'],26.0)
        self.assertIn('color',cmd)
        self.assertNotIn('on',cmd)
        self.assertEqual(self.server.settings['manual_states']['light-0']['brightness'],26)
        self.assertEqual(self.server.settings['light_modes']['light-0'],'manuel')

    def test_manual_off_only_stores_rgb_and_does_not_relight(self):
        self.bridge.lights[0]['on']['on']=False;self.server.poll()
        self.server.save_rgb_profile('light-0',payload('manuel'))
        self.assertEqual(self.bridge.calls,[])
        self.assertFalse(self.server.settings['manual_states']['light-0']['on'])
        self.server.switch('light-0',True)
        self.assertTrue(self.bridge.calls[-1][1]['on']['on'])
        self.assertIn('color',self.bridge.calls[-1][1])

    def test_rgb_independent_per_lamp(self):
        self.server.save_rgb_profile('light-1',payload('auto'))
        self.assertFalse(self.server.settings['rgb_auto_enabled'].get('light-0',False))
        self.assertEqual(self.server.settings['light_modes']['light-0'],'manuel')
        self.assertEqual(self.server.settings['light_modes']['light-2'],'manuel')

    def test_previous_custom_points_survive_auto_rgb_and_return(self):
        points=[{'minute':0,'brightness':11},{'minute':720,'brightness':91}]
        self.server.set_profile('light-1',points)
        self.server.save_rgb_profile('light-1',payload('auto'))
        self.assertEqual(self.server.profile('light-1'),[{'minute':0,'brightness':11.0},{'minute':720,'brightness':91.0}])
        self.server.set_profile_type('light-1','custom')
        self.assertEqual(self.server.simple_profile('light-1')['type'],'custom')

    def test_rgb_config_survives_restart(self):
        x=payload('auto');x['colors']['night']={'h':255,'s':65}
        self.server.save_rgb_profile('light-2',x)
        saved=json.loads(self.path.read_text())
        self.assertEqual(saved['rgb_profiles']['light-2']['night'],{'h':255,'s':65})
        rebooted=HueServer(self.bridge,self.path,logging.getLogger('test_v06'))
        rebooted.poll()
        self.assertEqual(rebooted.rgb_profile('light-2')['colors']['night'],{'h':255,'s':65})
        self.assertTrue(rebooted.rgb_profile('light-2')['enabled'])

    def test_invalid_rgb_does_not_modify_settings_or_send_hue(self):
        before=self.path.read_bytes()
        for invalid in ({**payload(),'manual':{'h':2,'s':80,'b':0}},
                        {**payload(),'colors':{'day':{'h':22,'s':50}}},
                        {**payload(),'mode':'color'},
                        {**payload(),'simple_params':{**DEFAULT_SIMPLE_PROFILE,'wake':900}}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.server.save_rgb_profile('light-0',invalid)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.bridge.calls,[])

    def test_missing_color_capability_is_rejected(self):
        del self.bridge.lights[0]['color'];self.server.poll()
        with self.assertRaisesRegex(ValueError,'RGB'):
            self.server.save_rgb_profile('light-0',payload())


class RGBApiTests(RGBControllerTests):
    def setUp(self):
        super().setUp()
        self.old=hue_web.controller
        hue_web.controller=self.server
        self.addCleanup(lambda:setattr(hue_web,'controller',self.old))
        self.client=TestClient(hue_web.app)
        self.addCleanup(self.client.close)

    def test_rgb_http_get_put(self):
        get=self.client.get('/api/rgb/light-0')
        self.assertEqual(get.status_code,200)
        self.assertFalse(get.json()['enabled'])
        put=self.client.put('/api/rgb/light-0',json=payload('auto'))
        self.assertEqual(put.status_code,200)
        self.assertTrue(put.json()['enabled'])
        self.assertEqual(self.client.get('/api/rgb/light-1').json()['enabled'],False)

    def test_rgb_http_invalid_and_unknown(self):
        self.assertEqual(self.client.put('/api/rgb/light-0',json={'mode':'auto'}).status_code,400)
        self.assertEqual(self.client.get('/api/rgb/missing').status_code,400)


if __name__=='__main__':unittest.main()
