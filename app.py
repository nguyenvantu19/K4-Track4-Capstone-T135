"""Streamlit UI: simulator, local video and evidence for the VinUni capstone."""
import json
import hashlib
import tempfile
import time
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from vinuni_move.core import Config, SquatCounter
from vinuni_move.simulation import samples
from vinuni_move.vision import infer, annotate
from vinuni_move.vision import MODEL_PATH
from vinuni_move.ui import style, header, stage, readout
from vinuni_move.webcam_ui import camera_panel, close_camera

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="VinUni Move · Local Studio", page_icon="🏃", layout="wide")
style()

with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark">VM</div><div><div class="brand-name">VinUni Move</div><div class="brand-sub">MOVEMENT STUDIO</div></div></div><div class="nav-label">KHÔNG GIAN LÀM VIỆC</div>', unsafe_allow_html=True)
    mode = st.radio("Điều hướng", ["Mô phỏng tương tác", "Mô phỏng 3D", "Video & webcam", "Bằng chứng", "Mục 4–9 & demo", "Hướng dẫn chạy local"], label_visibility="collapsed")
    st.divider()
    st.markdown('<div class="nav-label">TRẠNG THÁI MÔI TRƯỜNG</div>', unsafe_allow_html=True)
    st.caption("● Mô phỏng sẵn sàng")
    st.caption("● Model pose đã có" if MODEL_PATH.exists() else "○ Model pose chưa tải")
    st.markdown('<div class="local-note"><strong>Dữ liệu ở trên máy bạn</strong><p>Không nhận diện danh tính. Camera chỉ mở khi bạn bấm bắt đầu và không ghi video tự động.</p></div>', unsafe_allow_html=True)
    st.caption("VINUNI / TRACK 4 CAPSTONE")

if mode != "Video & webcam":
    close_camera()
if mode != "Mô phỏng tương tác":
    st.session_state["playing"] = False
header(mode)


def show_rows(rows, *, metrics=True, chart=True, key="csv"):
    frame = pd.DataFrame(rows)
    if metrics:
        cols = st.columns(4)
        cols[0].metric("Số lần hoàn tất", rows[-1]["reps"])
        cols[1].metric("Khung hình đã xử lý", len(rows))
        cols[2].metric("Dữ liệu hợp lệ", f"{(frame.status == 'VALID').mean():.0%}")
        processing = frame.get("processing_ms")
        cols[3].metric("P95 xử lý / frame", f"{np.percentile(processing,95):.0f} ms" if processing is not None else "—", help="Chỉ đo khi chạy video/webcam. Mô phỏng có số đo logic riêng ở tab Bằng chứng.")
    if chart:
        with st.container(border=True):
            st.subheader("Đường đi của góc gối")
            st.caption("Góc thô và góc sau làm mượt · thời gian của nguồn dữ liệu")
            st.line_chart(frame.set_index("timestamp_s")[["raw_angle_deg", "angle_deg"]].rename(columns={"raw_angle_deg":"Góc thô", "angle_deg":"Góc đã lọc"}), height=230, color=["#526c86", "#b7f56c"], x_label="Thời gian (s)", y_label="Góc (°)")
            st.download_button("Tải kết quả CSV", frame.to_csv(index=False).encode("utf-8-sig"), "vinuni-move.csv", "text/csv", key=key)


