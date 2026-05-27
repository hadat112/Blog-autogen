# MMO Automation Dashboard Design System

Tài liệu này mô tả bản chốt thiết kế giao diện cho một web app automation dành cho MMO, với các luồng chính gồm chạy pipeline từ URL, quản lý account, theo dõi job, và quản lý pipeline publishing lên WordPress/Facebook. Hướng thiết kế phù hợp với mô hình dashboard enterprise: ưu tiên tác vụ, điều hướng rõ ràng, và hiển thị trạng thái vận hành theo module thay vì trình bày kiểu marketing site.[1][2][3]

## 1. Định vị sản phẩm

### 1.1 Loại sản phẩm

- Web app nội bộ / SaaS-style automation tool cho MMO.[4]
- Input chính là URL, sau đó đi qua pipeline xử lý và publish sang các đầu ra như WordPress và Facebook.[2][3]
- Các module cốt lõi gồm dashboard, quick run, pipelines, accounts, jobs/logs, settings.[2][5]

### 1.2 Mục tiêu UX

- Ưu tiên thao tác nhanh, ít bước, scan nhanh trạng thái hệ thống.[1][6]
- Dashboard phải xoay quanh hành động chính thay vì chỉ hiển thị số liệu tổng quan.[7][8]
- Card-based layout phù hợp hơn table-heavy layout khi sản phẩm thiên về workflow và task blocks.[9]

## 2. Art direction

### 2.1 Tính cách giao diện

- Phong cách: enterprise UI.
- Cảm giác: nhanh, dứt khoát, kỹ thuật nhưng sạch.
- Bố cục: thoáng, gọn, ít nhiễu thị giác.
- Điều hướng: sidebar trái, thu gọn thành icon-only khi collapse, mở ra full text khi expand.

### 2.2 Nguyên tắc thị giác

- Nền và surface dùng dải neutral đen–xám làm chủ đạo để giữ độ tin cậy và giảm nhiễu trong môi trường dashboard.[6][10]
- Lime sáng chỉ dùng như accent có kiểm soát cho hành động chính, trạng thái tốt, và các điểm cần hút mắt.[6][11]
- Dark mode và light mode đều phải có đủ contrast riêng; không giả định một cặp màu dùng tốt cho cả hai theme mà không kiểm tra lại.[12][13]

## 3. Typography

Dashboard và giao diện dữ liệu nên ưu tiên sans-serif rõ chữ, x-height tốt và dễ đọc ở cỡ nhỏ.[14][15][16]

### 3.1 Font đề xuất chính

- **Primary font:** Inter
- **Alternative 1:** Geist
- **Alternative 2:** General Sans

### 3.2 Cách dùng font

- Dùng 1 font family chính cho toàn bộ app để giữ enterprise feel nhất quán.[15][16]
- Headings dùng weight 600.
- Body dùng weight 400.
- Label, tab, button dùng 500.
- Số liệu quan trọng dùng 600 và bật `font-variant-numeric: tabular-nums;` ở các vùng metric/job count nếu cần độ thẳng hàng.[1][15]

### 3.3 Type scale

| Vai trò             | Size | Weight | Line-height |
| ------------------- | ---: | -----: | ----------: |
| Display page title  | 30px |    600 |        38px |
| Section heading     | 22px |    600 |        30px |
| Card title          | 18px |    600 |        26px |
| Body                | 15px |    400 |        24px |
| Secondary text      | 14px |    400 |        22px |
| Button / input text | 14px |    500 |        20px |
| Label / badge       | 12px |    500 |        16px |

## 4. Layout foundations

### 4.1 Spacing scale

Dùng hệ 4px, đủ thoáng để card-based UI dễ scan và giữ nhịp enterprise sạch.[1][9]

| Token      | Giá trị |
| ---------- | ------- |
| `space-1`  | 4px     |
| `space-2`  | 8px     |
| `space-3`  | 12px    |
| `space-4`  | 16px    |
| `space-5`  | 20px    |
| `space-6`  | 24px    |
| `space-8`  | 32px    |
| `space-10` | 40px    |
| `space-12` | 48px    |
| `space-16` | 64px    |

