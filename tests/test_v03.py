import logging
import copy
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from hue_web import COMMAND_COOLDOWN_SECONDS, POLL_INTERVAL_SECONDS, HueServer
from hue_v03_runtime import HueEventStream, reconnect_transition_ms, event_has_reconnect_signal
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

    def test_observed_brightness_drift_bypasses_unchanged_target_throttle(self):
        self.ctrl.set_mode('accelere')
        self.ctrl.set_sim({'minute':600,'running':False})
        self.fake.lights[0]['dimming']['brightness']=10
        self.ctrl.poll()
        self.ctrl.last_sent['light-a']={'at':time.monotonic()-COMMAND_COOLDOWN_SECONDS-0.1,'target':100}
        self.fake.calls.clear()
        self.ctrl.automate()
        self.assertEqual(len(self.fake.calls),1)
        self.assertEqual(self.fake.calls[0][1]['dimming']['brightness'],100)
        self.assertEqual(self.fake.calls[0][1]['dynamics']['duration'],2000)
        self.fake.calls.clear()
        self.ctrl.automate()
        self.assertEqual(self.fake.calls,[])

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
        self.assertEqual(result['requested']['dimming']['dimming']['brightness'],10)
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

    def test_powerup_waits_until_bridge_reports_configured(self):
        class Delayed(FakeClient):
            def __init__(self):
                super().__init__();self.pending=None;self.light_reads=0
            def resource(self,path,method='GET',payload=None):
                if method == 'PUT' and 'powerup' in (payload or {}):
                    self.calls.append((path,payload));self.pending=copy.deepcopy(payload['powerup'])
                    self.lights[0]['powerup']={**copy.deepcopy(self.pending),'configured':False}
                    return []
                if path == 'light':
                    self.light_reads += 1
                    if self.pending and self.light_reads >= 3:
                        self.lights[0]['powerup']={**copy.deepcopy(self.pending),'configured':True}
                return super().resource(path,method,payload)
        client=Delayed();ctrl=HueServer(client,self.path,logging.getLogger('test_v03'));ctrl.poll()
        result=ctrl.set_powerup('light-a','custom',10)
        self.assertTrue(result['verified_readback'])
        self.assertTrue(result['readback']['configured'])

    def test_powerup_changes_only_requested_light(self):
        class ThreeLights(FakeClient):
            def __init__(self):
                super().__init__()
                self.lights=[
                    {**copy.deepcopy(self.lights[0]),'id':'light-a','powerup':{'preset':'last_on_state'}},
                    {**copy.deepcopy(self.lights[0]),'id':'light-b','powerup':{'preset':'powerfail'}},
                    {**copy.deepcopy(self.lights[0]),'id':'light-c','powerup':{'preset':'powerfail'}},
                ]
            def resource(self,path,method='GET',payload=None):
                if method == 'PUT' and 'powerup' in (payload or {}):
                    self.calls.append((path,payload))
                    target=path.rsplit('/',1)[-1]
                    next(light for light in self.lights if light['id']==target)['powerup']={
                        **copy.deepcopy(payload['powerup']),'configured':True,
                    }
                    return []
                return super().resource(path,method,payload)
        client=ThreeLights();ctrl=HueServer(client,self.path,logging.getLogger('test_v03'));ctrl.poll()
        ctrl.set_powerup('light-c','custom',10)
        presets={light['id']:light['powerup']['preset'] for light in client.lights}
        self.assertEqual(presets,{'light-a':'last_on_state','light-b':'powerfail','light-c':'custom'})
        self.assertEqual(client.calls[0][0],'light/light-c')

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

    def test_sse_has_no_read_timeout_and_can_be_interrupted(self):
        stop=threading.Event()
        response_closed=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
            def raise_for_status(self):return None
            def iter_lines(self,decode_unicode=True):
                yield 'data: []'
                stop.set()
            def close(self):response_closed.append(True)
        response=Response()
        client=SimpleNamespace(ip='10.0.0.2',session=SimpleNamespace(headers={'hue-application-key':'secret'}))
        stream=HueEventStream(lambda:client,lambda:None,stop,logging.getLogger('test_v03'))
        with patch('hue_v03_runtime.requests.get',return_value=response) as request:
            stream._run()
        self.assertEqual(request.call_args.kwargs['timeout'],(4,None))
        self.assertTrue(response_closed)
        self.assertEqual(POLL_INTERVAL_SECONDS,1.0)

if __name__=='__main__':unittest.main()
