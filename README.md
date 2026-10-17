# End-to-End Multimodal Visual Search & Real-Time Personalized Fashion Recommendation System on Lakehouse Architecture

> **Đồ án Liên môn:** Computer Vision $\times$ Big Data $\times$ Recommendation Systems  
> **Dataset cốt lõi:** H&M Personalized Fashion Recommendations (105.542 sản phẩm, 1,37 triệu khách hàng, 31,78 triệu giao dịch) + Fashionpedia (48.8K ảnh đường phố) + Tập ảnh thực tế Việt Nam (VN Streetwear Evaluation Set).  
> **Triết lý thiết kế:** *Baseline-first $\rightarrow$ Đo lường nghiêm ngặt $\rightarrow$ Nâng cấp qua các cổng quyết định (Decision Gates).*

---

## 1. Bản đồ Tài liệu Dự án (Documentation Map)

Nếu bạn là **Người phát triển** hoặc **AI Agent** mới vào dự án, hãy đọc theo thứ tự sau:

| Tài liệu | Mục đích | Đối tượng đọc |
| :--- | :--- | :--- |
| **[`AGENTS.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/AGENTS.md)** | Quy tắc điều phối Multi-Agent, phân quyền, 8 quy tắc kỹ thuật bất khả xâm phạm. | **Bắt buộc cho mọi AI Agent** |
| **[`docs/STATE.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/STATE.md)** | Bảng theo dõi tiến độ thời gian thực, trạng thái các Decision Gates và số liệu đã đo. | Lead Agent, Sub-Agents, User |
| **[`docs/MASTER_PLAN.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/MASTER_PLAN.md)** | Kế hoạch thực thi tổng thể (Plan v3) chia theo 6 Work Packages, danh sách Task và tiêu chí nghiệm thu. | Lead Agent, Sub-Agents, User |
| **[`docs/ARCHITECTURE.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/ARCHITECTURE.md)** | Kiến trúc chi tiết 4 phân hệ: Lakehouse, Computer Vision, Hybrid RecSys, và Real-time Serving. | Tất cả |
| **[`docs/DATA_CONTRACTS.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/DATA_CONTRACTS.md)** | Đặc tả Schema của các bảng Delta/Parquet, Qdrant Payload, Redis Keys, Kafka Event và FastAPI. | Sub-Agents khi viết code |
| **[`docs/INFRA_AND_COLAB_GUIDE.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/INFRA_AND_COLAB_GUIDE.md)** | Hướng dẫn kết hợp Laptop RTX 4060 $\leftrightarrow$ Colab Pro+, xử lý model lớn (ONNX FP16/INT8, tách CPU/GPU) và cơ chế kết nối/đồng bộ. | User & CV/RecSys Agents |
| **[`docs/HANDOFF.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/HANDOFF.md)** | Nhật ký bàn giao công việc giữa các Agent qua từng phiên làm việc. | Lead Agent & Sub-Agents |
| **[`docs/SUBAGENT_PROMPTS.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/SUBAGENT_PROMPTS.md)** | Các mẫu prompt chuẩn để gọi Sub-Agents thực thi từng module. | Lead Agent & User |
| **[`docs/ke_hoach_ban_dau/`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/ke_hoach_ban_dau/)** | Lưu trữ bản thảo ban đầu (v1, v2) và bản nhận xét/hiệu chỉnh kỹ thuật. | Tham khảo lịch sử |

---

## 2. Cấu trúc Thư mục Codebase (Repository Structure)

