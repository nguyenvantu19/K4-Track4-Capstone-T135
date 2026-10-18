"""Explicitly controlled local webcam view for the Streamlit dashboard."""
import time
import cv2
import streamlit as st
from .core import SquatCounter
from .vision import MODEL_PATH, load_model, infer, annotate
from .ui import readout


@st.cache_resource(show_spinner=False)
def cached_model():
    return load_model()


def close_camera():
    camera = st.session_state.pop("camera_capture", None)
    if camera is not None:
        camera.release()
    st.session_state["camera_running"] = False


def camera_panel(side):
    running = st.session_state.get("camera_running", False)
    index = st.number_input("Chỉ số camera", 0, 5, 0, disabled=running)
    a, b = st.columns(2)
    if a.button("Bắt đầu webcam", type="primary", disabled=running or not MODEL_PATH.exists(), width="stretch"):
        try:
            with st.spinner("Chuẩn bị model và camera…"):
                cached_model()
                capture = cv2.VideoCapture(int(index))
                if not capture.isOpened():
                    capture.release()
                    raise RuntimeError("Không mở được webcam. Đóng ứng dụng khác đang giữ camera hoặc thử chỉ số khác.")
                st.session_state.update(camera_capture=capture, camera_running=True, camera_counter=SquatCounter(), camera_rows=[], camera_start=time.perf_counter(), camera_side=side)
            st.rerun()
        except Exception as error:
            close_camera()
            st.error(str(error))
    if b.button("Dừng và đóng camera", disabled=not running, width="stretch"):
        close_camera()
        st.rerun()
    st.caption("Webcam của máy chạy ứng dụng · không tự ghi video · bấm Dừng trước khi đóng tab.")
    if not MODEL_PATH.exists():
        st.info("Cần tải model một lần để dùng webcam.")
        st.code('.\\.venv\\Scripts\\python.exe tools/setup_model.py', language="powershell")
    if running and side != st.session_state.get("camera_side"):
        close_camera()
        st.session_state["camera_notice"] = "Đã đóng camera khi đổi bên cơ thể. Bấm Bắt đầu để tạo phiên mới."
        st.rerun()
    if "camera_notice" in st.session_state:
        st.info(st.session_state.pop("camera_notice"))

    @st.fragment(run_every=.2 if st.session_state.get("camera_running") else None)
    def feed():
        if not st.session_state.get("camera_running"):
            return
        try:
            ok, frame = st.session_state.camera_capture.read()
            if not ok:
                raise RuntimeError("Mất tín hiệu camera. Đã đóng thiết bị; bạn có thể bắt đầu lại.")
            timestamp = time.perf_counter()-st.session_state.camera_start
            started = time.perf_counter()
            image, angle, conf, people = infer(cached_model(), frame, side)
            row = st.session_state.camera_counter.update(timestamp, angle, conf, people)
            row["processing_ms"] = (time.perf_counter()-started)*1000
            st.session_state.camera_rows.append(row)
            if len(st.session_state.camera_rows) > 30000:
                st.session_state.camera_rows.pop(0)
            left, right = st.columns([2.15, 1], gap="medium")
            left.image(annotate(image, row), channels="BGR", width="stretch")
            with right:
                readout(row)
                st.caption(f"Xử lý frame: {row['processing_ms']:.0f} ms")
        except Exception as error:
            close_camera()
            st.session_state["camera_error"] = str(error)
            st.rerun()

    feed()
    if "camera_error" in st.session_state:
        st.error(st.session_state.pop("camera_error"))
