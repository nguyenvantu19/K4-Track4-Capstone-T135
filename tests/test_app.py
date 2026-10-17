"""UI integration checks: each workspace renders, controls alter live results."""
import unittest
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
        for name in ["Video & webcam", "Bằng chứng", "Mục 4–9 & demo"]:
            app.sidebar.radio[0].set_value(name).run()
            self.assertEqual(len(app.exception), 0, name)


if __name__ == "__main__":
    unittest.main()