### 4.2 Radius

Radius nên ở mức vừa để tránh quá mềm nhưng vẫn giảm cảm giác cứng của dashboard enterprise.[17]

| Token         | Giá trị | Ứng dụng                |
| ------------- | ------- | ----------------------- |
| `radius-sm`   | 8px     | Badge, input nhỏ        |
| `radius-md`   | 10px    | Button, input, tabs     |
| `radius-lg`   | 12px    | Card, modal nhỏ         |
| `radius-xl`   | 16px    | Drawer, modal lớn       |
| `radius-full` | 9999px  | Pill badge, status chip |

### 4.3 Border và shadow

- Border mặc định: 1px, low-contrast, dùng để phân lớp nhẹ thay vì tạo khung cứng.[9][17]
- Shadow rất nhẹ; ưu tiên surface separation hơn shadow nặng.[1]

| Token                  | Giá trị                          |
| ---------------------- | -------------------------------- |
| `border-default-light` | `#D7DEE4`                        |
| `border-strong-light`  | `#C5CDD5`                        |
| `border-default-dark`  | `#2B3238`                        |
| `border-strong-dark`   | `#394149`                        |
| `shadow-sm-light`      | `0 1px 2px rgba(16,24,40,0.04)`  |
| `shadow-md-light`      | `0 6px 18px rgba(16,24,40,0.06)` |
| `shadow-sm-dark`       | `0 1px 2px rgba(0,0,0,0.28)`     |
| `shadow-md-dark`       | `0 10px 24px rgba(0,0,0,0.30)`   |

## 5. Color system

### 5.1 Color philosophy

Dải màu chính là đen–xám–lime. Neutral xử lý nền, text, border, surface; lime dành cho CTA chính, active states, status tốt, và các điểm nhấn hiệu năng.[6][10][11]

### 5.2 Light theme palette

| Token              | Hex       | Dùng cho                          |
| ------------------ | --------- | --------------------------------- |
| `bg`               | `#F5F7F8` | App background                    |
| `bg-subtle`        | `#EEF2F4` | Subtle section background         |
| `surface`          | `#FFFFFF` | Card, panel                       |
| `surface-2`        | `#F9FBFB` | Nested card, soft panel           |
| `surface-hover`    | `#F1F5F6` | Hover state                       |
| `text`             | `#11161A` | Text chính                        |
| `text-muted`       | `#52606D` | Text phụ                          |
| `text-faint`       | `#74808B` | Meta text                         |
| `icon`             | `#34424E` | Icon mặc định                     |
| `primary`          | `#84F72D` | CTA chính / active success accent |
| `primary-hover`    | `#72E01F` | Hover CTA                         |
| `primary-active`   | `#5CC315` | Active CTA                        |
| `primary-contrast` | `#0D1408` | Text/icon trên nền lime           |
| `primary-soft`     | `#EAFCD7` | Soft lime background              |
| `success`          | `#2BA84A` | Thành công ổn định                |
| `warning`          | `#F4A300` | Chờ / pending                     |
| `danger`           | `#E5484D` | Failed / error                    |
| `info`             | `#2F7BF6` | Info / ready                      |
| `divider`          | `#E2E8EE` | Divider                           |
| `focus-ring`       | `#9AF95B` | Focus outline                     |

### 5.3 Dark theme palette

