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

## 📦 Cài đặt nhanh (One-click Setup)

Yêu cầu: **Python 3.9+**

### Dành cho macOS / Ubuntu:
Mở Terminal tại thư mục dự án và chạy:
```bash
chmod +x setup.sh && ./setup.sh
```
Sau đó, để có thể chạy lệnh `blog-autogen` từ bất cứ đâu, hãy chạy lệnh này (chỉ cần 1 lần):
```bash
sudo ln -sf $(pwd)/blog-autogen-runner /usr/local/bin/blog-autogen
```

### Dành cho Windows:
Click đúp vào file `setup.bat` hoặc chạy trong CMD/PowerShell:
```cmd
setup.bat
```

## ⚙️ Cấu hình (Onboarding)

Lần đầu chạy tool bằng lệnh `blog-autogen`, hệ thống sẽ yêu cầu bạn nhập các thông tin cấu hình (API Key, WordPress, Google Sheets, Telegram...).

Để cập nhật lại cấu hình sau này:
```bash
blog-autogen --update
```

## 📖 Hướng dẫn sử dụng

Chuẩn bị danh sách chủ đề hoặc prompt vào file `prompts.txt` (mỗi dòng một prompt).

**Chạy tool:**
```bash
blog-autogen
```

**Ví dụ chạy 10 bài với 5 luồng song song:**
```bash
blog-autogen --limit 10 --threads 5
```

## 🧪 Phát triển & Kiểm thử

Dành cho nhà phát triển muốn đóng góp hoặc chạy test:
```bash
pip install -e ".[dev]"
pytest
```

---
*Phát triển bởi Gemini CLI Agent.*
