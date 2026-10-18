"""Smooth preview and independent pose analysis for the local webcam UI."""
import streamlit as st
from .vision import MODEL_PATH, load_model
from .ui import readout
from .camera import CameraStream
from .live_pipeline import LivePipeline


@st.cache_resource(show_spinner=False)
def cached_model():
    return load_model()


def close_camera():
    pipeline = st.session_state.pop("camera_pipeline", None)
    if pipeline is not None:
        pipeline.close()
        st.session_state["camera_rows"] = pipeline.rows()
    camera = st.session_state.pop("camera_capture", None)
    if camera is not None:
        camera.release()
    st.session_state["camera_running"] = False


def camera_panel(side):
    running = st.session_state.get("camera_running", False)
    settings = st.columns([1, 2])
    index = settings[0].number_input("Chỉ số camera", 0, 5, 0, disabled=running)
    profiles = {"Cân bằng": (416, 20, 76), "Ưu tiên mượt": (320, 20, 70), "Ưu tiên chi tiết": (640, 15, 82)}
    profile = settings[1].selectbox("Chế độ xử lý", list(profiles), disabled=running)
    skeleton = st.checkbox("Vẽ khớp trên khung hình đã phân tích", value=False, disabled=running)
    st.caption("Tắt vẽ khớp để xem hình mượt hơn; góc gối và số đếm vẫn cập nhật riêng. Chế độ chi tiết phù hợp khi khớp nhỏ hoặc khó thấy.")
    a, b = st.columns(2)
    if a.button("Bắt đầu webcam", type="primary", disabled=running or not MODEL_PATH.exists(), width="stretch"):
        try:
            with st.spinner("Mở camera…"):
                capture = CameraStream(int(index)).start()
                st.session_state["camera_capture"] = capture
                size, fps, quality = profiles[profile]
                pipeline = LivePipeline(capture, side, imgsz=size, skeleton=skeleton, preview_fps=fps, jpeg_quality=quality).start()
                st.session_state.update(camera_pipeline=pipeline, camera_running=True, camera_rows=[], camera_side=side)
            st.rerun()
        except Exception as error:
            close_camera()
            st.error(str(error))
    if b.button("Dừng và đóng camera", disabled=not running, width="stretch"):
        close_camera()
        st.rerun()
    st.caption("Chỉ xử lý trên máy này · không ghi video · bấm Dừng trước khi đóng tab.")
    if not MODEL_PATH.exists():
        st.info("Cần tải model một lần để dùng webcam.")
        st.code('.\\.venv\\Scripts\\python.exe tools/setup_model.py', language="powershell")
    if running and side != st.session_state.get("camera_side"):
        close_camera()
        st.session_state["camera_notice"] = "Đã đóng camera khi đổi bên cơ thể. Bấm Bắt đầu để tạo phiên mới."
        st.rerun()
    if "camera_notice" in st.session_state:
        st.info(st.session_state.pop("camera_notice"))
    if "camera_error" in st.session_state:
        st.error(st.session_state.pop("camera_error"))
    if not st.session_state.get("camera_running"):
        return

    pipeline = st.session_state.camera_pipeline
    left, right = st.columns([2.15, 1], gap="medium")
    # The browser updates this multipart stream independently of Streamlit's
    # reruns. Never replace the video element for each model result.
    left.markdown(f'<img alt="Luồng webcam trực tiếp trên máy này" src="{pipeline.url}" style="display:block;width:100%;height:auto;border-radius:12px;border:1px solid #2b3d4e" />', unsafe_allow_html=True)
    left.caption("Ảnh có khớp theo nhịp nhận diện" if pipeline.skeleton else "Hình camera mới nhất · nhận diện chạy riêng")

    with right:
        @st.fragment(run_every=.3)
        def metrics():
            if not st.session_state.get("camera_running"):
                return
            state = pipeline.stats()
            if state["error"]:
                close_camera()
                st.session_state["camera_error"] = state["error"]
                st.rerun()
            readout(state["row"])
            if state["processed"]:
                st.caption(f"Ảnh xem: {state['preview_fps']:.1f} FPS · nhận diện: {state['analysis_fps']:.1f} FPS")
                st.caption(f"Xử lý: {state['row']['processing_ms']:.0f} ms · tuổi kết quả: {state['result_age_ms']:.0f} ms")
                st.caption("Số đo chưa bao gồm độ trễ hiển thị trên màn hình.")
            else:
                st.caption("Đang nạp model; luồng camera vẫn chạy.")
            st.caption(f"Đã phân tích {state['processed']} / nhận {state['captured']} khung hình")
            sample = pipeline.camera.snapshot()
            if sample is not None and float(sample[2].mean()) < 22:
                st.caption("Ảnh hiện rất tối. Kiểm tra nắp che webcam và ánh sáng.")
        metrics()
