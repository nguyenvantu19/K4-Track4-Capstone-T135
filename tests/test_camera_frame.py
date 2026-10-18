import base64
import re
import unittest
import cv2
import numpy as np
from vinuni_move.ui import camera_frame


class CameraFrameTests(unittest.TestCase):
    def test_live_frame_is_self_contained_and_decodable(self):
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        markup = camera_frame(image)
        self.assertNotIn("/media/", markup)
        self.assertIn('alt="Luồng webcam', markup)
        encoded = re.search(r"base64,([^\"]+)", markup).group(1)
        decoded = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, image.shape)
