# VinUni Move — Track 4 Capstone

Hỗ trợ HLV CLB thể thao VinUni đếm chu trình squat và quan sát góc gối 2D. Mô phỏng tương tác, webcam/video cục bộ, confidence gating, trạng thái theo thời gian và bằng chứng tái lập. Phạm vi: một người, một bên cơ thể, góc camera nhìn ngang.

## Chạy nhanh (Windows / PowerShell)

**Trên máy đã có `.venv`: nhấp đúp `run_local.cmd`.** Ứng dụng tự mở trình duyệt; mặc định dùng `http://127.0.0.1:8501`, tự chọn cổng kế tiếp nếu cổng đang bận. Đóng ứng dụng bằng Ctrl+C tại cửa sổ chạy server.

Giao diện Local Studio có mô phỏng Chạy / Tạm dừng / Về đầu, xem từng frame và góc gối, biểu đồ, tải CSV, phân tích video và webcam liên tục ngay trong trang. Camera chỉ mở khi bạn xác nhận dữ liệu và bấm **Bắt đầu webcam**; bấm **Dừng và đóng camera** trước khi đóng tab. Có thể chạy bằng lệnh ngắn:

```powershell
.\.venv\Scripts\python.exe run_local.py
```

**Bản 3D:** chọn **Mô phỏng 3D** trên thanh điều hướng. Có thể kéo để xoay, cuộn/phóng to, chuyển góc Ngang/Trước/Chéo, phát/tạm dừng, đổi tốc độ và kéo từng frame. Mô hình động học tổng hợp dùng cùng kết quả bộ đếm Python; không phải ước lượng 3D từ webcam. Thư viện Three.js và giấy phép đã nằm trong `assets/vendor`, không gọi CDN khi chạy.

Có thể mở trực tiếp [bản 3D độc lập](outputs/vinuni-move-3d.html) bằng Chrome/Edge, hoặc tải HTML tại trang 3D. Tạo lại bằng `python tools/export3d.py`. Trình duyệt cần hỗ trợ WebGL; nếu không có, chế độ 2D vẫn dùng được.

Nếu cài trên máy mới:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools/setup_model.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Nếu môi trường `.venv` đã có, dùng trực tiếp. Mô phỏng không cần tải model, không cần webcam và không dùng dữ liệu người thật. Phiên bản Python đã kiểm tra: 3.14.7. Model YOLO11n-pose tải riêng từ Ultralytics vào `models/`, không commit trọng số vào repo.

Webcam liên tục, khi thành viên đội đã đồng ý đóng vai:

```powershell
.\.venv\Scripts\python.exe live.py --source 0 --side left
```

Q/Esc thoát; R đặt lại bộ đếm. `--source <video.mp4>` để replay. Chỉ lưu video khi truyền `--record recordings/team-backup.mp4`; mặc định lưu log số vào `recordings/session.csv`. Log có thời gian, góc và confidence nhưng không có ảnh/tên. Chỉ giữ dữ liệu cục bộ và xóa sau khi không còn cần. Không dùng dữ liệu thật của sinh viên/bệnh nhân; người đóng vai phải là thành viên đội.

## Hồ sơ mục 4–9

- [Nội dung hoàn chỉnh theo Vlearn](docs/MUC_4_DEN_9.md): yêu cầu, 7 trụ cột, công cụ, 6 tiêu chí chấm, tác động, lịch trình, checklist.
- [Lời trình bày và giới hạn cần nói rõ](docs/DEMO_SCRIPT.md).
- [Báo cáo số đo](evidence/benchmark.json), [ca chuẩn](evidence/clean.csv), [che khuất](evidence/occlusion.csv), [ca lỗi phép chiếu](evidence/projection.csv).
- Video dự phòng **mô phỏng tổng hợp**: [clean](evidence/clean.mp4), [occlusion](evidence/occlusion.mp4), [projection](evidence/projection.mp4).
- `index.html`: đề bài gốc được giữ nguyên.

## Kiểm chứng

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/benchmark.py
```

11 kiểm thử logic. Clean đếm 3/3; che khuất 2/3, 39 frame từ chối; ca projection đếm 2/3 dù confidence cao. Mỗi ca có 181 frame, nguồn mô phỏng 20 Hz. P50/P95 trong JSON chỉ đo logic bộ đếm, **không phải FPS/độ trễ inference model**. Video được sinh bằng OpenCV/H.264; nếu encoder không có trên máy khác, dùng video đã kèm repo.

Góc = arccos của tích vô hướng hai vector; EMA theo thời gian; hysteresis 100°/160°; dwell 0,15 s; confidence tối thiểu 0,55. Góc 2D phụ thuộc camera. Các ngưỡng là quy tắc demo, chưa chứng minh khả năng đánh giá an toàn/chuẩn kỹ thuật. Bộ đếm từ chối nhiều người và ngắt chu trình khi mất bằng chứng. Khớp cùng một người sau khi bị thay thế mà không có khoảng trống chưa được tracking đảm bảo.

**Còn cần người dùng:** thử webcam ở phòng demo, clip thành viên đội và đánh dấu đếm tay để đánh giá perception, phân vai/diễn tập hỏi đáp. Chưa có số đo accuracy trên người thật. Số đo mô phỏng không thay thế các bước này.

Tổng cộng **21 kiểm thử đã qua**: 11 logic, 5 tích hợp giao diện, 2 bản 3D và 3 kiểm tra webcam. Webcam Windows dùng DirectShow và một luồng riêng giữ thiết bị từ lúc mở đến lúc đóng; ảnh xem trước được truyền trong bộ nhớ để tránh URL media tạm bị mất. Xem [biên bản kiểm chứng](evidence/VALIDATION.md) và [smoke test model thật](evidence/vision_smoke.json). Mô phỏng điểm khớp không phải mô phỏng động lực học cơ thể.

## Nguồn chính thức

[Ultralytics Pose](https://docs.ultralytics.com/tasks/pose/), [Streamlit](https://docs.streamlit.io/develop/api-reference). Ultralytics và trọng số có [điều kiện cấp phép riêng](https://www.ultralytics.com/license); kiểm tra trước khi triển khai thương mại.