| Token              | Hex       | Dùng cho                  |
| ------------------ | --------- | ------------------------- |
| `bg`               | `#0E1113` | App background            |
| `bg-subtle`        | `#12171A` | Subtle section background |
| `surface`          | `#171C20` | Card, panel               |
| `surface-2`        | `#1C2328` | Nested card               |
| `surface-hover`    | `#222A30` | Hover state               |
| `text`             | `#F3F7F9` | Text chính                |
| `text-muted`       | `#B7C1C9` | Text phụ                  |
| `text-faint`       | `#8A969F` | Meta text                 |
| `icon`             | `#D6DEE5` | Icon mặc định             |
| `primary`          | `#A8FF60` | CTA chính / active accent |
| `primary-hover`    | `#98F94B` | Hover CTA                 |
| `primary-active`   | `#82E632` | Active CTA                |
| `primary-contrast` | `#0D1408` | Text/icon trên nền lime   |
| `primary-soft`     | `#1F2C15` | Soft lime background      |
| `success`          | `#46C96B` | Thành công                |
| `warning`          | `#FFB020` | Chờ / pending             |
| `danger`           | `#FF6369` | Failed / error            |
| `info`             | `#5A9BFF` | Info / ready              |
| `divider`          | `#2A3137` | Divider                   |
| `focus-ring`       | `#B8FF7A` | Focus outline             |

### 5.4 CSS variables gợi ý

```css
:root,
[data-theme="light"] {
  --bg: #f5f7f8;
  --bg-subtle: #eef2f4;
  --surface: #ffffff;
  --surface-2: #f9fbfb;
  --surface-hover: #f1f5f6;
  --text: #11161a;
  --text-muted: #52606d;
  --text-faint: #74808b;
  --icon: #34424e;
  --primary: #84f72d;
  --primary-hover: #72e01f;
  --primary-active: #5cc315;
  --primary-contrast: #0d1408;
  --primary-soft: #eafcd7;
  --success: #2ba84a;
  --warning: #f4a300;
  --danger: #e5484d;
  --info: #2f7bf6;
  --divider: #e2e8ee;
  --focus-ring: #9af95b;
}

[data-theme="dark"] {
  --bg: #0e1113;
  --bg-subtle: #12171a;
  --surface: #171c20;
  --surface-2: #1c2328;
  --surface-hover: #222a30;
  --text: #f3f7f9;
  --text-muted: #b7c1c9;
  --text-faint: #8a969f;
  --icon: #d6dee5;
  --primary: #a8ff60;
  --primary-hover: #98f94b;
  --primary-active: #82e632;
  --primary-contrast: #0d1408;
  --primary-soft: #1f2c15;
  --success: #46c96b;
  --warning: #ffb020;
  --danger: #ff6369;
  --info: #5a9bff;
  --divider: #2a3137;
  --focus-ring: #b8ff7a;
}
```

## 6. Information architecture

Một automation dashboard nên nhóm thông tin theo nhiệm vụ và trạng thái vận hành, không nên trộn action pages với quản trị tài nguyên trong cùng một màn hình.[1][2][3]

### 6.1 Sidebar structure

- Dashboard
- Quick Run
- Pipelines
- Accounts
- Jobs / Logs
- Settings

### 6.2 Vai trò từng trang

| Trang       | Vai trò chính                         |
| ----------- | ------------------------------------- |
| Dashboard   | Tổng quan nhanh + shortcut hành động  |
| Quick Run   | Nhập URL, chọn pipeline, chạy ngay    |
| Pipelines   | Tạo, sửa, bật/tắt, xem logic xử lý    |
| Accounts    | Quản lý tài khoản publish/integration |
| Jobs / Logs | Theo dõi lịch sử chạy, lỗi, retry     |
| Settings    | Theme, cấu hình mặc định, hệ thống    |

## 7. Dashboard homepage blueprint

Dashboard trang đầu nên đặt hành động chính lên trước, sau đó mới đến monitoring blocks để người dùng vừa có thể chạy việc ngay vừa kiểm soát tình trạng hệ thống.[7][8]

### 7.1 Bố cục đề xuất

- Hàng 1: Quick Run card lớn chiếm ưu tiên cao nhất.[7]
- Hàng 2: Recent Jobs, Active Pipelines, Connected Accounts.[1][3]
- Hàng 3: Failed Jobs / Alerts / Attention Required.

### 7.2 Card blocks nên có

| Card           | Nội dung                                                      |
| -------------- | ------------------------------------------------------------- |
| Quick Run      | URL input, pipeline selector, target output, run button       |
| Stat Card      | Jobs hôm nay, success rate, active accounts, active pipelines |
| Recent Jobs    | 5–10 job gần nhất, status, thời gian, retry                   |
| Attention Card | Lỗi account, pipeline failed, token hết hạn                   |

