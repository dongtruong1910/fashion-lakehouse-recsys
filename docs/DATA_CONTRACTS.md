# ĐẶC TẢ HỢP ĐỒNG DỮ LIỆU & GIAO DIỆN (DATA & API CONTRACTS)

> **Mục đích:** Đây là "Bản hợp đồng kỹ thuật" giữa các Sub-Agents (`Data-Agent`, `CV-Agent`, `RecSys-Agent`, `Serving-Agent`).  
> **Quy tắc bắt buộc:** Mọi Sub-Agent phải đặt tên cột, kiểu dữ liệu, khóa Redis, tên collection Qdrant và schema JSON khớp **100%** với tài liệu này và file [`src/contracts/schemas.py`](../src/contracts/schemas.py).

---

## 1. Quy ước Định danh Cốt lõi (Core ID Conventions)

| Tên trường | Kiểu dữ liệu | Định dạng bắt buộc | Ví dụ hợp lệ | Ví dụ SAI (Cấm!) |
| :--- | :--- | :--- | :--- | :--- |
| **`article_id`** | `string` (`UTF-8`) | Chuỗi đúng **10 chữ số**, có pad số `'0'` ở đầu | `"0108775015"` | `108775015` (int) hoặc `"108775015"` (9 ký tự) |
| **`product_code`** | `string` (`UTF-8`) | Chuỗi **7 chữ số đầu** của `article_id` | `"0108775"` | `108775` (int) |
| **`customer_id`** | `string` (`UTF-8`) | Chuỗi hex 64 ký tự gốc của H&M (chỉ dùng ở tầng Bronze, API đầu vào và khóa Redis) | `"000058a12d5b..."` | — |
| **`customer_idx`** | `int32` | Số nguyên liên tục từ `0` đến `1.371.979` (dùng trong mọi bảng Silver, Gold, ALS, LightGBM, Two-Tower) | `42105` | Dùng chuỗi hex 64 ký tự khi join bảng lớn |
| **`week_num`** | `int16` | Số thứ tự tuần neo từ Thứ Tư `2018-09-19` (`floor((t_dat - 2018-09-19) / 7)`). **Dev Week `2020-09-09` $\rightarrow$ `2020-09-15` có `week_num = 103`**; **Final Test Holdout Week `2020-09-16` $\rightarrow$ `2020-09-22` có `week_num = 104`** | `103`, `104` | Lệch ngày `2020-09-16` sang tuần 103 |

---

## 2. Schema các Bảng Delta Lake / Parquet (`data/lakehouse/`)

*(Khi chạy `--smoke-test`, toàn bộ bảng dưới đây được ghi tách biệt sang `data/lakehouse_smoke/` để bảo vệ dữ liệu chính).*

### 2.1. Tầng Silver (`data/lakehouse/silver/`)

#### Bảng 1: `silver/articles`
* `article_id`: `string` (Primary Key, 10 ký tự chữ số dương, kiểm tra hợp lệ trước khi pad)
* `product_code`: `string` (7 ký tự đầu của `article_id`)
* `prod_name`: `string`
* `product_type_no`: `int32`
* `product_type_name`: `string`
* `product_group_name`: `string`
* `graphical_appearance_no`: `int32`
* `graphical_appearance_name`: `string`
* `colour_group_code`: `int32`
* `colour_group_name`: `string`
* `perceived_colour_value_name`: `string`
* `index_group_no`: `int32`
* `index_group_name`: `string`
* `section_no`: `int32`
* `garment_group_no`: `int32`
* `garment_group_name`: `string`
* `detail_desc`: `string` (đã điền `""` nếu null)
* `detector_class`: `string` (1 trong 12 lớp chuẩn ánh xạ từ `configs/class_mapping.yaml` hoặc `"other"`)
* `image_rel_path`: `string` (ví dụ: `"010/0108775015.jpg"`)

