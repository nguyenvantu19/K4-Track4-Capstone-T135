"""Rebuild reproducible simulation evidence, CSV traces and backup videos."""
import csv
import json
import platform
import sys
import time
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vinuni_move.core import SquatCounter
from vinuni_move.simulation import samples, render


def run():
    destination = ROOT / "evidence"
    destination.mkdir(exist_ok=True)
    summaries = []
    for scenario in ("clean", "occlusion", "projection"):
        counter, rows, timings = SquatCounter(), [], []
        video = cv2.VideoWriter(str(destination / f"{scenario}.mp4"), cv2.VideoWriter_fourcc(*"avc1"), 20, (960, 540))
        if not video.isOpened():
            raise RuntimeError("H264 encoder unavailable; cannot produce browser-compatible backup")
        for s in samples(scenario):
            before = time.perf_counter()
            row = counter.update(s["t"], s["angle"], s["confidence"], s["people"])
            timings.append((time.perf_counter()-before)*1000)
            row.update(target_angle_deg=s["target_angle"], scenario=scenario)
            rows.append(row)
            video.write(render(s, row))
        video.release()
        with open(destination / f"{scenario}.csv", "w", newline="", encoding="utf-8") as f:
            out = csv.DictWriter(f, fieldnames=rows[0].keys())
            out.writeheader()
            out.writerows(rows)
        summaries.append(dict(scenario=scenario, frames=len(rows), source_fps=20,
                              expected_reps=3, counted_reps=counter.reps,
                              absolute_count_error=abs(counter.reps-3),
                              rejected_frames=sum(r["status"] != "VALID" for r in rows),
                              logic_p50_ms=float(np.percentile(timings, 50)),
                              logic_p95_ms=float(np.percentile(timings, 95))))
    report = dict(evidence_type="synthetic keypoints; NOT model accuracy or camera FPS",
                  python=platform.python_version(), platform=platform.platform(),
                  config=dict(down=100, up=160, confidence=.55, dwell_s=.15, smoothing_tau_s=.09),
                  scenarios=summaries)
    (destination / "benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
