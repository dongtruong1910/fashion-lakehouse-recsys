# KẾ HOẠCH THỰC THI TỔNG THỂ (MASTER PLAN v3.1 — ARCHITECTURE & EXECUTION SPEC)

> **Tài liệu trung tâm:** Kế hoạch 6 Work Packages (`WP-0` $\rightarrow$ `WP-6`), danh mục nhiệm vụ chi tiết (`TASK-xx`), tiêu chí nghiệm thu (Acceptance Criteria) và điều kiện qua cổng (Decision Gates).
> **Tài liệu liên quan:**
> - Bảng theo dõi tiến độ thời gian thực: [`STATE.md`](STATE.md)
> - Kiến trúc kỹ thuật chi tiết: [`ARCHITECTURE.md`](ARCHITECTURE.md)
> - Đặc tả dữ liệu & Data Contracts: [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md)
> - Hướng dẫn hạ tầng & Colab: [`INFRA_AND_COLAB_GUIDE.md`](INFRA_AND_COLAB_GUIDE.md)
> - Quy tắc điều phối & 8 quy tắc vàng: [`../AGENTS.md`](../AGENTS.md)

---

## 1. Triết lý Thiết kế: Baseline-First, Tách Dev/Final & Decision Gates

Hệ thống được phát triển theo 4 nguyên tắc nền tảng:
1. **Xây dựng Vertical Slice & Hệ thống Baseline v0 ngay từ giai đoạn đầu:**
   - Computer Vision: Trích xuất vector catalog H&M bằng Zero-shot model tốt nhất (`SigLIP-2` / `FashionSigLIP` / `FashionCLIP` / `CLIP`) và nạp vào collection `hm_products` trên Qdrant.
   - RecSys: Triển khai các baseline Heuristic vững chắc (Popularity suy giảm theo thời gian, Repurchase, Item Co-occurrence) để tạo ngưỡng so sánh (`MAP@12` & `Candidate Recall@100`).
   - Serving & UI tối thiểu: Nối thông một luồng dọc (Vertical Slice) từ Qdrant/Redis lên FastAPI (`/api/v1/...`) sớm để xác nhận hợp đồng dữ liệu trước khi mở rộng.
2. **Không huấn luyện tràn lan nếu không vượt qua Decision Gate:**
   - Mọi nỗ lực Fine-tune (`YOLO11m`, `LoRA + WiSE-FT`) và Deep Learning (`Two-Tower`) chỉ được kích hoạt hoặc giữ lại trong kiến trúc cuối khi vượt qua ngưỡng đo đạc của Decision Gate trên tập Dev. Nếu không cải thiện, ghi nhận trung thực **Negative Result / `SKIPPED`** kèm phân tích khoa học.
3. **Tách biệt nghiêm ngặt Tập Chọn Mô Hình (Dev) và Tập Báo Cáo Cuối (Final Holdout) — Chống Rò rỉ Thời gian:**
   - Lịch tuần chuẩn hóa neo tại Thứ Tư `2018-09-19` (`src/utils/id_utils.py`):
     - **Tập Train Ranker:** `week_num` `100, 101, 102` (`2020-08-19` $\rightarrow$ `2020-09-08`).
     - **Tập Dev / Model Selection (`week_num = 103`):** **`2020-09-09` đến `2020-09-15`** (7 ngày) — dùng cho Early Stopping của LightGBM, chọn siêu tham số và xét duyệt các Decision Gates (`t_dat < 2020-09-09`).
     - **Tập Final Test Holdout (`week_num = 104`):** **`2020-09-16` đến `2020-09-22`** (7 ngày cuối cùng của bộ H&M) — khóa cứng để báo cáo kết quả cuối cùng (`t_dat < 2020-09-16`).
   - Với Computer Vision trên H&M: Chia 105.542 sản phẩm theo nhóm `product_code` thành `85% Train / 7.5% Val (Dev) / 7.5% Test (Final)` lưu tại `data/splits/hm_split_v1.parquet`.
4. **Bảo vệ Tài nguyên Phần cứng & Cô lập Smoke Test:**
   - Active-User Filtering: Chỉ tạo bảng huấn luyện `gold/candidate_features` trên khách hàng thực sự mua hàng trong tuần nhãn (~70K khách $\times$ 100 ứng viên $\approx$ 7M dòng $\times$ 24 đặc trưng).
   - Mọi lệnh `--smoke-test` bắt buộc ghi ra `data/lakehouse_smoke/`, tuyệt đối không ghi đè vào `data/lakehouse/` chính.

