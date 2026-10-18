"""Keep Windows camera creation, reads and release on one owning thread."""
import sys
import threading
import time
import cv2


class CameraStream:
    def __init__(self, index=0, factory=None):
        self.index = index
        self.factory = factory or cv2.VideoCapture
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._frame = None
        self._last_frame = 0.
        self.frame_index = 0
        self.error = None
        self._thread = threading.Thread(target=self._run, name="VinUniCamera", daemon=True)

    def start(self, timeout=8.):
        self._thread.start()
        if not self._ready.wait(timeout):
            self.release()
            raise RuntimeError("Camera chưa trả hình. Đóng ứng dụng khác đang dùng webcam rồi thử lại.")
        if self.error:
            self.release()
            raise RuntimeError(self.error)
        return self

    def _run(self):
        capture = None
        try:
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
            capture = self.factory(self.index, backend)
            if not capture.isOpened():
                raise RuntimeError("Không mở được webcam. Thử chỉ số khác hoặc đóng ứng dụng đang giữ camera.")
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    raise RuntimeError("Mất tín hiệu webcam. Hãy kiểm tra kết nối camera.")
                with self._lock:
                    self._frame = frame
                    self._last_frame = time.perf_counter()
                    self.frame_index += 1
                self._ready.set()
                self._stop.wait(.005)
        except Exception as error:
            self.error = str(error)
        finally:
            if capture is not None:
                capture.release()
            self._ready.set()

    def read(self):
        snapshot = self.snapshot()
        return (False, None) if snapshot is None else (True, snapshot[2])

    def snapshot(self, after_sequence=None):
        """Return only the freshest frame with its capture time and sequence."""
        if self.error:
            raise RuntimeError(self.error)
        with self._lock:
            if self._frame is None:
                return None
            if time.perf_counter()-self._last_frame > 3:
                raise RuntimeError("Webcam đã ngừng cập nhật hình. Dừng và mở lại camera.")
            if after_sequence is not None and self.frame_index <= after_sequence:
                return None
            return self.frame_index, self._last_frame, self._frame.copy()

    def release(self):
        self._stop.set()
        if self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.)
