import math
import unittest
from vinuni_move.core import Config, SquatCounter, knee_angle
from vinuni_move.simulation import samples


class CoreTests(unittest.TestCase):
    def test_geometry(self):
        self.assertAlmostEqual(knee_angle((0, -1), (0, 0), (1, 0)), 90)
        self.assertAlmostEqual(knee_angle((0, -1), (0, 0), (0, 1)), 180)
        self.assertIsNone(knee_angle((0, 0), (0, 0), (0, 1)))
        self.assertIsNone(knee_angle((math.nan, 1), (0, 0), (0, 1)))

    def test_invariant_to_translation_and_scale(self):
        a = knee_angle((1, 3), (4, 6), (9, 7))
        b = knee_angle((102, 206), (108, 212), (118, 214))
        self.assertAlmostEqual(a, b)

    def test_clean_counts_three_at_multiple_rates(self):
        for fps in (10, 20, 30, 60):
            counter = SquatCounter()
            for s in samples(fps=fps):
                counter.update(s["t"], s["angle"], s["confidence"])
            self.assertEqual(counter.reps, 3, fps)

    def test_occlusion_does_not_bridge_a_rep(self):
        counter = SquatCounter()
        for s in samples("occlusion"):
            counter.update(s["t"], s["angle"], s["confidence"])
        self.assertEqual(counter.reps, 2)

    def test_projection_is_a_documented_failure(self):
        counter = SquatCounter()
        for s in samples("projection"):
            counter.update(s["t"], s["angle"], s["confidence"])
        self.assertEqual(counter.reps, 2)

    def test_start_at_bottom_not_a_full_rep(self):
        counter = SquatCounter(Config(smoothing_tau=0))
        for i in range(20):
            counter.update(i*.05, 85 if i < 10 else 175)
        self.assertEqual(counter.reps, 0)

    def test_too_short_a_dip_is_not_counted(self):
        counter = SquatCounter(Config(smoothing_tau=0))
        for i in range(20):
            counter.update(i*.05, 85 if i == 10 else 175)
        self.assertEqual(counter.reps, 0)

    def test_multiple_people_reset_tracking(self):
        counter = SquatCounter()
        row = counter.update(0, 175, .99, 2)
        self.assertEqual(row["status"], "MULTIPLE_PEOPLE")
        self.assertIsNone(row["angle_deg"])

    def test_frame_gap_cannot_complete_rep(self):
        counter = SquatCounter(Config(smoothing_tau=0))
        for t, angle in [(0, 175), (.2, 175), (.3, 85), (.5, 85), (2, 175), (2.2, 175)]:
            counter.update(t, angle)
        self.assertEqual(counter.reps, 0)

    def test_invalid_timestamp_rejected(self):
        counter = SquatCounter()
        counter.update(1, 175)
        with self.assertRaises(ValueError):
            counter.update(1, 175)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            Config(down=170, up=100)


if __name__ == "__main__":
    unittest.main()
