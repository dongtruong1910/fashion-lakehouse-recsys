# NHẬT KÝ BÀN GIAO GIỮA CÁC AGENT (AGENT-TO-AGENT HANDOFF LOG)

> **Quy tắc bắt buộc:** Mỗi khi một Agent (Lead Agent hoặc Sub-Agent) hoàn thành một phiên làm việc hoặc một `TASK`, Agent đó phải ghi thêm một mục bàn giao vào **đầu mục 2 (Nhật ký Bàn giao — Mới nhất ở trên)** theo đúng mẫu ở Mục 1.

---

## 1. Mẫu Bàn Giao Chuẩn (Handoff Template)

Khi kết thúc nhiệm vụ, hãy sao chép mẫu sau và điền đầy đủ thông tin:

```markdown
### [YYYY-MM-DD HH:MM] — <Tên Role / Agent> bàn giao `<Mã TASK>`
- **Trạng thái Task:** `DONE` | `PARTIAL` | `BLOCKED`
- **Tóm tắt công việc đã làm:**
  - ...
- **Các file đã tạo mới hoặc chỉnh sửa:**
  - `path/to/file1.py`
  - `path/to/output_table.csv`
- **Kết quả kiểm thử / Số liệu thực nghiệm (Verification & Metrics):**
  - Lệnh đã chạy: `pytest ...` hoặc `python -m ...`
  - Kết quả: ...
- **Vấn đề tồn đọng / Lưu ý cho Agent tiếp theo (Next Steps):**
  - ...
```

---

## 2. Nhật ký Bàn giao (Mới nhất ở trên)

### [2026-10-18 13:00] — Lead Architect Agent bàn giao `TASK-00-FIX` (Khắc phục toàn bộ 20 Findings `A01`–`A20` & Đồng bộ hóa v3.1)
- **Trạng thái Task:** `DONE`
- **Tóm tắt công việc đã làm:**
  1. Commit trạng thái rà soát v3 (`9c60889` — `docs: record v3 codebase and plan audit findings (A01-A20)`).
  2. Khắc phục toàn bộ 20 findings (`A01`–`A20`) và 5 edge cases Mục 5 từ [`nhan_xet_codebase_va_docs_v3_2026-10-17.md`](ke_hoach_ban_dau/nhan_xet_codebase_va_docs_v3_2026-10-17.md):
     - **`A01`, `A10` (Lịch tuần H&M & Two-Stage Split):** Chuẩn hóa `HM_WEEK_ANCHOR_DATE = date(2018, 9, 19)` trong [`src/utils/id_utils.py`](../src/utils/id_utils.py) và [`spark_jobs/batch/b1_clean_silver.py`](../spark_jobs/batch/b1_clean_silver.py), giúp `2020-09-09..15 -> week 103` (7 ngày, **Dev Week**) và `2020-09-16..22 -> week 104` (7 ngày, **Final Test Week**), bổ sung `validate_no_temporal_leakage()`.
     - **`A02` (LightGBM Query Grouping):** Bổ sung `prepare_lgbm_query_frame()` trong [`src/recsys/lgbm_ranker.py`](../src/recsys/lgbm_ranker.py) sắp xếp và tính `group` theo `("target_week", "customer_idx")` kèm kiểm tra trùng `(target_week, customer_idx, article_id)`.
     - **`A03`, `5.5` (Smoke-Test Isolation & ID Validation):** Tách đường dẫn `--smoke-test` sang `data/lakehouse_smoke/...` trong [`spark_jobs/batch/b0_ingest_bronze.py`](../spark_jobs/batch/b0_ingest_bronze.py) và [`spark_jobs/batch/b1_clean_silver.py`](../spark_jobs/batch/b1_clean_silver.py), kiểm tra regex chữ số trước `lpad`, và thêm cột `mapping_version` cho `customer_mapping`.
     - **`A04`, `A16`, `A17` (CV Detector, Qdrant & SigLIP Tokenizer):** Chặn nhầm checkpoint COCO80 (`0: person`) trong [`src/cv/detector.py`](../src/cv/detector.py), thêm `get_text_tokenizer_kwargs()` (`padding="max_length", max_length=64` cho SigLIP) trong [`src/cv/embedder.py`](../src/cv/embedder.py), và thêm `validate_existing_collection_params()` trong [`src/cv/qdrant_indexer.py`](../src/cv/qdrant_indexer.py).
     - **`A05`, `A19` (Two-Tower Cold-Start & Time-Decay):** Sửa lỗi `NaN` khi lịch sử rỗng trong `UserTower` bằng `empty_history_emb` fallback, thêm trọng số vị trí + suy giảm thời gian (`recency_decay_lambda`), và hỗ trợ OOV/ID-dropout (`unk_item_idx = 0`) trong `ItemTower` tại [`src/recsys/two_tower.py`](../src/recsys/two_tower.py).
     - **`A06`, `A07`, `A08`, `A09` (Contracts, Kafka & Streaming Idempotency):** Kiểm tra chặt UUID/ISO-8601/price/enums/`product_code` prefix trong [`src/contracts/schemas.py`](../src/contracts/schemas.py); thêm `KAFKA_LOG_DIRS: /var/lib/kafka/data` vào [`docker-compose.yml`](../docker-compose.yml); tách `event_time` (UTC) và `original_t_dat` trong [`src/streaming/event_simulator.py`](../src/streaming/event_simulator.py); thêm `record_session_event_idempotent()` (`event:seen:{event_id}`) và `publish_trending_window_snapshot()` trong [`spark_jobs/streaming/s1_stream_processor.py`](../spark_jobs/streaming/s1_stream_processor.py).
     - **`A11`–`A15`, `A18`, `A20`:** Cập nhật [`src/metrics/cv_metrics.py`](../src/metrics/cv_metrics.py), [`src/metrics/recsys_metrics.py`](../src/metrics/recsys_metrics.py), [`src/recsys/features_gpu.py`](../src/recsys/features_gpu.py), [`scripts/check_hm256_aspect_ratio.py`](../scripts/check_hm256_aspect_ratio.py), [`src/backend/main.py`](../src/backend/main.py), [`pyproject.toml`](../pyproject.toml) và đồng bộ toàn bộ tài liệu [`MASTER_PLAN.md`](MASTER_PLAN.md), [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`INFRA_AND_COLAB_GUIDE.md`](INFRA_AND_COLAB_GUIDE.md).
