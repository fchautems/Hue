"""v0.6: validation, smooth colour schedule, Hue xy conversion and gamut."""
import copy
import math
import unittest

from hue_rgb import (
    DEFAULT_RGB_PHASES, DEFAULT_MANUAL_COLOR, validate_hs, validate_rgb_phases,
    rgb_at, hsv_to_xy, gamut_vertices, point_inside_triangle, xy_distance,
)
from hue_simple_profile import DEFAULT_SIMPLE_PROFILE


class HueRGBMathTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(validate_rgb_phases(DEFAULT_RGB_PHASES), DEFAULT_RGB_PHASES)
        self.assertEqual(validate_hs(DEFAULT_MANUAL_COLOR), DEFAULT_MANUAL_COLOR)

    def test_hue_and_saturation_are_strict(self):
        for bad in ({'h': 360, 's': 20}, {'h': -1, 's': 20},
                    {'h': 10.5, 's': 20}, {'h': True, 's': 20},
                    {'h': 10, 's': '70'}, {'h': 10, 's': 101}, {'h': 10}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_hs(bad)

    def test_all_four_colours_required(self):
        with self.assertRaises(ValueError):
            validate_rgb_phases({'day': {'h': 0, 's': 0}})

    def test_colour_plateaux_and_overnight(self):
        p=DEFAULT_SIMPLE_PROFILE
        c=DEFAULT_RGB_PHASES
        for t in (0, p['wake'], p['bed'], 1439.9):
            self.assertEqual(rgb_at(c,p,t), c['night'])
        for t in (p['morning_end'], 900, p['evening_start']):
            self.assertEqual(rgb_at(c,p,t), c['day'])
        self.assertEqual(rgb_at(c,p,(p['wake']+p['morning_end'])/2),c['morning'])
        self.assertEqual(rgb_at(c,p,(p['evening_start']+p['bed'])/2),c['evening'])

    def test_continuity_at_all_transition_boundaries(self):
        p=DEFAULT_SIMPLE_PROFILE
        boundaries=[p['wake'],(p['wake']+p['morning_end'])/2,p['morning_end'],
                    p['evening_start'],(p['evening_start']+p['bed'])/2,p['bed'],0,1440]
        for bound in boundaries:
            left=rgb_at(DEFAULT_RGB_PHASES,p,bound-0.001)
            right=rgb_at(DEFAULT_RGB_PHASES,p,bound+0.001)
            dist=abs(((right['h']-left['h']+180)%360)-180)
            with self.subTest(bound=bound):
                self.assertLess(dist,0.001)
                self.assertLess(abs(right['s']-left['s']),0.001)

    def test_shortest_hue_path_through_zero(self):
        c=copy.deepcopy(DEFAULT_RGB_PHASES)
        c['night']={'h':350,'s':70};c['morning']={'h':10,'s':70}
        p=DEFAULT_SIMPLE_PROFILE
        pos=p['wake']+(p['morning_end']-p['wake'])/4
        colour=rgb_at(c,p,pos)
        self.assertAlmostEqual(colour['h'],0,places=3)

    def test_all_times_finite(self):
        with self.assertRaises(ValueError):rgb_at(DEFAULT_RGB_PHASES,DEFAULT_SIMPLE_PROFILE,float('nan'))
        with self.assertRaises(ValueError):rgb_at(DEFAULT_RGB_PHASES,DEFAULT_SIMPLE_PROFILE,float('inf'))

    def test_primary_rgb_xy_values(self):
        for hs in ({'h':0,'s':100},{'h':120,'s':100},{'h':240,'s':100},{'h':50,'s':30},{'h':0,'s':0}):
            xy=hsv_to_xy(hs)
            self.assertTrue(0<xy['x']<1 and 0<xy['y']<1)
            self.assertLess(xy['x']+xy['y'],1)

    def test_saturation_zero_is_neutral_white(self):
        a=hsv_to_xy({'h':0,'s':0});b=hsv_to_xy({'h':220,'s':0})
        self.assertEqual(a,b)
        self.assertAlmostEqual(a['x'],0.3127,delta=0.001)

    def test_xy_never_outside_device_gamut(self):
        gamut={'red':{'x':0.7,'y':0.3}, 'green':{'x':0.17,'y':0.7}, 'blue':{'x':0.15,'y':0.06}}
        verts=gamut_vertices(gamut)
        for h in range(0,360,5):
            for sat in (0,30,70,100):
                xy=hsv_to_xy({'h':h,'s':sat},gamut)
                self.assertTrue(point_inside_triangle((xy['x'],xy['y']),verts))

    def test_invalid_gamut_is_ignored(self):
        bad={'red':{'x':1.2,'y':0.3},'green':{'x':0.2,'y':0.7},'blue':{'x':0.2,'y':0.1}}
        self.assertIsNone(gamut_vertices(bad))
        self.assertEqual(hsv_to_xy({'h':32,'s':80},bad),hsv_to_xy({'h':32,'s':80}))

    def test_xy_distance(self):
        self.assertEqual(xy_distance({'x':.2,'y':.3},{'x':.2,'y':.3}),0)
        self.assertTrue(math.isinf(xy_distance(None,{'x':.2,'y':.3})))


if __name__ == '__main__':unittest.main()
