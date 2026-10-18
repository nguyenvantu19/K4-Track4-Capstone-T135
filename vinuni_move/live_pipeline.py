"""Independent, freshest-frame pose analysis and loopback-only MJPEG preview."""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import threading
import time
import cv2
from .core import SquatCounter
from .vision import load_model, infer, annotate


class LivePipeline:
    def __init__(self, camera, side="left", *, imgsz=416, skeleton=False,
                 preview_fps=20, jpeg_quality=76, processor=None, model_loader=None):
        self.camera, self.side = camera, side
        self.imgsz, self.skeleton = imgsz, skeleton
        self.preview_fps, self.jpeg_quality = preview_fps, jpeg_quality
        self.processor, self.model_loader = processor or infer, model_loader or load_model
        self.started = time.perf_counter()
        self.counter = SquatCounter()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._rows = deque(maxlen=30000)
        self._times = deque(maxlen=30)
        self._preview_times = deque(maxlen=60)
        self._packet = None
        self.processed = 0
        self.error = None
        self.server = None
        self.url = None
        self._thread = threading.Thread(target=self._run, name="VinUniPose", daemon=True)

    def start(self, serve=True):
        if serve:
            self._start_preview()
        self._thread.start()
        return self

    def _run(self):
        try:
            model = self.model_loader()
            last_sequence = -1
            while not self._stop.is_set():
                sample = self.camera.snapshot(after_sequence=last_sequence)
                if sample is None:
                    self._stop.wait(.005)
                    continue
                sequence, captured_at, frame = sample
                if captured_at < self.started:
                    self._stop.wait(.005)
                    continue
                before = time.perf_counter()
                image, angle, confidence, people = self.processor(model, frame, self.side, imgsz=self.imgsz, draw=self.skeleton)
                finished = time.perf_counter()
                if self._stop.is_set():
                    break
                row = self.counter.update(captured_at-self.started, angle, confidence, people)
                row.update(processing_ms=(finished-before)*1000,
                           capture_to_result_ms=(finished-captured_at)*1000,
                           source_frame=sequence)
                with self._lock:
                    self._rows.append(row)
                    self._times.append(finished)
                    self.processed += 1
                    self._packet = (row, captured_at, image if self.skeleton else None)
                last_sequence = sequence
        except Exception as error:
            if not self._stop.is_set():
                self.error = str(error)

    def stats(self):
        with self._lock:
            packet = self._packet
            fps = (len(self._times)-1)/(self._times[-1]-self._times[0]) if len(self._times)>1 else 0.
            preview_fps = (len(self._preview_times)-1)/(self._preview_times[-1]-self._preview_times[0]) if len(self._preview_times)>1 else 0.
            if packet is None:
                row = dict(timestamp_s=0., angle_deg=None, confidence=0., status="MODEL_LOADING", phase="WAIT_STAND", reps=0)
                age = None
            else:
                row = dict(packet[0])
                age = (time.perf_counter()-packet[1])*1000
                if age > 1000:
                    row.update(angle_deg=None, confidence=0., status="STALE_RESULT")
            return dict(row=row, analysis_fps=fps, preview_fps=preview_fps, result_age_ms=age, processed=self.processed,
                        captured=self.camera.frame_index, error=self.error)

    def rows(self):
        with self._lock:
            return list(self._rows)

    def preview_packet(self, after_sequence=None):
        with self._lock:
            packet = self._packet
        # Pose overlay stays on the exact analysed image. Smooth mode displays
        # fresh camera frames and the asynchronously updated counter only.
        if self.skeleton and packet is not None and time.perf_counter()-packet[1] <= 1:
            image, row = packet[2].copy(), dict(packet[0])
            sequence = row["source_frame"]
            if after_sequence is not None and sequence <= after_sequence:
                return None
        else:
            sample = self.camera.snapshot(after_sequence=after_sequence)
            if sample is None:
                return None
            image = sample[2]
            sequence = sample[0]
            row = self.stats()["row"]
        if image.shape[1] > 960:
            image = cv2.resize(image, (960, round(image.shape[0]*960/image.shape[1])))
        ok, encoded = cv2.imencode(".jpg", annotate(image, row), [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        return (encoded.tobytes(), sequence) if ok else None

    def _start_preview(self):
        pipeline = self
        endpoint = "/video/"+secrets.token_urlsafe(24)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != endpoint:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                try:
                    last_sequence = -1
                    while not pipeline._stop.is_set():
                        started = time.perf_counter()
                        packet = pipeline.preview_packet(last_sequence)
                        if packet is not None:
                            jpeg, last_sequence = packet
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nX-Source-Frame: "+str(last_sequence).encode()+b"\r\nContent-Length: "+str(len(jpeg)).encode()+b"\r\n\r\n"+jpeg+b"\r\n")
                            self.wfile.flush()
                            with pipeline._lock:
                                pipeline._preview_times.append(time.perf_counter())
                        pipeline._stop.wait(max(0., 1/pipeline.preview_fps-(time.perf_counter()-started)))
                except (BrokenPipeError, ConnectionResetError, OSError, RuntimeError):
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_port}{endpoint}"
        self._http_thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .1}, name="VinUniPreview", daemon=True)
        self._http_thread.start()

    def close(self):
        self._stop.set()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self._http_thread.join(timeout=1.)
        if self._thread.is_alive():
            self._thread.join(timeout=2.)
