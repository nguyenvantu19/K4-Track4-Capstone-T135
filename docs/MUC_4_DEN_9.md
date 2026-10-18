# VinUni Move — Phân tích động tác squat bằng camera

**Đề tài đã chọn:** VinUni / camera trong thể thao. Phạm vi MVP là đếm squat và quan sát góc gối 2D cho huấn luyện viên, thành viên CLB thể thao trong buổi tập. Đây là một động tác nền tảng trong tập sức mạnh/nâng tạ. Chưa triển khai phân tích ném bóng rổ, cầu lông, PPE phòng lab hay đếm người thư viện.

**Trạng thái:** có demo mô phỏng chạy được, mã webcam/video dùng model pretrained, log và video dự phòng tổng hợp. Thử nghiệm với thành viên đội tại phòng demo và phản biện nhóm cần thực hiện trực tiếp; không xem là đã hoàn tất chỉ vì có mã nguồn.

## Mục 4 — Bốn yêu cầu bắt buộc

| Yêu cầu | Cách thực hiện | Bằng chứng / điều còn cần làm |
|---|---|---|
| Chạy thật | Streamlit chạy mô phỏng tương tác; OpenCV nhận webcam hoặc video cục bộ; YOLO11n-pose lấy khớp người | `app.py`, `live.py`, `vinuni_move/vision.py`; `evidence/clean.mp4` là video **mô phỏng**, không phải quay người thật |
| Dùng kiến thức khóa | Hình học góc khớp, bất định, biểu diễn trạng thái, xử lý thời gian, dữ liệu và bằng chứng; pretrained pose hỗ trợ trụ cột học | Bảng ánh xạ ở mục 5, mã nguồn tách riêng từng tầng |
| Một số đo, một ca lỗi | Số lần dự đoán so với 3 chu trình tổng hợp; sai số đếm tuyệt đối; tỷ lệ từ chối; P95 thời gian logic | `evidence/benchmark.json`, CSV từng frame; ca projection sai 1 lần dù confidence cao |
| Dữ liệu an toàn | Mô phỏng không chứa người. Khi dùng webcam/video, chỉ thành viên đội tự đóng vai, không có người ngoài khung hình; không nhận diện danh tính | Không thu dữ liệu sinh viên/bệnh nhân thực tế; video thật chỉ ghi khi có `--record`; log góc được lưu tại máy |

**Luồng xử lý:** webcam/video → YOLO pretrained → 3 khớp hông–gối–cổ chân ở bên đã chọn → kiểm tra số người/confidence → góc 2D → làm mượt theo thời gian → máy trạng thái → số lần + trạng thái + log. Mô phỏng cung cấp trực tiếp các điểm khớp cho cùng tầng hình học/bộ đếm, bỏ qua tầng model.

**Quy tắc:** chỉ một người; confidence nhỏ nhất của ba khớp ≥ 0,55. Góc ≤ 100° là vùng hạ, ≥ 160° là vùng đứng. Một vùng phải duy trì ≥ 0,15 s. Đứng → hạ → đứng mới được tính một lần. Khởi đầu ở tư thế hạ, một frame nhiễu, mất khớp hoặc nhiều người không tạo lần đếm. Mất dữ liệu hoặc cách quãng > 0,5 s sẽ yêu cầu đứng lại. Đây là ngưỡng demo có thể điều chỉnh, chưa phải tiêu chuẩn huấn luyện.

## Mục 5 — Bảy trụ cột Track 4

