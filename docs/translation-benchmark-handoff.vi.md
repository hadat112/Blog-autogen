# Handoff: Translation Benchmark Và Tối Ưu Luồng Dịch

Tài liệu này ghi lại trạng thái triển khai tại ngày 12/06/2026 để phiên làm
việc sau có thể tiếp tục mà không cần đọc lại toàn bộ repository.

## Trạng Thái Git

- Nhánh hiện tại: `feature/translation-benchmark-ui`
- Nhánh được tạo từ: `feature/professional-readme`
- Thay đổi hiện tại chưa commit.
- Không checkout về nhánh cũ hoặc reset worktree trước khi kiểm tra
  `git status`.

Các thay đổi thuộc feature này nằm trong:

- `adapters/ai/ninerouter.py`
- `application/translation_benchmark_service.py`
- `apps/api/routes/benchmarks.py`
- `apps/api/schemas.py`
- `apps/api/main.py`
- `infrastructure/db/models.py`
- `frontend/src/pages/TranslationBenchmarks/`
- `frontend/src/api/`
- `frontend/src/App.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/pages/Accounts/components/AccountForm.tsx`
- `tests/api/test_api_benchmarks.py`
- `tests/core/test_translation_benchmark.py`
- `tests/adapters/test_ai_9router.py`
- `docs/translation-benchmark.md`

## Mục Tiêu Đã Thống Nhất

1. Có một màn hình benchmark riêng, không trộn với Dashboard hoặc pipeline
   production.
2. Người dùng chọn các model muốn so sánh thông qua các AI account đã cấu hình.
3. Benchmark chạy nền và UI polling để hiển thị tiến độ/kết quả.
4. Mỗi HTTP request chỉ được gọi một lần, không retry.
5. So sánh dựa trên hard metrics, latency, token usage và đánh giá thủ công
   blind.
6. Đồng thời tối ưu production translation workflow nhưng không thêm agent,
   LangChain hoặc LangGraph.

## Phần Đã Hoàn Thành

### 1. Translation Benchmark Backend

Model DB mới:

```text
TranslationBenchmarkRun
```

Các trường chính:

- `status`, `progress`, `current_step`
- `target_language`, `suite`
- `selected_account_ids`
- `request_config`
- `results`
- `manual_ratings`
- `error`
- timestamps

API:

```text
GET  /translation-benchmarks
GET  /translation-benchmarks/{run_id}
POST /translation-benchmarks
POST /translation-benchmarks/{run_id}/ratings
```

Runner:

- Chạy bằng background asyncio task kết hợp `asyncio.to_thread`.
- Các candidate/model chạy song song, tối đa 4 worker.
- Các case của cùng một candidate chạy tuần tự.
- Lưu partial result và progress sau khi mỗi candidate hoàn thành.
- Mỗi candidate dùng `request_max_attempts=1`.

Benchmark hỗ trợ:

- `standard`: 3 case tiếng Anh cố định.
- `custom`: title và content do người dùng nhập.
- Target language do người dùng chọn.

### 2. Scoring

Hard score hiện kiểm tra:

- Output rỗng.
- Refusal/policy/copyright response.
- Giữ số paragraph.
- Giữ số, ngày tháng và tiền tệ.
- Length ratio bất thường.
- Prefix như `Translation:`.
- Khả năng còn nguyên source text.
- Latency.
- Request count.
- Input/output tokens nếu provider trả trường `usage`.

Hard score không đánh giá chính xác:

- Độ tự nhiên.
- Sắc thái văn hóa.
- Semantic fidelity đầy đủ.
- Cách xưng hô và văn phong.

Vì vậy UI có blind review và rating thủ công 1-5.

### 3. Translation Benchmark Frontend

Route:

```text
/translation-benchmarks
```

Sidebar có mục `Benchmarks`.

Màn hình hỗ trợ:

- Chọn ít nhất 2 AI accounts.
- Chọn target language.
- Chọn standard suite hoặc custom article.
- Bấm run.
- Poll progress.
- Xem lịch sử run.
- Xem bảng xếp hạng:
  - hard score
  - valid rate
  - latency
  - request count
  - token usage
  - manual rating
- Blind output review.
- Ẩn hoặc reveal tên account/model.

### 4. Production Translation Engine

Các thay đổi đã làm:

- `AI_MAX_ATTEMPTS = 1`: cả production và benchmark không HTTP retry.
- Chunk mặc định tăng từ 2.500 lên 5.000 ký tự.
- Chunking ưu tiên:
  1. sentence boundary
  2. punctuation
  3. whitespace
  4. hard cut
- Các phần của cùng một paragraph được merge bằng khoảng trắng thay vì tạo
  paragraph giả.
