"""Local pretrained YOLO pose adapter. No remote image/video inference."""
from pathlib import Path
import cv2
from .core import knee_angle

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "yolo11n-pose.pt"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Chua co model. Chay: python tools/setup_model.py")
    from ultralytics import YOLO
    model = YOLO(str(MODEL_PATH))
    model.add_callback("on_predict_start", _limit_cpu_threads)
    return model


def _limit_cpu_threads(predictor):
    # Ultralytics configures its CPU backend on first prediction. Apply the
    # limit afterwards so capture, JPEG encoding and the UI retain CPU time.
    import torch
    if torch.get_num_threads() != 2:
        torch.set_num_threads(2)


def infer(model, frame, side="left", *, imgsz=640, draw=True):
    result = model.predict(frame, imgsz=imgsz, conf=.35, device="cpu", verbose=False)[0]
    count = 0 if result.keypoints is None else len(result.keypoints)
    if count != 1:
        return frame.copy(), None, 0., count
    indices = [11, 13, 15] if side == "left" else [12, 14, 16]
    points = result.keypoints.xy[0, indices].cpu().numpy()
    conf = result.keypoints.conf
    confidence = 0. if conf is None else float(conf[0, indices].min().item())
    angle = knee_angle(*points)
    return result.plot(boxes=False) if draw else frame.copy(), angle, confidence, count


def annotate(image, row):
    angle = row["angle_deg"]
    text = f"Reps {row['reps']} | {row['phase']} | {row['status']} | angle {angle:.1f}" if angle is not None else f"Reps {row['reps']} | {row['status']}"
    cv2.rectangle(image, (0, 0), (image.shape[1], 46), (28, 25, 20), -1)
    cv2.putText(image, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .6, (240, 245, 240), 1, cv2.LINE_AA)
    return image