---

## 2. Danh Mục Work Packages & Nhiệm Vụ Chi Tiết

### WP-0: Khởi tạo Hạ tầng, Codebase, Vá Nền tảng & Kiểm định Dữ liệu (Tuần 1)

* **`TASK-00` & `TASK-00-FIX`: Khởi tạo Codebase, Đồng bộ Contracts & Kiểm thử Chống Hồi Quy**
  - **Mục tiêu:** Thiết lập cấu trúc repo chuẩn, hợp đồng dữ liệu chặt chẽ (`src/contracts/schemas.py`), lịch tuần thống nhất (`date_to_hm_week_num`), bộ metric chuẩn (`MAP@12`, `Candidate Recall@K`, `nDCG@10`, `I2I Precision@K`, `Cohen's Kappa`) và sửa toàn bộ 20 findings `A01`–`A20`.
  - **Đầu ra:** Toàn bộ unit tests & kiểm tra liên kết Markdown chạy pass qua `.venv/Scripts/python.exe -m unittest discover -s tests -v`.
  - **Tiêu chí nghiệm thu:** 100% test cases pass; không còn mâu thuẫn tên bảng/key/API giữa các tài liệu.

* **`TASK-01`: Dựng Hạ tầng Dịch vụ Docker Compose**
  - **Mục tiêu:** Khởi động Qdrant (`6333`), Redis (`6379`), Kafka KRaft 3.9.0 với Dual-Listener (`INTERNAL://kafka:29092`, `EXTERNAL://localhost:9092`) và `KAFKA_LOG_DIRS=/var/lib/kafka/data`.
  - **Đầu ra:** `docker-compose.yml` hoạt động ổn định, dữ liệu Kafka giữ nguyên khi recreate container.
  - **Tiêu chí nghiệm thu:** Kết nối thông suốt từ máy host vào cổng `9092`, `6333`, `6379` và kiểm chứng persistence qua chu trình `produce -> recreate -> consume`.

* **`TASK-02`: Tải Dataset & Kiểm định Hình học / Viền trắng Ảnh (`hm256x256`)**
  - **Mục tiêu:** Tải dataset H&M và Fashionpedia vào `data/raw/`. Chạy [`../scripts/check_hm256_aspect_ratio.py`](../scripts/check_hm256_aspect_ratio.py) để thống kê độ phân giải và tỉ lệ viền trắng (`white_border_heuristic_ratio`), đối chiếu với ảnh gốc hoặc kiểm tra trực quan mẫu ngẫu nhiên.
  - **Đầu ra:** File báo cáo `reports/tables/hm256_aspect_check.json` kèm `seed`, `timestamp_utc` và `sampled_article_ids`.
  - **Tiêu chí nghiệm thu:** Nếu phát hiện ảnh bị bóp vuông làm méo tỉ lệ, dùng [`../scripts/resize_hm_aspect_pad.py`](../scripts/resize_hm_aspect_pad.py) tạo bộ ảnh đã pad sang thư mục đích riêng.

---

### WP-1: Baseline Hệ thống & Xử lý Dữ liệu Lakehouse (Tuần 1 - 2)

* **`TASK-BD-01`: PySpark Batch Pipeline (Bronze $\rightarrow$ Silver Delta Lake)**
  - **Mục tiêu:** Ingest dữ liệu CSV H&M vào `data/lakehouse/bronze/`; kiểm tra định dạng chữ số dương trước khi pad `article_id` 10 ký tự; tạo bảng ánh xạ `silver/customer_mapping` (`customer_idx` `int32` kèm `mapping_version`); tính `week_num` neo tại `2018-09-19` và lưu bảng `silver/transactions` partitioned theo `week_num`.
  - **Đầu ra:** [`../spark_jobs/batch/b0_ingest_bronze.py`](../spark_jobs/batch/b0_ingest_bronze.py), [`../spark_jobs/batch/b1_clean_silver.py`](../spark_jobs/batch/b1_clean_silver.py).
  - **Tiêu chí nghiệm thu:** Chạy `--smoke-test` vào `data/lakehouse_smoke/` thành công trước khi chạy full; lưu kết quả benchmark lưu trữ (`CSV` vs `Parquet` vs `Delta`) vào `reports/tables/storage_benchmark.json`.