| Trụ cột | Vị trí trong hệ thống | Lý do thiết kế và giới hạn |
|---|---|---|
| 1. Học | `vision.py`: YOLO11n-pose pretrained, bộ 17 khớp theo COCO | Tiết kiệm thời gian, không train từ đầu. Chỉ dùng 3 khớp mỗi bên để tính góc. Chưa fine-tune hay đo độ chính xác trên VinUni; mô phỏng không kiểm chứng model |
| 2. Hình học | `core.py:knee_angle`: arccos của tích vô hướng hai vector hông–gối và cổ chân–gối | Góc không phụ thuộc tịnh tiến/tỉ lệ ảnh; không cần biết chiều dài chân. Góc chiếu 2D vẫn thay đổi theo góc camera; chưa có hiệu chuẩn hay 3D |
| 3. Bất định | Confidence nhỏ nhất 3 khớp; `LOW_CONFIDENCE`, `NO_PERSON`, `MULTIPLE_PEOPLE`, `INVALID_GEOMETRY` | Từ chối khi thiếu bằng chứng thay vì báo kết quả chắc chắn. Confidence là điểm model, không phải xác suất đã hiệu chuẩn; góc chiếu sai có thể vẫn rất tự tin |
| 4. Biểu diễn | 3 điểm 2D + confidence → góc thô/góc lọc → `WAIT_STAND`, `STANDING`, `DOWN` | Trạng thái dễ đọc và truy vết hơn một nhãn “squat” mỗi frame. Không đánh giá mọi lỗi kỹ thuật cơ thể |
| 5. Thời gian | EMA dùng `alpha = 1-exp(-dt/tau)` với tau 0,09 s; dwell 0,15 s; timestamp tăng nghiêm ngặt | Cùng quy tắc hoạt động ở 10/20/30/60 Hz; hysteresis tránh đếm rung quanh ngưỡng. Video dùng thời gian nguồn, webcam dùng đồng hồ đơn điệu. Chưa đồng bộ IMU |
| 6. Dữ liệu | `simulation.py`, CSV, video replay, log webcam/video | Tái lập ca chuẩn/che khuất/sai hình học; số đo có nguồn. Log không ghi tên hoặc ảnh; vẫn chỉ giữ cục bộ và xóa sau buổi demo khi không còn cần |
| 7. Bằng chứng | `tools/benchmark.py`, `tests/test_core.py`, `evidence/` | Phân biệt kiểm tra logic và đánh giá nhận thức trên video thật; công khai ca sai và các mục chưa xác nhận |

**Điểm nhấn để giải thích:** không chỉ gọi pretrained model. Đóng góp của hệ thống là hợp đồng dữ liệu có kiểm tra, phép tính hình học, làm mượt theo thời gian thực, quy tắc chuyển trạng thái và bằng chứng tái lập. Chọn hysteresis + dwell vì dễ giải thích trong thời gian hackathon; chưa cần bộ lọc Kalman khi không có mô hình động học/đo nhiễu đã kiểm chứng.

## Mục 6 — Công cụ và cách chạy

**Công cụ:** Python; Ultralytics YOLO11n-pose; OpenCV đọc/vẽ/ghi video; NumPy tính và thống kê; Streamlit giao diện. Tất cả inference ở máy chạy ứng dụng. Model tải một lần từ kho Ultralytics chính thức; không tải ảnh người dùng lên API inference.

Tại thư mục repo, PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools/setup_model.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Nếu `.venv` đã có, bỏ qua bước tạo/cài lại. Môi trường đang dùng đã cài đủ thư viện; kết quả kiểm tra và phiên bản ở `evidence/`.

Webcam trực tiếp (chỉ mở sau khi người đóng vai đồng ý):

```powershell
.\.venv\Scripts\python.exe live.py --source 0 --side left
# Ghi video dự phòng khi thành viên đội đồng ý:
.\.venv\Scripts\python.exe live.py --source 0 --side left --record recordings/team-backup.mp4
# Replay một video của đội:
.\.venv\Scripts\python.exe live.py --source recordings/team-backup.mp4 --side left
```

Nhấn **Q/Esc** để thoát, **R** để bắt đầu lượt đếm mới. Chọn `--side right` nếu bên phải gần camera. Không đổi bên giữa một chu trình. Video ghi từ webcam dùng FPS khai báo của camera; khi inference chậm, thời lượng video xuất có thể lệch thời gian thực, log timestamp là nguồn đo thời gian. Muốn benchmark video phải dùng clip gốc và đánh dấu thủ công, không dùng bản đã vẽ skeleton để kết luận độ chính xác.

Giao diện có mô phỏng không cần model, replay từng frame, chỉnh ngưỡng, biểu đồ, CSV, video tải xuống và hồ sơ mục 4–9. Tab video nhận tối đa 30 MB và xử lý tối đa 1.800 frame; ảnh webcam là phép kiểm tra góc đơn lẻ, không phải luồng đếm liên tục.

