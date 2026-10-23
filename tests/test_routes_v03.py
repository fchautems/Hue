import unittest
from fastapi.testclient import TestClient
import hue_web
from test_server import FakeClient
from pathlib import Path
from tempfile import TemporaryDirectory
import logging

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.original=hue_web.controller
        self.temp=TemporaryDirectory()
        hue_web.controller=hue_web.HueServer(FakeClient(),Path(self.temp.name)/'settings.json',logging.getLogger('routes'))
        hue_web.controller.poll()
        self.http=TestClient(hue_web.app)
    def tearDown(self):
        hue_web.controller=self.original
        self.temp.cleanup()
        self.http.close()
    def test_mode_endpoint(self):
        r=self.http.post('/api/mode',json={'mode':'reel'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.http.get('/api/state').json()['mode'],'reel')
        r=self.http.post('/api/mode',json={'mode':'accelere'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.http.get('/api/state').json()['mode'],'accelere')
        self.assertFalse(self.http.get('/api/state').json()['auto'])
    def test_simulation_requires_mode(self):
        r=self.http.post('/api/simulation',json={'minute':600})
        self.assertEqual(r.status_code,400)
        self.http.post('/api/mode',json={'mode':'accelere'})
        self.assertEqual(self.http.post('/api/simulation',json={'minute':600}).status_code,200)
    def test_powerup_api_readback(self):
        r=self.http.post('/api/light/light-a/powerup',json={'preset':'custom','brightness':10})
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.json()['data']['verified_readback'])

if __name__=='__main__':unittest.main()