* **`TASK-BD-02`: EDA Big Data & Phân tích Hành vi Mua sắm**
  - **Mục tiêu:** Dùng PySpark phân tích phân phối Long-tail, tỉ lệ Repurchase theo ngành hàng, độ trễ giữa các lần mua và tỉ lệ khách hàng/sản phẩm Cold-start.
  - **Đầu ra:** Script `spark_jobs/batch/b2_eda_stats.py`, bảng thống kê lưu tại `reports/tables/eda_summary.json`.

* **`TASK-REC-01`: Khung Đánh giá Temporal (Dev Week 103 / Final Week 104) & Baselines L0 + L1**
  - **Mục tiêu:** Xây dựng module đánh giá chuẩn thời gian trên `Dev Week 103` (`2020-09-09..15`) và `Final Test Week 104` (`2020-09-16..22`). Cài đặt Baseline **L0** (Global & Age-group Popularity suy giảm theo thời gian $\lambda = 0.08$, lưu tại `gold/popularity_global` & `gold/popularity_age`) và **L1** (Repurchase gần nhất + Item Co-occurrence theo giỏ hàng ngày `(customer_idx, t_dat)`, lưu tại `gold/cooccurrence_all` & `gold/cooccurrence_outfit`).
  - **Đầu ra:** [`../src/recsys/baselines.py`](../src/recsys/baselines.py), bảng kết quả `MAP@12` & `Candidate Recall@100` tại `reports/tables/recsys_baselines_val.json`.
  - **Tiêu chí nghiệm thu:** Không rò rỉ bất kỳ giao dịch nào có `t_dat >= week_start`.

* **`TASK-CV-01`: Phân chia H&M Split theo `product_code`**
  - **Mục tiêu:** Chia 105.542 sản phẩm thành Train (85%), Val/Dev (7.5%), Test/Final (7.5%) theo nhóm `product_code` (7 chữ số đầu) để chống rò rỉ các biến thể màu sắc của cùng một kiểu dáng giữa các tập.
  - **Đầu ra:** `src/cv/split_data.py`, file phân chia `data/splits/hm_split_v1.parquet`.

* **`TASK-CV-02`: Benchmark Zero-shot Multimodal Embeddings (`GATE-CV-1`)**
  - **Mục tiêu:** Đánh giá các ứng viên Zero-shot (`openai/clip-vit-base-patch32`, `google/siglip2-base-patch16-224`, `Marqo/marqo-fashionSigLIP` / `patrickjohncyh/fashion-clip`) với cấu hình padding chuẩn từng họ model (`padding="max_length", max_length=64` cho SigLIP). Đo `T2I Recall@10` và `I2I Precision@10` (loại trừ chính `article_id` truy vấn qua hàm `i2i_precision_at_k`) trên tập Val (`Dev`) để chọn model và báo cáo trên tập Test (`Final`).
  - **Đầu ra:** Bảng kết quả `reports/tables/cv_zeroshot_benchmark.json`.
  - **Tiêu chí nghiệm thu:** Chọn ra model tốt nhất làm nền tảng cho Qdrant Indexer; xét duyệt `GATE-CV-1`.

* **`TASK-CV-03`: Đánh chỉ mục Qdrant Catalog (`hm_products`) & Vertical Slice Đầu Tiên**
  - **Mục tiêu:** Trích xuất vector cho catalog H&M bằng model tốt nhất từ `TASK-CV-02`, nạp vào collection `hm_products` trên Qdrant với Named Vectors (`visual_emb`, `two_tower_emb`) và payload chuẩn (kèm `encoder_model_id`). Benchmark `FP32` vs `INT8 Scalar Quantization` và nối thử vào endpoint FastAPI `/api/v1/visual-search`.
  - **Đầu ra:** [`../src/cv/qdrant_indexer.py`](../src/cv/qdrant_indexer.py), bảng benchmark tại `reports/tables/qdrant_benchmark.json`.

---

### WP-2: Nâng cấp Computer Vision & Đánh giá 3 Tầng (Tuần 3)

