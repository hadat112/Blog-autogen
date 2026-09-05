# Article Pattern Store — Design
 
## Bối cảnh
 
Pipeline hiện có (xem [2026-08-14-wp-drama-rewrite-pipeline-design.md](2026-08-14-wp-drama-rewrite-pipeline-design.md)) fetch 1 bài blog WP, dịch (thuần hoặc dịch+viết lại), reup lên WP khác. Mỗi lần generate hiện tại đều phải bám vào 1 bài nguồn cụ thể.
 
**Mục tiêu dài hạn:** tích lũy dữ liệu từ các bài đã xử lý để sau này AI có thể **generate truyện mới độc lập, không cần dựa trên 1 bài nguồn cụ thể nào** — dựa trên hiểu biết tổng hợp về:
1. Cấu trúc mạch truyện thường gặp (structure).
2. Nội dung đa dạng theo những chủ đề/thể loại nào (content diversity).
3. Cách viết title/giật tít thường dùng (headline patterns).
 
Đây là 1 luồng dữ liệu **độc lập**, tách biệt hoàn toàn với spec dịch/viết lại — không phụ thuộc và không ảnh hưởng đến pipeline đó.
 
## Lưu trữ: SQLite
 
Dùng SQLite (1 file DB), không dựng vector DB hay DB server riêng. Lý do:
- Chưa có DB nào trong hệ thống, không cần thêm hạ tầng.
- Đủ để query thật sự cho đúng 3 mục đích trên: đếm/group theo tag (content diversity), lấy mẫu ngẫu nhiên/lọc theo tag (few-shot title/structure sau này) — không cần semantic/vector search vì mục tiêu là generate độc lập (không có 1 "bài query cụ thể" để tìm bài tương tự lúc generate).
- Vector DB / embedding bị loại ở giai đoạn này (xem "Non-goals").
 
**Bảng `articles`:**
```
- id
- source_url          -- trace lại bài gốc nếu cần
- original_title       -- verbatim, dùng để học pattern giật tít
- theme_tags           -- vd: ["ngoại tình","mẹ chồng nàng dâu","báo thù"]
- structure (JSON):     -- học cấu trúc mạch truyện
    hook
    conflict
    turning_points[]
    climax
    resolution
- word_count
- processed_at
```
 
## Cách lấy dữ liệu cho từng field
 
| Field | Cách lấy | Cần AI? |
|---|---|---|
| `source_url`, `original_title`, `word_count`, `processed_at` | Code thuần — lấy trực tiếp từ dữ liệu đã fetch qua WP REST API | Không |
| `theme_tags` | Code thuần — match từ khóa theo 1 file cấu hình dạng `{tag: [keywords]}`, tự duy trì/mở rộng dần theo thời gian | Không |
| `structure` | 1 lệnh gọi AI/bài, input = toàn bộ bản gốc (task phân tích/tóm tắt, không phải sáng tác lại — không có rủi ro bị từ chối như bước rewrite, không cần chunk vì đây không phải bài toán generation) | Có, đúng 1 lần/bài |
 
`theme_tags` bằng keyword-matching sẽ miss/gắn sai một số bài không chứa đúng từ khóa — chấp nhận đánh đổi này để giữ chi phí = 0 cho field này; có thể cải thiện sau nếu cần (không nằm trong scope lần này).
 
## Tích hợp vào pipeline
 
Bước mới, chạy ngay sau khi fetch content gốc từ WP, **độc lập hoàn toàn** với 2 pipeline dịch (thuần / dịch+viết lại) đã có:
- Không sửa/xóa code của 2 pipeline dịch.
- Chỉ thêm 1 nhánh song song: fetch xong → (a) đưa vào pipeline dịch như cũ, (b) đồng thời trích tags (code thuần) + gọi AI trích `structure`, ghi 1 row vào SQLite.
 
## Error handling
 
Nếu lệnh gọi AI trích `structure` bị lỗi/từ chối → bỏ qua field `structure` cho bài đó (log lại lỗi: bài nào, lý do gì), **không chặn** pipeline dịch chính của bài đó — vì đây là dữ liệu phụ trợ, không phải output chính.
 
## Non-goals (ngoài phạm vi lần này)
 
- Không dựng vector DB (Chroma/Qdrant/Pinecone...) hay dịch vụ semantic search riêng — mục tiêu hiện tại (thống kê/lấy mẫu theo tag) không cần đến, và generate độc lập không có "query cụ thể" để tìm bài tương tự.
- Không thêm cột `embedding` vào bảng ngay bây giờ — để lại nếu sau này thực sự cần semantic search (thêm cột là migration đơn giản, không cần backfill logic phức tạp trước).
- Không xây cơ chế retrieval/RAG hay bước "generate truyện độc lập" trong spec này — đây chỉ là bước thu thập/lưu trữ dữ liệu; cơ chế dùng lại dữ liệu để generate sẽ là 1 spec riêng ở tương lai khi đã rõ nhu cầu.
- Không cải thiện độ chính xác `theme_tags` (vd. bằng AI hoặc embedding-based clustering) trong lần này.