## 8. Component rules

### 8.1 Button

- Primary button dùng lime nền đặc, text tối để giữ độ sắc nét trên nền sáng.[6]
- Secondary button dùng surface + border.
- Ghost button dùng cho hành động phụ trong card.
- Button height đề xuất: 40px mặc định, 36px compact, 44px prominent.

### 8.2 Input

- Input URL là thành phần quan trọng nhất của Quick Run, nên chiếm chiều ngang lớn và có label rõ ràng.[7][8]
- Placeholder chỉ là ví dụ, không thay label.[1]
- Focus state dùng `focus-ring` và `primary-soft`, không chỉ đổi border.

### 8.3 Card

Card phải nhất quán về spacing, cấu trúc heading/content/action để người dùng scan nhanh toàn dashboard.[9]

Quy chuẩn card:

- Padding: 20–24px.
- Gap nội bộ: 12–16px.
- Title phía trên, action phụ góc phải nếu có.
- Nội dung chia block rõ, tránh nhồi quá nhiều micro-text.[9]

### 8.4 Sidebar

- Expanded: icon + label.
- Collapsed: icon only, vẫn giữ tooltip hoặc title khi hover/focus.
- Mục active dùng soft lime background, không dùng lime full-fill cho cả thanh để tránh quá chói ở dark mode.[10]

### 8.5 Badge / status chip

Badge phù hợp để truyền đạt trạng thái ngắn gọn, nhất quán, một nghĩa trên mỗi thực thể.[18][19][20]

## 9. Status system

### 9.1 Bộ status V1

| Status   | Ý nghĩa             |
| -------- | ------------------- |
| Draft    | Chưa sẵn sàng chạy  |
| Ready    | Có thể chạy         |
| Queued   | Đã vào hàng đợi     |
| Running  | Đang xử lý          |
| Success  | Hoàn tất thành công |
| Failed   | Chạy lỗi            |
| Paused   | Tạm dừng            |
| Disabled | Bị tắt              |

### 9.2 Map màu status

| Status   | Light                 | Dark                  | Style          |
| -------- | --------------------- | --------------------- | -------------- |
| Draft    | `#EEF2F4` + `#52606D` | `#1C2328` + `#B7C1C9` | Neutral soft   |
| Ready    | `#EAF2FF` + `#2F7BF6` | `#16233B` + `#5A9BFF` | Info           |
| Queued   | `#FFF4D6` + `#B87400` | `#33270C` + `#FFB020` | Warning        |
| Running  | `#EAFCD7` + `#5CC315` | `#1F2C15` + `#A8FF60` | Primary active |
| Success  | `#E8F8EC` + `#2BA84A` | `#163221` + `#46C96B` | Success        |
| Failed   | `#FDEBEC` + `#E5484D` | `#351619` + `#FF6369` | Danger         |
| Paused   | `#F1F5F6` + `#52606D` | `#222A30` + `#B7C1C9` | Neutral        |
| Disabled | `#EEF2F4` + `#74808B` | `#1C2328` + `#8A969F` | Faint neutral  |

### 9.3 Quy tắc dùng status

- Mỗi item chỉ có một status chính tại một thời điểm.[18][19]
- Không dùng riêng màu để truyền tải meaning; luôn có label text rõ ràng.[18][20]
- Với lỗi nghiêm trọng, badge đi cùng inline message hoặc log detail, không chỉ badge màu đỏ.[19]

## 10. Quick Run screen

Quick Run là trang quan trọng nhất của app nên phải tối ưu cho tốc độ nhập và ra quyết định.[7][8]

### 10.1 Thành phần bắt buộc

- URL input lớn.
- Pipeline selector.
- Target selector: WordPress / Facebook / cả hai.
- Run button nổi bật.
- Option nâng cao đặt trong accordion hoặc drawer, không bung sẵn nếu không cần.[1][8]

