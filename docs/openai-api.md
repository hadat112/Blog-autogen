# OpenAI Responses API với Python — Ghi chú & code mẫu

> Tổng hợp theo khoá học: Responses API → Web search → Function calling → Structured outputs → Streaming → Multimodal.

## Chuẩn bị

```bash
pip install openai pydantic
export OPENAI_API_KEY="sk-..."      # Windows PowerShell: $env:OPENAI_API_KEY="sk-..."
```

```python
from openai import OpenAI

client = OpenAI()   # tự đọc OPENAI_API_KEY từ env
```

---

## Chương 1 — Responses API cơ bản

### Request đầu tiên

```python
resp = client.responses.create(
    model="gpt-5",
    instructions="Bạn là trợ lý trả lời ngắn gọn, bằng tiếng Việt.",  # ~ system prompt
    input="Giải thích WebRTC ICE candidate trong 3 câu.",
)

print(resp.output_text)   # shortcut lấy toàn bộ text
print(resp.id)            # dùng cho multi-turn ở dưới
```

### Chỉnh reasoning / token / model để cân chi phí – chất lượng – độ trễ

```python
resp = client.responses.create(
    model="gpt-5",
    input="Tính xem 37 * 48 rồi giải thích cách nhẩm.",
    reasoning={"effort": "low"},      # "minimal" | "low" | "medium" | "high"
    text={"verbosity": "low"},        # độ dài câu trả lời
    max_output_tokens=300,            # trần token đầu ra (gồm cả reasoning token)
)

print(resp.output_text)
print(resp.usage.input_tokens, resp.usage.output_tokens, resp.usage.total_tokens)
print(resp.usage.output_tokens_details.reasoning_tokens)  # token "suy nghĩ" ẩn

# Coi chừng: nếu max_output_tokens bị đụng trần, status = "incomplete"
if resp.status == "incomplete":
    print("Bị cắt:", resp.incomplete_details.reason)
```

**Quy tắc chọn:** latency thấp + rẻ → model nhỏ (`gpt-5-mini`, `gpt-5-nano`) + `effort="minimal"`.
Bài toán suy luận nhiều bước → model lớn + `effort="high"`.

### Hội thoại nhiều lượt

Cách 1 — để server nhớ giúp (`previous_response_id`):

```python
r1 = client.responses.create(model="gpt-5", input="Thủ đô Việt Nam là gì?")
r2 = client.responses.create(
    model="gpt-5",
    input="Dân số ở đó khoảng bao nhiêu?",   # "đó" = Hà Nội, model vẫn hiểu
    previous_response_id=r1.id,
)
print(r2.output_text)
```

Cách 2 — tự giữ lịch sử (kiểm soát được, khỏi phụ thuộc `store=True`):

```python
messages = [{"role": "user", "content": "Thủ đô Việt Nam là gì?"}]

r1 = client.responses.create(model="gpt-5", input=messages, store=False)
messages += r1.output          # nối nguyên các item output vào lịch sử
messages.append({"role": "user", "content": "Dân số ở đó khoảng bao nhiêu?"})

r2 = client.responses.create(model="gpt-5", input=messages, store=False)
print(r2.output_text)
```

---

## Chương 2 — Web search (tool có sẵn, không cần API key riêng)

```python
resp = client.responses.create(
    model="gpt-5",
    input="Tuần này có tin gì mới về chuẩn WebRTC?",
    tools=[{"type": "web_search"}],
)

print(resp.output_text)

# Trích nguồn (citations) đính kèm trong annotations
for item in resp.output:
    if item.type == "message":
        for content in item.content:
            for ann in getattr(content, "annotations", []) or []:
                if ann.type == "url_citation":
                    print("-", ann.title, "→", ann.url)
```

Ép model **luôn** tìm web thay vì tự quyết:

```python
resp = client.responses.create(
    model="gpt-5",
    input="Giá cổ phiếu AAPL hôm nay?",
    tools=[{"type": "web_search"}],
    tool_choice={"type": "web_search"},   # bắt buộc gọi tool
)
```

> Tuỳ phiên bản SDK/model, tên tool có thể là `"web_search_preview"`. Nếu báo lỗi unknown tool thì đổi sang tên đó.

