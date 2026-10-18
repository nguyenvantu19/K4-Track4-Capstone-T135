"""Presentation helpers for the local dashboard; no model or camera side effects."""
import html
import base64
import cv2
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PHASES = {"WAIT_STAND": "Chờ đứng thẳng", "STANDING": "Đang đứng", "DOWN": "Đã hạ người"}
STATUSES = {"VALID": "Đủ dữ liệu", "LOW_CONFIDENCE": "Khớp chưa rõ", "NO_PERSON": "Chưa thấy người", "MULTIPLE_PEOPLE": "Có nhiều người", "INVALID_GEOMETRY": "Không tính được góc"}


def camera_frame(image):
    """Inline JPEG avoids temporary media URLs being retired between live frames."""
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise ValueError("Không mã hóa được ảnh webcam")
    data = base64.b64encode(encoded).decode("ascii")
    return f'<img alt="Luồng webcam trực tiếp trên máy này" src="data:image/jpeg;base64,{data}" style="display:block;width:100%;height:auto;border-radius:12px;border:1px solid #2b3d4e" />'


def style():
    st.markdown(f"<style>{(ROOT / 'assets' / 'local-ui.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def header(mode):
    titles = {
        "Mô phỏng tương tác": ("PHÒNG PHÂN TÍCH", "Quan sát từng chuyển động.", "Khám phá chu trình squat, xem góc gối và kiểm tra bộ đếm qua ba kịch bản."),
        "Mô phỏng 3D": ("KHÔNG GIAN CHUYỂN ĐỘNG", "Nhìn chuyển động từ mọi phía.", "Xoay, phóng to và khám phá tư thế squat trên mô hình 3D tương tác."),
        "Video & webcam": ("PHIÊN TẬP CỦA BẠN", "Từ camera đến kết quả.", "Phân tích video hoặc webcam trên máy này. Bắt đầu bằng một người và góc nhìn ngang."),
        "Bằng chứng": ("DỮ LIỆU & KIỂM CHỨNG", "Mỗi kết quả, một bằng chứng.", "Đối chiếu số đếm, xem ca lỗi và tải dữ liệu để kiểm tra lại."),
        "Mục 4–9 & demo": ("HỒ SƠ CAPSTONE", "Sẵn sàng kể câu chuyện.", "Tài liệu, checklist và kịch bản trình bày của VinUni Move."),
        "Hướng dẫn chạy local": ("BẮT ĐẦU TẠI ĐÂY", "Mở máy. Chạy Move.", "Hướng dẫn khởi động, chọn nguồn dữ liệu và chuẩn bị một phiên demo."),
    }
    eyebrow, title, intro = titles[mode]
    st.markdown('<div class="page-top"><span>VinUni Move / Không gian làm việc</span><span class="local-chip">LOCAL · Xử lý trên máy</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<p class="intro">{intro}</p>', unsafe_allow_html=True)


def stage(s, row):
    """Draw source keypoints as SVG; deliberately not a photorealistic person."""
    hip, knee, ankle = s["points"]
    shoulder, head = (hip[0]-12, hip[1]-95), (hip[0]-12, hip[1]-130)
    color = "#b7f56c" if row["status"] == "VALID" else "#ffc273"
    grid = ''.join(f'<path d="M{x} 30 V460"/>' for x in range(20, 620, 40))
    grid += ''.join(f'<path d="M20 {y} H600"/>' for y in range(20, 480, 40))
    bones = [(head, shoulder), (shoulder, hip), (hip, knee), (knee, ankle), (shoulder, (390, 190))]
    lines = ''.join(f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]}"/>' for a, b in bones)
    joints = ''.join(f'<circle cx="{p[0]}" cy="{p[1]}" r="7" fill="#edf8e7"/>' for p in (shoulder, hip, knee, ankle))
    labels = ''.join(f'<text x="{p[0]-24}" y="{p[1]+5}" text-anchor="end">{label}</text>' for p, label in [(hip,"HÔNG"),(knee,"GỐI"),(ankle,"CỔ CHÂN")])
    return f'''<div class="stage"><div class="stage-top"><span>GÓC NHÌN NGANG / 2D</span><span class="stage-time">{s['t']:05.2f} / 09.00 s</span></div>
<svg viewBox="0 0 620 490" role="img" aria-label="Mô phỏng ba khớp hông, gối và cổ chân"><g stroke="#213146" stroke-width=".5" fill="none">{grid}</g>
<ellipse cx="310" cy="465" rx="115" ry="7" fill="#182c35"/><path d="M135 465 H475" stroke="#3b5360"/>
<path d="M{hip[0]} {hip[1]} V{ankle[1]}" stroke="#5a7383" stroke-dasharray="4 6" opacity=".5"/>
<g fill="none" stroke="{color}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">{lines}<circle cx="{head[0]}" cy="{head[1]}" r="24" stroke-width="3"/></g>
<circle cx="{knee[0]}" cy="{knee[1]}" r="24" fill="{color}" fill-opacity=".08" stroke="{color}" stroke-opacity=".25"/>{joints}
<g fill="#7591a5" font-family="Segoe UI,sans-serif" font-size="9" letter-spacing="1">{labels}</g></svg>
<div class="stage-bottom"><span>● DỮ LIỆU MÔ PHỎNG</span><span>3 điểm khớp · 20 Hz nguồn</span></div></div>'''


def readout(row):
    angle = "—" if row["angle_deg"] is None else f"{row['angle_deg']:.1f}"
    status = STATUSES.get(row["status"], row["status"])
    phase = PHASES.get(row["phase"], row["phase"])
    variant = "" if row["status"] == "VALID" else " uncertain"
    st.markdown(f'''<div class="readout"><div class="readout-label">Góc gối tại khung hình này</div><div class="readout-value">{angle}<small> °</small></div><div class="readout-note">Góc chiếu trên mặt phẳng ảnh</div></div>
<span class="state-label{variant}">{html.escape(status)}</span>
<div class="micro-grid"><div><b>{row['reps']}</b><span>LẦN ĐÃ HOÀN TẤT</span></div><div><b>{row['confidence']:.0%}</b><span>CONFIDENCE KHỚP</span></div></div>
<div class="mini-note">{html.escape(phase)}<br>Đứng → Hạ → Đứng để hoàn tất một lần.</div>''', unsafe_allow_html=True)
