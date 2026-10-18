"""UI integration checks: each workspace renders, controls alter live results."""
import unittest
import time
from unittest.mock import Mock, patch
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_simulator_and_failure_interaction(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "3")
        app.selectbox[0].select("Ca lỗi: sai góc chiếu lần 2").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "2")
        self.assertTrue(any("CA LỖI" in warning.value for warning in app.warning))

    def test_other_workspaces(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        for name in ["Mô phỏng 3D", "Video & webcam", "Bằng chứng", "Mục 4–9 & demo", "Hướng dẫn chạy local", "Mô phỏng tương tác"]:
            app.sidebar.radio[0].set_value(name).run()
            self.assertEqual(len(app.exception), 0, name)

    def test_seek_pause_and_reset(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.slider(key="replay_frame").set_value(100).run()
        self.assertEqual(app.session_state["active_frame"], 100)
        next(b for b in app.button if b.label == "▶ Chạy mô phỏng").click().run()
        self.assertTrue(app.session_state["playing"])
        next(b for b in app.button if b.label == "Tạm dừng").click().run()
        self.assertFalse(app.session_state["playing"])
        self.assertEqual(app.session_state["selected_frame"], app.session_state["active_frame"])
        self.assertGreaterEqual(app.session_state["active_frame"], 100)
        next(b for b in app.button if b.label == "Về đầu").click().run()
        self.assertEqual(app.session_state["active_frame"], 0)
        self.assertEqual(len(app.exception), 0)

    def test_playback_reaches_end_without_widget_state_error(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.session_state["playing"] = True
        app.session_state["play_start"] = time.perf_counter()-10
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.session_state["playing"])
        self.assertEqual(app.session_state["replay_frame"], 180)

    def test_webcam_does_not_open_until_start_and_releases_on_navigation(self):
        with patch("cv2.VideoCapture") as capture:
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
            app.sidebar.radio[0].set_value("Video & webcam").run()
            app.checkbox[0].check().run()
            app.radio[0].set_value("Webcam trực tiếp").run()
            self.assertEqual(len(app.exception), 0)
            capture.assert_not_called()
            fake_camera = Mock()
            app.session_state["camera_capture"] = fake_camera
            app.session_state["camera_running"] = True
            app.sidebar.radio[0].set_value("Mô phỏng tương tác").run()
            self.assertEqual(len(app.exception), 0)
            fake_camera.release.assert_called_once()
            self.assertFalse(app.session_state["camera_running"])


if __name__ == "__main__":
    unittest.main()
