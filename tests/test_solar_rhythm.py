from datetime import date, datetime
from unittest import TestCase

from hue_solar_profile import DEFAULT_SOLAR_CONFIG, LEGACY_SOLAR_CONFIG, draft_profile, validate_solar_config
from hue_simple_profile import simple_brightness_at
from hue_rgb import rgb_at, DEFAULT_RGB_PHASES, hsv_to_xy, point_inside_triangle, gamut_vertices
from hue_solar_rhythm import day_white_xy, daylight_xy


class SolarRhythmTests(TestCase):
    def profile(self, **changes):
        return draft_profile(date(2026,11,6), **dict(DEFAULT_SOLAR_CONFIG, wake=315, **changes))['params']

    def test_exact_personal_targets_and_night_with_shared_duration(self):
        p=self.profile();b=lambda m:simple_brightness_at(p,m)
        c=lambda m:rgb_at(DEFAULT_RGB_PHASES,p,m)
        self.assertEqual(b(285),10)
        self.assertEqual(b(315),55)
        self.assertEqual(c(315)['s'],45)
        self.assertEqual(b(1320),55)
        self.assertEqual(b(1350),10)
        self.assertEqual(c(1350)['s'],100)
        self.assertEqual(c(1350)['h'],30)
        self.assertEqual(b(1380),10)
        self.assertEqual(b(443),85)
        self.assertEqual(c(443)['s'],0)
        self.assertEqual(b(1033),85)
        self.assertEqual(c(1033)['s'],45)
        self.assertGreater(b(1340),10,'the decline reaches its minimum at bedtime')
        self.assertGreater(b(300),10,'wakeup anticipated')

    def test_continuity_monotonicity_shapes_and_color_boundaries(self):
        p=self.profile();anchors=[285,315,443,988,1033,1290,1320,1350]
        for lo,hi,up in [(285,315,True),(315,443,True),(1290,1320,False),(1320,1350,False)]:
            levels=[simple_brightness_at(p,m) for m in range(lo,hi+1)]
            self.assertTrue(all(a<=b if up else a>=b for a,b in zip(levels,levels[1:])))
        self.assertGreater(simple_brightness_at(p,300),(10+55)/2)
        self.assertGreater(simple_brightness_at(p,1335),(10+55)/2)
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
        timing = draft['timing']
        sunset = datetime.fromisoformat(draft['sunset'])
        minute = sunset.hour * 60 + sunset.minute
        samples = {sample['minute']: sample for sample in draft['samples']}
        self.assertEqual(timing['warm_at'], minute)
        self.assertEqual(samples[timing['warm_start']]['color']['s'], 0)
        self.assertEqual(samples[minute]['color']['s'], config['saturation'])
        for m in (minute, minute + 60, timing['dim_start']):
            color = rgb_at(DEFAULT_RGB_PHASES, draft['params'], m)
            self.assertEqual(color['s'], config['saturation'])
            self.assertEqual(color['h'], config['evening_hue'])
            self.assertEqual(simple_brightness_at(draft['params'], m), 100)
        self.assertEqual(samples[config['bed']]['brightness'], config['low'])

    def test_late_sunset_and_polar_day_keep_order_and_continuity(self):
        for config in [dict(wake=315, bed=1200), dict(latitude=78.22, longitude=15.65)]:
            with self.subTest(config=config):
                draft = draft_profile(date(2027, 6, 21), **dict(DEFAULT_SOLAR_CONFIG, **config))
                p, timing = draft['params'], draft['timing']
                self.assertLess(timing['warm_at'], p['bed'])
                self.assertGreaterEqual(timing['dim_start'], p['morning_end'])
                self.assertEqual(simple_brightness_at(p, p['bed']), 10)
                self.assertEqual(rgb_at(DEFAULT_RGB_PHASES, p, p['bed'])['s'], 100)
                for minute in (timing["warm_start"], timing["warm_at"], timing["night_color_start"], p["bed"]):
                    before, after = (rgb_at(DEFAULT_RGB_PHASES, p, minute + d) for d in (-.001, .001))
                    self.assertAlmostEqual(before['s'], after['s'], places=4)

    def test_existing_fixed_rhythm_keeps_its_original_timing(self):
        p = self.profile()
        del p['solar_warm_at']
        self.assertEqual(simple_brightness_at(p, 1350), 55)
        self.assertEqual(simple_brightness_at(p, 1380), 10)
        self.assertEqual(rgb_at(DEFAULT_RGB_PHASES, p, 1033)['s'], 0)

    def test_midnight_transitions_are_cyclic_and_do_not_overlap(self):
        for config in [dict(wake=10,bed=1200),dict(wake=315,bed=1430)]:
            c=dict(DEFAULT_SOLAR_CONFIG,**config)
            p=draft_profile(date(2026,11,6),**c)['params']
            for m in [c['wake']-30,c['bed']+30]:
                self.assertEqual(simple_brightness_at(p,m),c['low'])
                self.assertEqual(rgb_at(DEFAULT_RGB_PHASES,p,m)['s'],100)
            self.assertEqual(simple_brightness_at(p,c['wake']),c['comfort'])
            self.assertEqual(simple_brightness_at(p,c['bed']),c['low'])
            self.assertEqual(simple_brightness_at(p,-.01),simple_brightness_at(p,1439.99))
        with self.assertRaises(ValueError):validate_solar_config(dict(DEFAULT_SOLAR_CONFIG,wake=60,bed=1430,transition=40))

    def test_daylight_uses_cie_d_white_separate_from_saturation_and_gamut(self):
        # D50 chromaticity, not an arbitrary white HSV or default lamp preset.
        xy=daylight_xy(5000)
        self.assertAlmostEqual(xy['x'],.34574,places=4)
        self.assertAlmostEqual(xy['y'],.35867,places=4)
        p=self.profile(day_kelvin=5000);color=rgb_at(DEFAULT_RGB_PHASES,p,720)
        self.assertEqual(color['s'],0)
        self.assertEqual(hsv_to_xy(color),{k:round(v,5) for k,v in xy.items()})
        warm=rgb_at(DEFAULT_RGB_PHASES,self.profile(day_kelvin=4000),720)
        warm_3000 = rgb_at(DEFAULT_RGB_PHASES, self.profile(day_kelvin=3000), 720)
        warm_2700 = rgb_at(DEFAULT_RGB_PHASES, self.profile(), 720)
        self.assertAlmostEqual(day_white_xy(2700)['x'], .45931, places=5)
        self.assertAlmostEqual(day_white_xy(3000)['x'], .43658, places=5)
        self.assertLess(color['xy']['x'], warm['xy']['x'])
        self.assertLess(warm['xy']['x'], warm_3000['xy']['x'])
        self.assertLess(warm_3000['xy']['x'], warm_2700['xy']['x'])
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
                      dict(saturation=101),dict(day_kelvin=2699),dict(morning_hue=360)]:
            with self.subTest(delta=delta),self.assertRaises(ValueError):validate_solar_config(dict(DEFAULT_SOLAR_CONFIG,**delta))
        with self.assertRaises(ValueError):validate_solar_config(dict(LEGACY_SOLAR_CONFIG,transition=30))
        for m in [float('inf'),float('nan')]:
            with self.assertRaises(ValueError):simple_brightness_at(self.profile(),m)