---

## Chương 2 — Function calling: biến hàm Python thành tool (5 bước)

```python
import json
from openai import OpenAI

client = OpenAI()

# ---- BƯỚC 1: viết hàm thật + mô tả schema cho model ----
def get_weather(city: str, unit: str = "celsius") -> str:
    fake_db = {"Hanoi": 31, "Tokyo": 24}
    temp = fake_db.get(city, 20)
    if unit == "fahrenheit":
        temp = temp * 9 / 5 + 32
    return json.dumps({"city": city, "temp": temp, "unit": unit})

tools = [{
    "type": "function",
    "name": "get_weather",                       # LƯU Ý: Responses API để phẳng,
    "description": "Lấy nhiệt độ hiện tại của một thành phố.",  # không bọc trong {"function": {...}}
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "Tên thành phố, vd 'Hanoi'"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["city", "unit"],
        "additionalProperties": False,
    },
    "strict": True,     # ép model sinh đúng schema
}]

TOOL_REGISTRY = {"get_weather": get_weather}

# ---- BƯỚC 2: gửi request kèm tools, để model tự chọn ----
messages = [{"role": "user", "content": "Hà Nội hôm nay nóng bao nhiêu độ F?"}]
resp = client.responses.create(model="gpt-5", input=messages, tools=tools)

# ---- BƯỚC 3 + 4: đọc lời gọi tool, thực thi bằng đúng arguments model chọn ----
messages += resp.output          # phải giữ lại item function_call trong lịch sử

called = False
for item in resp.output:
    if item.type == "function_call":
        called = True
        args = json.loads(item.arguments)
        result = TOOL_REGISTRY[item.name](**args)

        # ---- BƯỚC 5: trả output về cho model ----
        messages.append({
            "type": "function_call_output",
            "call_id": item.call_id,      # phải khớp call_id, không phải id
            "output": result,             # luôn là string
        })

# ---- Gọi lần 2 để model dùng kết quả tool trả lời câu hỏi gốc ----
if called:
    final = client.responses.create(model="gpt-5", input=messages, tools=tools)
    print(final.output_text)
else:
    print(resp.output_text)
```

### Vòng lặp tổng quát (model có thể gọi tool nhiều vòng)

```python
def run_agent(user_msg: str, tools, registry, model="gpt-5", max_turns=5):
    messages = [{"role": "user", "content": user_msg}]
    for _ in range(max_turns):
        resp = client.responses.create(model=model, input=messages, tools=tools)
        messages += resp.output

        calls = [i for i in resp.output if i.type == "function_call"]
        if not calls:
            return resp.output_text

        for call in calls:
            out = registry[call.name](**json.loads(call.arguments))
            messages.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": out if isinstance(out, str) else json.dumps(out),
            })
    raise RuntimeError("Vượt quá số vòng tool cho phép")
```

---

## Chương 3 — Structured outputs với Pydantic

```python
from pydantic import BaseModel, Field
from typing import Literal

class Ticket(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"]
    tags: list[str]
    estimate_hours: float = Field(description="Ước lượng số giờ làm")

resp = client.responses.parse(          # parse, không phải create
    model="gpt-5",
    input="Khách báo: gọi video bị đen màn hình trên Safari, gấp, ảnh hưởng demo chiều nay.",
    text_format=Ticket,
)

ticket = resp.output_parsed             # đã là object Ticket, không phải string
print(ticket.priority, ticket.estimate_hours, ticket.tags)
print(type(ticket))                     # <class '__main__.Ticket'>
```

### Lồng model + danh sách

```python
class Entity(BaseModel):
    name: str
    type: Literal["person", "org", "product"]

class Extraction(BaseModel):
    summary: str
    entities: list[Entity]

resp = client.responses.parse(
    model="gpt-5",
    input="OpenAI ra mắt Responses API, Sam Altman công bố tại DevDay.",
    text_format=Extraction,
)
for e in resp.output_parsed.entities:
    print(e.type, "→", e.name)
```

Cẩn thận: model có thể từ chối. Kiểm tra trước khi dùng:

```python
if resp.output_parsed is None:
    print("Model từ chối hoặc output bị cắt:", resp.status)
```

---

## Chương 3 — Streaming + semantic events

### Cách đơn giản nhất — in từng chunk

```python
stream = client.responses.create(
    model="gpt-5",
    input="Viết đoạn giới thiệu 100 từ về WebRTC.",
    stream=True,
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
print()
```

### Semantic events — gắn logic riêng theo từng loại sự kiện

```python
with client.responses.stream(
    model="gpt-5",
    input="Tin mới nhất về WebRTC là gì?",
    tools=[{"type": "web_search"}],
) as stream:
    for event in stream:
        match event.type:
            case "response.created":
                print("[UI] Đang suy nghĩ...")
            case "response.web_search_call.in_progress":
                print("\n[UI] Đang tìm trên web...")
            case "response.web_search_call.completed":
                print("[UI] Tìm xong, đang tổng hợp")
            case "response.output_text.delta":
                print(event.delta, end="", flush=True)
            case "response.output_text.done":
                print("\n[UI] Xong đoạn text")
            case "response.completed":
                print("\n[UI] Hoàn tất")
            case "error":
                print("\n[UI] Lỗi:", event.error)

    final = stream.get_final_response()   # object đầy đủ như khi không stream
    print("Tokens:", final.usage.total_tokens)
```

### Stream + structured output (vừa chảy chữ vừa ra object cuối)

```python
with client.responses.stream(
    model="gpt-5",
    input="Khách báo lag khi share screen, không gấp lắm.",
    text_format=Ticket,
) as stream:
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
    ticket = stream.get_final_response().output_parsed

print("\n→", ticket.priority)
```

---

## Chương 3 — Multimodal (ảnh + text)

### Hỏi về ảnh qua URL

```python
resp = client.responses.create(
    model="gpt-5",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Biểu đồ này cho thấy xu hướng gì? Nêu 2 điểm đáng chú ý."},
            {"type": "input_image",
             "image_url": "https://example.com/aapl-stock.png",
             "detail": "high"},   # "low" rẻ & nhanh hơn, "high" nhìn được chi tiết nhỏ
        ],
    }],
)
print(resp.output_text)
```

### Ảnh local → base64 data URL

```python
import base64, mimetypes
from pathlib import Path

def to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:{mime};base64,{b64}"

resp = client.responses.create(
    model="gpt-5",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Trong ảnh có bao nhiêu người?"},
            {"type": "input_image", "image_url": to_data_url("photo.jpg")},
        ],
    }],
)
print(resp.output_text)
```

### Phân loại ảnh — kết hợp multimodal + structured output

```python
class ImageLabel(BaseModel):
    category: Literal["chart", "screenshot", "photo", "diagram", "other"]
    confidence: float
    reason: str

def classify(image_path: str) -> ImageLabel:
    resp = client.responses.parse(
        model="gpt-5",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Phân loại ảnh này."},
                {"type": "input_image", "image_url": to_data_url(image_path)},
            ],
        }],
        text_format=ImageLabel,
    )
    return resp.output_parsed

label = classify("aapl.png")
print(label.category, label.confidence, label.reason)
```

---

## Những chỗ dễ vấp

| Vấn đề | Cách xử lý |
|---|---|
| Lỗi 400 khó đoán khi trả kết quả tool | `function_call_output` phải dùng `call_id`, **không** phải `item.id` |
| Tool schema báo invalid | Responses API để **phẳng** (`{"type":"function","name":...}`), khác Chat Completions (bọc trong `"function"`) |
| `strict: True` báo lỗi schema | Mọi field phải nằm trong `required` và có `additionalProperties: False` |
| Response rỗng, `status="incomplete"` | `max_output_tokens` tính cả reasoning token — đặt quá thấp với `effort="high"` sẽ hết token trước khi ra chữ |
| `unknown tool: web_search` | Đổi sang `"web_search_preview"` tuỳ phiên bản SDK |
| `output_parsed` là `None` | Model từ chối hoặc output bị cắt — luôn kiểm tra trước khi dùng |

 Trước hết một điểm ảnh hưởng cả 3 bài: **`gpt-5` (và o-series) không nhận `temperature`** — truyền vào là lỗi 400. Muốn chỉnh temperature thì phải dùng model non-reasoning (`gpt-4.1`, `gpt-4.1-mini`). Với gpt-5, hai núm thay thế là `reasoning.effort` và `text.verbosity`.

