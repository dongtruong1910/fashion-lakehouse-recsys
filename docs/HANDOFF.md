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