if mode == "Mô phỏng tương tác":
    top_left, top_right = st.columns([2, 1], vertical_alignment="bottom")
    case = top_left.selectbox("Kịch bản kiểm tra", ["Chuẩn: 3 lần squat", "Che khuất: mất khớp lần 2", "Ca lỗi: sai góc chiếu lần 2"])
    scenario = {"Chuẩn: 3 lần squat":"clean", "Che khuất: mất khớp lần 2":"occlusion", "Ca lỗi: sai góc chiếu lần 2":"projection"}[case]
    with top_right.popover("Ngưỡng phân tích", width="stretch"):
        down = st.slider("Ngưỡng hạ (độ)", 60, 140, 100)
        up = st.slider("Ngưỡng đứng (độ)", 145, 178, 160)
        dwell = st.slider("Thời gian giữ tối thiểu (s)", .05, .5, .15, .05)
        st.caption("Ngưỡng dành cho demo, chưa dùng để kết luận an toàn tập luyện.")
    config = Config(down=down, up=up, dwell=dwell)
    counter, rows = SquatCounter(config), []
    stream = list(samples(scenario))
    for s in stream:
        rows.append(counter.update(s["t"], s["angle"], s["confidence"]))
    signature = (scenario, down, up, dwell)
    if st.session_state.get("simulation_signature") != signature:
        st.session_state.update(simulation_signature=signature, playing=False, replay_frame=0, active_frame=0, selected_frame=0)
    st.session_state.setdefault("selected_frame", st.session_state.get("active_frame", 0))
    st.session_state["replay_frame"] = st.session_state.selected_frame
    if "replay_seek_after_play" in st.session_state:
        st.session_state["replay_frame"] = st.session_state.pop("replay_seek_after_play")
    st.markdown('<div class="section-label">KẾT QUẢ TOÀN BỘ CHUỖI</div>', unsafe_allow_html=True)
    show_rows(rows, chart=False)

    def play():
        cursor = st.session_state.get("active_frame", 0)
        if cursor >= len(rows)-1:
            cursor = 0
        st.session_state.update(playing=True, play_start=time.perf_counter()-cursor/20)

    def pause():
        cursor = st.session_state.get("active_frame", 0)
        st.session_state.update(playing=False, replay_frame=cursor, selected_frame=cursor)

    def reset():
        st.session_state.update(playing=False, replay_frame=0, active_frame=0, selected_frame=0)

    def seek():
        st.session_state.update(playing=False, active_frame=st.session_state.replay_frame, selected_frame=st.session_state.replay_frame)

    st.markdown('<div class="section-label">CHUYỂN ĐỘNG & QUAN SÁT TẠI KHUNG HÌNH</div>', unsafe_allow_html=True)
    controls = st.columns([1.25, 1, 1, 2])
    controls[0].button("▶ Chạy mô phỏng", type="primary", on_click=play, width="stretch", disabled=st.session_state.get("playing", False))
    controls[1].button("Tạm dừng", on_click=pause, width="stretch", disabled=not st.session_state.get("playing", False))
    controls[2].button("Về đầu", on_click=reset, width="stretch")
    controls[3].caption("Chọn từng khung hình để kiểm tra góc và trạng thái.")

    @st.fragment(run_every=.1 if st.session_state.get("playing") else None)
    def playback():
        playing = st.session_state.get("playing", False)
        cursor = min(len(rows)-1, max(0, int((time.perf_counter()-st.session_state.play_start)*20))) if playing else st.session_state.selected_frame
        st.session_state["active_frame"] = cursor
        left, right = st.columns([2.15, 1], gap="medium")
        left.markdown(stage(stream[cursor], rows[cursor]), unsafe_allow_html=True)
        with right:
            readout(rows[cursor])
            st.caption(f"Frame {cursor+1} / {len(rows)} · {cursor/20:.2f} giây")
            st.progress(cursor/(len(rows)-1))
        if playing and cursor == len(rows)-1:
            st.session_state["playing"] = False
            st.session_state["selected_frame"] = cursor
            st.session_state["replay_seek_after_play"] = cursor
            st.rerun()

    playback()
    st.slider("Khung hình replay · 9 giây / 20 Hz nguồn", 0, len(rows)-1, key="replay_frame", on_change=seek, disabled=st.session_state.get("playing", False))
    show_rows(rows, metrics=False)
    st.caption("Đầu vào tổng hợp kiểm tra hình học và bộ đếm; không chứng minh độ chính xác model trên người thật.")
    if scenario == "projection":
        st.warning("CA LỖI: đầu vào có 3 chu trình nhưng đếm được 2. Confidence vẫn 0,98. Phép chiếu làm sai góc 2D; bộ lọc confidence không phát hiện được lỗi này. Cần camera nhìn ngang, kiểm tra góc đặt hoặc bổ sung đa góc/3D.")
    elif scenario == "occlusion":
        st.info("Từ chối chu trình bị che khuất là chủ ý. Sau khi lấy lại khớp, cần đứng lại để bắt đầu chu trình mới.")