```text
fashion-lakehouse-recsys/
├── AGENTS.md                        # Quy chuẩn điều phối Multi-Agent (Đọc đầu tiên)
├── README.md                        # Tổng quan dự án & hướng dẫn chạy nhanh
├── docker-compose.yml               # Hạ tầng Docker (Kafka KRaft, Kafka-UI, Qdrant, Redis, MinIO opt)
├── pyproject.toml                   # Quản lý package, dependencies & cấu hình pytest/ruff
├── requirements.txt                 # Thư viện Python cho máy local (WSL2 / Windows)
├── requirements-colab.txt           # Thư viện tinh gọn cho các job huấn luyện trên Colab Pro+
├── .env.example                     # Biến môi trường mẫu
│
├── docs/                            # TÀI LIỆU VẬN HÀNH CHÍNH THỨC
│   ├── MASTER_PLAN.md               # Kế hoạch tổng thể v3, Work Packages & Decision Gates
│   ├── STATE.md                     # Trạng thái dự án trực tiếp (Single Source of Truth)
│   ├── ARCHITECTURE.md              # Thiết kế kiến trúc hệ thống chi tiết
│   ├── DATA_CONTRACTS.md            # Chuẩn hóa Schema, bảng, khóa Redis, Qdrant, API
│   ├── INFRA_AND_COLAB_GUIDE.md     # Chiến lược Colab Pro+, tối ưu VRAM RTX 4060 & kết nối
│   ├── HANDOFF.md                   # Nhật ký bàn giao giữa các Sub-Agents
│   ├── SUBAGENT_PROMPTS.md          # Prompt mẫu để phân việc cho Sub-Agents
│   └── ke_hoach_ban_dau/            # Hồ sơ thảo luận ban đầu (đã đóng băng)
│
├── configs/                         # CẤU HÌNH HỆ THỐNG TẬP TRUNG
│   ├── paths.yaml                   # Đường dẫn dữ liệu, lakehouse, models, reports
│   ├── class_mapping.yaml           # Ánh xạ 46 lớp Fashionpedia -> 12 lớp YOLO -> H&M product_type
│   ├── spark_config.yaml            # Cấu hình tối ưu PySpark + Delta Lake cho RAM 16GB-24GB
│   └── model_config.yaml            # Siêu tham số cho CV, ALS, LightGBM, Two-Tower
│
├── src/                             # MÃ NGUỒN PYTHON CỐT LÕI
│   ├── utils/                       # Tiện ích dùng chung (config loader, pad article_id, seed, logger)
│   ├── contracts/                   # Pydantic schemas cho Kafka, Qdrant, Redis, FastAPI
│   ├── metrics/                     # Hàm đo lường chuẩn (MAP@12, Candidate Recall@K, nDCG@10, Kappa)
│   ├── cv/                          # Module Computer Vision (Detector, Embedder, Qdrant, ONNX Export)
│   ├── recsys/                      # Module RecSys (Baselines, GPU Visual Affinity, LightGBM, Two-Tower)
│   ├── streaming/                   # Kafka Event Simulator & Producer
│   ├── backend/                     # FastAPI Serving Engine (Visual Search, Hybrid RecSys, Outfit)
│   └── frontend/                    # Giao diện Streamlit (E-Commerce Demo, Dashboard, Labeling App)
│
├── spark_jobs/                      # PIPELINE BIG DATA (PYSPARK + DELTA LAKE)
│   ├── spark_session.py             # Khởi tạo SparkSession chuẩn với Delta Lake & AQE
│   ├── batch/                       # Các job Batch (B0_ingest -> B8_export)
│   └── streaming/                   # Các job Spark Structured Streaming (S1_bronze -> S4_kpi)
│
├── scripts/                         # SCRIPTS TIỆN ÍCH & KIỂM ĐỊNH DỮ LIỆU
│   ├── check_hm256_aspect_ratio.py  # Kiểm tra ảnh H&M 256x256 có bị méo tỉ lệ không
│   └── resize_hm_aspect_pad.py      # Resize ảnh giữ nguyên tỉ lệ + pad nền trắng (Letterbox)
│
├── colab/                           # NOTEBOOK & SCRIPT CHẠY TRÊN GOOGLE COLAB PRO+
│   └── README_COLAB.md              # Quy trình chạy job nặng trên Colab L4 và tự động ngắt runtime
│
├── tests/                           # UNIT TESTS & INTEGRATION TESTS
│   └── test_metrics_and_ids.py      # Kiểm thử tự động cho chuẩn hóa ID và các hàm đo MAP@12, nDCG@10
│
├── data/                            # DỮ LIỆU (Được .gitignore, lưu trên đĩa cục bộ/WSL2)
├── models/                          # TRỌNG SỐ MÔ HÌNH ĐÃ XUẤT ONNX / LGBM (Được .gitignore)
└── reports/                         # BẢNG SỐ LIỆU & BIỂU ĐỒ THỰC NGHIỆM
    ├── figures/
    └── tables/
```

---

## 3. Khởi động Nhanh (Quickstart)

### Bước 1: Cài đặt môi trường & Chạy Unit Tests kiểm tra nền tảng
```bash
# Tạo môi trường ảo kế thừa toàn bộ thư viện đã cài ở bản Global (PyTorch CUDA, NumPy, Pandas...)
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv --system-site-packages
# Kích hoạt trên Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Kích hoạt trên WSL2/Linux: source .venv/bin/activate

# Chạy bộ kiểm thử đơn vị (Unit Tests) cho ID padding, Two-Tower & Metrics (MAP@12, nDCG@10)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Bước 2: Khởi động Hạ tầng Docker (Qdrant, Redis, Kafka KRaft, Kafka-UI)
```bash
docker compose up -d
```
* **Qdrant Dashboard:** `http://localhost:6333/dashboard`
* **Kafka UI:** `http://localhost:8080`
* **Redis:** `localhost:6379`
* *(Tùy chọn)* Nếu muốn bật thêm **MinIO S3**: `docker compose --profile s3 up -d` (`http://localhost:9001`).

### Bước 3: Kiểm tra chất lượng ảnh H&M 256x256 (Task đầu tiên của Tuần 1)
```bash
python scripts/check_hm256_aspect_ratio.py --image-dir data/raw/hm/images
```
