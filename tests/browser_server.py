"""Dedicated browser fixture: real Hue Lab routes with fake lamps, no Hue network."""
import copy
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hue_web
from test_v05 import ThreeLamps
from test_v06_rgb_integration import GAMUT

TEMP = TemporaryDirectory()
ROOT = Path(TEMP.name)
bridge = ThreeLamps()
bridge.ip = '10.0.0.12'
for lamp in bridge.lights[:2]:
    lamp['color'] = {'xy': {'x': .3, 'y': .3}, 'gamut': copy.deepcopy(GAMUT)}
server = hue_web.HueServer(bridge, ROOT / 'settings.json', logging.getLogger('browser'))
server.poll()
original_state = server.state

def state_after_poll():
    server.poll()
    return original_state()

server.state = state_after_poll
hue_web.controller = server
config = ROOT / 'config.json'
config.write_text(json.dumps({'ip': bridge.ip, 'key': 'fake-browser-key'}))
hue_web.setup = hue_web.HueOnboarding(config)
hue_web.setup.discover = lambda: [bridge.ip]
app = hue_web.app
