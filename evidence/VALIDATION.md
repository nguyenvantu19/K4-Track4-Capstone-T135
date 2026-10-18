# Kiểm chứng bản triển khai

- **21/21 kiểm thử qua:** 11 logic, 5 tích hợp giao diện, 2 dữ liệu 3D và 3 kiểm tra truyền ảnh/vòng đời thiết bị webcam. Lệnh: `python -m unittest discover -s tests -v`.
- Kiểm thử giao diện tự động: render đủ 6 không gian, đổi clean sang projection và xác nhận số đếm từ 3 thành 2; seek/chạy/tạm dừng/về đầu, kết thúc playback, quay lại trang mô phỏng và giải phóng camera giả khi chuyển trang. Không bật webcam thật trong kiểm thử.
- Kiểm tra Chrome: ứng dụng mở tại `http://127.0.0.1:8501`, các điều khiển và biểu đồ hiển thị; nút chạy mô phỏng thực thi animation.
- **Model thật:** tải YOLO11n-pose từ release Ultralytics; chạy CPU trên 3 ảnh đen và trả 0 người. Chi tiết thời gian/phiên bản/hash ở `vision_smoke.json`. Đây là smoke test đường inference, không đánh giá pose trên người thật.
- **Bộ đếm:** tái tạo bằng `python tools/benchmark.py`; 3 CSV + 3 video H.264, mỗi clip đọc lại được 181 frame, kích thước 960×540. `benchmark.json` chứa thông số, sai số đếm và thời gian logic.
- Đã chạy Integrated Webcam thật 640×480: bộ đọc nhận hơn 600 khung hình, model xử lý và giao diện cập nhật. Ảnh thực tế rất tối, hệ thống báo chưa thấy người; chưa có xác nhận nhận diện tư thế hay đếm squat trên người thật. Không lưu ảnh/video webcam; ảnh bằng chứng chỉ chụp cột trạng thái. Chưa kiểm thử tại phòng demo, chưa có số đo model accuracy hay xác nhận phản biện nhóm.

Khởi động nhanh Local Studio bằng `run_local.cmd` hoặc `python run_local.py`. Bộ khởi động đã kiểm tra đủ dependency, giữ server trên loopback và tự chọn cổng nếu cổng mặc định bận. UI dùng SVG để xem khớp, có replay có thể tạm dừng, webcam trực tiếp có nút mở/đóng và tải CSV sau phiên.

Bản 3D dùng Three.js r160 được lưu kèm giấy phép MIT. Khớp và hình thể là mô hình động học tổng hợp. Dữ liệu góc, confidence, trạng thái và số đếm lấy từ cùng logic Python; bản HTML độc lập chứa sẵn thư viện và payload. `node --check` đã kiểm tra cú pháp mã điều khiển 3D.

Mô phỏng là bộ sinh điểm khớp xác định và fault injection, không phải mô phỏng động lực học cơ thể. Chỉ kết luận về các ca kiểm tra được cung cấp.
