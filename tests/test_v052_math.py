import math
import unittest
from hue_simple_profile import DEFAULT_SIMPLE_PROFILE, simple_brightness_at, smootherstep, validate_simple_profile

class SimpleCurveMathTests(unittest.TestCase):
    def test_defaults_and_plateau(self):
        p = DEFAULT_SIMPLE_PROFILE
        samples = {m:simple_brightness_at(p,m) for m in (0,375,376,600,779,780,900,1080,1081,1200,1379,1380,1439,1440)}
        self.assertEqual(samples[0],10.0)
        self.assertEqual(samples[375],10.0)
        self.assertEqual(samples[780],85.0)
        self.assertEqual(samples[900],85.0)
        self.assertEqual(samples[1080],85.0)
        self.assertEqual(samples[1380],10.0)
        self.assertEqual(samples[1440],10.0)
    def test_no_reverse_direction(self):
        p=DEFAULT_SIMPLE_PROFILE
        rising=[simple_brightness_at(p,m) for m in range(p['wake'],p['morning_end']+1)]
        falling=[simple_brightness_at(p,m) for m in range(p['evening_start'],p['bed']+1)]
        self.assertTrue(all(x<=y for x,y in zip(rising,rising[1:])))
        self.assertTrue(all(x>=y for x,y in zip(falling,falling[1:])))
    def test_easing_derivatives_and_limits(self):
        self.assertEqual(smootherstep(0),0)
        self.assertEqual(smootherstep(1),1)
        self.assertEqual(smootherstep(-1),0)
        self.assertEqual(smootherstep(2),1)
        h=0.0001
        self.assertLess(smootherstep(h)/h,0.00001)
        self.assertLess((1-smootherstep(1-h))/h,0.00001)
    def test_minimal_plateau_and_short_intervals(self):
        p=dict(DEFAULT_SIMPLE_PROFILE,wake=420,morning_end=450,evening_start=450,bed=480)
        self.assertEqual(simple_brightness_at(p,450),85)
        self.assertGreater(simple_brightness_at(p,440),simple_brightness_at(p,430))
        self.assertLess(simple_brightness_at(p,460),85)
    def test_cyclic_and_fractional(self):
        p=DEFAULT_SIMPLE_PROFILE
        self.assertEqual(simple_brightness_at(p,-15),simple_brightness_at(p,1425))
        self.assertEqual(simple_brightness_at(p,400.5),simple_brightness_at(p,1840.5))
    def test_invalid_parameters(self):
        bads=[None,[],{},dict(DEFAULT_SIMPLE_PROFILE,wake=True),dict(DEFAULT_SIMPLE_PROFILE,bed=1440),dict(DEFAULT_SIMPLE_PROFILE,morning_end=375),dict(DEFAULT_SIMPLE_PROFILE,evening_start=700),dict(DEFAULT_SIMPLE_PROFILE,evening_start=1380),dict(DEFAULT_SIMPLE_PROFILE,max_brightness=10),dict(DEFAULT_SIMPLE_PROFILE,min_brightness=0),dict(DEFAULT_SIMPLE_PROFILE,extra='x')]
        for bad in bads:
            with self.subTest(bad=bad),self.assertRaises(ValueError): validate_simple_profile(bad)
        with self.assertRaises(ValueError): simple_brightness_at(DEFAULT_SIMPLE_PROFILE,float('nan'))

if __name__ == '__main__': unittest.main()