---

## Bài 1 — Dịch story 3000–7000 words

**Dùng:**

| Mục | Vì sao |
|---|---|
| Ch1: `instructions` + `input` | Glossary/quy tắc dịch nhét vào `instructions`, văn bản vào `input` — tách ra để phần cố định được cache, rẻ hơn |
| Ch1: `max_output_tokens` cao (≥ 16000) | Dịch ra tiếng Việt token nở ~1.5–2x so với tiếng Anh. Đây là chỗ chết người nhất: đặt thấp → cụt giữa chừng, `status="incomplete"` |
| Ch1: `reasoning={"effort": "minimal"}` | Dịch không phải bài toán suy luận. Effort cao chỉ đốt tiền và làm chậm, không làm bản dịch hay hơn |
| Ch3: Streaming | Output 10k+ token mất vài phút/chunk — không stream dễ timeout và không biết nó đang chạy hay treo |
| Ch3: Structured output | **Chỉ dùng cho bước tạo glossary** (tên riêng, cách xưng hô, thuật ngữ) chạy 1 lần trước khi dịch |

**Không dùng:** web search, function calling, multimodal. Và **đừng bọc bản dịch vào structured output** — text dài phải escape JSON, dễ vỡ và tốn token vô ích.

**Chunk hay gửi full:** chunk. Nhưng lý do không phải context window (7000 words ≈ 10k token input, thừa sức chứa) mà là **output**: bắt model sinh 10k+ token một lượt thì nó sẽ tóm tắt lược bớt đoạn giữa — đó chính là cái bạn gọi là "halu". Chia ~800–1200 words theo ranh giới tự nhiên (hết scene, hết đoạn hội thoại), không cắt giữa câu.

**Nhưng đừng dùng kiểu "hội thoại nhiều lượt"** cho việc này. `previous_response_id` sẽ tích luỹ toàn bộ bản gốc + bản dịch qua từng chunk → chi phí tăng bậc hai, và context càng dài model càng trôi giọng. Thay vào đó mỗi chunk là request độc lập, kèm đúng 3 thứ:

```python
instructions = f"""Dịch sang tiếng Việt. Giữ nguyên xuống dòng và dấu hội thoại.
GLOSSARY (bắt buộc dùng đúng): {glossary}
TÓM TẮT PHẦN TRƯỚC: {summary_so_far}
2 CÂU CUỐI CỦA BẢN DỊCH TRƯỚC (để nối giọng, đừng dịch lại): {tail}
Chỉ xuất bản dịch, không thêm lời nào khác."""
```

Context cố định ~300 token thay vì phình lên 20k. Temperature (nếu dùng gpt-4.1): **0.2–0.3** — dịch cần bám sát, không cần sáng tạo.

---

## Bài 2 — Rewrite đoạn đầu + viết tiếp

**Dùng:**

| Mục | Vì sao |
|---|---|
| Ch1: Hội thoại nhiều lượt — `previous_response_id` | **Đây mới là chỗ đúng để dùng nó.** Bước 2 cần nguyên văn bản rewrite ở bước 1; nối bằng `previous_response_id` thì khỏi copy-paste và model tự nhớ nó đã viết gì |
| Ch3: Structured output | Chèn 1 bước trung gian: trích "bộ xương" (nhân vật, bối cảnh, motive, các beat) → rồi rewrite **từ bộ xương**, không phải từ bản gốc. Đây là cách hiệu quả nhất để tránh ra bản giống hệt chỉ đổi từ đồng nghĩa |
| Ch1: `reasoning={"effort": "medium"}` cho bước rewrite | Rewrite mà không được giống bản gốc là bài toán có ràng buộc — cần model cân nhắc |
| Ch3: Streaming cho bước viết tiếp | Phần viết thêm thường dài, cần feedback sớm |

**Không dùng:** web search, function calling, multimodal.

Khung:

```python
# B1: trích skeleton (structured) — ép rewrite khác thật sự
skel = client.responses.parse(model="gpt-5", input=original, text_format=StorySkeleton)

# B2: rewrite từ skeleton + chỉ thị đổi trục (đổi setting/POV/nghề nhân vật)
r1 = client.responses.create(model="gpt-5", input=rewrite_prompt(skel.output_parsed),
                             reasoning={"effort": "medium"})

# B3: viết tiếp — nối vào r1, model đã có nguyên văn bản rewrite
r2 = client.responses.create(model="gpt-5", input=your_existing_prompt,
                             previous_response_id=r1.id, stream=True)
```

Temperature (gpt-4.1): **0.8–1.0**. Đây là bài duy nhất trong 3 bài cần temperature cao.

---

## Bài 3 — Random story từ DB → viết mới theo chủ đề/độ gay cấn/plot twist

**Dùng:**

| Mục | Vì sao |
|---|---|
| Ch3: Structured output | Hai chỗ: (a) chuẩn hoá phân tích khi ingest story vào DB — đảm bảo mọi bản ghi cùng schema; (b) sinh **outline/beat sheet** trước khi viết prose. Bước (b) là chỗ bạn kiểm soát được "độ gay cấn" và "plot twist" — chúng thành field có thể validate, không phải lời khấn trong prompt |
| Ch1: Hội thoại nhiều lượt | outline → prose qua `previous_response_id`, model bám đúng outline nó vừa duyệt |
| Ch1: `effort="high"` cho outline, `"low"` cho prose | Nghĩ cốt truyện cần suy luận; viết chữ từ outline có sẵn thì không |
| Ch3: Streaming cho prose | Output dài |

**Function calling — chỉ dùng nếu**: bạn muốn model tự quyết lấy thêm dữ liệu (kiểu "cho tôi 3 story cùng theme để tham khảo motif"). Còn nếu **random là do code bạn quyết** thì bỏ hẳn function calling đi — cứ SELECT rồi nhét thẳng record vào prompt. Rẻ hơn, nhanh hơn 1 round-trip, và deterministic (random do code kiểm soát được, do model thì không).

**Không dùng:** web search, multimodal.

```python
class Outline(BaseModel):
    theme: str
    logline: str
    tension_curve: list[int]        # độ gay cấn từng beat, 1-10 — validate được
    beats: list[Beat]
    twist: str
    twist_setup_beats: list[int]    # ép model cài cắm trước, không twist từ trên trời rơi

seed = db.random_story()            # random bằng code, không phải bằng model
o = client.responses.parse(model="gpt-5", input=prompt(seed),
                           text_format=Outline, reasoning={"effort": "high"})

# validate ở Python trước khi viết prose
assert max(o.output_parsed.tension_curve) >= 8
assert o.output_parsed.twist_setup_beats, "twist chưa được cài cắm"

prose = client.responses.create(model="gpt-5", input="Viết full prose theo outline trên.",
                                previous_response_id=o.id, reasoning={"effort": "low"},
                                max_output_tokens=16000, stream=True)
```

Temperature (gpt-4.1): **0.9–1.0 cho outline**, **0.7 cho prose** — cốt truyện cần lạ, câu chữ cần ổn định.

---

**Tóm lại:**

| | Bài 1 | Bài 2 | Bài 3 |
|---|---|---|---|
| Multi-turn (`previous_response_id`) | ❌ (dùng context thủ công) | ✅ | ✅ |
| Web search | ❌ | ❌ | ❌ |
| Function calling | ❌ | ❌ | ⚠️ chỉ khi model tự query DB |
| Structured output | ⚠️ chỉ cho glossary | ✅ skeleton | ✅ ingest + outline |
| Streaming | ✅ | ✅ | ✅ |
| Multimodal | ❌ | ❌ | ❌ |
| `effort` | minimal | medium | high → low |
| temperature (nếu gpt-4.1) | 0.2–0.3 | 0.8–1.0 | 0.9 → 0.7 |

Điểm chung cả 3: `max_output_tokens` phải đặt rộng tay, vì cả 3 đều sinh text dài và đây là nguyên nhân số 1 gây cụt output.