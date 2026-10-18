"""Offline Three.js viewer of synthetic kinematic poses and Python counter rows."""
import base64
import json
from pathlib import Path
import streamlit as st
from .core import SquatCounter
from .simulation import samples

ROOT = Path(__file__).resolve().parents[1]


def document(scenario="clean"):
    module = ROOT / "assets" / "vendor" / "three-r160.module.min.js"
    if not module.exists():
        raise FileNotFoundError("Thiếu thư viện 3D. Chạy python tools/setup_three.py một lần.")
    counter, frames = SquatCounter(), []
    for sample in samples(scenario):
        row = counter.update(sample["t"], sample["angle"], sample["confidence"])
        frames.append(dict(row, target_angle=sample["target_angle"]))
    encoded = base64.b64encode(module.read_bytes()).decode("ascii")
    template = (ROOT / "assets" / "movement-3d.html").read_text(encoding="utf-8")
    return template.replace("__MOTION_DATA__", json.dumps(frames)).replace("__THREE_MODULE__", "data:text/javascript;base64,"+encoded)


def show(scenario="clean"):
    st.iframe(document(scenario), height=660, alt="Mô phỏng tư thế squat 3D tương tác")
