# WordPress Publisher: nhập nội dung và chạy pipeline

## Mục tiêu và quyết định đã thống nhất

Thêm chế độ nhập nội dung vào WordPress Publisher, chạy đúng luồng xử lý và đăng bài của Dashboard. Người dùng chọn pipeline và V1/V2, nhập title, content và ảnh tùy chọn. Chế độ đăng trực tiếp hiện tại tiếp tục hoạt động như cũ.

Ưu tiên mở rộng Article Workflow đang có. Không tạo một bộ dịch, scheduler hoặc bộ đăng đa kênh riêng.

## Phạm vi giao diện

- Hai chế độ: `Direct publishing` và `Pipeline workflow`. Mặc định vẫn là chế độ đăng trực tiếp để giữ trải nghiệm hiện tại.
- Chuyển chế độ không tự gửi bài, không tự chạy dịch và không xóa nội dung đang nhập trong phiên trang hiện tại.
- Chế độ mới có lựa chọn pipeline cùng tiêu chí như Dashboard hiện tại: pipeline đang hoạt động, có AI và WordPress account. Hiển thị tên và ngôn ngữ pipeline.
- Chọn V1/V2 theo cùng ý nghĩa và giá trị lưu lựa chọn của Dashboard. V1 dịch sát nội dung; V2 viết lại theo prompt hiện có.
- Title và content bắt buộc, không chấp nhận chỉ có khoảng trắng. Content đầu vào là văn bản thuần, giữ xuống dòng. Không thêm trình biên tập HTML cho chế độ mới.
- Ảnh tùy chọn: URL hoặc upload theo khả năng hiện có của Publisher; chỉ chọn một nguồn ảnh. Có thể gỡ ảnh trước khi chạy.
- Nút `Run workflow` tự động chạy xử lý và đăng theo pipeline, giống nút Run của Dashboard; không thêm bước duyệt bài trước khi đăng.
- Hiển thị tiến độ, lỗi, kết quả và thao tác retry bằng thành phần job hiện có. Job vẫn xuất hiện trong danh sách Dashboard; tránh tạo một hệ thống lịch sử job thứ hai.
- Publisher history và trình soạn thảo của chế độ trực tiếp giữ nguyên phạm vi bài manual hiện tại.
- Bố cục dùng các thành phần UI hiện có, co giãn theo màn hình; không thay đổi thiết kế tổng thể.

## Các phương án đã xem xét

1. **Mở rộng Article Workflow với nguồn nhập tay — chọn phương án này.** Tái sử dụng dịch, viết lại, đăng đa kênh, checkpoint, retry và concurrency. Chỉ cần thêm biên nhận đầu vào và phân nhánh phần chuẩn bị nguồn.
2. Tạo workflow dịch riêng trong Publisher: dễ tách giao diện, nhưng nhân đôi xử lý và dễ lệch hành vi Dashboard.
3. Dịch trong DraftEditor rồi đăng thủ công: dùng lại editor, nhưng thay đổi yêu cầu tự động chạy toàn bộ pipeline.

## Kiến trúc và luồng dữ liệu

### Tiếp nhận nguồn nhập tay

Thêm endpoint `POST /article-workflows/run-text` nhận multipart: pipeline_id, mode, title, content, image_url tùy chọn hoặc image file tùy chọn. Endpoint này chỉ là adapter đầu vào cho Article Workflow dùng chung.

Kiểm tra pipeline/account theo cùng quy tắc Dashboard; kiểm tra trường bắt buộc và nguồn ảnh loại trừ nhau. Upload dùng lại giới hạn dung lượng, MIME, kiểm tra chữ ký file và lưu trữ ảnh của Publisher. Nếu cần tách helper, cả endpoint cũ và mới cùng gọi helper đó, giữ hợp đồng endpoint cũ.

Trước khi đưa job vào runner, lưu bền vững draft, job, manifest và snapshot nguồn. Manifest có `source_kind = manual`; snapshot chứa title, content và thông tin ảnh. Không dùng title/content kết quả làm nơi lưu duy nhất cho nguồn vì chúng sẽ bị ghi đè sau dịch. Dữ liệu liên kết được commit trước khi chạy; lỗi tiếp nhận không để lại job chạy với nguồn chưa đầy đủ. File vừa lưu được dọn nếu giao dịch tiếp nhận thất bại.

Giữ draft kind và workflow type `article_v1`/`article_v2` để dùng lại hiển thị, hủy, retry và xử lý kết quả. `source_url` để trống cho nguồn nhập tay; không tạo URL giả.

### Chuẩn bị nguồn và thực thi chung

ArticleWorkflowService nhận biết nguồn từ manifest. Bản ghi cũ thiếu source_kind được hiểu là nguồn URL, giữ tương thích.

- Nguồn URL: tiếp tục fetch và xử lý nguồn như hiện tại.
- Nguồn manual: đọc snapshot đã lưu; tuyệt đối không gọi source gateway hoặc chuẩn hóa URL rỗng. Khôi phục đúng thông tin ảnh đã chọn, bao gồm ảnh upload.
- Sau chuẩn bị nguồn, hai loại đầu vào đi chung nhánh V1/V2 và toàn bộ phần đăng WordPress, Facebook, Telegram hiện tại.

Ngôn ngữ, AI account, WordPress account, danh mục và các kênh phụ lấy từ pipeline, được đóng băng theo manifest như hiện tại. Prompt, title translation, caption, quy tắc chia nội dung và cách đăng không tạo biến thể riêng cho Publisher.

