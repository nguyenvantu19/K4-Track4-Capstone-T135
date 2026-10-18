import threading
import unittest
import numpy as np
from vinuni_move.camera import CameraStream


class CameraStreamTests(unittest.TestCase):
    def test_device_is_opened_read_and_released_on_same_thread(self):
        calls = []
        class FakeCapture:
            def __init__(self, *args):
                calls.append(("open", threading.get_ident()))
            def isOpened(self):
                return True
            def read(self):
                calls.append(("read", threading.get_ident()))
                return True, np.zeros((20, 30, 3), dtype=np.uint8)
            def release(self):
                calls.append(("release", threading.get_ident()))
        stream = CameraStream(factory=FakeCapture).start()
        ok, image = stream.read()
        stream.release()
        self.assertTrue(ok)
        self.assertEqual(image.shape, (20, 30, 3))
        self.assertEqual(len({thread for _, thread in calls}), 1)
        self.assertNotEqual(calls[0][1], threading.get_ident())
        self.assertEqual(calls[-1][0], "release")

    def test_open_failure_is_reported_without_hanging(self):
        class Unavailable:
            def __init__(self, *args):
                pass
            def isOpened(self):
                return False
            def release(self):
                pass
        with self.assertRaisesRegex(RuntimeError, "Không mở được"):
            CameraStream(factory=Unavailable).start(timeout=1.)