### 10.2 Thứ tự ưu tiên thị giác

1. URL input.
2. Chọn pipeline.
3. Chọn output target.
4. Nút Run.
5. Recent run / latest status.

## 11. Accessibility và theme behavior

Dark/light theme nên mặc định theo system preference rồi cho người dùng đổi thủ công, phù hợp với pattern theme hiện đại.[21][22]

### 11.1 Quy tắc

- Mặc định đọc `prefers-color-scheme`.[12][22]
- Có toggle theme rõ trong header hoặc settings.[23][24]
- Focus ring luôn hiển thị rõ trên cả light và dark.[12]
- Không dùng nền đen tuyệt đối cùng text trắng tinh trên toàn app vì dễ gây mỏi mắt ở dark mode.[13]

## 12. CSS token starter

```css
:root {
  --font-sans: "Inter", "Geist", "Segoe UI", Arial, sans-serif;

  --text-display: 30px;
  --text-h2: 22px;
  --text-h3: 18px;
  --text-body: 15px;
  --text-sm: 14px;
  --text-xs: 12px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;
}
```

## 13. Kết luận triển khai

Bản thiết kế này phù hợp với một web app automation cho MMO theo hướng enterprise, card-first, nhanh và sạch, với quick run làm trung tâm, neutral surfaces làm nền, và lime sáng làm accent vận hành. Cấu trúc này bám các nguyên tắc dashboard UX: action-first, hierarchy rõ, card nhất quán, theme có kiểm soát, và status system ngắn gọn để hỗ trợ vận hành hàng ngày.[1][6][9][7]

## 14. Token naming system

Phần quan trọng của design token không phải chỉ là mã màu, mà là **tên biến thể hiện đúng mục đích sử dụng**. Nhiều hệ design token hiện đại đều tách thành lớp constant/primitive, semantic và contextual hoặc component-level token; semantic token nên được đặt tên theo cách dùng, còn raw color chỉ là lớp nền tham chiếu.[25][26][27]

### 14.1 Cấu trúc đặt tên đề xuất

Dùng 4 tầng tên token:

- **Primitive token**: màu gốc, không dùng trực tiếp trong component, ví dụ `--primitive-lime-400`, `--primitive-neutral-900`.[26][27]
- **Semantic token**: mô tả vai trò UI, ví dụ `--color-bg-surface`, `--color-text-primary`, `--color-border-subtle`.[28][26]
- **State token**: semantic token có trạng thái, ví dụ `--color-bg-accent-hover`, `--color-border-focus`, `--color-text-danger`.[29][30]
- **Component token**: token dành riêng cho component nếu thật sự cần, ví dụ `--button-primary-bg`, `--input-border-focus`, `--badge-success-bg`.[26][30]

### 14.2 Nguyên tắc đặt tên

- Tên đi từ **chung đến riêng** để dễ đọc và dễ tìm, ví dụ `color.text.secondary` là cách nhiều design system lớn mô tả token semantic.[26][27][29]
- Tên nên trả lời được 3 câu hỏi: đây là gì, dùng ở đâu, và mang vai trò gì.[29][30]
- Không đặt semantic token theo tên màu nếu token đó dùng cho mục đích UI; ví dụ ưu tiên `--color-text-primary` hơn `--green-400` khi apply lên text thật.[25][28][31]
- Primitive token là nơi giữ giá trị màu; semantic token là nơi team design/dev nên dùng hàng ngày.[26][27]

### 14.3 Bộ tên biến token nên chốt cho app này

#### Primitive layer

