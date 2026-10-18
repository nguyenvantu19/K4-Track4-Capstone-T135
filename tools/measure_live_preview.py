"""Measure the real local preview path; discard every JPEG after reception."""
import json
from pathlib import Path
import statistics
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vinuni_move.camera import CameraStream
from vinuni_move.live_pipeline import LivePipeline

if __name__ == "__main__":
    camera = CameraStream(0).start()
    pipeline = LivePipeline(camera, imgsz=416).start()
    received, source_ids = [], []
    try:
        started = time.perf_counter()
        with urlopen(pipeline.url, timeout=5) as response:
            while time.perf_counter()-started < 30:
                line = response.readline().strip()
                if line != b"--frame":
                    continue
                headers = {}
                while True:
                    line = response.readline().strip()
                    if not line:
                        break
                    key, value = line.split(b":", 1)
                    headers[key.lower()] = value.strip()
                response.read(int(headers[b"content-length"]))
                received.append(time.perf_counter())
                source_ids.append(int(headers[b"x-source-frame"]))
                if len(received) >= 60 and pipeline.processed >= 15:
                    break
        state, rows = pipeline.stats(), pipeline.rows()
        report = dict(source="real integrated webcam; no footage saved", mode="balanced 416; preview without pose overlay",
                      preview_unique_frames=len(set(source_ids)), preview_frames=len(received),
                      received_fps=round((len(received)-1)/(received[-1]-received[0]), 2) if len(received)>1 else 0,
                      analysis_fps=round(state["analysis_fps"], 2), processed=state["processed"],
                      processing_median_ms=round(statistics.median(r["processing_ms"] for r in rows), 2) if rows else None,
                      capture_to_result_median_ms=round(statistics.median(r["capture_to_result_ms"] for r in rows),2) if rows else None,
                      excludes="browser paint and monitor latency")
        output = ROOT/".test-tmp"/"live-preview-performance.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
    finally:
        pipeline.close()
        camera.release()