* **`TASK-CV-04A`: Chuẩn bị Dữ liệu Fashionpedia 12 Lớp & Đánh giá Zero-shot Detector**
  - **Mục tiêu:** Ánh xạ 46 lớp Fashionpedia về 12 lớp cốt lõi thời trang theo [`../configs/class_mapping.yaml`](../configs/class_mapping.yaml). Đánh giá detector zero-shot (`yolov8s-worldv2.pt` với `set_classes()`) trên tập dev Fashionpedia để kiểm tra `GATE-CV-2`.
  - **Đầu ra:** `src/cv/prepare_fashionpedia.py`, file kết quả `reports/tables/detector_zeroshot_eval.json`.

* **`TASK-CV-04B`: (Có điều kiện qua `GATE-CV-2`) Huấn luyện YOLO11m trên Fashionpedia & Xuất ONNX FP16**
  - **Mục tiêu:** Nếu `GATE-CV-2` kích hoạt, huấn luyện `YOLO11m` trên Colab L4 trên 12 lớp thời trang. Xuất model sang chuẩn ONNX FP16 tại `models/yolo11m_fashion_fp16.onnx`.
  - **Đầu ra:** `colab/train_yolo11_fashionpedia.ipynb`, [`../src/cv/export_onnx.py`](../src/cv/export_onnx.py), model `models/yolo11m_fashion_fp16.onnx`.

* **`TASK-CV-05`: (Có điều kiện qua `GATE-CV-1`) Fine-tune Multimodal Encoder với LoRA + WiSE-FT**
  - **Mục tiêu:** Nếu `GATE-CV-1` kích hoạt (và được chọn làm nhánh nâng cao), fine-tune adapter LoRA (Rank 16, Alpha 32) trên tập Train H&M (tránh false negatives cùng `product_code`) trên Colab L4, áp dụng nội suy trọng số **WiSE-FT** ($\alpha \in \{0.3, 0.5, 0.7\}$) và kiểm định trên tập Dev trước khi chốt.
  - **Đầu ra:** `colab/train_siglip_lora.ipynb`, model xuất ra `models/visual_encoder_fp16.onnx` & `models/text_encoder_fp16.onnx`.

* **`TASK-CV-06`: Đánh giá Toàn diện 3 Tầng (In-domain, Proxy Fashionpedia & Việt Nam Street Set)**
  - **Mục tiêu:**
    1. **Tầng B (Unfiltered Category Consistency):** Đo `CatConsistency@10` **trước khi lọc payload** trên cả Ground-Truth bbox (đánh giá riêng Encoder) và Predicted bbox (đánh giá toàn luồng Detector $\rightarrow$ Encoder, ghi nhận tỉ lệ miss detection).
    2. **Tầng C (VN Streetwear Pilot 60–80 ảnh):** Chạy các cấu hình qua cùng một tập query, gộp Top-10 ứng viên thành **Common Pool đã khử trùng lặp**, chấm mù độc lập bởi 2 người theo thang 0–3 trên Streamlit Labeling Tool, tính `nDCG@10` với **Shared Pool IDCG** (`ndcg_at_k(preds, ideal_relevances=common_pool)`) và `cohens_kappa_summary`.
  - **Đầu ra:** [`../src/metrics/cv_metrics.py`](../src/metrics/cv_metrics.py), bảng kết quả `reports/tables/cv_3tier_evaluation.json`.

---

### WP-3: Mô hình Hóa RecSys — Spark ALS & LightGBM LambdaRank (Tuần 3 - 4)

* **`TASK-REC-02`: Huấn luyện Spark MLlib Implicit ALS (Baseline L2)**
  - **Mục tiêu:** Huấn luyện mô hình Collaborative Filtering phân tán Implicit ALS (`rank=64`) trên PySpark với trọng số tương tác suy giảm theo thời gian, lưu vector tại `gold/als_user_factors` và `gold/als_item_factors`.
  - **Đầu ra:** `spark_jobs/batch/b5_als_model.py`.
  - **Tiêu chí nghiệm thu:** Đo `Candidate Recall@100` và `MAP@12` trên Dev Week 103 và Final Week 104.