- Context được giới hạn:
  - 400 ký tự cuối của source chunk trước.
  - 400 ký tự cuối của translation chunk trước.
- `translation_chunk_size` và `translation_context_chars` có thể cấu hình trên
  AI account.
- Prompt dịch đã được rút gọn.
- Output được validate một lần, không retry.
- Output invalid ném `TranslationOutputError`, do đó crawl job fail trước khi
  publish.

Validation production hiện kiểm tra:

- Empty output.
- Refusal/policy text.
- Paragraph count thay đổi.
- Output ngắn dưới 35% source với source đủ dài.

## Quyết Định Quan Trọng

### Không Dùng Agent Framework

Luồng hiện tại vẫn là deterministic prompt chaining:

```text
extract -> chunk -> translate sequentially -> validate -> merge -> publish
```

Không thêm LangChain/LangGraph vì model không cần tự chọn tool hoặc tự quyết
định luồng.

### Không Retry

Yêu cầu sản phẩm là một lần gọi duy nhất:

- Không semantic retry.
- Không critic/revision loop.
- Không HTTP retry.
- Output lỗi phải fail rõ ràng.

### Blind Review

Tên model bị ẩn mặc định để giảm bias. Người dùng nên chấm output trước, sau đó
mới reveal model.

## Verification Gần Nhất

Đã chạy thành công:

```text
PYTHONPATH=. pytest -q
102 passed, 3 skipped
```

Frontend:

```text
pnpm run build
pnpm run lint
```

Cả build và lint đều thành công.

TypeScript:

```text
frontend/node_modules/.bin/tsc --noEmit -p frontend/tsconfig.json
```

Thành công.

Lưu ý: shell login từng có lúc chọn Node 16 và làm pnpm không chạy. Chạy command
với môi trường Node hiện tại hoặc `login=false`; Node đã dùng thành công là
`v24.13.0`.

## Cách Chạy Thử Thủ Công

1. Tạo ít nhất 2 AI accounts, mỗi account dùng model hoặc provider khác nhau.
2. Chạy backend/frontend như quy trình dev hiện tại.
3. Mở `Benchmarks`.
4. Chọn model.
5. Chọn ngôn ngữ.
6. Chạy standard suite trước.
7. Chấm output blind.
8. Reveal model và so sánh latency/token.

Không nên dùng production API key đắt tiền trước khi xác nhận standard suite
với model rẻ.

## Giới Hạn Và Việc Còn Lại

### Ưu Tiên Cao

1. Chạy benchmark thật với ít nhất 2 model để xác nhận response shape của
   9Router, đặc biệt trường `usage`.
2. Kiểm tra UI trực tiếp trên desktop/mobile.
3. Mở rộng standard corpus từ 3 lên khoảng 20-30 case thực tế.
4. Thêm nhiều source language; standard suite hiện chỉ là English source.
5. Quyết định có commit feature hiện tại hay chia thành:
   - commit translation engine
   - commit benchmark backend
   - commit benchmark frontend/docs

### Giới Hạn Kỹ Thuật

- Background task sống trong FastAPI process. Restart server giữa benchmark sẽ
  để run ở trạng thái `running`; chưa có recovery.
- Chưa có cancel benchmark.
- Chưa giới hạn số benchmark chạy đồng thời.
- Kết quả JSON có thể lớn nếu custom article dài hoặc corpus tăng nhiều.
- Chưa có pagination cho benchmark history/results.
- Chưa có export CSV/JSON.
- Chưa có pairwise voting; hiện mới có rating 1-5.
- Chưa tính tiền vì config chưa chứa bảng giá model.
- Hard score có thể false positive/false negative, đặc biệt source leakage.
- Database dùng `create_all`; chưa có migration framework.
- Frontend `dist` được build nhưng thường không tracked. Kiểm tra packaging trước
  khi release.

## Bước Tiếp Theo Đề Xuất

Thứ tự hợp lý cho phiên sau:

1. `git status` và xác nhận vẫn ở `feature/translation-benchmark-ui`.
2. Chạy một benchmark thật với 2 model.
3. Ghi nhận lỗi response/provider nếu có và sửa instrumenting.
4. Kiểm tra trực quan UI.
5. Tăng corpus dựa trên bài crawl thật.
6. Thêm export report hoặc pairwise comparison nếu cần.
7. Commit theo các nhóm thay đổi rõ ràng.

## File Nên Đọc Trước Trong Phiên Sau

Theo thứ tự:

1. `docs/translation-benchmark-handoff.vi.md`
2. `docs/translation-benchmark.md`
3. `application/translation_benchmark_service.py`
4. `frontend/src/pages/TranslationBenchmarks/index.tsx`
5. `adapters/ai/ninerouter.py`
6. `apps/api/routes/benchmarks.py`

