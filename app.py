"""Streamlit UI: simulator, local video and evidence for the VinUni capstone."""
import json
import tempfile
import time
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from vinuni_move.core import Config, SquatCounter
from vinuni_move.simulation import samples, render
from vinuni_move.vision import load_model, infer, annotate

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="VinUni Move · Track 4", page_icon="🏃", layout="wide")
st.markdown("""<style>
.stApp {background: #0c1524; color: #edf3fb;}
[data-testid="stSidebar"] {background:#121f33;}
h1,h2,h3 {color:#f5f8fc;}
[data-testid="stMetric"] {background:#15263d;border:1px solid #29435c;padding:18px;border-radius:14px;}
.banner {padding:24px 28px;background:linear-gradient(115deg,#173659,#122239);border-radius:18px;border:1px solid #315372;margin-bottom:24px;}
.eyebrow {color:#75d6bf;letter-spacing:2px;font-size:12px;font-weight:700;}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="banner"><div class="eyebrow">VINUNI / PERCEPTION HACKATHON / TRACK 4</div><h1>Move with evidence.</h1><p>Đếm squat · Góc gối 2D · Biết khi nào chưa đủ dữ liệu</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("VinUni Move")
    st.caption("Trợ lý quan sát cho huấn luyện viên CLB thể thao")
    mode = st.radio("Không gian làm việc", ["Mô phỏng tương tác", "Video & webcam", "Bằng chứng", "Mục 4–9 & demo"])
    st.divider()
    st.caption("Chạy cục bộ. Không nhận diện danh tính. Không lưu ảnh/video mặc định.")
    st.info("Góc 2D và ngưỡng đếm là quy tắc minh họa, chưa được kiểm chứng để đánh giá an toàn tập luyện.")


def show_rows(rows):
    frame = pd.DataFrame(rows)
    cols = st.columns(4)
    cols[0].metric("Số lần hoàn tất", rows[-1]["reps"])
    cols[1].metric("Khung hình", len(rows))
    cols[2].metric("Từ chối suy luận", int((frame.status != "VALID").sum()))
    processing = frame.get("processing_ms")
    cols[3].metric("P95 xử lý / frame", f"{np.percentile(processing,95):.1f} ms" if processing is not None else "—", help="Chỉ hiển thị khi đã đo pipeline video. Mô phỏng có số đo logic riêng ở tab Bằng chứng.")
    st.line_chart(frame.set_index("timestamp_s")[["raw_angle_deg", "angle_deg"]], x_label="Thời gian nguồn (s)", y_label="Góc chiếu 2D (độ)")
    st.download_button("Tải log CSV", frame.to_csv(index=False).encode("utf-8"), "vinuni-move.csv", "text/csv")


if mode == "Mô phỏng tương tác":
    st.subheader("01 / Chạy một vòng từ đầu vào đến quyết định")
    st.caption("ĐẦU VÀO TỔNG HỢP — kiểm tra hình học và bộ đếm; không chứng minh độ chính xác model trên người thật.")
    case = st.selectbox("Kịch bản", ["Chuẩn: 3 lần squat", "Che khuất: mất khớp lần 2", "Ca lỗi: sai góc chiếu lần 2"])
    scenario = {"Chuẩn: 3 lần squat":"clean", "Che khuất: mất khớp lần 2":"occlusion", "Ca lỗi: sai góc chiếu lần 2":"projection"}[case]
    c1, c2, c3 = st.columns(3)
    down = c1.slider("Ngưỡng hạ (độ)", 60, 140, 100)
    up = c2.slider("Ngưỡng đứng (độ)", 145, 178, 160)
    dwell = c3.slider("Thời gian giữ tối thiểu (s)", .05, .5, .15, .05)
    config = Config(down=down, up=up, dwell=dwell)
    counter, rows = SquatCounter(config), []
    stream = list(samples(scenario))
    for s in stream:
        rows.append(counter.update(s["t"], s["angle"], s["confidence"]))
    cursor = st.slider("Replay từng khung hình", 0, len(rows)-1, 0)
    screen = st.empty()
    screen.image(render(stream[cursor], rows[cursor]), channels="BGR", width="stretch")
    col_a, col_b = st.columns(2)
    realtime = col_a.checkbox("Phát theo thời gian nguồn", value=True)
    if col_b.button("▶ Chạy mô phỏng", type="primary"):
        began = time.perf_counter()
        for s, row in zip(stream, rows):
            if realtime:
                time.sleep(max(0., began+s["t"]-time.perf_counter()))
            screen.image(render(s, row), channels="BGR", width="stretch")
        st.success(f"Hoàn tất · {rows[-1]['reps']} / 3 chu trình đầu vào")
    show_rows(rows)
    if scenario == "projection":
        st.warning("CA LỖI: đầu vào có 3 chu trình nhưng đếm được 2. Confidence vẫn 0,98. Phép chiếu làm sai góc 2D; bộ lọc confidence không phát hiện được lỗi này. Cần camera nhìn ngang, kiểm tra góc đặt hoặc bổ sung đa góc/3D.")
    elif scenario == "occlusion":
        st.info("Từ chối chu trình bị che khuất là chủ ý. Sau khi lấy lại khớp, cần đứng lại để bắt đầu chu trình mới.")

elif mode == "Video & webcam":
    st.subheader("02 / Đầu vào thật, xử lý trên máy này")
    st.write("Đặt camera nhìn ngang, thấy trọn hông–gối–cổ chân; chỉ một thành viên đội trong khung hình. Chọn cố định bên cơ thể gần camera.")
    st.code('.\\.venv\\Scripts\\python.exe live.py --source 0 --side left', language="powershell")
    st.caption("Lệnh trên mở webcam liên tục bằng OpenCV; cửa sổ này phân tích video hoặc một ảnh chụp webcam. Nhấn Q để dừng webcam.")
    consent = st.checkbox("Dữ liệu do thành viên đội tự đóng vai; tôi đồng ý xử lý cục bộ")
    side_vi = st.selectbox("Bên cơ thể", ["Trái", "Phải"])
    side = "left" if side_vi == "Trái" else "right"
    source = st.radio("Loại đầu vào", ["Video cục bộ", "Ảnh webcam"])
    if consent:
        uploaded = st.file_uploader("Video tối đa 30 MB", type=["mp4", "mov", "avi"], max_upload_size=30) if source == "Video cục bộ" else st.camera_input("Chụp ảnh kiểm tra tư thế")
        if uploaded and st.button("Phân tích trên máy", type="primary"):
            try:
                with st.spinner("Nạp model pretrained…"):
                    model = load_model()
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
                        st.success("Đã phân tích; bản video tạm sẽ được xóa khi kết thúc lượt này.")
                    finally:
                        handle.close()
                        if cap:
                            cap.release()
                        path.unlink(missing_ok=True)
            except Exception as error:
                st.error(f"Không phân tích được: {error}")
                st.code('.\\.venv\\Scripts\\python.exe tools/setup_model.py', language="powershell")
        if source == "Video cục bộ" and "video_rows" in st.session_state:
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

else:
    st.subheader("04 / Hồ sơ capstone theo mục 4–9")
    st.markdown((ROOT / "docs" / "MUC_4_DEN_9.md").read_text(encoding="utf-8"))
    st.download_button("Tải nội dung mục 4–9", (ROOT / "docs" / "MUC_4_DEN_9.md").read_bytes(), "VINUNI_MUC_4_DEN_9.md", "text/markdown")
