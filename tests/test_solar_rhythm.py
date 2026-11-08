from datetime import date
from unittest import TestCase

from hue_solar_profile import DEFAULT_SOLAR_CONFIG, LEGACY_SOLAR_CONFIG, draft_profile, validate_solar_config
from hue_simple_profile import simple_brightness_at
from hue_rgb import rgb_at, DEFAULT_RGB_PHASES, hsv_to_xy, point_inside_triangle, gamut_vertices
from hue_solar_rhythm import daylight_xy


class SolarRhythmTests(TestCase):
    def profile(self, **changes):
        return draft_profile(date(2026,11,6), **dict(DEFAULT_SOLAR_CONFIG, wake=315, **changes))['params']

    def test_exact_personal_targets_and_night_with_shared_duration(self):
        p=self.profile();b=lambda m:simple_brightness_at(p,m)
        c=lambda m:rgb_at(DEFAULT_RGB_PHASES,p,m)
        self.assertEqual(b(285),10)
        self.assertEqual(b(315),55)
        self.assertEqual(c(315)['s'],45)
        self.assertEqual(b(1350),55)
        self.assertEqual(c(1350)['s'],45)
        self.assertEqual(b(1380),10)
        self.assertEqual(c(1380)['s'],100)
        self.assertEqual(c(1380)['h'],16)
        self.assertEqual(b(443),85)
        self.assertEqual(c(443)['s'],0)
        self.assertEqual(b(1033),85)
        self.assertEqual(c(1033)['s'],0)
        self.assertGreater(b(1340),55,'comfort remains available before bed')
        self.assertGreater(b(300),10,'wakeup anticipated')

    def test_continuity_monotonicity_shapes_and_color_boundaries(self):
        p=self.profile();anchors=[285,315,443,1033,1350,1380]
        for lo,hi,up in [(285,315,True),(315,443,True),(1033,1350,False),(1350,1380,False)]:
            levels=[simple_brightness_at(p,m) for m in range(lo,hi+1)]
            self.assertTrue(all(a<=b if up else a>=b for a,b in zip(levels,levels[1:])))
        self.assertGreater(simple_brightness_at(p,300),(10+55)/2)
        self.assertGreater(simple_brightness_at(p,1365),(10+55)/2)
        for m in anchors+[0,1440]:
            self.assertLess(abs(simple_brightness_at(p,m-.001)-simple_brightness_at(p,m+.001)),.03)
            a,b=(rgb_at(DEFAULT_RGB_PHASES,p,t) for t in [m-.001,m+.001])
            self.assertLess(abs(a['xy']['x']-b['xy']['x']),.0001)
            self.assertLess(abs(a['xy']['y']-b['xy']['y']),.0001)
        for m in range(1440):
            c=rgb_at(DEFAULT_RGB_PHASES,p,m)
            self.assertTrue(0<=c['s']<=100)
            self.assertTrue(10<=simple_brightness_at(p,m)<=85)

    def test_evening_color_develops_while_the_room_is_still_bright(self):
        config = dict(DEFAULT_SOLAR_CONFIG, wake=315, high=100)
        draft = draft_profile(date(2026, 11, 8), **config)
        sunset = draft['params']['evening_start']
        samples = {sample['minute']: sample for sample in draft['samples']}
        self.assertEqual(samples[sunset]['color']['s'], 0)
        self.assertGreater(samples[sunset + 60]['color']['s'], 8)
        self.assertEqual(samples[sunset + 60]['brightness'], 99.98)
        self.assertGreater(samples[sunset + 130]['color']['s'], 30)
        self.assertEqual(samples[sunset + 130]['brightness'], 98.44)
        self.assertEqual(samples[config['bed']]['color']['s'], config['saturation'])

    def test_midnight_transitions_are_cyclic_and_do_not_overlap(self):
        for config in [dict(wake=10,bed=1200),dict(wake=315,bed=1430)]:
            c=dict(DEFAULT_SOLAR_CONFIG,**config)
            p=draft_profile(date(2026,11,6),**c)['params']
            for m in [c['wake']-30,c['bed']+30]:
                self.assertEqual(simple_brightness_at(p,m),c['low'])
                self.assertEqual(rgb_at(DEFAULT_RGB_PHASES,p,m)['s'],100)
            self.assertEqual(simple_brightness_at(p,c['wake']),c['comfort'])
            self.assertEqual(simple_brightness_at(p,c['bed']),c['comfort'])
            self.assertEqual(simple_brightness_at(p,-.01),simple_brightness_at(p,1439.99))
        with self.assertRaises(ValueError):validate_solar_config(dict(DEFAULT_SOLAR_CONFIG,wake=60,bed=1430,transition=40))

    def test_daylight_uses_cie_d_white_separate_from_saturation_and_gamut(self):
        # D50 chromaticity, not an arbitrary white HSV or default lamp preset.
        xy=daylight_xy(5000)
        self.assertAlmostEqual(xy['x'],.34574,places=4)
        self.assertAlmostEqual(xy['y'],.35867,places=4)
        p=self.profile();color=rgb_at(DEFAULT_RGB_PHASES,p,720)
        self.assertEqual(color['s'],0)
        self.assertEqual(hsv_to_xy(color),{k:round(v,5) for k,v in xy.items()})
        warm=rgb_at(DEFAULT_RGB_PHASES,self.profile(day_kelvin=4000),720)
        self.assertGreater(warm['xy']['x'],color['xy']['x'])
        from test_v06_rgb_integration import GAMUT
        for minute in [0,300,720,1200,1350,1380]:
            result=hsv_to_xy(rgb_at(DEFAULT_RGB_PHASES,p,minute),GAMUT)
            self.assertTrue(point_inside_triangle((result['x'],result['y']),gamut_vertices(GAMUT)) or
                            min(abs(result['x']-v[0])+abs(result['y']-v[1]) for v in gamut_vertices(GAMUT))<.0001)

    def test_legacy_profiles_are_not_implicitly_converted_and_reject_partial_new_settings(self):
        self.assertEqual(validate_solar_config(LEGACY_SOLAR_CONFIG),LEGACY_SOLAR_CONFIG)
        old=draft_profile(date(2026,11,6),**LEGACY_SOLAR_CONFIG)['params']
        self.assertNotIn('solar_rhythm',old)
        self.assertEqual(simple_brightness_at(old,1350),10)
        for delta in [dict(comfort=5),dict(comfort=100),dict(transition=0),dict(transition=True),
                      dict(saturation=101),dict(day_kelvin=3999),dict(morning_hue=360)]:
            with self.subTest(delta=delta),self.assertRaises(ValueError):validate_solar_config(dict(DEFAULT_SOLAR_CONFIG,**delta))
        with self.assertRaises(ValueError):validate_solar_config(dict(LEGACY_SOLAR_CONFIG,transition=30))
        for m in [float('inf'),float('nan')]:
            with self.assertRaises(ValueError):simple_brightness_at(self.profile(),m)