* **`TASK-REC-03`: Sinh Ứng Viên Active Users & Tính Bảng Đặc Trưng `gold/candidate_features`**
  - **Mục tiêu:** Sinh 100 ứng viên đa nguồn cho các `Active Users` trong từng tuần nhãn (`100, 101, 102` cho Train; `103` cho Dev; `104` cho Final Test) với cutoff lịch sử nghiêm ngặt `t_dat < week_start`. Dùng [`../src/recsys/features_gpu.py`](../src/recsys/features_gpu.py) tính `visual_affinity_score` theo mini-batch an toàn bộ nhớ.
  - **Đầu ra:** Bảng `data/lakehouse/gold/candidate_features` (~24 cột đặc trưng chuẩn trong `FEATURE_COLUMNS`) và bảng `data/lakehouse/gold/item_features_latest.parquet`.

* **`TASK-REC-04`: Huấn luyện Unified LightGBM LambdaRank (L3) & Phân tích SHAP**
  - **Mục tiêu:** Huấn luyện LightGBM `lambdarank` trên tuần `100..102` với Query Group `(target_week, customer_idx)` (`prepare_lgbm_query_frame`), dùng `Dev Week 103` làm `valid_sets` cho Early Stopping (`GATE-REC-1`), và đánh giá báo cáo cuối trên `Final Test Week 104`. Xuất SHAP Summary Plot.
  - **Đầu ra:** [`../src/recsys/lgbm_ranker.py`](../src/recsys/lgbm_ranker.py), model `models/lgbm_ranker.txt`, báo cáo `reports/tables/recsys_lgbm_eval.json`, hình `reports/figures/lgbm_shap_summary.png`.

---

### WP-4: Deep Retrieval Two-Tower & Visual Fusion (Tuần 4 - 5)

* **`TASK-REC-05`: Thiết kế & Huấn luyện Mạng Two-Tower (L4) trên RTX 4060**
  - **Mục tiêu:** Xây dựng mạng Two-Tower PyTorch ([`../src/recsys/two_tower.py`](../src/recsys/two_tower.py)) với `UserTower` (chuỗi $N=15$ món gần nhất có Positional + Recency Time-Decay Attention và fallback an toàn không sinh `NaN` cho lịch sử rỗng) và `ItemTower` (có cơ chế ID Dropout / OOV token cho sản phẩm mới). Huấn luyện 3 biến thể Ablation khớp với code:
    - `id_only`: Chỉ dùng embedding định danh `article_idx`.
    - `id_plus_meta`: Kết hợp `article_idx` + thuộc tính phân loại (`product_type`, `colour`).
    - `id_meta_visual`: Kết hợp ID (có OOV dropout) + thuộc tính + nhánh chiếu vector ảnh SigLIP/CLIP đóng băng (`768 -> 64`).
  - **Đầu ra:** [`../src/recsys/two_tower.py`](../src/recsys/two_tower.py), bảng kết quả `reports/tables/two_tower_ablation.json`.
  - **Tiêu chí nghiệm thu:** Đo mức cải thiện `Candidate Recall@100` và `Cold-start Item Recall` trên Dev Week 103 (`GATE-REC-2`).

* **`TASK-REC-06`: Tích hợp Two-Tower vào Qdrant (`two_tower_emb`) & LightGBM Ranker**
  - **Mục tiêu:** Nếu vượt qua `GATE-REC-2`, lưu vector Item Tower vào `data/lakehouse/gold/twotower_item_embeddings.parquet`, cập nhật Named Vector `two_tower_emb` trong collection `hm_products` của Qdrant, xuất `models/two_tower_user.onnx` và tích hợp `tt_score` + `src_twotower_rank` vào `gold/candidate_features`.
  - **Đầu ra:** Bảng kết quả tổng hợp `reports/tables/recsys_final_comparison.json`.

---

### WP-5: Big Data Streaming & Thí nghiệm Tối ưu Apache Spark (Tuần 5)

* **`TASK-BD-03`: Kafka Event Simulator & Spark Structured Streaming Idempotent Sink**
  - **Mục tiêu:** Xây dựng [`../src/streaming/event_simulator.py`](../src/streaming/event_simulator.py) phát sự kiện vào topic `fashion-events` với đồng hồ UTC thống nhất (`event_time`) và giữ ngày gốc tại `original_t_dat`. Xây dựng [`../spark_jobs/streaming/s1_stream_processor.py`](../spark_jobs/streaming/s1_stream_processor.py) đọc từ Kafka với `watermark = 10 minutes`, cửa sổ trượt `15 minutes` (trượt `1 minute`), ghi xuống Bronze Delta và cập nhật Redis idempotent qua `record_session_event_idempotent` (`user:{customer_id}:recent`, TTL 7 ngày, khử trùng bằng `event:seen:{event_id}`) cùng snapshot `trend:15m` (`publish_trending_window_snapshot`).
  - **Đầu ra:** Pipeline streaming hoàn chỉnh, đo Throughput và End-to-End Processing Latency (`sink_time - ingest_time`) lưu tại `reports/tables/streaming_benchmark.json`.

