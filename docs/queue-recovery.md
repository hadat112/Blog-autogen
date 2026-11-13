# Xử lý hàng chờ AI và lỗi WordPress

## Cơ chế phòng tránh trong app

- Mỗi lượt chờ luôn được xóa khi cancel, timeout hoặc kiểm tra trạng thái bị lỗi. Không còn để lại lượt mồ côi chặn đầu hàng.
- Kiểm tra trạng thái job và ghi tiến độ chạy ngoài khóa chung của scheduler. DB chậm không giữ khóa của mọi tài khoản AI.
- Chờ slot AI dùng ngân sách `ai_request_timeout` (mặc định 300 giây). Hết thời gian, job báo lỗi có số request đang chạy/chờ và giới hạn tài khoản, thay vì chờ vô hạn.
- Một lần gọi AI chia sẻ ngân sách cho chờ slot và retry. Thời gian đã dùng không được cấp lại ở mỗi lần retry. Timeout HTTP của thư viện requests là timeout không có dữ liệu, không phải cam kết cắt kết nối đúng tổng số giây nếu server liên tục gửi dữ liệu nhỏ giọt.
- Retry-After/cooldown được giới hạn tối đa 30 giây; giá trị không hữu hạn bị loại. Nếu provider yêu cầu nghỉ lâu, giảm tải hoặc tạm dừng các job; không tăng concurrency để vượt rate limit.
- Các log `Translating title`, `Waiting for AI slot`, `Calling AI`, và `retrying` giúp phân biệt chờ worker, chờ slot, gọi provider và retry. Log slot được cập nhật tối đa mỗi 5 giây khi chờ.
- Worker chờ bằng asyncio, không chiếm thêm thread chỉ để đợi semaphore. Hết 300 giây chờ worker, job chuyển sang thất bại và giữ bản nháp.
- Cancel ngăn việc gọi/retry AI tiếp theo khi app nhận biết trạng thái hủy. Request HTTP đã gửi có thể vẫn giữ slot đến khi trả kết quả hoặc timeout; app giữ giới hạn concurrency thật và ghi rõ điều này ở log hủy.
- Không tự đổi sang model dự phòng trong bản dịch đang phục hồi: model được cố định theo manifest để tránh trộn kết quả từ các model khác nhau.

## Khi AI Home đứng hàng chờ

1. Đọc log cuối. `Waiting for AI slot: active=1/1` nghĩa là vẫn có request chiếm slot; `active=0` cùng cooldown lớn nghĩa là đang nghỉ do rate limit.
2. Sau cancel, không bấm chạy lại liên tục. Đợi request cũ kết thúc hoặc timeout; cancel không bảo đảm provider ngừng xử lý phía server.
3. Kiểm tra AI Home/9Router đang chạy và endpoint của tài khoản đúng máy. `localhost:20128` là máy chạy Story Autogen, không phải máy từ xa.
4. Giữ concurrency 1 cho AI Home khi chưa xác định năng lực provider. Có thể chọn tài khoản/model khác cho một lượt chạy mới.
5. Khi tất cả worker bị request cũ giữ, lượt mới sẽ hết hạn chờ và có thể retry sau. Nếu provider gửi dữ liệu nhỏ giọt hoặc không thoát được kết nối, cần kiểm tra log router; restart app có kiểm soát là biện pháp cuối, rồi dùng Resume cho bản nháp đã lưu.
6. Muốn hủy cứng request đang bay và bảo đảm deadline theo đồng hồ cần chuyển transport hỗ trợ hủy hoặc cô lập request bằng process. Không giải phóng giả slot và mở thêm thread vì sẽ vượt giới hạn request thật.

## Khi WordPress trả 403

App ghi status, `code` và `message` của phản hồi JSON đã lọc mật khẩu/token. Với phản hồi HTML, app ghi gợi ý kiểm tra hosting/firewall và không lưu nguyên HTML. Không tự retry thao tác tạo bài để tránh đăng trùng.

- `rest_cannot_create` hoặc thông báo quyền: kiểm tra quyền tạo/publish bài của user và Application Password.
- Phản hồi HTML: đối chiếu thời điểm lỗi với log WAF/ModSecurity/plugin bảo mật và quy tắc chặn REST API.
- Kiểm tra đúng URL site và cơ chế Basic Auth ở hosting. DB cũ chỉ có mã 403 nên không thể chốt nguyên nhân phía server từ bản sao này.
- Sau khi sửa quyền/quy tắc chặn, dùng Resume hoặc đăng lại bản nháp đã dịch. Nếu trạng thái `publish_unknown`, kiểm tra WordPress trước để tránh tạo bài trùng.

## Kiểm chứng

Các test trong `tests/integrations/test_ai_scheduler.py`, `test_translation_upgrade.py`, `test_wordpress_destination.py` và `tests/domain/test_concurrent_workflows.py` giả lập lỗi/cancel bằng event và request giả; không gọi provider hoặc đăng bài thật.
