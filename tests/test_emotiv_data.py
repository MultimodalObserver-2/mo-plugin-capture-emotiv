import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'emotiv_recorder'))

from emotiv_data import EmotivData, EmotivMetrics, EmotivPower


class TestEmotivMetrics(unittest.TestCase):

    def test_defaults(self):
        m = EmotivMetrics()
        self.assertEqual(m.stress, 0.0)
        self.assertEqual(m.engagement, 0.0)
        self.assertEqual(m.interest, 0.0)
        self.assertEqual(m.excitement, 0.0)
        self.assertEqual(m.focus, 0.0)
        self.assertEqual(m.relaxation, 0.0)

    def test_set_values(self):
        m = EmotivMetrics(stress=0.5, engagement=0.8, interest=0.3,
                          excitement=0.2, focus=0.9, relaxation=0.4)
        self.assertAlmostEqual(m.stress, 0.5)
        self.assertAlmostEqual(m.engagement, 0.8)
        self.assertAlmostEqual(m.interest, 0.3)
        self.assertAlmostEqual(m.excitement, 0.2)
        self.assertAlmostEqual(m.focus, 0.9)
        self.assertAlmostEqual(m.relaxation, 0.4)

    def test_str_field_labels(self):
        m = EmotivMetrics(stress=0.1, engagement=0.2)
        s = str(m)
        self.assertIn("str:", s)
        self.assertIn("eng:", s)
        self.assertIn("foc:", s)

    def test_str_shows_values(self):
        m = EmotivMetrics(stress=0.55)
        s = str(m)
        self.assertIn("0.55", s)

    def test_independent_instances(self):
        m1 = EmotivMetrics()
        m2 = EmotivMetrics()
        m1.stress = 0.9
        self.assertEqual(m2.stress, 0.0)


class TestEmotivPower(unittest.TestCase):

    def test_defaults(self):
        p = EmotivPower()
        self.assertEqual(p.theta, 0.0)
        self.assertEqual(p.alpha, 0.0)
        self.assertEqual(p.low_beta, 0.0)
        self.assertEqual(p.high_beta, 0.0)
        self.assertEqual(p.gamma, 0.0)

    def test_set_values(self):
        p = EmotivPower(theta=5.0, alpha=8.0, low_beta=12.0,
                        high_beta=20.0, gamma=30.0)
        self.assertAlmostEqual(p.theta, 5.0)
        self.assertAlmostEqual(p.alpha, 8.0)
        self.assertAlmostEqual(p.low_beta, 12.0)
        self.assertAlmostEqual(p.high_beta, 20.0)
        self.assertAlmostEqual(p.gamma, 30.0)

    def test_independent_instances(self):
        p1 = EmotivPower()
        p2 = EmotivPower()
        p1.theta = 99.0
        self.assertEqual(p2.theta, 0.0)


class TestEmotivData(unittest.TestCase):

    def test_defaults(self):
        d = EmotivData()
        self.assertEqual(d.timestamp, 0.0)
        self.assertEqual(d.battery_level, 0)
        self.assertEqual(d.signal_quality, 0)
        self.assertEqual(d.headset_id, "")
        self.assertIsNone(d.status)

    def test_metrics_type(self):
        d = EmotivData()
        self.assertIsInstance(d.metrics, EmotivMetrics)

    def test_power_type(self):
        d = EmotivData()
        self.assertIsInstance(d.power, EmotivPower)

    def test_independent_(self):
        d1 = EmotivData()
        d2 = EmotivData()
        d1.metrics.stress = 0.9
        self.assertEqual(d2.metrics.stress, 0.0)

    def test_independent_power_per_instance(self):
        d1 = EmotivData()
        d2 = EmotivData()
        d1.power.theta = 99.0
        self.assertEqual(d2.power.theta, 0.0)

    def test_set_scalar_fields(self):
        d = EmotivData()
        d.timestamp = 123.0
        d.battery_level = 75
        d.signal_quality = 4
        d.headset_id = "EPOC-001"
        d.status = "connected"
        self.assertAlmostEqual(d.timestamp, 123.0)
        self.assertEqual(d.battery_level, 75)
        self.assertEqual(d.signal_quality, 4)
        self.assertEqual(d.headset_id, "EPOC-001")
        self.assertEqual(d.status, "connected")

    def test_str_contains_time_and_battery(self):
        d = EmotivData()
        d.timestamp = 1.0
        d.battery_level = 100
        s = str(d)
        self.assertIn("Time:", s)
        self.assertIn("Bat:", s)
        self.assertIn("Metrics", s)
        self.assertIn("Pow", s)


if __name__ == '__main__':
    unittest.main()
