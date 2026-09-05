# WP Drama Article Rewrite Pipeline — Design
 
## Bối cảnh
 
Pipeline hiện có:
1. Nhập link blog WordPress → dùng WP REST API lấy `title`, `content`, ảnh.
2. Bài viết dài 1500–4000 từ, mỗi bài là 1 câu chuyện drama.
3. Chia content thành các chunk ~900–1000 từ để dịch. Mỗi lệnh gọi API dịch mang theo câu cuối của chunk trước làm context giữ mạch chuyện.
4. Lấy title + content đã dịch, reup lên WP của người dùng.
 
**Vấn đề cần giải quyết:** không chỉ dịch thuần, mà cần *viết lại* bài dựa trên bản gốc (biến tấu mạnh — có thể đổi tên nhân vật/bối cảnh, chỉ giữ tinh thần câu chuyện). Khi thử gửi cả bài để viết lại trong 1 lần gọi, đã gặp thật: model từ chối / báo lỗi (nghi do bị coi là vi phạm bản quyền) và rủi ro hallucination khi output quá dài.
 
## Mục tiêu
 
Thêm 1 chế độ mới "dịch + viết lại" (rewrite biến tấu mạnh) chạy song song với chế độ "dịch thuần" hiện có, chạy mượt mà không gặp lại lỗi từ chối/hallucination do gửi nội dung quá lớn trong 1 lần gọi.
 
## Ràng buộc bắt buộc: không ảnh hưởng pipeline cũ
 
- Pipeline "dịch thuần" hiện có **giữ nguyên hoàn toàn** — không sửa, không xóa code/logic đang chạy của nó. Cả 2 chế độ (dịch thuần / dịch + viết lại) cùng tồn tại song song, chọn qua toggle cấu hình (xem "Toggle chế độ" bên dưới).
- Các phần dùng chung có thể tái sử dụng được giữa 2 pipeline (lấy content/ảnh qua WP REST API, logic chia chunk, logic reup lên WP) thì **tái sử dụng lại**, không viết trùng lặp — nhưng chỉ tái sử dụng ở dạng gọi lại (import/call), không sửa đổi hành vi của các hàm/module đó theo hướng phá vỡ pipeline cũ.
- Phần logic gọi AI khác nhau giữa 2 pipeline (dịch thuần: 1 lệnh gọi/chunk kèm câu cuối chunk trước; dịch+viết lại: chat-history theo Phần kiến trúc bên dưới) — đây là phần **mới, tách riêng**, không dùng chung với logic gọi AI của pipeline dịch thuần.
 
## Toggle chế độ
 
Chọn chế độ (dịch thuần / dịch + viết lại) là 1 field mới trong cấu hình pipeline hiện có — đúng nơi đã chọn model/provider cho mỗi pipeline. Không cần chọn lại theo từng lần chạy/từng bài — cấu hình 1 lần cho pipeline đó, áp dụng cho các bài chạy qua pipeline đó.
 
## Kiến trúc pipeline
 
Bước 1, 2, 5 dưới đây dùng chung code với pipeline dịch thuần hiện có (tái sử dụng, không viết lại). Bước 3, 4 là logic mới, chỉ chạy khi pipeline được cấu hình ở chế độ "dịch + viết lại"; khi cấu hình ở chế độ "dịch thuần", bước 3-4 chạy đúng như code cũ hiện có (không đổi).
 
```
1. Nhập link blog WP → WP REST API lấy title, content, images (không đổi,
   dùng chung)
2. Chia content gốc thành các chunk ~900-1000 từ (không đổi cách chia,
   dùng chung)
3. [MỚI — chỉ khi chế độ = dịch + viết lại] Dịch + Viết lại theo chat-history:
   - System prompt cố định cho cả bài (xem "Prompt framing" bên dưới)
   - Chunk 1: gọi AI với [system, user(chunk 1 gốc + hướng dẫn)]
     → nhận bản viết lại #1
   - Chunk 2: gọi AI với [system, assistant(#1), user(chunk 2 gốc + hướng dẫn)]
     → nhận bản viết lại #2
   - Chunk N: gọi AI với [system, assistant(#1)...assistant(#N-1), user(chunk N gốc)]
   - Cơ chế "câu cuối chunk trước" cũ bị loại bỏ hoàn toàn — chat history
     đảm nhiệm việc giữ mạch chuyện, tên nhân vật, bối cảnh, văn phong.
4. [MỚI — chỉ khi chế độ = dịch + viết lại] Sau khi xong tất cả chunk,
   thêm 1 user turn cuối trong CÙNG conversation: title gốc + yêu cầu đặt
   tên mới → AI tự đặt tên nhất quán với toàn bộ nội dung đã viết lại
   trong các assistant turn trước đó.
5. Ghép các chunk đã dịch (thuần hoặc viết lại, tùy chế độ) thành content
   mới, cùng title mới → reup lên WP của người dùng kèm ảnh gốc (ảnh
   không đổi). Bước reup dùng chung code với pipeline cũ.
```
 
