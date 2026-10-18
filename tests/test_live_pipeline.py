import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen
import cv2
import numpy as np
from vinuni_move.live_pipeline import LivePipeline


def wait_until(predicate, timeout=2):
    deadline = time.perf_counter()+timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.002)
    raise AssertionError("Timed out waiting for live result")


class Source:
    def __init__(self):
        self.version = 1
        self.frame_index = 1

    def snapshot(self, after_sequence=None):
        self.frame_index = self.version
        if after_sequence is not None and after_sequence >= self.version:
            return None
        return self.version, time.perf_counter(), np.full((60, 80, 3), self.version, dtype=np.uint8)


class PipelineTests(unittest.TestCase):
    def test_old_result_is_marked_stale_and_angle_hidden(self):
        pipeline = LivePipeline(Source())
        captured = time.perf_counter()
        pipeline._packet = (dict(angle_deg=175., confidence=.98, status="VALID", reps=0), captured, None)
        with patch("vinuni_move.live_pipeline.time.perf_counter", return_value=captured+1.1):
            state = pipeline.stats()
        self.assertEqual(state["row"]["status"], "STALE_RESULT")
        self.assertIsNone(state["row"]["angle_deg"])
        self.assertEqual(state["row"]["confidence"], 0.)

    def test_slow_model_skips_old_frames_and_preview_stays_available(self):
        source, entered, unblock = Source(), threading.Event(), threading.Event()
        seen = []
        def process(model, frame, side, **options):
            seen.append(int(frame[0, 0, 0]))
            if len(seen) == 1:
                entered.set()
                unblock.wait(2)
            return frame, 175., .98, 1
        pipeline = LivePipeline(source, processor=process, model_loader=lambda: object()).start(serve=False)
        try:
            self.assertTrue(entered.wait(1))
            source.version = 99
            # A busy model never blocks getting the newest preview frame.
            packet = pipeline.preview_packet()
            self.assertEqual(packet[1], 99)
            unblock.set()
            wait_until(lambda: pipeline.processed >= 2)
            self.assertEqual(seen[:2], [1, 99])
            self.assertEqual([row["source_frame"] for row in pipeline.rows()][:2], [1, 99])
        finally:
            unblock.set()
            pipeline.close()
        self.assertFalse(pipeline._thread.is_alive())

    def test_stream_is_loopback_token_protected_and_contains_valid_jpeg(self):
        source = Source()
        pipeline = LivePipeline(source, model_loader=lambda: object(), processor=lambda m,f,s,**k: (f,175.,.98,1)).start()
        try:
            self.assertEqual(pipeline.server.server_address[0], "127.0.0.1")
            with self.assertRaises(HTTPError) as error:
                urlopen(pipeline.url.rsplit("/", 1)[0]+"/wrong-token", timeout=1)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
            with urlopen(pipeline.url, timeout=2) as response:
                self.assertIn("multipart/x-mixed-replace", response.headers["Content-Type"])
                self.assertEqual(response.readline().strip(), b"--frame")
                headers = {}
                while True:
                    line = response.readline().strip()
                    if not line:
                        break
                    key, value = line.split(b":",1)
                    headers[key.lower()] = value.strip()
                jpeg = response.read(int(headers[b"content-length"]))
                image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                self.assertEqual(image.shape, (60,80,3))
                self.assertEqual(headers[b"x-source-frame"], b"1")
        finally:
            pipeline.close()
        self.assertFalse(pipeline._thread.is_alive())

    def test_pose_overlay_uses_the_analysed_frame(self):
        source = Source()
        pipeline = LivePipeline(source, skeleton=True, processor=lambda m,f,s,**k: (f,175.,.98,1), model_loader=lambda: object()).start(serve=False)
        try:
            wait_until(lambda: pipeline.processed == 1)
            self.assertEqual(pipeline.preview_packet()[1], 1)
            self.assertIsNone(pipeline.preview_packet(after_sequence=1))
        finally:
            pipeline.close()
