"""Download the documented Ultralytics model to an explicit local directory."""
import sys
from pathlib import Path
from urllib.request import urlretrieve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vinuni_move.vision import MODEL_PATH

if __name__ == "__main__":
    MODEL_PATH.parent.mkdir(exist_ok=True)
    if not MODEL_PATH.exists():
        urlretrieve("https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt", MODEL_PATH.with_suffix(".part"))
        MODEL_PATH.with_suffix(".part").replace(MODEL_PATH)
    print(MODEL_PATH)
