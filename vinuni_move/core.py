"""Geometry and a timestamp-based, conservative repetition counter.

No model dependency: this layer can be replayed and tested independently.
"""
from dataclasses import dataclass
import math


def knee_angle(hip, knee, ankle):
    u = [float(hip[i]) - float(knee[i]) for i in (0, 1)]
    v = [float(ankle[i]) - float(knee[i]) for i in (0, 1)]
    nu, nv = math.hypot(*u), math.hypot(*v)
    if not all(math.isfinite(x) for x in u + v) or min(nu, nv) < 1e-6:
        return None
    cosine = max(-1., min(1., sum(a*b for a, b in zip(u, v)) / (nu*nv)))
    return math.degrees(math.acos(cosine))


@dataclass(frozen=True)
class Config:
    down: float = 100.
    up: float = 160.
    confidence: float = .55
    dwell: float = .15
    smoothing_tau: float = .09
    max_gap: float = .5

    def __post_init__(self):
        if not (0 < self.down < self.up <= 180):
            raise ValueError("Need 0 < down < up <= 180")
        if not (0 <= self.confidence <= 1) or min(self.dwell, self.smoothing_tau) < 0 or self.max_gap <= 0:
            raise ValueError("Invalid confidence/timing configuration")


class SquatCounter:
    def __init__(self, config=Config()):
        self.config = config
        self.reps = 0
        self.phase = "WAIT_STAND"
        self.filtered = None
        self.last_t = None
        self.candidate = None
        self.since = None

    def _reset_tracking(self):
        self.phase = "WAIT_STAND"
        self.filtered = None
        self.candidate = self.since = None

    def update(self, t, angle, confidence=1., people=1):
        t = float(t)
        if not math.isfinite(t) or (self.last_t is not None and t <= self.last_t):
            raise ValueError("Timestamps must be finite and strictly increasing")
        dt = None if self.last_t is None else t-self.last_t
        self.last_t = t
        if dt is not None and dt > self.config.max_gap:
            self._reset_tracking()
        reason = ""
        if people != 1:
            reason = "NO_PERSON" if people == 0 else "MULTIPLE_PEOPLE"
        elif angle is None or not math.isfinite(angle) or not 0 <= angle <= 180:
            reason = "INVALID_GEOMETRY"
        elif not math.isfinite(confidence) or confidence < self.config.confidence:
            reason = "LOW_CONFIDENCE"
        if reason:
            self._reset_tracking()
            return self._result(t, angle, confidence, reason, False)
        alpha = 1. if dt is None or self.config.smoothing_tau == 0 else 1-math.exp(-dt/self.config.smoothing_tau)
        self.filtered = angle if self.filtered is None else self.filtered + alpha*(angle-self.filtered)
        zone = "UP" if self.filtered >= self.config.up else "DOWN" if self.filtered <= self.config.down else "MID"
        if zone != self.candidate:
            self.candidate, self.since = zone, t
        event = False
        if t-self.since >= self.config.dwell:
            if zone == "UP":
                if self.phase == "DOWN":
                    self.reps += 1
                    event = True
                self.phase = "STANDING"
            elif zone == "DOWN" and self.phase == "STANDING":
                self.phase = "DOWN"
        return self._result(t, angle, confidence, "VALID", event)

    def _result(self, t, angle, confidence, status, event):
        return dict(timestamp_s=round(t, 4), raw_angle_deg=angle,
                    angle_deg=self.filtered, confidence=confidence,
                    status=status, phase=self.phase, reps=self.reps,
                    rep_event=event)