* **`TASK-BD-04`: 4 Thí nghiệm Tối ưu hóa Apache Spark phục vụ Báo cáo Big Data**
  - **Mục tiêu:** Thực hiện 4 bài thí nghiệm định lượng trên dữ liệu thật:
    1. **Adaptive Query Execution (AQE):** Bật/tắt AQE đo thời gian thực thi và số partition sau shuffle.
    2. **Broadcast Hash Join vs Sort-Merge Join:** Join `silver/transactions` với `silver/articles`.
    3. **Data Skew & Basket Cap Handling:** So sánh thời gian tính Co-occurrence khi có và không giới hạn kích thước giỏ hàng (`max_basket_size = 30`).
    4. **Storage Format & Z-Ordering:** Benchmark `CSV` vs `Parquet` vs `Delta Lake` (kèm `OPTIMIZE ZORDER BY`).
  - **Đầu ra:** Script `spark_jobs/experiments/spark_optimizations.py`, bảng dữ liệu tại `reports/tables/spark_optimization_experiments.json`.

---

### WP-6: Real-time Serving, UI Demo & Tổng kết Báo cáo (Tuần 6)

* **`TASK-SRV-01`: FastAPI High-Performance Serving Engine**
  - **Mục tiêu:** Hoàn thiện [`../src/backend/main.py`](../src/backend/main.py) phục vụ đúng hợp đồng REST API tại [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md):
    - `GET /health` (Liveness) & `GET /ready` (Readiness kiểm tra kết nối thật tới Qdrant, Redis, Kafka và models).
    - `POST /api/v1/visual-search`: Phát hiện trang phục (`YOLO11 ONNX`) $\rightarrow$ trích vector (`Encoder ONNX`) $\rightarrow$ truy vấn `hm_products` trên Qdrant $\rightarrow$ kết hợp điểm cá nhân hóa.
    - `GET /api/v1/recommend/{customer_id}`: Tra cứu Redis (`user:{customer_id}:recent`, `trend:15m`) $\rightarrow$ ghép `item_features_latest.parquet` $\rightarrow$ chấm điểm bằng `UnifiedLGBMRanker` $\rightarrow$ trả về Top-12 sản phẩm.
    - `GET /api/v1/outfit/{article_id}`: Gợi ý phối đồ khác nhóm trang phục dựa trên quy tắc danh mục + proxy `item:{article_id}:cooc_outfit` + tương đồng thị giác.
    - `POST /api/v1/events`: Kiểm tra hợp đồng `FashionEvent`, cập nhật idempotent vào Redis `user:{customer_id}:recent` và đẩy vào Kafka `fashion-events`.
  - **Đầu ra:** [`../src/backend/main.py`](../src/backend/main.py), kết quả đo latency & VRAM thực tế tại `reports/tables/serving_latency.json`.

* **`TASK-SRV-02`: Giao diện Web Streamlit 4 Tabs & Kịch bản Demo**
  - **Mục tiêu:** Hoàn thiện [`../src/frontend/app.py`](../src/frontend/app.py) gồm 4 Tabs: (1) Visual Search & Smart Outfit, (2) Real-Time Personalized Feed, (3) Lakehouse & Streaming Monitor, và (4) VN Streetwear Pooled Labeling App.
  - **Đầu ra:** [`../src/frontend/app.py`](../src/frontend/app.py), hướng dẫn chạy tại [`../README.md`](../README.md).

* **`TASK-DOC-01`: Tổng kết Số liệu Báo cáo & Đóng gói Đề tài**
  - **Mục tiêu:** Điền số liệu thực nghiệm đã kiểm chứng (hoặc ghi rõ `SKIPPED` kèm lý do qua cổng) vào [`STATE.md`](STATE.md), hoàn thiện báo cáo 2 môn học (Computer Vision & Big Data).
  - **Tiêu chí nghiệm thu:** Tuân thủ tuyệt đối `Zero Hallucinated Metrics`; mọi con số đều truy vết được về file JSON/CSV trong `reports/tables/`.