elif mode == "Mô phỏng 3D":
    from vinuni_move.viewer3d import show, document
    scenario = st.selectbox("Kịch bản 3D", ["clean", "occlusion", "projection"], format_func={"clean":"Chuẩn · 3 lần squat", "occlusion":"Che khuất · confidence giảm", "projection":"Ca lỗi · góc chiếu 2D sai"}.get)
    try:
        show(scenario)
        st.download_button("Tải bản 3D chạy độc lập (.html)", document(scenario).encode("utf-8"), "vinuni-move-3d.html", "text/html")
    except FileNotFoundError as error:
        st.error(str(error))
    if scenario == "projection":
        st.info("Cơ thể 3D vẫn thực hiện đủ 3 chu trình, nhưng góc 2D bị làm sai ở lần thứ 2. Đây là fault injection để quan sát khác biệt giữa chuyển động và góc chiếu.")
    elif scenario == "occlusion":
        st.info("Mô hình 3D tiếp tục chuyển động khi khớp 2D bị che. Bộ đếm sẽ từ chối phần dữ liệu thiếu confidence.")
    st.caption("Mô phỏng động học tổng hợp, không phải kết quả ước lượng 3D từ camera hoặc đánh giá cơ sinh học.")

elif mode == "Video & webcam":
    st.write("Đặt camera nhìn ngang, thấy trọn hông–gối–cổ chân; chỉ một thành viên đội trong khung hình. Chọn cố định bên cơ thể gần camera.")
    consent = st.checkbox("Dữ liệu do thành viên đội tự đóng vai; tôi đồng ý xử lý cục bộ")
    side_vi = st.selectbox("Bên cơ thể", ["Trái", "Phải"])
    side = "left" if side_vi == "Trái" else "right"
    source = st.radio("Loại đầu vào", ["Video cục bộ", "Webcam trực tiếp", "Ảnh webcam"], horizontal=True)
    if source != "Webcam trực tiếp" or not consent:
        close_camera()
    if not consent:
        st.markdown('<div class="case-card"><b>Sẵn sàng khi bạn muốn bắt đầu</b><p>Xác nhận nguồn dữ liệu ở trên để mở bộ chọn video hoặc điều khiển camera. Mô phỏng không cần camera.</p></div>', unsafe_allow_html=True)
    elif source == "Webcam trực tiếp":
        camera_panel(side)
        if not st.session_state.get("camera_running") and st.session_state.get("camera_rows"):
            st.subheader("Kết quả phiên webcam gần nhất")
            show_rows(st.session_state.camera_rows, key="webcam_csv")
    else:
        uploaded = st.file_uploader("Video tối đa 30 MB", type=["mp4", "mov", "avi"], max_upload_size=30) if source == "Video cục bộ" else st.camera_input("Chụp ảnh kiểm tra tư thế")
        source_id = None if uploaded is None else (hashlib.sha256(uploaded.getvalue()).hexdigest(), side, source)
        if uploaded and st.button("Phân tích trên máy", type="primary"):
            try:
                with st.spinner("Nạp model pretrained…"):
                    from vinuni_move.webcam_ui import cached_model
                    model = cached_model()
                if source == "Ảnh webcam":
                    frame = cv2.imdecode(np.frombuffer(uploaded.getvalue(), np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        raise ValueError("Ảnh không hợp lệ")
                    image, angle, conf, people = infer(model, frame, side)
                    row = SquatCounter().update(0, angle, conf, people)
                    st.image(annotate(image, row), channels="BGR")
                    st.json(row)
                    st.caption("Một ảnh chỉ đo góc; cần chuỗi video để đếm squat.")
                else:
                    st.session_state.pop("video_rows", None)
                    handle = tempfile.NamedTemporaryFile(suffix=Path(uploaded.name).suffix, delete=False)
                    path = Path(handle.name)
                    cap = None
                    try:
                        handle.write(uploaded.getvalue())
                        handle.close()
                        cap = cv2.VideoCapture(str(path))
                        if not cap.isOpened():
                            raise ValueError("Không đọc được video/codec")
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        fps = fps if 1 <= fps <= 240 else 25.
                        screen, progress = st.empty(), st.progress(0.)
                        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        counter, rows = SquatCounter(), []
                        for i in range(1800):
                            ok, frame = cap.read()
                            if not ok:
                                break
                            started = time.perf_counter()
                            image, angle, conf, people = infer(model, frame, side)
                            row = counter.update(i/fps, angle, conf, people)
                            row["processing_ms"] = (time.perf_counter()-started)*1000
                            rows.append(row)
                            if i % 3 == 0:
                                screen.image(annotate(image, row), channels="BGR", width="stretch")
                                progress.progress(min(1., (i+1)/max(count, 1)))
                        if not rows:
                            raise ValueError("Video không có frame đọc được")
                        if len(rows) == 1800:
                            st.warning("Đã dừng ở giới hạn 1.800 frame; số đếm chỉ cho phần đã xử lý.")
                        progress.progress(1.)
                        st.session_state["video_rows"] = rows
                        st.session_state["video_source_id"] = source_id
                        st.success("Đã phân tích; bản video tạm sẽ được xóa khi kết thúc lượt này.")
                    finally:
                        handle.close()
                        if cap:
                            cap.release()
                        path.unlink(missing_ok=True)
            except Exception as error:
                st.error(f"Không phân tích được: {error}")
                st.code('.\\.venv\\Scripts\\python.exe tools/setup_model.py', language="powershell")
        if source == "Video cục bộ" and source_id is not None and st.session_state.get("video_source_id") == source_id and "video_rows" in st.session_state:
            show_rows(st.session_state["video_rows"])

elif mode == "Bằng chứng":
    st.subheader("03 / Số đo có thể tái lập")
    evidence = ROOT / "evidence" / "benchmark.json"
    if evidence.exists():
        report = json.loads(evidence.read_text(encoding="utf-8"))
        st.dataframe(pd.DataFrame(report["scenarios"]), hide_index=True, width="stretch")
        st.caption("logic_p95_ms chỉ đo bộ đếm sau khi đã có góc. source_fps = tần số giả lập đầu vào, không phải FPS inference camera.")
        case = st.selectbox("Video dự phòng mô phỏng", ["clean", "occlusion", "projection"])
        video_path = ROOT / "evidence" / f"{case}.mp4"
        if video_path.exists():
            st.video(str(video_path))
            st.download_button("Tải video dự phòng", video_path.read_bytes(), f"{case}.mp4", "video/mp4")
        st.download_button("Tải báo cáo JSON", evidence.read_bytes(), "benchmark.json", "application/json")
    else:
        st.info("Chạy python tools/benchmark.py để tạo bằng chứng.")
    st.warning("Chưa có đánh giá trên video người thật. Không suy rộng kết quả mô phỏng thành độ chính xác của model, hay xác nhận an toàn tập luyện.")

elif mode == "Mục 4–9 & demo":
    report = ROOT / "docs" / "MUC_4_DEN_9.md"
    if report.exists():
        st.download_button("Tải nội dung mục 4–9", report.read_bytes(), "VINUNI_MUC_4_DEN_9.md", "text/markdown")
        with st.container(border=True):
            st.markdown(report.read_text(encoding="utf-8"))
    else:
        st.info("Thêm tài liệu docs/MUC_4_DEN_9.md để xem hồ sơ ở đây.")
else:
    for number, title, text in [
        ("01", "Khởi động ứng dụng", "Nhấp đúp run_local.cmd trong thư mục dự án. Trình duyệt sẽ mở khi ứng dụng sẵn sàng."),
        ("02", "Thử ngay, không cần camera", "Chọn Mô phỏng tương tác. Chạy, tạm dừng, kéo thanh khung hình hoặc đổi ca che khuất/sai phép chiếu."),
        ("3D", "Khám phá tư thế trong không gian", "Chọn Mô phỏng 3D; kéo chuột để xoay, cuộn hoặc bấm +/− để zoom. Chọn góc Ngang/Trước/Chéo, đổi tốc độ và tải bản HTML chạy độc lập."),
        ("03", "Dùng video hoặc webcam", "Tải model một lần, xác nhận dữ liệu của đội và chọn nguồn. Bấm Bắt đầu webcam để phân tích liên tục trong trang này."),
        ("04", "Lưu kết quả và kết thúc", "Tải CSV để xem góc và số đếm. Dừng camera trước khi đóng tab; nhấn Ctrl+C trong cửa sổ chạy ứng dụng để tắt server."),
    ]:
        st.markdown(f'<div class="step-card"><b>{number} / {title}</b><p>{text}</p></div>', unsafe_allow_html=True)
    with st.expander("Chạy bằng PowerShell hoặc cài trên máy mới"):
        st.code('python -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n.\\.venv\\Scripts\\python.exe tools/setup_model.py\n.\\.venv\\Scripts\\python.exe run_local.py', language="powershell")
        st.caption("Bỏ qua tạo/cài môi trường nếu .venv đã có. Model chỉ cần cho video và webcam.")
    with st.expander("Webcam không mở hoặc xử lý chậm"):
        st.write("Đóng ứng dụng khác đang dùng camera; thử chỉ số 0 hoặc 1. Đứng nhìn ngang, để lộ trọn hông–gối–cổ chân. Tốc độ CPU phụ thuộc máy, có thể dùng clip ngắn để replay.")