- **Các file đã tạo mới hoặc chỉnh sửa:**
  - Code & Configs: [`src/utils/id_utils.py`](../src/utils/id_utils.py), [`src/contracts/schemas.py`](../src/contracts/schemas.py), [`src/recsys/lgbm_ranker.py`](../src/recsys/lgbm_ranker.py), [`src/recsys/two_tower.py`](../src/recsys/two_tower.py), [`src/recsys/features_gpu.py`](../src/recsys/features_gpu.py), [`src/cv/detector.py`](../src/cv/detector.py), [`src/cv/embedder.py`](../src/cv/embedder.py), [`src/cv/qdrant_indexer.py`](../src/cv/qdrant_indexer.py), [`src/metrics/cv_metrics.py`](../src/metrics/cv_metrics.py), [`src/metrics/recsys_metrics.py`](../src/metrics/recsys_metrics.py), [`src/streaming/event_simulator.py`](../src/streaming/event_simulator.py), [`spark_jobs/batch/b0_ingest_bronze.py`](../spark_jobs/batch/b0_ingest_bronze.py), [`spark_jobs/batch/b1_clean_silver.py`](../spark_jobs/batch/b1_clean_silver.py), [`spark_jobs/streaming/s1_stream_processor.py`](../spark_jobs/streaming/s1_stream_processor.py), [`src/backend/main.py`](../src/backend/main.py), [`scripts/check_hm256_aspect_ratio.py`](../scripts/check_hm256_aspect_ratio.py), [`scripts/resize_hm_aspect_pad.py`](../scripts/resize_hm_aspect_pad.py), [`docker-compose.yml`](../docker-compose.yml), [`pyproject.toml`](../pyproject.toml), [`configs/paths.yaml`](../configs/paths.yaml), [`configs/model_config.yaml`](../configs/model_config.yaml).
  - Tests & Verification Evidence: [`tests/test_metrics_and_ids.py`](../tests/test_metrics_and_ids.py), [`tests/test_markdown_links.py`](../tests/test_markdown_links.py), [`reports/tables/codebase_fixes_v3_1_2026-10-18.json`](../reports/tables/codebase_fixes_v3_1_2026-10-18.json).
  - Docs: [`AGENTS.md`](../AGENTS.md), [`README.md`](../README.md), [`docs/MASTER_PLAN.md`](MASTER_PLAN.md), [`docs/DATA_CONTRACTS.md`](DATA_CONTRACTS.md), [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/INFRA_AND_COLAB_GUIDE.md`](INFRA_AND_COLAB_GUIDE.md), [`docs/SUBAGENT_PROMPTS.md`](SUBAGENT_PROMPTS.md), [`docs/STATE.md`](STATE.md), [`docs/HANDOFF.md`](HANDOFF.md).
- **Kết quả kiểm thử / Số liệu thực nghiệm (Verification & Metrics):**
  - Lệnh đã chạy: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` -> **14/14 tests PASS** (bao gồm 6 regression tests mới cho `A01`–`A20` và 2 markdown-link tests).
  - Lệnh đã chạy: `docker compose config --quiet` -> **exit 0**.
- **Vấn đề tồn đọng / Lưu ý cho Agent tiếp theo (Next Steps):**
  - Bắt đầu **`TASK-01`** (`docker compose up -d`) và **`TASK-02`** (tải dataset H&M + Fashionpedia vào `data/raw/` và chạy [`scripts/check_hm256_aspect_ratio.py`](../scripts/check_hm256_aspect_ratio.py)).

### [2026-10-17 21:59] — Lead Architect Agent bàn giao `DOC-REVIEW-V3` (Lưu đầy đủ nhận xét vào Markdown riêng)
- **Trạng thái Task:** `DONE` (tổng hợp tài liệu; các lỗi implementation vẫn mở).
- **Tóm tắt công việc đã làm:** Theo yêu cầu người dùng, tạo bản nhận xét độc lập trong `ke_hoach_ban_dau/`, giữ đủ A01–A20, bằng chứng, tác động, đề xuất, giới hạn kiểm chứng và nhận định bổ sung về metrics/gates/scope.
- **Các file đã tạo mới hoặc chỉnh sửa:**
  - [nhan_xet_codebase_va_docs_v3_2026-10-17.md](ke_hoach_ban_dau/nhan_xet_codebase_va_docs_v3_2026-10-17.md).
  - [STATE.md](STATE.md) và [HANDOFF.md](HANDOFF.md): dẫn tới bản đầy đủ và ghi bàn giao.
- **Kết quả kiểm thử / Số liệu thực nghiệm:** **20/20 finding IDs đầy đủ**, UTF-8/code fences hợp lệ; **138 relative Markdown links PASS** bằng `python -X utf8 tests/test_markdown_links.py`. Số unittest/ML/probe trong file là bằng chứng của lượt audit trước, không phải kết quả chạy lại ở tác vụ ghi tài liệu.
- **Vấn đề tồn đọng / Next Steps:** Chưa sửa code/config, chưa áp dụng split hoặc scope đề xuất. Khi quyết định sửa, cập nhật tài liệu vận hành chính tương ứng; bản review này là hồ sơ lịch sử.

### [2026-10-17 20:38] — Lead Architect Agent bàn giao `REVIEW-2026-10-17` (Rà soát code, docs và tính hợp lệ thí nghiệm)
- **Trạng thái Task:** `DONE` (hoàn tất review; các lỗi dưới đây vẫn `OPEN`, chưa sửa implementation).
- **Tóm tắt công việc đã làm:**
  - Đọc tài liệu bắt buộc theo AGENTS; đối chiếu source, tests, configs, Git và nguồn chính thức Spark/LightGBM/Kafka/Ultralytics/Hugging Face/ONNX Runtime/Colab.
  - Rà soát độc lập theo vai trò contracts/metrics, infra/runtime và evaluation; Lead tái hiện các lỗi chính bằng probe nhỏ, không cần tải dữ liệu/model.
  - Kết luận hiện tại: scaffold có định hướng kiến trúc phù hợp nhưng còn lỗi correctness và mâu thuẫn spec; chưa đủ căn cứ gọi production-ready.
- **Các file đã tạo mới hoặc chỉnh sửa:**
  - [Review evidence JSON](../reports/tables/codebase_review_2026-10-17.json): seed `42`, timestamp, môi trường, 20 findings A01–A20, evidence type, probe outputs và nguồn đối chiếu.
  - [STATE.md](STATE.md): cập nhật bằng chứng kiểm tra và các vấn đề còn mở.
  - [HANDOFF.md](HANDOFF.md): mục bàn giao này. Không sửa code/config/requirements; thay đổi có sẵn ở MASTER_PLAN (một dòng trắng cuối file) được giữ nguyên.
- **Kết quả kiểm thử / Số liệu thực nghiệm (Verification & Metrics):**
  - `./.venv/Scripts/python.exe -m unittest discover -s tests -v`: **6/6 PASS**, 11.413s. Không bao gồm hai test function của script Markdown.
  - `./.venv/Scripts/python.exe tests/test_markdown_links.py`: **PASS**, kiểm lại sau cập nhật journal: **66 links/13 Markdown files** (trước cập nhật: 61 links).
  - `ast.parse`: **37/37 Python files PASS**. Đây chỉ là kiểm cú pháp.
  - `./.venv/Scripts/python.exe -m pytest tests/`: **không chạy được**, `No module named pytest`; không cài thêm dependencies.
  - `docker compose config --quiet`: **exit 0**, có cảnh báo không đọc được Docker user config. Không khởi động container, không kiểm persistence/network runtime.
  - Probe lịch tuần: `2020-09-16 -> 103`, `2020-09-17..22 -> 104`; trái khoảng ngày validation quy định.
  - Probe Dataset LightGBM bằng stub: một khách, hai tuần, mỗi tuần hai candidates → groups hiện tại `[4]`, đúng phải `[2, 2]`. Không chạy LightGBM thật.
  - Probe UserTower CPU eval với history rỗng: **64/64 chiều NaN**; history đảo thứ tự vẫn cùng vector trong sai số FP32, chưa có time-decay/position variant.
  - Probe direct dataclass: event có enum/UUID/timestamp/customer/price sai vẫn được nhận; payload giữ product_code sai prefix. Không suy rộng kết luận này sang validation của FastAPI chưa cài.
  - Probe detector giả lập: COCO `person=0 -> top`, `handbag=26 -> other`; không tải checkpoint hay đo detector accuracy.
  - Probe Candidate Recall: ground truth list → `1.0`, iterator cùng dữ liệu → `0.0`; probe ảnh trắng đã kéo méo vẫn pass padding heuristic.
- **Vấn đề tồn đọng / Lưu ý cho Agent tiếp theo (Next Steps):**

| Nhóm | Findings | Điều chỉnh ưu tiên |
| :--- | :--- | :--- |
| Correctness dữ liệu và học xếp hạng | A01, A02, A03 | Một lịch tuần dùng chung; group `(target_week, customer_idx)`; smoke output riêng; mapping IDs ổn định/versioned. |
| Model wrappers và validation | A04, A05, A06 | Kiểm ontology checkpoint; fallback history rỗng; validation chung ở cả producer/offline/API; product prefix nhất quán. |
| Kafka persistence | A07 | Đặt `KAFKA_LOG_DIRS=/var/lib/kafka/data`, rồi kiểm produce → recreate → consume. Finding dựa trên source image tag 3.9.0, chưa test Docker runtime. |
| Streaming correctness | A08, A09 | Tách clock replay/live; xác định một session writer; atomic event_id dedup; Redis window snapshots có version và retry idempotency. |
| Đánh giá và contracts | A10, A11, A12 | Tách dev/final; freeze qrels/gallery/pool; đo CatConsistency trước filter; thống nhất tên bảng, Redis keys, TTL, API, Qdrant và vocab indices. |
| Tài nguyên và cài đặt | A13, A14 | Đánh dấu ước lượng/chỉ tiêu khác số đã đo; chunk NumPy fallback; provider/dtype từng model; sửa packaging/quickstart và giữ global PyTorch CUDA. |
| CV/index và metrics utilities | A15, A16, A17, A18 | Aspect check cần ảnh gốc hoặc inconclusive; Qdrant model fingerprint; SigLIP fixed padding; materialize iterable một lần. |
| Tính trung thực và phạm vi | A19, A20 | Ablation/time-decay/OOV/feature parity phải có bằng chứng; API readiness và unimplemented status rõ; một vertical slice sớm, một nhánh nâng cao. |

- **Giới hạn / quyết định chưa áp dụng:**
  - Đề xuất giữ tuần 16–22/09 làm final và dùng tuần trước đó cho dev là **đề xuất**, chưa thay đổi Golden Rule hoặc cấu hình split.
  - API/UI/streaming thiếu nghiệp vụ là phần chưa triển khai theo STATE; không đếm từng placeholder thành lỗi riêng. Tuy nhiên `/events accepted` và `/health ok` hiện chưa chứng minh có ghi event hay kết nối dependency.
  - Các bảng VRAM/latency/CU trong INFRA vẫn chưa được đo. Dùng chung file LightGBM chưa chứng minh feature parity; proxy basket cùng khách/ngày chưa chứng minh outfit compatibility.
  - Không chạy full jobs, GPU inference/training, service integration hoặc benchmark ML. Mọi metric dự án hiện tại tiếp tục `[TBD]`.


### [2026-10-17 09:35] — Lead Architect Agent bàn giao `CHORE-MD-LINKS` (Chuẩn hóa toàn bộ liên kết Markdown sang Relative Paths)
- **Trạng thái Task:** `DONE`
- **Tóm tắt công việc đã làm:**
  1. Khởi tạo Git repository và hoàn thành commit đầu tiên ("Initial commit: create project structure").
  2. Tạo mới hoàn chỉnh tài liệu Kế hoạch tổng thể [`MASTER_PLAN.md`](MASTER_PLAN.md) để loại bỏ hoàn toàn dead links.
  3. Chuyển đổi toàn bộ liên kết `file:///...` sang đường dẫn tương đối chuẩn (`relative paths`) có tính toán chính xác cấp thư mục (dùng dấu `/`, xử lý `../` và `../../` phù hợp từng vị trí file).
  4. Bổ sung script kiểm thử tự động [`../tests/test_markdown_links.py`](../tests/test_markdown_links.py) để kiểm tra tính toàn vẹn của tất cả internal links.
- **Kết quả kiểm thử / Số liệu thực nghiệm (Verification & Metrics):**
  - Chạy `python tests/test_markdown_links.py`: 100% (59/59) relative links kiểm tra thành công, không còn URL `file:///` hay dấu `\`.
  - Chạy `.venv/Scripts/python.exe -m unittest discover tests`: 6/6 test cases kiểm tra contracts/metrics đều pass.
- **Vấn đề tồn đọng / Lưu ý cho Agent tiếp theo (Next Steps):**
  - Codebase và hệ thống tài liệu đã hoàn thiện, sẵn sàng bắt đầu **`TASK-01`** (`docker compose up -d`) và **`TASK-02`** (tải dataset H&M + Fashionpedia).

### [2026-10-17 08:30] — Lead Architect Agent bàn giao `TASK-00` (Khởi tạo Kiến trúc & Codebase v3)
- **Trạng thái Task:** `DONE`
- **Tóm tắt công việc đã làm:**
  1. Đánh giá chi tiết bản kế hoạch `plan_v2_opus55.md`, chỉ ra 7 điểm nghẽn thực tế trên cấu hình Laptop RTX 4060 (8GB VRAM) + 24GB RAM và ghi nhận đầy đủ tại [`docs/ke_hoach_ban_dau/nhan_xet_va_chinh_sua_plan_v2.md`](ke_hoach_ban_dau/nhan_xet_va_chinh_sua_plan_v2.md).
  2. Xây dựng bộ tài liệu điều phối Multi-Agent hoàn chỉnh gồm: [`AGENTS.md`](../AGENTS.md), [`README.md`](../README.md), [`docs/MASTER_PLAN.md`](MASTER_PLAN.md), [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/DATA_CONTRACTS.md`](DATA_CONTRACTS.md), [`docs/INFRA_AND_COLAB_GUIDE.md`](INFRA_AND_COLAB_GUIDE.md), [`docs/STATE.md`](STATE.md), và [`docs/SUBAGENT_PROMPTS.md`](SUBAGENT_PROMPTS.md).
  3. Thiết lập toàn bộ cấu trúc Codebase chuẩn Production:
     - `docker-compose.yml` (đã sửa lỗi Dual-Listener cho Kafka KRaft `INTERNAL://kafka:29092` & `EXTERNAL://localhost:9092`).
     - `configs/` (`paths.yaml`, `class_mapping.yaml`, `spark_config.yaml`, `model_config.yaml`).
     - `src/utils/` (xử lý cấu hình, chuẩn hóa `article_id` 10 ký tự, cố định seed).
     - `src/contracts/` (Pydantic schemas cho toàn bộ hệ thống).
     - `src/metrics/` (cài đặt chính xác hàm `MAP@12`, `Candidate Recall@K`, `nDCG@K`, `CatConsistency@K`, `Cohen's Kappa`).
     - Các module khung cho `src/cv/`, `src/recsys/`, `src/streaming/`, `src/backend/`, `src/frontend/`, `spark_jobs/`, và `scripts/`.
- **Kết quả kiểm thử / Số liệu thực nghiệm (Verification & Metrics):**
  - Chạy bộ kiểm thử tự động `tests/test_metrics_and_ids.py` kiểm chứng logic chuẩn hóa `article_id`, `MAP@12`, `nDCG@10` và Data Contracts.
- **Vấn đề tồn đọng / Lưu ý cho Agent tiếp theo (Next Steps):**
  - Bắt đầu **`TASK-01`** (bật `docker compose up -d` kiểm tra các container) và **`TASK-02`** (tải dữ liệu H&M + Fashionpedia vào `data/raw/` và chạy `scripts/check_hm256_aspect_ratio.py`).
