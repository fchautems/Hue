import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from hue_web import HueServer
from hue_v03_runtime import reconnect_transition_ms, event_has_reconnect_signal
from test_server import FakeClient

class Version03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"
        self.fake = FakeClient()
        self.ctrl = HueServer(self.fake, self.path, logging.getLogger("test_v03"))
        self.ctrl.poll()

    def tearDown(self):
        self.tmp.cleanup()

    def test_modes_exclusifs(self):
        self.assertEqual(self.ctrl.state()['mode'], 'manuel')
        self.ctrl.set_mode('reel')
        self.assertFalse(self.ctrl.sim['enabled'])
        self.assertTrue(self.ctrl.settings['auto'])
        self.ctrl.set_mode('accelere')
        self.assertFalse(self.ctrl.settings['auto'])
        self.assertTrue(self.ctrl.sim['enabled'])
        self.assertTrue(self.ctrl.sim['apply'])
        self.assertTrue(self.ctrl.sim['running'])
        self.ctrl.set_mode('manuel')
        self.assertFalse(self.ctrl.sim['enabled'])
        self.assertFalse(self.ctrl.settings['auto'])
        self.assertFalse(self.ctrl.sim['apply'])

    def test_no_automation_in_manual_even_at_reconnect(self):
        self.fake.connectivity[0]['status'] = 'disconnected';self.ctrl.poll()
        self.fake.connectivity[0]['status'] = 'connected';self.ctrl.poll()
        self.ctrl.automate()
        self.assertFalse(self.fake.calls)

    def test_accelerated_brightness_actually_applies(self):
        self.ctrl.set_mode('accelere')
        self.ctrl.set_sim({'minute':600,'running':False})
        self.ctrl.automate()
        self.assertEqual(self.fake.calls[-1][1]['dimming']['brightness'], 100)

    def test_accelerated_mode_needs_selection(self):
        with self.assertRaises(ValueError): self.ctrl.set_sim({'minute':600})
        with self.assertRaises(ValueError): self.ctrl.set_sim({'enabled':True})
        with self.assertRaises(ValueError): self.ctrl.set_mode('observation')

    def test_realtime_mode_persists(self):
        self.ctrl.set_mode('reel')
        restored=HueServer(self.fake,self.path,logging.getLogger('test_v03'))
        self.assertEqual(restored.state()['mode'],'reel')
        self.assertFalse(restored.sim['enabled'])

    def test_accelerated_does_not_restart_after_server_reboot(self):
        self.ctrl.set_mode('accelere')
        restored=HueServer(self.fake,self.path,logging.getLogger('test_v03'))
        self.assertEqual(restored.state()['mode'],'manuel')

    def test_powerup_readback_10_percent(self):
        self.fake.lights[0]['dimming']['brightness']=100
        result=self.ctrl.set_powerup('light-a','custom',10)
        self.assertEqual(result['requested']['dimming']['dimming'],10)
        self.assertTrue(result['verified_readback'])
        self.assertEqual(self.fake.lights[0]['dimming']['brightness'],100)

    def test_non_powerup_model_rejected(self):
        del self.ctrl.lights[0]['powerup']
        with self.assertRaises(ValueError):self.ctrl.set_powerup('light-a','custom',10)

    def test_no_empty_powerup_success(self):
        class Stale(FakeClient):
            def resource(self,path,method='GET',payload=None):
                if method == 'PUT':
                    self.calls.append((path,payload));return []
                return super().resource(path,method,payload)
        client=Stale();ctrl=HueServer(client,self.path,logging.getLogger('test_v03'));ctrl.poll()
        self.assertFalse(ctrl.set_powerup('light-a','custom',10)['verified_readback'])

    def test_transition_adaptive(self):
        self.assertEqual(reconnect_transition_ms(10,18),500)
        self.assertEqual(reconnect_transition_ms(10,30),1000)
        self.assertEqual(reconnect_transition_ms(10,63),1500)
        self.assertEqual(reconnect_transition_ms(10,100),2000)

    def test_sse_parser(self):
        self.assertTrue(event_has_reconnect_signal([{'type':'update','data':[{'type':'zigbee_connectivity','status':'connected'}]}]))
        self.assertTrue(event_has_reconnect_signal([{'type':'update','data':[{'type':'light','on':{'on':True}}]}]))
        self.assertFalse(event_has_reconnect_signal([{'type':'update','data':[{'type':'light','dimming':{'brightness':63}}]}]))
        self.assertFalse(event_has_reconnect_signal(None))

if __name__=='__main__':unittest.main()