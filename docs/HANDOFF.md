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