Proxy nguồn, lưu nguồn theo URL vào Pattern Library và AI enrichment gắn với bài nguồn hiện phụ thuộc URL. Chế độ nhập tay bỏ qua các bước phụ thuộc URL này và không hiển thị các công tắc tương ứng. Không tạo URL giả hoặc tự thêm bài nhập tay vào Pattern Library. Đây là khác biệt do bỏ nguồn URL; hành vi dịch/viết lại và đăng đa kênh vẫn giống Dashboard.

Ảnh upload được giữ nguyên đường dẫn nội bộ cho WordPress. Adapter Facebook hiện chỉ hỗ trợ URL: bổ sung phương thức gửi file multipart cho ảnh upload, giữ cùng caption và cơ chế receipt; ảnh URL tiếp tục dùng phương thức hiện có. Không truyền đường dẫn local như URL từ xa. Không thêm tính năng sinh ảnh AI.

### Retry, hủy và giới hạn tài nguyên

- Retry nguồn manual đi qua endpoint retry Article Workflow hiện có; xác định loại nguồn bằng recovery record thay vì đòi job.input_text là URL.
- Retry tạo attempt mới cho cùng draft, dùng snapshot cũ và giữ các phần đã hoàn thành. Không yêu cầu nhập lại nội dung hoặc upload lại ảnh.
- Lỗi dịch tiếp tục từ phần chưa hoàn thành; lỗi WordPress không dịch lại; lỗi kênh phụ không đăng lại WordPress hay kênh đã có receipt.
- Kết quả đăng chưa chắc chắn vẫn dùng cơ chế xác minh delivery hiện có. Không tự xóa trạng thái uncertain.
- Hủy, quyền ghi của attempt hiện hành, kiểm tra job đang chạy và chống retry đồng thời dùng cơ chế hiện tại.
- Dùng chung scheduler toàn ứng dụng, giới hạn theo account/credential, cooldown và retry provider. Không tạo pool riêng cho Publisher.
- Giới hạn ký tự theo AI account và giá trị kế thừa Settings giữ nguyên. Đây là giới hạn mỗi request/chunk, không phải giới hạn toàn bộ content nhập vào.
- Sửa nội dung, đổi ảnh hoặc đổi pipeline để chạy một bản mới phải tạo run mới; retry không sửa nguồn đã đóng băng.

## Dữ liệu và tương thích

Dùng ContentDraft, Job và WorkflowRecovery hiện có; thêm loại nguồn và snapshot trong JSON manifest/artifacts, không cần migration cấu trúc bảng mới. Không thay DB người dùng hoặc cấu hình account trong quá trình kiểm thử.

Các record recovery và job URL cũ tiếp tục hoạt động khi không có trường mới. Retention tiếp tục giữ artifact của run chưa hoàn thành. Ảnh upload gắn với draft dùng cùng vòng đời lưu trữ/xóa như Publisher hiện tại.

## Xử lý lỗi

- Lỗi validation hoặc upload: hiển thị lỗi trong form, giữ nội dung đã nhập, chưa chạy workflow.
- Lỗi khởi chạy: không làm mất snapshot đã commit; trạng thái phải cho phép xác định và tiếp tục job theo cơ chế phục hồi hiện có, không hiển thị thành công khi chưa tiếp nhận được job.
- Lỗi provider, xuất bản và kênh phụ: dùng cùng thông báo đã lọc thông tin nhạy cảm và trạng thái như Dashboard.
- Ảnh lỗi khi xuất bản: tuân theo hành vi Publisher hiện tại, tiếp tục đăng không ảnh với cảnh báo nếu dịch vụ đang xử lý theo cách đó.

## Kiểm chứng và tiêu chí hoàn thành

- API từ chối title/content trắng, pipeline không hợp lệ và hai nguồn ảnh cùng lúc; upload dùng cùng validation hiện có.
- Nguồn nhập tay không fetch, không chuẩn hóa URL trống, không chạy các bước thu thập/enrichment phụ thuộc URL.
- V1/V2 gọi đúng engine hiện có với đúng title/content/ngôn ngữ, ảnh và cấu hình account.
- Kiểm tra không ảnh, ảnh URL và ảnh upload; WordPress và Facebook nhận đúng loại ảnh, Telegram dùng kết quả WordPress như hiện tại.
- Kiểm tra checkpoint nguồn tồn tại trước thực thi và retry sau restart không mất nguồn/ảnh, không dịch lại khi chỉ lỗi đăng bài, không gửi lại kênh đã có receipt.
- Chạy đồng thời từ Dashboard và Publisher cùng account vẫn tuân thủ một giới hạn concurrency.
- Kiểm tra chế độ trực tiếp, chạy nguồn URL và retry job URL cũ không bị hồi quy.
- Kiểm tra UI chuyển chế độ, giữ nội dung trong phiên, validation, V1/V2, tiến độ/retry và màn hình nhỏ.
- Chạy bộ test backend liên quan, frontend lint/typecheck/build và browser tests phù hợp. Dùng mock cho AI và các nền tảng đăng bài; không phát sinh API trả phí hay đăng bài thật khi kiểm thử.

## Ngoài phạm vi

Không chọn nhiều pipeline trong một lần, không sửa ngôn ngữ tách khỏi pipeline, không dịch trực tiếp trong editor cũ, không thêm bước duyệt vào chế độ tự động, không tạo pipeline hoặc scheduler mới và không build release trong thay đổi này trừ khi người dùng yêu cầu tiếp.