```css
:root {
  --primitive-primary-50: #f7ffe5;
  --primitive-primary-100: #f0ffcc;
  --primitive-primary-200: #e0ff99;
  --primitive-primary-300: #d1ff66;
  --primitive-primary-400: #c2ff33;
  --primitive-primary-500: #b2ff00;
  --primitive-primary-600: #8fcc00;
  --primitive-primary-700: #6b9900;

  --primitive-neutral-0: #ffffff;
  --primitive-neutral-50: #fafafa;
  --primitive-neutral-100: #f4f4f4;
  --primitive-neutral-200: #e4e4e4;
  --primitive-neutral-300: #d4d4d4;
  --primitive-neutral-400: #a1a1a1;
  --primitive-neutral-500: #717171;
  --primitive-neutral-600: #303030;
  --primitive-neutral-700: #272727;
  --primitive-neutral-800: #1b1b1b;
  --primitive-neutral-900: #101010;
  --primitive-neutral-950: #020202;

  --primitive-success-300: #70ffc9;
  --primitive-success-500: #00ff9c;
  --primitive-success-700: #00965c;

  --primitive-danger-300: #ff8b80;
  --primitive-danger-500: #ff3d33;
  --primitive-danger-700: #990800;

  --primitive-warning-300: #ffbd70;
  --primitive-warning-500: #ff920a;
  --primitive-warning-700: #c74307;

  --primitive-info-300: #88ceff;
  --primitive-info-500: #288fff;
  --primitive-info-700: #0a58eb;
}
```

#### Semantic layer

```css
:root {
  --color-bg-canvas: var(--primitive-neutral-50);
  --color-bg-surface: var(--primitive-neutral-0);
  --color-bg-surface-subtle: var(--primitive-neutral-100);
  --color-bg-surface-elevated: var(--primitive-neutral-0);
  --color-bg-inverse: var(--primitive-neutral-950);

  --color-bg-accent: var(--primitive-primary-500);
  --color-bg-accent-subtle: color-mix(
    in srgb,
    var(--primitive-primary-500) 12%,
    transparent
  );
  --color-bg-success-subtle: color-mix(
    in srgb,
    var(--primitive-success-500) 12%,
    transparent
  );
  --color-bg-danger-subtle: color-mix(
    in srgb,
    var(--primitive-danger-500) 12%,
    transparent
  );
  --color-bg-warning-subtle: color-mix(
    in srgb,
    var(--primitive-warning-500) 12%,
    transparent
  );
  --color-bg-info-subtle: color-mix(
    in srgb,
    var(--primitive-info-500) 12%,
    transparent
  );

  --color-text-primary: var(--primitive-neutral-950);
  --color-text-secondary: var(--primitive-neutral-600);
  --color-text-tertiary: var(--primitive-neutral-400);
  --color-text-inverse: var(--primitive-neutral-50);

  --color-text-accent: var(--primitive-primary-700);
  --color-text-success: var(--primitive-success-700);
  --color-text-danger: var(--primitive-danger-700);
  --color-text-warning: var(--primitive-warning-700);
  --color-text-info: var(--primitive-info-700);

  --color-border-subtle: var(--primitive-neutral-200);
  --color-border-default: var(--primitive-neutral-300);
  --color-border-strong: var(--primitive-neutral-400);
  --color-border-inverse: var(--primitive-neutral-800);
  --color-border-accent: var(--primitive-primary-400);
  --color-border-focus: var(--primitive-primary-500);

  --color-icon-primary: var(--color-text-primary);
  --color-icon-secondary: var(--color-text-secondary);
  --color-icon-accent: var(--color-text-accent);

  --color-overlay-scrim: rgba(0, 0, 0, 0.5);
}
```

#### Dark theme semantic remap