Tái tạo số đo và kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/benchmark.py
```

Nếu webcam không mở: đóng Teams/Zoom hoặc ứng dụng giữ camera; thử chỉ số camera khác. Nếu model thiếu: chạy `tools/setup_model.py`. Nếu ánh sáng/góc đặt kém: đặt lại camera; chuyển sang mô phỏng hoặc video dự phòng khi cần. Mô phỏng luôn được dán nhãn rõ.

Tham khảo API chính thức: [Ultralytics Pose](https://docs.ultralytics.com/tasks/pose/), [Streamlit file uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader), [Streamlit camera input](https://docs.streamlit.io/develop/api-reference/widgets/st.camera_input). Model/Ultralytics có điều kiện cấp phép riêng; kiểm tra [Ultralytics licensing](https://www.ultralytics.com/license) trước khi triển khai ngoài bài lab.

## Mục 7 — Hồ sơ theo sáu tiêu chí, tổng 100 điểm

Đây là ánh xạ bằng chứng để giám khảo đánh giá; không phải điểm đã được chấm.

| Tiêu chí | Trọng số | Nội dung trình bày và bằng chứng |
|---|---:|---|
| Vận dụng kiến thức | 25 | Chỉ trực tiếp `core.py`, `vision.py`, bảng 7 trụ cột; giải thích góc 2D, confidence, trạng thái, timestamp và lựa chọn hysteresis |
| Demo chạy được | 25 | Chạy mô phỏng tương tác tại chỗ; thay ngưỡng/case để đáp ứng đầu vào mới. Mã webcam/video sẵn có; thử với người đóng vai trước khi tuyên bố chạy ổn trên người thật |
| Độ hữu ích | 15 | Người dùng là HLV/điều phối viên CLB thể thao VinUni: theo dõi số lần hoàn tất và xem đoạn cần kiểm tra lại; đầu ra dễ đọc, có trạng thái chưa đủ dữ liệu |
| Impact | 15 | Phép tính giả định bên dưới; lộ trình pilot → đánh giá → mở rộng; nêu rủi ro đếm sai, góc camera, đồng thuận dữ liệu |
| Bằng chứng | 10 | Ca chuẩn 3/3; che khuất 2/3 với 39 frame từ chối; projection 2/3 dù confidence 0,98; CSV, JSON và video; chưa đo model trên người thật |
| Trình bày và hỏi đáp | 10 | Kịch bản 10 phút và FAQ bên dưới; cần từng thành viên tự diễn tập |

### Số đo và phương pháp

- **Dữ liệu:** mỗi kịch bản 181 frame, timestamp từ 0 đến 9 s, bước 0,05 s; 3 chu trình động tác có nhãn bằng bộ sinh xác định. Không có người thật hay dữ liệu sinh viên.
- **Sai số đếm tuyệt đối:** `abs(số đếm cuối − 3)`. Clean = 0; occlusion = 1; projection = 1. Không tính “accuracy 100%” từ một clip tổng hợp.
- **Occlusion:** confidence hạ xuống 0,12 ở khoảng 3,8–5,7 s; 39 frame bị từ chối. Bỏ qua một lần trong trường hợp này là hành vi bảo thủ theo thiết kế.
- **Logic P50/P95:** `perf_counter` đo riêng `counter.update` từng frame, lấy percentile 50/95, đơn vị ms. Giá trị thực tế ở JSON; thay đổi theo máy/lần chạy. Không bao gồm model, render, I/O hay độ trễ camera.
- **source_fps = 20** là tần số nguồn mô phỏng. Không được diễn giải là FPS model, FPS webcam hoặc độ trễ end-to-end.
- **Kiểm thử:** 11 kiểm thử bao phủ hình học, bất biến tịnh tiến/tỉ lệ, 4 tần số, che khuất, projection, khởi đầu ở đáy, nhiễu ngắn, nhiều người, mất nhịp, timestamp và cấu hình sai.

### Một ca lỗi phải cho xem

Chọn “Ca lỗi: sai góc chiếu lần 2”. Ở lần 2, giả lập nén trục ngang/biến dạng phép chiếu làm góc quan sát không còn phản ánh đúng động tác. Bộ đếm chỉ ghi 2 trong 3 chu trình; các khớp vẫn có confidence 0,98. Nguyên nhân: mô hình hình học 2D và giả định camera nhìn ngang bị vi phạm. Lọc confidence không xử lý được sai lệch hệ thống này. Đây là fault injection tổng hợp minh họa giới hạn, chưa phải đo lỗi của một camera thật. Cách giảm thiểu: hướng dẫn vị trí camera, thêm kiểm tra góc quan sát, hoặc dùng đa góc/3D và kiểm chứng lại.

### Tác động dự kiến — giả định minh bạch

Giả sử một CLB có **40 lượt tập/ngày**, HLV dành **30 giây/lượt** để ghi tay số lần; đọc/xác nhận kết quả mất **10 giây/lượt**. Tiết kiệm lý thuyết `40 × (30−10) / 60 = 13,3 phút/ngày`, khoảng **4,4 giờ trong 20 ngày hoạt động**. Đây là giả thuyết để kiểm tra qua pilot, chưa phải kết quả triển khai VinUni, chưa trừ thời gian lắp đặt, sửa đếm sai và bảo trì.

Pilot đề xuất: thành viên đội tự nguyện, camera cố định nhìn ngang; đối chiếu đếm tay với dự đoán trên 10 clip, gồm đủ góc/ánh sáng/che khuất. Đo MAE số lần mỗi clip, tỷ lệ từ chối và P95 xử lý. Mục tiêu thăm dò có thể đặt MAE ≤ 1 lần/10 lần, song phải kiểm chứng trước khi cam kết. Sau khi có đồng thuận và phê duyệt phù hợp mới thử tại đơn vị thật. Mở rộng sang nhiều người cần tracking danh tính phiên ổn định; MVP hiện chủ động từ chối nhiều người.

### Kịch bản 10 phút

| Thời gian | Nội dung |
|---|---|
| 0:00–1:00 | “VinUni Move giúp HLV CLB theo dõi chu trình squat; hôm nay chứng minh logic bằng mô phỏng, tách rõ khả năng model chưa đánh giá trên người thật.” |
| 1:00–3:00 | Chạy clean, xem 3/3, biểu đồ góc, chỉ chu trình đứng–hạ–đứng; chỉnh ngưỡng trực tiếp |
| 3:00–5:00 | Chạy webcam do đội đóng vai nếu đã thử thành công; nếu không, dùng mô phỏng tương tác. Chuyển sang occlusion và thấy từ chối |
| 5:00–7:00 | Projection 2/3; chỉ số đo trong JSON/CSV, 2–3 trụ cột quan trọng và phép tính 13,3 phút/ngày có giả định |
| 7:00–10:00 | Hội đồng hỏi đáp; mỗi thành viên giải thích phần mình và luồng toàn hệ thống |

**FAQ phản biện:** Vì sao không train? Thời gian ngắn, model pretrained đủ làm điểm xuất phát. Vì sao không chỉ gọi YOLO? Khớp chưa phải số lần; cần hình học, thời gian và quy tắc chất lượng. Tại sao góc 100/160? Ngưỡng minh họa có hysteresis, cần hiệu chỉnh/đánh giá theo camera và người dùng. Confidence cao có chắc đúng? Không, projection minh họa rõ. Đã chứng minh điều gì? Logic và pipeline mô phỏng; chưa có bằng chứng tổng quát trên người thật. Có thay HLV không? Công cụ hỗ trợ quan sát/ghi nhận, HLV vẫn đánh giá kỹ thuật.

Có thêm 5 kiểm thử tích hợp giao diện và 2 kiểm tra dữ liệu 3D: render 6 không gian, đổi kịch bản, chạy/tạm dừng/replay đến cuối, giải phóng webcam giả và xác nhận payload 3D dùng đúng bộ đếm. Tổng cộng 18 kiểm thử đã qua. Model thật đã được smoke test trên 3 ảnh đen để kiểm tra nạp model và đường “không có người”; chưa đánh giá trên người thật. Có thể mở UI bằng `run_local.cmd`, dùng webcam liên tục ngay trong trang, hoặc chọn mô hình 3D xoay/zoom và tải HTML độc lập. Mô hình 3D là minh họa động học tổng hợp, không phải dựng 3D từ camera hay mô phỏng động lực học cơ thể.

## Mục 8 — Lịch trình một buổi và phân vai

Mốc tương đối theo đề Vlearn, không phải lịch hẹn đã đặt.

| Mốc | Hoạt động / đầu ra |
|---|---|
| 0:00–0:15 | Chốt squat, người dùng HLV, quy tắc dữ liệu; phân vai, kiểm tra repo và quyền truy cập |
| 0:15–1:15 | Build vòng đầu vào → góc → bộ đếm → overlay; dựng mô phỏng để có vòng chạy sớm; mốc 1:15 phải chạy được clean |
| 1:15–2:15 | Thêm confidence/dwell, kiểm thử, webcam/video, CSV, lỗi projection; viết báo cáo và thử trên đúng máy |
| 2:15–2:30 | Dừng code; tạo video dự phòng; chốt số đo; từng thành viên mở repo, diễn tập và nộp link repo chung |
| Từ 2:30 | Demo 10 phút/team; giữ sẵn video dự phòng và ứng dụng cục bộ |
| Cuối buổi | Giám khảo tổng hợp điểm; ghi lại phản hồi và giới hạn cần cải thiện |

**Gợi ý vai trò, chưa gán tên thay người dùng:** trưởng nhóm/tích hợp; model & hình học; thời gian & log/kiểm thử; giao diện & demo; bằng chứng & tác động. Với 3 người có thể ghép vai. Cả nhóm đọc được toàn pipeline, không chỉ phần riêng.

**Link repo đã xuất hiện ở bài nộp Vlearn:** https://github.com/nguyenvantu19/K4-Track4-Capstone-T135 — cần bảo đảm bản triển khai mới đã được đẩy lên trước khi coi link này chứa đủ sản phẩm.

## Mục 9 — Checklist trung thực trước demo

| # | Điều kiện | Trạng thái |
|---|---|---|
| 1 | Chạy trên đúng máy, thử webcam/cảm biến tại phòng demo | **Chưa xác nhận tại phòng demo.** Mô phỏng đã kiểm thử cục bộ; cần thành viên đứng trước camera để thử |
| 2 | Video dự phòng | **Có 3 video mô phỏng** `evidence/*.mp4`; nếu demo người thật cần tự quay thêm video của đội |
| 3 | Có số đo và cách đo | **Có:** JSON/CSV, sai số đếm, frame từ chối, P50/P95 logic; cả đội cần tự đọc và giải thích |
| 4 | Có ca lỗi và nguyên nhân | **Có:** projection 2/3, confidence 0,98, sai phép chiếu 2D |
| 5 | Chỉ ra ≥ 2 trụ cột | **Có:** bảng 7 trụ cột và vị trí trong mã; ưu tiên hình học, thời gian, bất định |
| 6 | Không dùng dữ liệu thật sinh viên/bệnh nhân | **Đạt với bộ dữ liệu kèm repo:** toàn bộ tổng hợp; người dùng tự chịu trách nhiệm chọn clip mới đúng yêu cầu |
| 7 | Mỗi thành viên trả lời được lựa chọn thiết kế | **Chưa xác nhận:** có FAQ, cần diễn tập và phân vai thật |
| 8 | Biết người dùng và lợi ích | **Có:** HLV CLB thể thao VinUni, hỗ trợ đếm và quan sát; chưa khảo sát người dùng thực tế |
| 9 | Ước lượng tác động | **Có:** giả định 40 lượt/ngày, tiết kiệm lý thuyết 13,3 phút/ngày; cần pilot đo lại |

Không tự tích hai điều kiện cần kiểm chứng ngoài đời (#1, #7). Tiến độ “đã học” trên Vlearn chỉ cho biết đã mở nội dung, không chứng minh checklist đã đạt.
