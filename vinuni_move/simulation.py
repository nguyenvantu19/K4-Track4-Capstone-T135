"""Deterministic keypoint simulator; never represented as camera evidence."""
import math
import cv2
import numpy as np
from .core import knee_angle


def sample(t, scenario="clean"):
    # Three cycles of three seconds; start and end upright.
    phase = t % 3.
    if phase < .6 or phase >= 2.5:
        target = 175.
    elif phase < 1.3:
        target = 175.-90.*(phase-.6)/.7
    elif phase < 1.8:
        target = 85.
    else:
        target = 85.+90.*(phase-1.8)/.7
    theta = math.radians(target)
    hip, knee = (290., 205.), (290., 330.)
    ankle = (290.+125.*math.sin(theta), 330.-125.*math.cos(theta))
    confidence = .98
    # Occlusion removes the evidence for cycle 2.
    if scenario == "occlusion" and 3.8 <= t <= 5.7:
        confidence = .12
    # A controlled projection fault: same latent bend, compressed horizontal axis.
    # High confidence cannot guarantee a geometrically meaningful 2-D angle.
    if scenario == "projection" and 3 <= t < 6:
        ankle = (290.+(ankle[0]-290.)*.12, ankle[1])
        # Simulate camera elevation foreshortening: ankle projects below knee.
        ankle = (ankle[0], 330.+abs(ankle[1]-330.))
    return dict(t=t, target_angle=target, points=(hip, knee, ankle),
                angle=knee_angle(hip, knee, ankle), confidence=confidence,
                people=1, scenario=scenario)


def samples(scenario="clean", fps=20, duration=9.):
    for i in range(round(duration*fps)+1):
        yield sample(i/fps, scenario)


def render(s, row):
    image = np.full((540, 960, 3), (30, 23, 16), dtype=np.uint8)
    color = (140, 225, 70) if row["status"] == "VALID" else (70, 170, 255)
    hip, knee, ankle = [tuple(map(round, p)) for p in s["points"]]
    shoulder, head = (hip[0]-12, hip[1]-95), (hip[0]-12, hip[1]-130)
    for a, b in [(head, shoulder), (shoulder, hip), (hip, knee), (knee, ankle), (shoulder, (390, 190))]:
        cv2.line(image, a, b, color, 7, cv2.LINE_AA)
    for p in [shoulder, hip, knee, ankle]:
        cv2.circle(image, p, 10, (245, 245, 245), -1)
    cv2.circle(image, head, 25, color, 3)
    lines = ["VINUNI MOVE", "SYNTHETIC SIMULATION / NOT CAMERA", f"Case: {s['scenario']}",
             f"Time: {s['t']:.2f} s", f"Reps: {row['reps']}   Phase: {row['phase']}",
             f"Projected angle: {s['angle']:.1f} deg", f"Status: {row['status']}"]
    for i, line in enumerate(lines):
        cv2.putText(image, line, (445, 70+i*49), cv2.FONT_HERSHEY_SIMPLEX,
                    .6 if i == 1 else .75, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.putText(image, "2D angle heuristic - no assessment of injury risk", (40, 500),
                cv2.FONT_HERSHEY_SIMPLEX, .65, (170, 185, 200), 1, cv2.LINE_AA)
    return image
