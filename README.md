# Blog Auto-Generator CLI

Một công cụ mạnh mẽ giúp tự động hóa quy trình sản xuất nội dung bằng AI: từ việc lên ý tưởng, viết truyện, tạo ảnh minh họa cho đến việc đăng bài lên WordPress và quản lý báo cáo.

## 🚀 Tính năng chính

- **AI Automation (9router):** 
    - Tự động tạo tiêu đề và nội dung truyện dựa trên prompt.
    - Tạo caption Facebook kịch tính, ngắt quãng để thu hút người dùng click vào link.
    - Tự động thiết kế prompt cho ảnh và tạo ảnh minh họa chất lượng cao.
- **Quản lý đăng bài:**
    - Tích hợp WordPress REST API để đăng bài tự động.
    - Hỗ trợ Upload Media (ảnh) trực tiếp lên thư viện WordPress.
- **Hệ thống báo cáo & Thông báo:**
    - Tự động ghi log chi tiết vào Google Sheets (Title, Content, URL, Status...).
    - Bắn thông báo kết quả qua Telegram Bot ngay sau mỗi task.
- **Hiệu năng cao:**
    - Hỗ trợ đa luồng (Multithreading) giúp xử lý hàng loạt truyện cùng lúc.
    - Tham số `--limit` và `--threads` linh hoạt.
- **Giao diện thân thiện:**
    - Interactive CLI (Onboarding) giúp cấu hình dễ dàng bằng phím mũi tên và Enter.

## 🛠 Kiến trúc hệ thống (Modular Design)

Hệ thống được thiết kế theo hướng module hóa để dễ dàng mở rộng:

- **`core/`**: Điều phối luồng xử lý (Orchestrator) và quản lý cấu hình.
- **`providers/`**: Các dịch vụ bên ngoài (AI 9router, Google Sheets, Image Storage).
- **`publishers/`**: Các nền tảng đăng bài (WordPress hiện tại, Facebook chuẩn bị sẵn).
- **`utils/`**: Các công cụ hỗ trợ (Telegram Notify, Helpers).

## 📦 Cài đặt

Yêu cầu: **Python 3.9+**

1. Clone thư mục dự án.
2. Cài đặt công cụ và các phụ thuộc:
```bash
pip install -e .
```

## ⚙️ Cấu hình (Onboarding)

Lần đầu chạy tool, hệ thống sẽ yêu cầu bạn nhập các thông tin cấu hình:
- **AI:** API Key 9router và chọn Model.
- **WordPress:** URL website, Username và Application Password.
- **Google Sheets:** ID bảng tính và đường dẫn file JSON Credentials.
- **Telegram:** Token Bot và Chat ID.

Để cập nhật lại cấu hình sau này:
```bash
blog-autogen --update
```

## 📖 Hướng dẫn sử dụng

Chuẩn bị danh sách chủ đề hoặc prompt vào file `prompts.txt` (mỗi dòng một prompt).

**Chạy tool với cấu hình mặc định:**
```bash
blog-autogen
```

**Chạy 10 bài với 5 luồng song song:**
```bash
blog-autogen --limit 10 --threads 5
```

## 🧪 Phát triển & Kiểm thử

Dành cho nhà phát triển muốn đóng góp hoặc chạy test:

```bash
# Cài đặt các thư viện dev
pip install -e ".[dev]"

# Chạy toàn bộ test
pytest
```

## 📝 Cột trong Google Sheets
Sau khi chạy xong, dữ liệu sẽ được điền vào Google Sheets với các cột:
`title`, `content`, `caption`, `image_url`, `wordpress_url`, `date_added`, `status`.

---
*Phát triển bởi Gemini CLI Agent.*