#### Bảng 2: `silver/customers` & `silver/customer_mapping`
* `customer_idx`: `int32` (Primary Key nội bộ)
* `customer_id`: `string` (64-char hex gốc)
* `mapping_version`: `string` (`"v1_full"` hoặc `"v1_smoke"` để tránh trộn lẫn dense index giữa các bản chạy)
* `age`: `int16` (đã điền median = `32` nếu thiếu + thêm cờ `age_is_null`: `int8`)
* `age_bucket`: `string` (`"16-22"`, `"23-30"`, `"31-45"`, `"46+"`)
* `club_member_status`: `string` (`"ACTIVE"`, `"PRE-CREATE"`, `"LEFT CLUB"`, `"UNKNOWN"`)
* `fashion_news_frequency`: `string` (`"Regularly"`, `"Monthly"`, `"NONE"`)
* `active_flag`: `int8` (`1` hoặc `0`)

#### Bảng 3: `silver/transactions` *(Partitioned by `week_num`)*
* `t_dat`: `date` (`YYYY-MM-DD`)
* `week_num`: `int16` (`0` $\rightarrow$ `104`, neo tại `2018-09-19`)
* `customer_idx`: `int32`
* `article_id`: `string` (10 ký tự)
* `price`: `float32`
* `sales_channel_id`: `int8` (`1` = Store, `2` = Online)

---

### 2.2. Tầng Gold (`data/lakehouse/gold/`)

#### Bảng 4: `gold/candidate_features` *(Dùng cho LightGBM LambdaRank)*
Chỉ sinh cho các `customer_idx` thuộc nhóm **Active Users** (có phát sinh giao dịch mua hàng trong tuần nhãn `target_week`), và mọi đặc trưng của `target_week` chỉ dùng lịch sử có `t_dat < week_start(target_week)`:
* **Khóa, Query Group & Nhãn:**
  * `target_week`: `int16` (`100`, `101`, `102` cho Train; `103` cho Dev/Model Selection; `104` cho Final Test Holdout)
  * `customer_idx`: `int32` — **Query Group ID cho LambdaRank là cặp `(target_week, customer_idx)`**; khóa duy nhất của mỗi dòng là `(target_week, customer_idx, article_id)`.
  * `article_id`: `string` (10 ký tự)
  * `label`: `int8` (`1` nếu khách mua `article_id` trong `target_week`, ngược lại `0`)
* **Đặc trưng Nguồn Ứng Viên (Candidate Source Signals):**
  * `src_repurchase_rank`, `src_cooc_rank`, `src_age_pop_rank`, `src_als_rank`, `src_twotower_rank`: `int16` (mặc định `999` nếu không xuất hiện ở nguồn đó)
  * `src_count`: `int8` (số nguồn cùng gợi ý sản phẩm này, từ `1` đến `5`)
  * `als_score`: `float32`
  * `tt_score`: `float32` (điểm dot-product từ mạng Two-Tower)
* **Đặc trưng Thị giác từ CV (Visual Feature):**
  * `visual_affinity_score`: `float32` — $\cos(\mathbf{v}_{\text{item}}, \overline{\mathbf{v}}_{\text{user\_recent\_5}})$ tính theo batch tại `src/recsys/features_gpu.py`.
* **Đặc trưng Tương tác & Lịch sử (User $\times$ Item & Historical Features):**
  * `user_item_purchase_cnt`: `int16` (số lần khách đã mua chính sản phẩm này trước `target_week`)
  * `days_since_last_buy_item`: `int16` (mặc định `999` nếu chưa từng mua)
  * `user_ptype_affinity`: `float32` (tỉ lệ lịch sử của khách thuộc cùng `product_type_no`)
  * `user_colour_affinity`: `float32` (tỉ lệ lịch sử của khách thuộc cùng `colour_group_code`)
  * `price_diff_user_avg`: `float32` (`item_price - user_avg_price`)
  * `item_sales_1w`, `item_sales_4w`: `int32`
  * `item_trend_ratio`: `float32` (`item_sales_1w / (item_sales_4w / 4.0 + 1.0)`)
  * `user_age`: `int16`
  * `user_total_tx_4w`: `int16`
  * `user_online_ratio`: `float32`
  * `product_type_no`, `colour_group_code`, `index_group_no`, `garment_group_no`: `int32` (Categorical features cho LightGBM)

