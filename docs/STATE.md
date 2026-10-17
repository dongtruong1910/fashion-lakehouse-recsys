# TRẠNG THÁI DỰ ÁN TRỰC TIẾP (LIVE PROJECT STATE — SINGLE SOURCE OF TRUTH)

> **Cập nhật lần cuối:** `2026-10-17T08:30:00+07:00`  
> **Người cập nhật:** Lead Architect Agent  
> **Giai đoạn hiện tại:** `WP-0` — Khởi tạo Hạ tầng, Codebase & Kiểm định Dữ liệu.

---

## 1. Bảng Theo Dõi Tiến Độ Các Work Packages & Tasks

| Work Package | Mã Task | Mô tả ngắn | Phụ trách | Trạng thái | Ghi chú / Đầu ra đã kiểm chứng |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **WP-0** | `TASK-00` | Khởi tạo toàn bộ Codebase, Docs, Configs, Contracts & Unit Tests | Lead Agent | ✅ **DONE** | Đã tạo cấu trúc chuẩn + pass `pytest tests/` |
| **WP-0** | `TASK-01` | Dựng Docker Compose (Qdrant, Redis, Kafka KRaft Dual-Listener) | Data / Serving Agent | ⏳ **READY** | File `docker-compose.yml` đã sẵn sàng chạy |
| **WP-0** | `TASK-02` | Tải Dataset (H&M + Fashionpedia) & Kiểm tra tỉ lệ ảnh 256 | Data / CV Agent | ⏳ **READY** | Script `scripts/check_hm256_aspect_ratio.py` đã sẵn sàng |
| **WP-1** | `TASK-BD-01` | Ingest CSV $\rightarrow$ Bronze $\rightarrow$ Silver Delta Lake + Benchmark lưu trữ | Data Sub-Agent | ⬜ **PENDING** | Phụ thuộc `TASK-02` |
| **WP-1** | `TASK-BD-02` | EDA Big Data (Long-tail, Repurchase rate, Cold-start stats) | Data Sub-Agent | ⬜ **PENDING** | Phụ thuộc `TASK-BD-01` |
| **WP-1** | `TASK-REC-01` | Khung đánh giá RecSys (Tuần 104) + Baselines **L0** & **L1** | RecSys Sub-Agent | ⬜ **PENDING** | Phụ thuộc `TASK-BD-01` |
| **WP-1** | `TASK-CV-01` | Chia split H&M theo `product_code` (85/7.5/7.5) | CV Sub-Agent | ⬜ **PENDING** | Phụ thuộc `TASK-BD-01` |
| **WP-1** | `TASK-CV-02` | Benchmark 3 model Zero-shot (`CLIP`, `SigLIP-2`, `FashionSigLIP`) | CV Sub-Agent | ⬜ **PENDING** | Xét duyệt `GATE-CV-1` |
| **WP-1** | `TASK-CV-03` | Index 105.1K vector vào Qdrant + Benchmark `int8` Quantization | CV Sub-Agent | ⬜ **PENDING** | Hoàn tất Hệ thống Baseline v0 |
| **WP-2** | `TASK-CV-04A` | Chuẩn bị Fashionpedia 12 lớp + Đánh giá Detector Zero-shot | CV Sub-Agent | ⬜ **PENDING** | Xét duyệt `GATE-CV-2` |
| **WP-2** | `TASK-CV-04B` | Huấn luyện `YOLO11m` trên Colab L4 + Xuất `ONNX FP16` | CV Sub-Agent | ⬜ **PENDING** | Chạy trên Colab L4 (~12-18 CU) |
| **WP-2** | `TASK-CV-05` | *(Có điều kiện)* Fine-tune LoRA + WiSE-FT trên Colab L4 | CV Sub-Agent | ⬜ **PENDING** | Chỉ chạy nếu `GATE-CV-1` yêu cầu |
| **WP-2** | `TASK-CV-06` | Đánh giá `CatConsistency@10` & Tập ảnh thực tế VN (`nDCG@10`) | CV Sub-Agent | ⬜ **PENDING** | Dùng công cụ Pooled Labeling |
| **WP-3** | `TASK-REC-02` | Huấn luyện Spark MLlib Implicit ALS (**L2**) | RecSys Sub-Agent | ⬜ **PENDING** | Đo `MAP@12` & `Candidate Recall@100` |
| **WP-3** | `TASK-REC-03` | Sinh ứng viên cho Active Users (~70K) + Tính Feature GPU | Data + RecSys Agent | ⬜ **PENDING** | Dùng `src/recsys/features_gpu.py` |
| **WP-3** | `TASK-REC-04` | Huấn luyện **LightGBM LambdaRank (L3)** + SHAP | RecSys Sub-Agent | ⬜ **PENDING** | Xét duyệt `GATE-REC-1` |
| **WP-4** | `TASK-REC-05` | Huấn luyện 3 biến thể **Two-Tower (L4)** trên RTX 4060 | RecSys Sub-Agent | ⬜ **PENDING** | Ablation Cold-start Items |
| **WP-4** | `TASK-REC-06` | Tích hợp Two-Tower vào Qdrant & LightGBM + Tune hệ số $\beta$ | RecSys Sub-Agent | ⬜ **PENDING** | Xét duyệt `GATE-REC-2` |
| **WP-5** | `TASK-BD-03` | Kafka Event Simulator + Spark Structured Streaming $\rightarrow$ Redis | Data Sub-Agent | ⬜ **PENDING** | Đo Throughput & Latency p50/p95 |
| **WP-5** | `TASK-BD-04` | 4 Thí nghiệm Tối ưu hóa Apache Spark cho báo cáo Big Data | Data Sub-Agent | ⬜ **PENDING** | AQE, Broadcast, Skew, Storage |
| **WP-6** | `TASK-SRV-01` | Hoàn thiện FastAPI Serving Engine (< 150ms p95) | Serving Sub-Agent | ⬜ **PENDING** | Tích hợp ONNX + LightGBM + Redis + Qdrant |
| **WP-6** | `TASK-SRV-02` | Hoàn thiện Giao diện Streamlit 4 Tabs & Kịch bản Live Demo | Serving Sub-Agent | ⬜ **PENDING** | — |
| **WP-6** | `TASK-DOC-01` | Tổng hợp số liệu thực nghiệm vào Báo cáo 2 môn & CV | Lead Agent + User | ⬜ **PENDING** | Không còn số `[TBD]` |