```css
[data-theme="dark"] {
  --color-bg-canvas: var(--primitive-neutral-950);
  --color-bg-surface: var(--primitive-neutral-900);
  --color-bg-surface-subtle: var(--primitive-neutral-800);
  --color-bg-surface-elevated: var(--primitive-neutral-800);
  --color-bg-inverse: var(--primitive-neutral-0);

  --color-bg-accent: var(--primitive-primary-400);
  --color-bg-accent-subtle: color-mix(
    in srgb,
    var(--primitive-primary-500) 20%,
    transparent
  );
  --color-bg-success-subtle: color-mix(
    in srgb,
    var(--primitive-success-500) 20%,
    transparent
  );
  --color-bg-danger-subtle: color-mix(
    in srgb,
    var(--primitive-danger-500) 20%,
    transparent
  );
  --color-bg-warning-subtle: color-mix(
    in srgb,
    var(--primitive-warning-500) 20%,
    transparent
  );
  --color-bg-info-subtle: color-mix(
    in srgb,
    var(--primitive-info-500) 20%,
    transparent
  );

  --color-text-primary: var(--primitive-neutral-100);
  --color-text-secondary: var(--primitive-neutral-400);
  --color-text-tertiary: var(--primitive-neutral-500);
  --color-text-inverse: var(--primitive-neutral-950);

  --color-text-accent: var(--primitive-primary-300);
  --color-text-success: var(--primitive-success-300);
  --color-text-danger: var(--primitive-danger-300);
  --color-text-warning: var(--primitive-warning-300);
  --color-text-info: var(--primitive-info-300);

  --color-border-subtle: var(--primitive-neutral-800);
  --color-border-default: var(--primitive-neutral-700);
  --color-border-strong: var(--primitive-neutral-600);
  --color-border-inverse: var(--primitive-neutral-100);
  --color-border-accent: var(--primitive-primary-400);
  --color-border-focus: var(--primitive-primary-400);

  --color-icon-primary: var(--color-text-primary);
  --color-icon-secondary: var(--color-text-secondary);
  --color-icon-accent: var(--color-text-accent);

  --color-overlay-scrim: rgba(0, 0, 0, 0.6);
}
```

### 14.4 Component token layer nên dùng nếu cần

```css
:root {
  --button-primary-bg: var(--color-bg-accent);
  --button-primary-text: var(--color-text-inverse);
  --button-primary-border: var(--color-border-accent);
  --button-primary-bg-hover: var(--primitive-primary-600);

  --button-secondary-bg: var(--color-bg-surface);
  --button-secondary-text: var(--color-text-primary);
  --button-secondary-border: var(--color-border-default);

  --input-bg: var(--color-bg-surface);
  --input-text: var(--color-text-primary);
  --input-placeholder: var(--color-text-tertiary);
  --input-border: var(--color-border-default);
  --input-border-focus: var(--color-border-focus);

  --card-bg: var(--color-bg-surface);
  --card-bg-subtle: var(--color-bg-surface-subtle);
  --card-border: var(--color-border-subtle);
  --card-title: var(--color-text-primary);
  --card-description: var(--color-text-secondary);

  --badge-success-bg: var(--color-bg-success-subtle);
  --badge-success-text: var(--color-text-success);
  --badge-danger-bg: var(--color-bg-danger-subtle);
  --badge-danger-text: var(--color-text-danger);
  --badge-warning-bg: var(--color-bg-warning-subtle);
  --badge-warning-text: var(--color-text-warning);
  --badge-info-bg: var(--color-bg-info-subtle);
  --badge-info-text: var(--color-text-info);
}
```

### 14.5 Bộ tên tối thiểu nên dùng ngay

Nếu muốn gọn và practical, app này chỉ cần chốt nhóm tên biến sau là đủ dùng cho đa số màn hình:[27][29][30]

- `--color-bg-canvas`
- `--color-bg-surface`
- `--color-bg-surface-subtle`
- `--color-bg-accent`
- `--color-text-primary`
- `--color-text-secondary`
- `--color-text-tertiary`
- `--color-text-inverse`
- `--color-border-subtle`
- `--color-border-default`
- `--color-border-focus`
- `--color-text-success`
- `--color-text-danger`
- `--color-text-warning`
- `--color-text-info`
- `--button-primary-bg`
- `--button-primary-text`
- `--input-border`
- `--input-border-focus`
- `--card-bg`
- `--card-border`

### 14.6 Kết luận dùng token

Nếu mục tiêu là làm app dễ scale và dev dễ dùng, hãy để team dùng **semantic tokens** và chỉ giữ primitive ở tầng nền. Đây là cách naming dễ hiểu nhất vì tên token mô tả vai trò của nó trong UI thay vì bắt mọi người nhớ từng mã màu hay shade cụ thể.[25][26][27]