---

## 3. Cấu trúc Qdrant Vector Database

* **Tên Collection:** `hm_products` (Khi khởi tạo hoặc kết nối lại, `ensure_collection()` bắt buộc kiểm tra khớp kích thước `visual_emb.size`, `two_tower_emb.size` và `encoder_model_id`).
* **Point ID:** `int(article_id)` (ví dụ `"0108775015"` $\rightarrow$ `108775015` làm Point ID số nguyên của Qdrant, đồng thời giữ chuỗi `"0108775015"` trong `payload.article_id`).
* **Named Vectors:**
  ```json
  {
    "visual_emb": {
      "size": 768,
      "distance": "Cosine"
    },
    "two_tower_emb": {
      "size": 64,
      "distance": "Dot"
    }
  }
  ```
  *(Lưu ý: `visual_emb.size` là `768` với `SigLIP-2 Base` / `FashionSigLIP` hoặc `512` với `CLIP ViT-B/32` / `FashionCLIP`, cấu hình trong `configs/model_config.yaml`).*
* **Payload Schema (Có đánh chỉ mục Keyword/Float Index):**
  ```json
  {
    "article_id": "0108775015",
    "product_code": "0108775",
    "prod_name": "Strap top",
    "detector_class": "top",
    "product_type_name": "Vest top",
    "product_group_name": "Garment Upper body",
    "colour_group_name": "Black",
    "graphical_appearance_name": "Solid",
    "index_group_name": "Ladieswear",
    "price": 0.0169,
    "image_rel_path": "010/0108775015.jpg",
    "encoder_model_id": "google/siglip2-base-patch16-224"
  }
  ```

---

## 4. Cấu trúc Khóa Redis (Online Feature & Session Store)

| Mẫu Khóa (Key Pattern) | Kiểu Redis | TTL | Nội dung & Cơ chế Idempotency |
| :--- | :---: | :---: | :--- |
| `event:seen:{event_id}` | `STRING` | 24 giờ | Khóa khử trùng lặp nguyên tử (`SET ... NX EX 86400`) đảm bảo mỗi `event_id` chỉ cập nhật `user:{customer_id}:recent` đúng 1 lần dù đi qua cả API và Spark retry. |
| `user:{customer_id}:recent` | `LIST` | 7 ngày | Danh sách tối đa 50 `article_id` (10 ký tự) tương tác gần nhất (`LPUSH` + `LTRIM 0 49` qua hàm `record_session_event_idempotent`). Phần tử `0` là mới nhất. |
| `user:{customer_id}:profile` | `HASH` | Không | `{ "customer_idx": "42105", "age": "24", "age_bucket": "23-30", "avg_price": "0.028", "online_ratio": "0.85" }` |
| `user:{customer_id}:batch_recs` | `ZSET` | 24 giờ | Top-50 `article_id` tính sẵn từ Batch Pipeline kèm điểm số. |
| `item:{article_id}:cooc_all` | `ZSET` | Không | Top-20 `article_id` hay mua cùng giỏ hàng ngày `(customer_idx, t_dat)` nhất (phục vụ sinh ứng viên RecSys). |
| `item:{article_id}:cooc_outfit` | `ZSET` | Không | Top-20 `article_id` **khác `detector_class`** hay mua cùng giỏ hàng ngày nhất (proxy cross-category co-purchase phục vụ API `/api/v1/outfit/{article_id}`). |
| `pop:age:{age_bucket}` | `LIST` | Không | Top-100 `article_id` phổ biến nhất của nhóm tuổi đó. |
| `trend:15m` | `ZSET` | 30 phút | Điểm thịnh hành toàn cục của cửa sổ trượt 15 phút mới nhất (`max(window_end)`), ghi đè nguyên tử (`DELETE` + `ZADD`) từ Spark Streaming. |
| `trend:15m:{detector_class}` | `ZSET` | 30 phút | Điểm thịnh hành theo từng lớp trang phục (`top`, `pants`, `shoe`...) của cửa sổ mới nhất. |
| `trend:15m:version` | `STRING` | 30 phút | Timestamp `window_end` của bản snapshot `trend:15m` hiện hành. |
| `metrics:streaming:kpi` | `HASH` | Không | `{ "events_per_sec": "...", "online_share": "...", "last_updated": "..." }` |