**Nguyên tắc cốt lõi:** văn bản gốc chỉ xuất hiện đúng 1 lần trong mỗi lệnh gọi — là chunk hiện tại (~900-1000 từ), không bao giờ resend lại các chunk gốc trước đó. "Trí nhớ" về tên nhân vật/bối cảnh/văn phong đến hoàn toàn từ các `assistant` turn (nội dung do chính AI tạo ra, không phải văn gốc), nên không tích lũy lại nội dung gốc qua các lượt gọi → tránh rủi ro bị flag bản quyền và tránh context phình to với nội dung không cần thiết.
 
## Cấu trúc message
 
```
[
  { role: "system", content: <prompt cố định cho cả bài> },
  { role: "assistant", content: <chunk 1 đã viết lại> },   // nếu có
  { role: "assistant", content: <chunk 2 đã viết lại> },   // nếu có
  ...
  { role: "user", content: <chunk N gốc + hướng dẫn viết lại> }
]
```
 
Ghi chú kỹ thuật: nếu provider không cho phép 2 `assistant` message liên tiếp (yêu cầu xen kẽ user/assistant nghiêm ngặt), chèn thêm 1 `user` placeholder ngắn (ví dụ "(tiếp tục)") giữa các turn assistant. Chi tiết implementation, không ảnh hưởng thiết kế tổng thể.
 
## Prompt framing
 
- System prompt nêu rõ đây là nhiệm vụ **sáng tác truyện mới lấy cảm hứng** từ đoạn tham khảo, không phải "dịch nguyên văn" hay "viết lại bài báo của người khác" — tránh trigger content-policy filter về bản quyền.
- Được phép đổi tên nhân vật/địa danh tự do miễn nhất quán xuyên suốt.
- Giữ tinh thần drama của câu chuyện gốc.
- Viết bằng ngôn ngữ đích.
- Độ dài mỗi đoạn viết lại tương đương chunk gốc (~900-1000 từ), không bắt buộc tuyệt đối.
 
## Title
 
Sau khi hết các chunk, thêm 1 user turn cuối trong cùng conversation chứa title gốc + yêu cầu đặt tên mới. Tận dụng toàn bộ context assistant đã tích lũy để đặt tên nhất quán với nội dung đã viết lại — không cần gọi API riêng hay bước tóm tắt bổ sung.
 
## Model selection
 
Dùng lại abstraction chọn-model-theo-config đã có sẵn (mỗi user chọn model/provider trong config, có thể đổi linh hoạt) — không đổi. Chỉ cần đảm bảo model được chọn hỗ trợ chat-message-array (system/user/assistant), điều mà hầu hết provider chính đều hỗ trợ.
 
## Vì sao không dùng agent framework
 
Cân nhắc và quyết định **không** build thành agent (framework có reasoning loop / tool-calling / memory quản lý sẵn), lý do:
 
1. Đây là workflow tuyến tính, thứ tự cố định (chunk 1 → N → title) — không có quyết định động nào AI cần tự đưa ra ngoài nội dung viết lại. Việc lấy content/ảnh qua WP REST API đã xong trước khi vào loop.
2. "Memory" cần thiết chỉ là 1 mảng message sống trong đúng thời gian xử lý 1 bài (vài chục giây đến vài phút) — không cần lưu trạng thái xuyên session.
3. Các cơ chế agent-memory sẵn có (vd. OpenAI Assistants threads) thường đặc thù theo provider, mâu thuẫn với yêu cầu chọn model/provider linh hoạt theo config.
 
Pipeline gọi API thuần (tự quản message array trong code) là đủ và phù hợp hơn.
 
## Error handling
 
- Nếu 1 lệnh gọi API cho bất kỳ chunk/title nào bị từ chối (content policy) hoặc lỗi khác → dừng xử lý bài đó ngay lập tức, ghi log lỗi (bài nào, chunk thứ mấy, lỗi gì). Không tự động retry, không tự đổi model, không tự đổi prompt — để người dùng xem và xử lý thủ công.
- Lỗi ở 1 bài không ảnh hưởng các bài khác trong queue.
- Không cần rollback phức tạp: bước reup lên WP chỉ chạy sau khi toàn bộ chunk + title đã viết lại xong thành công, nên nếu lỗi giữa chừng thì chưa có gì được đăng lên WP.
 
## Non-goals (ngoài phạm vi lần update này)
 
- Không sửa/xóa code hoặc hành vi của pipeline "dịch thuần" hiện có.
- Không tự động retry/đổi model/đổi frame prompt khi bị từ chối — xử lý thủ công.
- Không đổi cách xử lý ảnh — ảnh gốc giữ nguyên, không rewrite/regenerate.
- Không cần agent framework/tool-calling.
- Không có bước "story bible"/glossary JSON tường minh riêng — chat-history đảm nhiệm việc giữ nhất quán tên/bối cảnh.