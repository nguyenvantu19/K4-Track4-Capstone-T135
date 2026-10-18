# Lời trình bày ngắn — VinUni Move

“Nhóm chọn bài toán camera thể thao tại VinUni: hỗ trợ HLV đếm squat và xem góc gối 2D. Phạm vi hôm nay là một người, camera nhìn ngang; chưa đánh giá kỹ thuật tập toàn thân.

Đầu vào đi qua model pose pretrained để có khớp hông–gối–cổ chân. Chúng em tính góc, kiểm tra confidence, làm mượt theo timestamp và chỉ đếm chu trình đứng–hạ–đứng. Khi mất khớp hoặc nhiều người, hệ thống yêu cầu đứng lại thay vì đoán tiếp.

Đây là mô phỏng tương tác dùng cùng bộ đếm, có 3 chu trình và kết quả 3 lần. Bộ mô phỏng không đi qua model, nên kết quả này chứng minh logic, không phải độ chính xác model trên người thật.

Ở ca che khuất, 39 frame bị từ chối và hệ thống chỉ đếm 2 lần. Ở ca lỗi góc chiếu, confidence vẫn cao nhưng cũng chỉ đếm 2 trong 3 lần. Nguyên nhân là góc chiếu 2D bị biến dạng. Chúng em không dùng confidence làm cam kết rằng góc đúng.

Ba trụ cột rõ nhất là hình học ở phép tính góc, bất định ở quyết định từ chối và thời gian ở bộ lọc/dwell. Log CSV và benchmark tái lập tạo bằng chứng cho kết luận.

Nếu 40 lượt/ngày mỗi lượt tiết kiệm ròng 20 giây ghi nhận, lợi ích lý thuyết là 13,3 phút/ngày. Con số này là giả định; cần pilot với dữ liệu đồng thuận để đo lại. Bước tiếp theo là camera nhìn ngang với thành viên đội tự đóng vai, so sánh đếm tay, đo sai số và độ trễ trước khi áp dụng thật.”

Tất cả thành viên đọc thêm bảng trụ cột, cách đo và FAQ ở `MUC_4_DEN_9.md`. Khi chưa thử webcam thật, giữ nguyên lời giới hạn ở trên.