---

## 3. Quy Tắc Duyệt Cổng Quyết Định (Decision Gates Rules)

| Mã Gate | Điều kiện mở cổng để thử nghiệm (Trigger) | Tiêu chí chấp nhận mô hình sau thử nghiệm (Acceptance trên tập Dev) | Hành động nếu không đạt |
| :--- | :--- | :--- | :--- |
| **`GATE-CV-1`** | Model Zero-shot tốt nhất có `T2I R@10 < 0.35` trên tập Val H&M hoặc sai lệch hệ thống trên thuộc tính màu sắc/kiểu dáng. | Bản `LoRA + WiSE-FT` tăng $\ge +2.0$ điểm phần trăm (`pp`) `T2I R@10` trên Val H&M **và** không làm giảm quá $1.0\text{ pp}$ `CatConsistency@10` (unfiltered) trên Fashionpedia crops. | Giữ nguyên bản Zero-shot tốt nhất, báo cáo Negative Result của fine-tuning. |
| **`GATE-CV-2`** | Detector Zero-shot (`YOLO-World`) đạt `mAP@50 < 0.45` trên 12 lớp Fashionpedia dev hoặc độ trễ inference `> 50ms/ảnh`. | `YOLO11m` fine-tuned đạt `mAP@50 >= 0.50` trên 12 lớp và xuất ONNX FP16 chạy `< 30ms/ảnh`. | Giữ detector đạt `mAP@50` / latency tốt hơn trên tập dev. |
| **`GATE-REC-1`** | Bắt buộc chạy để kiểm định mô hình xếp hạng chính `LightGBM LambdaRank` (L3). | `MAP@12` của L3 trên `Dev Week 103` tăng $\ge +0.0020$ so với baseline Heuristic L1 tốt nhất. | Rà soát lại Candidate Recall, query grouping `(target_week, customer_idx)` và công thức đặc trưng. |
| **`GATE-REC-2`** | Chỉ kích hoạt sau khi L3 đã vượt qua `GATE-REC-1`. | Biến thể `id_meta_visual` tăng $\ge +1.5\text{ pp}$ `Candidate Recall@100` tổng thể hoặc tăng $\ge +3.0\text{ pp}$ `Recall@100` trên nhóm **Cold-start Items** ở `Dev Week 103`. | Giữ pipeline gọn nhẹ `Heuristic + ALS + LightGBM` cho Serving, báo cáo kết quả Ablation trong báo cáo. |

---

## 4. Bảng Phân Bổ Thời Gian 6 Tuần

| Tuần | Trọng tâm công việc | Giao phẩm chính |
| :---: | :--- | :--- |
| **Tuần 1** | Hạ tầng, Vá nền tảng (`TASK-00-FIX`), Data Check, Lakehouse Bronze/Silver | Unit tests & Regression tests pass, Docker Compose, Silver Delta (`week_num` chuẩn) |
| **Tuần 2** | Baselines L0/L1, CV Zero-shot Benchmark, Qdrant Index & Vertical Slice API | Điểm `MAP@12` L0/L1 (Dev 103 & Test 104), `hm_products` trên Qdrant, xét `GATE-CV-1` & `GATE-CV-2` |
| **Tuần 3** | Detector Fashionpedia (`YOLO-World` / `YOLO11m`), Spark ALS (L2), Feature GPU | Model ONNX, bảng `gold/candidate_features`, kết quả ALS L2 |
| **Tuần 4** | LightGBM LambdaRank (L3), Đánh giá CV 3 Tầng (Fashionpedia & VN Pooled Set) | Model `lgbm_ranker.txt`, SHAP plot, xét `GATE-REC-1`, bảng `cv_3tier_evaluation.json` |
| **Tuần 5** | Two-Tower Ablation (L4), Kafka + Spark Structured Streaming Idempotent Sink | Bảng `two_tower_ablation.json` (`GATE-REC-2`), Streaming benchmark + 4 thí nghiệm Spark |
| **Tuần 6** | Hoàn thiện FastAPI Serving + Giao diện Streamlit 4 Tabs + Báo cáo 2 môn | Serving benchmark (`serving_latency.json`), App 4 Tabs, Báo cáo hoàn chỉnh |

