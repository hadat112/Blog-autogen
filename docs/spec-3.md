# Generate New Story Pipeline — Design
 
## Bối cảnh
 
2 spec trước đã có:
- [2026-08-14-wp-drama-rewrite-pipeline-design.md](2026-08-14-wp-drama-rewrite-pipeline-design.md) — fetch 1 bài WP nguồn, dịch (thuần hoặc dịch+viết lại), reup lên WP.
- [2026-08-14-article-pattern-store-design.md](2026-08-14-article-pattern-store-design.md) — lưu lại pattern (title, tags, structure) từ các bài đã xử lý vào SQLite, phục vụ mục tiêu dài hạn: generate truyện **độc lập, không cần bài nguồn**.
 
Spec này là bước hiện thực hóa mục tiêu đó: 1 pipeline generate truyện drama mới hoàn toàn, dựa trên data đã tích lũy trong pattern-store, phục vụ đăng FB (câu view) + WP.
 
**Khác biệt quan trọng với 2 pipeline trước:** input không phải link WP — chỉ cần **ngôn ngữ đích**. Không có bài nguồn nào để dịch/viết lại.
 
## Mục tiêu
 
Pipeline generate ra:
1. 1 câu chuyện drama mới, câu view, dùng để đăng FB.
2. Title đủ độ giật/hấp dẫn, dựa trên pattern title đã học từ data cũ.
3. 1 đoạn caption FB — trích đúng phần mở đầu của câu chuyện, dừng ở điểm tò mò nhất.
4. Đăng title + story lên WP qua API (cuối pipeline).
 
## Kiến trúc
 
Đây là pipeline mới, không tái sử dụng logic gọi-AI của 2 pipeline dịch (vì bản chất khác: generate từ đầu, không có input text để chunk/dịch). Chỉ tái sử dụng bước đăng-lên-WP.
 
**Quyết định kiến trúc — dùng AI agent (tool-calling) thật, không phải pipeline gọi API thuần:** khác với 2 pipeline trước (đã quyết định không cần agent vì luồng tuyến tính, cố định), pipeline này cần AI **tự quyết định theme và số lượng ví dụ tham khảo** — một quyết định động, không cố định trước bằng code. Đây là lý do chính đáng để dùng agent (có tool-calling), khác với 2 spec trước.
 
```
Input: ngôn ngữ đích
 
1. [Agent] AI được cấp 2 tool:
   - list_themes()            -- code query SQLite bảng `articles` (từ pattern-store),
                                  trả về [{theme, count}]
   - get_examples(theme, n)   -- code query SQLite, trả về n bản ghi {title, structure}
                                  (không có full text gốc — đúng theo pattern-store đã
                                  thiết kế, cũng giảm rủi ro "lặp" nguyên văn nội dung)
 
   AI tự quyết định: gọi list_themes() xem phân bố theme, chọn 1 theme phù hợp,
   gọi get_examples() với số lượng ví dụ tự chọn. Có thể gọi nhiều vòng nếu muốn
   xem thêm theme khác hoặc lấy thêm ví dụ.
 
   Giới hạn tối đa ~6 lượt gọi tool/run để tránh loop vô hạn — vượt giới hạn thì
   dừng, báo lỗi (không tự retry).
 
2. Sau khi đủ thông tin, AI trả về output cuối cùng (JSON, 1 lần):
   {
     title: string,    -- giật tít, dựa trên pattern title đã học từ ví dụ
     story: string,     -- truyện đầy đủ 1500-4000 từ, viết bằng ngôn ngữ input,
                           xuất hết trong 1 lần gọi (không chunk — xem "Rủi ro đã
                           chấp nhận" bên dưới)
     caption: string    -- đoạn mở đầu THẬT của story (verbatim), AI tự dừng ở
                           điểm tò mò nhất để làm caption FB
   }
 
3. [Code] Validate: `caption` phải là tiền tố (prefix) chính xác của `story`.
   Sai thì coi là lỗi generate — dừng, log lại, không tự sửa/tự retry.
 
4. [Code, tái sử dụng] Đăng `title` + `story` lên WP qua REST API — dùng lại
   đúng logic reup đã có từ pipeline dịch (spec 1).
 
5. [Code] Sau khi đăng WP thành công, lưu vào bảng mới `generated_posts`
   (cùng file SQLite với pattern-store):
   { id, theme, language, title, caption, wp_post_url, generated_at }
   Không lưu lại full story text — đã có sẵn trên WP qua `wp_post_url`.
```
 
Bạn tự vào bảng `generated_posts` lấy `caption` + `wp_post_url` để đăng FB tay.
 
## Model / Agent runtime
 
Dùng lại abstraction chọn-model-theo-config đã có (như 2 pipeline trước), nhưng model được chọn cho pipeline này phải hỗ trợ tool-calling (function calling) — hầu hết provider chính đều hỗ trợ.
 
## Rủi ro đã chấp nhận
 
- **Story generate trong 1 lệnh gọi duy nhất (1500-4000 từ), không chunk:** có rủi ro chất lượng/mạch truyện giảm khi output dài, giống vấn đề từng gặp ở pipeline dịch. Đã trình bày trade-off và người dùng chủ động chọn giữ nguyên 1 lần gọi, không chunk.
 
## Error handling
 
- Lỗi tool call (query SQLite lỗi) → dừng, log lỗi, không tự retry.
- Vượt giới hạn ~6 lượt gọi tool trong 1 run mà agent không "chốt" được output cuối → dừng, log lỗi.
- Model từ chối/lỗi API ở bước generate → dừng, log lỗi.
- `caption` không phải tiền tố chính xác của `story` → coi là lỗi generate, dừng, log — không tự sửa.
- Lỗi khi đăng WP → dừng, log lỗi. Chỉ ghi vào bảng `generated_posts` **sau khi** đăng WP thành công, để tránh log rác khi run thất bại giữa chừng.
- 1 run lỗi không ảnh hưởng các run khác.
 
## Non-goals (ngoài phạm vi lần này)
 
- Không tự động retry/đổi model/đổi prompt khi lỗi ở bất kỳ bước nào — xử lý thủ công, nhất quán với 2 spec trước.
- Không tích hợp FB API để tự đăng — chỉ lưu `caption` + `wp_post_url` để đăng tay.
- **Không feedback truyện đã generate ngược lại vào bảng `articles` (pattern-store)** — tránh vòng lặp AI học lại từ chính output tổng hợp của nó (rủi ro suy giảm chất lượng dần / model collapse). Bảng `articles` chỉ lớn lên từ bài nguồn thật qua pipeline fetch WP (spec pattern-store).
- Không chunk quá trình viết truyện — giữ 1 lệnh gọi duy nhất cho `story`, chấp nhận rủi ro chất lượng đã nêu.
- Không cho người dùng chọn theme/số lượng ví dụ tham khảo mỗi lần chạy — để agent tự quyết định hoàn toàn.
- Không dùng vector DB/embedding (kế thừa quyết định từ spec pattern-store).
- Không sửa/ảnh hưởng 2 pipeline dịch đã có — chỉ tái sử dụng bước đăng-WP.