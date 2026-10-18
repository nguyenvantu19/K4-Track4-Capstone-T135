"""Measure CPU inference sizes on one real frame in RAM; never save footage."""
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vinuni_move.camera import CameraStream
from vinuni_move.vision import load_model, infer

if __name__ == "__main__":
    camera = CameraStream(0).start()
    try:
        _, frame = camera.read()
    finally:
        camera.release()
    model = load_model()
    reports = []
    for size in (640, 416, 320):
        infer(model, frame, imgsz=size, draw=False)
        times = []
        for _ in range(8):
            started = time.perf_counter()
            infer(model, frame, imgsz=size, draw=False)
            times.append((time.perf_counter()-started)*1000)
        reports.append(dict(imgsz=size, samples=len(times), median_ms=round(statistics.median(times), 2), max_ms=round(max(times), 2)))
    result = dict(source="one real webcam frame kept only in RAM", includes="CPU model inference; excludes browser/stream delivery", measurements=reports)
    out = ROOT / ".test-tmp" / "webcam-speed.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