---

## 5. Schema Bản tin Kafka (`topic: fashion-events`)

* **Partition Key:** `customer_id` (UTF-8 bytes) — đảm bảo các sự kiện của cùng 1 khách hàng đi vào cùng 1 partition.
* **Quy ước Đồng hồ Streaming (`event_time` vs `original_t_dat`):** Để tránh hiện tượng sự kiện UI năm 2026 kéo watermark của Spark Structured Streaming tiến lên hiện tại và làm rơi các bản ghi Replay năm 2020, cả sự kiện `replay` và `ui` trong luồng trực tiếp đều phát `event_time` theo đồng hồ UTC hiện hành, còn ngày giao dịch gốc của H&M được lưu tường minh tại trường `original_t_dat`.
* **Message Value (JSON):**
  ```json
  {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_time": "2026-10-18T12:30:00Z",
    "ingest_time": "2026-10-18T12:30:00Z",
    "customer_id": "000058a12d5b43e67d225668fa1f8d618c13dc232df0cad8ffe7ad4a1091e318",
    "article_id": "0108775015",
    "event_type": "click",
    "source": "replay",
    "price": 0.0169,
    "sales_channel_id": 2,
    "original_t_dat": "2020-09-18"
  }
  ```

---

## 6. Hợp đồng REST API trên FastAPI (`src/backend/main.py`)

1. **`GET /health`**: Kiểm tra Liveness của tiến trình FastAPI (`status="alive"`).
2. **`GET /ready`**: Kiểm tra Readiness thực tế của kết nối Qdrant, Redis, Kafka và trạng thái nạp các model ONNX/LightGBM.
3. **`POST /api/v1/visual-search`**:
   - **Input:** `multipart/form-data` hoặc JSON gồm ảnh tải lên (`image`), văn bản điều chỉnh tùy chọn (`text_query`), hệ số pha trộn (`alpha = 0.75`), `customer_id` (tùy chọn), `top_k = 12`.
   - **Output:** Danh sách các vùng Bounding Box phát hiện được (`detections`) + Top-K sản phẩm khớp nhất cho vùng được chọn, kèm điểm `visual_similarity`, `personalization_score`, `final_score` và lời giải thích (`explanation`).
4. **`GET /api/v1/recommend/{customer_id}?top_k=12`**:
   - **Output:** Danh sách 12 sản phẩm gợi ý cá nhân hóa kết hợp lịch sử dài hạn và các cú click vừa diễn ra trong phiên (`recent_session_items`), kèm nguồn đóng góp (`repurchase`, `cooccurrence`, `two_tower_realtime`, `trending_15m`).
5. **`GET /api/v1/outfit/{article_id}?top_k=6`**:
   - **Output:** Danh sách các sản phẩm **khác nhóm trang phục** phối hợp với `article_id` (dựa trên quy tắc nhóm trang phục bổ trợ + proxy `cooc_outfit` từ Redis + tương đồng phong cách trên Qdrant).
6. **`POST /api/v1/events`**:
   - **Input:** Bản tin sự kiện theo đúng Schema Mục 5 $\rightarrow$ đẩy vào Kafka topic `fashion-events` và cập nhật idempotent qua `record_session_event_idempotent` vào Redis `user:{customer_id}:recent` (khử trùng lặp bằng `event:seen:{event_id}`).
