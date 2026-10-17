"""Smoke test real model loading and no-person handling; no human data needed."""
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vinuni_move.vision import load_model, infer, MODEL_PATH

model = load_model()
rows = []
for _ in range(3):
    start = time.perf_counter()
    image, angle, confidence, people = infer(model, np.zeros((480, 640, 3), dtype=np.uint8))
    rows.append(dict(processing_ms=(time.perf_counter()-start)*1000,
                     people=people, angle=angle, confidence=confidence))
    assert people == 0 and angle is None
report = dict(test="real YOLO model on three blank frames; not accuracy validation", python=platform.python_version(),
              versions={name: importlib.metadata.version(name) for name in ["numpy", "pandas", "opencv-python", "streamlit", "ultralytics", "torch"]},
              model_sha256=hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(), results=rows)
(ROOT / "evidence" / "vision_smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
