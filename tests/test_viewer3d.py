import json
import re
import unittest
from vinuni_move.viewer3d import document


class ViewerTests(unittest.TestCase):
    def test_offline_payload_and_counter(self):
        html = document()
        self.assertNotIn("__THREE_MODULE__", html)
        self.assertNotIn("__MOTION_DATA__", html)
        self.assertIn("data:text/javascript;base64,", html)
        self.assertNotRegex(html, r'<script[^>]+src=["\']https?://')
        rows = json.loads(re.search(r'id="motion-data">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(len(rows), 181)
        self.assertEqual(rows[-1]["reps"], 3)
        self.assertEqual(rows[0]["target_angle"], 175)

    def test_projection_preserves_true_3d_motion_but_misses_2d_rep(self):
        html = document("projection")
        rows = json.loads(re.search(r'id="motion-data">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(rows[-1]["reps"], 2)
        self.assertTrue(any(abs(r["target_angle"]-r["raw_angle_deg"])>40 for r in rows))
