# BỘ PROMPT MẪU ĐỂ ĐIỀU PHỐI SUB-AGENTS (SUB-AGENT DISPATCH PROMPTS)

> **Mục đích:** Khi Lead Agent (thông qua công cụ `invoke_subagent`) hoặc Người dùng muốn giao một Work Package / Task cho một Sub-Agent chuyên biệt, hãy dùng các mẫu Prompt chuẩn dưới đây để Sub-Agent nắm đầy đủ ngữ cảnh và không làm sai quy chuẩn của dự án.

---

## 1. Prompt Giao việc cho `Data & Lakehouse Sub-Agent` (`WP-1` & `WP-5`)

```text
Role: Data & Lakehouse Engineer Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-BD-01 / TASK-BD-02 / TASK-BD-03 / TASK-BD-04] trong dự án Hệ thống Tìm kiếm Ảnh & Gợi ý Thời trang trên kiến trúc Lakehouse.

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC:
1. AGENTS.md (nắm 8 quy tắc vàng, đặc biệt quy tắc giữ số 0 ở đầu cho article_id 10 ký tự và ánh xạ customer_id sang customer_idx int32).
2. docs/STATE.md và docs/HANDOFF.md (nắm trạng thái hiện tại).
3. docs/DATA_CONTRACTS.md (Mục 1, 2, 4, 5 — tuyệt đối tuân thủ tên cột và kiểu dữ liệu của các bảng Silver/Gold, khóa Redis và bản tin Kafka).
4. configs/spark_config.yaml và configs/paths.yaml.

YÊU CẦU THỰC THI:
- Hoàn thiện code trong thư mục `spark_jobs/` và `src/streaming/`.
- Bắt buộc viết chế độ `--smoke-test` (chạy thử trên 5.000 dòng giao dịch) và chạy kiểm chứng thành công trước khi chạy toàn bộ 31,8 triệu dòng.
- Lưu bảng số liệu benchmark thực tế vào `reports/tables/` và cập nhật `docs/STATE.md` + `docs/HANDOFF.md` trước khi báo cáo hoàn thành.
```

---

## 2. Prompt Giao việc cho `Computer Vision Sub-Agent` (`WP-1` & `WP-2`)

```text
Role: Computer Vision Engineer Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-CV-01 / TASK-CV-02 / TASK-CV-03 / TASK-CV-04 / TASK-CV-05 / TASK-CV-06].

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC:
1. AGENTS.md và docs/STATE.md.
2. docs/ARCHITECTURE.md (Mục 2.2) và docs/DATA_CONTRACTS.md (Mục 3 — cấu trúc Qdrant Named Vectors & Payload).
3. docs/INFRA_AND_COLAB_GUIDE.md (nắm rõ cái gì chạy trên Laptop RTX 4060 8GB VRAM ở chuẩn FP16, cái gì đóng gói lên Colab L4, và quy tắc xuất ONNX FP16 + tự động gọi runtime.unassign()).
4. configs/class_mapping.yaml và configs/model_config.yaml.

YÊU CẦU THỰC THI:
- Hoàn thiện code trong `src/cv/` và notebook tương ứng trong `colab/` (nếu cần train trên Colab L4).
- Đảm bảo chia tập H&M theo `product_code` (không rò rỉ các màu của cùng một kiểu dáng giữa train và test).
- Chạy thử nghiệm trên 200 ảnh (`--limit 200`) để kiểm tra VRAM và đầu ra trước khi chạy toàn bộ 105.100 ảnh.
- Ghi kết quả đo đạc thực tế vào `reports/tables/` và cập nhật `docs/STATE.md` + `docs/HANDOFF.md`.
```

---

## 3. Prompt Giao việc cho `RecSys Modeling Sub-Agent` (`WP-1`, `WP-3` & `WP-4`)

```text
Role: Recommendation System Engineer Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-REC-01 / TASK-REC-02 / TASK-REC-03 / TASK-REC-04 / TASK-REC-05 / TASK-REC-06].

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC:
1. AGENTS.md (Chú ý Quy tắc #4 chống rò rỉ thời gian và Quy tắc #5 chỉ tạo bảng huấn luyện LightGBM trên nhóm Active Users ~70.000 khách/tuần để không tràn RAM).
2. docs/ARCHITECTURE.md (Mục 2.3) và docs/DATA_CONTRACTS.md (Mục 2.2 — Schema bảng gold/candidate_features).
3. src/metrics/recsys_metrics.py (sử dụng đúng hàm map_at_k và candidate_recall_at_k đã có unit test).

YÊU CẦU THỰC THI:
- Hoàn thiện code trong `src/recsys/`.
- Khi tính đặc trưng tương đồng thị giác (`visual_affinity_score`), bắt buộc dùng GPU RTX 4060 qua `src/recsys/features_gpu.py` (không dùng PySpark UDF).
- Khi huấn luyện mạng Two-Tower (`src/recsys/two_tower.py`), giữ độ dài chuỗi lịch sử `N = 15`, đóng băng bảng vector ảnh trong VRAM và xuất nhánh User Tower sang `models/two_tower_user.onnx`.
- Lưu kết quả `MAP@12`, `Recall@12`, `Candidate Recall@100` và `Cold-start Item Recall` vào `reports/tables/`, cập nhật `docs/STATE.md` + `docs/HANDOFF.md`.
```

---

## 4. Prompt Giao việc cho `Serving & UI Sub-Agent` (`WP-6`)

```text
Role: Full-Stack AI Serving & UI Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-SRV-01 / TASK-SRV-02].

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC:
1. AGENTS.md và docs/STATE.md.
2. docs/DATA_CONTRACTS.md (Mục 3, 4, 5, 6 — đặc tả Qdrant, Redis, Kafka và 4 REST API endpoints).
3. docs/INFRA_AND_COLAB_GUIDE.md (Mục 2 — Quy tắc đặt YOLO11 & Vision Encoder trên GPU ONNX FP16, đặt Text Encoder, Two-Tower User Encoder & LightGBM trên CPU để tổng VRAM < 1.2GB).

YÊU CẦU THỰC THI:
- Hoàn thiện FastAPI Backend tại `src/backend/main.py` và giao diện Streamlit 4 Tabs tại `src/frontend/app.py`.
- Viết integration test kiểm tra 4 endpoints phản hồi đúng schema Pydantic trong `src/contracts/schemas.py` với độ trễ p95 < 150ms.
- Cập nhật `docs/STATE.md` + `docs/HANDOFF.md` sau khi kiểm thử thành công.
```