---

## 2. Trạng Thái Các Cổng Quyết Định (Decision Gates Status)

| Mã Gate | Câu hỏi quyết định | Tiêu chí mở cổng | Trạng thái | Quyết định cuối |
| :--- | :--- | :--- | :---: | :--- |
| **`GATE-CV-1`** | Có cần Fine-tune LoRA cho Multimodal Encoder không? | Model zero-shot tốt nhất có lỗi hệ thống trên thuật ngữ/màu sắc H&M; và bản LoRA phải tăng $\ge 2\%$ `T2I R@10` mà không giảm quá $1\%$ `CatConsistency@10`. | ⏳ **CHỜ ĐO** | `[TBD]` |
| **`GATE-CV-2`** | Có cần Train `YOLO11m` trên Fashionpedia không? | Detector Zero-shot (`YOLO-World`) có `mAP@50 < 0.45` trên 12 lớp thời trang hoặc độ trễ `> 50ms/ảnh`. | ⏳ **CHỜ ĐO** | `[TBD]` |
| **`GATE-REC-1`** | Mô hình `LightGBM LambdaRank` đã hợp lệ chưa? | `MAP@12` trên tuần kiểm định (`week 104`) phải thắng vượt trội phương pháp Heuristic L1 tốt nhất. | ⏳ **CHỜ ĐO** | `[TBD]` |
| **`GATE-REC-2`** | Có giữ mạng `Two-Tower` trong pipeline cuối không? | Tăng `Candidate Recall@100`, hoặc tăng `MAP@12` khi thêm `tt_score`, hoặc cải thiện rõ rệt `Recall` trên nhóm **Cold-start Items**. | ⏳ **CHỜ ĐO** | `[TBD]` |

---

## 3. Bảng Số Liệu Thực Nghiệm Đã Ghi Nhận (Verified Metrics Registry)

*(Chỉ điền số vào đây sau khi script thực nghiệm chạy xong và xuất file lưu trong `reports/tables/`)*

* **Tỉ lệ ảnh H&M 256x256 (`hm256_aspect_check.json`):** `[TBD]`
* **Benchmark Lưu trữ (`CSV` vs `Parquet` vs `Delta`):** `[TBD]`
* **CV Zero-shot Best Model (`T2I R@10` / `I2I P@10-type+colour`):** `[TBD]`
* **CV Detector (`Zero-shot mAP@50` vs `YOLO11m mAP@50`):** `[TBD]`
* **RecSys `MAP@12` (Tuần 104):**
  * `L0 (Age Popularity + Time Decay)`: `[TBD]`
  * `L1 (Repurchase + Co-occurrence)`: `[TBD]`
  * `L2 (Spark ALS)`: `[TBD]`
  * `L3 (LightGBM LambdaRank + GPU Visual Feature)`: `[TBD]`
  * `L4 (Hybrid LightGBM + Two-Tower Neural Retrieval)`: `[TBD]`
* **Streaming Throughput & Latency (p50 / p95):** `[TBD]`
