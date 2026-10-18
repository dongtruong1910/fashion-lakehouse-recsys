# BỘ PROMPT MẪU ĐỂ ĐIỀU PHỐI SUB-AGENTS (SUB-AGENT DISPATCH PROMPTS)

> **Mục đích:** Khi Lead Agent (thông qua công cụ `invoke_subagent`) hoặc Người dùng muốn giao một Work Package / Task cho một Sub-Agent chuyên biệt, hãy dùng các mẫu Prompt chuẩn dưới đây để Sub-Agent nắm đầy đủ ngữ cảnh và không làm sai quy chuẩn của dự án.

---

## 1. Prompt Giao việc cho `Data & Lakehouse Sub-Agent` (`WP-1` & `WP-5`)

```text
Role: Data & Lakehouse Engineer Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-BD-01 / TASK-BD-02 / TASK-BD-03 / TASK-BD-04] trong dự án Hệ thống Tìm kiếm Ảnh & Gợi ý Thời trang trên kiến trúc Lakehouse.

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC ĐÚNG THỨ TỰ:
1. AGENTS.md (nắm 8 quy tắc vàng: giữ số 0 đầu cho article_id 10 ký tự, ánh xạ customer_id sang customer_idx int32 có mapping_version, lịch tuần neo tại 2018-09-19, cô lập --smoke-test).
2. docs/STATE.md và docs/HANDOFF.md (nắm trạng thái hiện tại và bàn giao gần nhất).
3. docs/MASTER_PLAN.md (xem chi tiết Task và Acceptance Criteria).
4. docs/DATA_CONTRACTS.md (Mục 1, 2, 4, 5 — tuân thủ tên cột Silver/Gold, khóa Redis idempotent và bản tin Kafka).
5. configs/spark_config.yaml và configs/paths.yaml.

YÊU CẦU THỰC THI:
- Hoàn thiện code trong thư mục `spark_jobs/`, `src/streaming/` và `tests/`.
- Bắt buộc chạy chế độ `--smoke-test` (ghi vào `data/lakehouse_smoke/`, tuyệt đối không ghi đè `data/lakehouse/` chính) trước khi chạy toàn bộ 31,8 triệu dòng.
- Lưu bảng số liệu benchmark thực tế (kèm seed & timestamp) vào `reports/tables/` và cập nhật `docs/STATE.md` + `docs/HANDOFF.md` trước khi báo cáo hoàn thành.
```

---

## 2. Prompt Giao việc cho `Computer Vision Sub-Agent` (`WP-1` & `WP-2`)

```text
Role: Computer Vision Engineer Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-CV-01 / TASK-CV-02 / TASK-CV-03 / TASK-CV-04A / TASK-CV-04B / TASK-CV-05 / TASK-CV-06].

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC ĐÚNG THỨ TỰ:
1. AGENTS.md, docs/STATE.md và docs/HANDOFF.md.
2. docs/MASTER_PLAN.md (xem tiêu chí GATE-CV-1, GATE-CV-2 và giao thức đánh giá 3 tầng).
3. docs/ARCHITECTURE.md (Mục 2.2) và docs/DATA_CONTRACTS.md (Mục 3 — cấu trúc Qdrant Named Vectors & Payload).
4. docs/INFRA_AND_COLAB_GUIDE.md (nắm rõ cái gì chạy trên Laptop RTX 4060 8GB VRAM, cái gì chạy trên Colab L4, và quy tắc xuất ONNX + tự động gọi runtime.unassign()).
5. configs/class_mapping.yaml và configs/model_config.yaml.

YÊU CẦU THỰC THI:
- Hoàn thiện code trong `src/cv/`, `scripts/`, `colab/` và `tests/`.
- Đảm bảo chia tập H&M theo `product_code` (`data/splits/hm_split_v1.parquet`: 85% Train / 7.5% Val-Dev / 7.5% Test-Final), loại trừ chính `article_id` truy vấn khi tính `I2I Precision@10` và đo `CatConsistency@10` trước khi lọc payload.
- Chạy thử nghiệm trên 200 ảnh (`--limit 200`) để kiểm tra VRAM và đầu ra trước khi chạy toàn bộ 105.100 ảnh.
- Ghi kết quả đo đạc thực tế vào `reports/tables/` và cập nhật `docs/STATE.md` + `docs/HANDOFF.md`.
```

---

## 3. Prompt Giao việc cho `RecSys Modeling Sub-Agent` (`WP-1`, `WP-3` & `WP-4`)

```text
Role: Recommendation System Engineer Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-REC-01 / TASK-REC-02 / TASK-REC-03 / TASK-REC-04 / TASK-REC-05 / TASK-REC-06].

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC ĐÚNG THỨ TỰ:
1. AGENTS.md, docs/STATE.md và docs/HANDOFF.md (Chú ý Quy tắc #4 tách Dev Week 103 / Final Test Week 104 và Quy tắc #5 lọc Active Users + gom nhóm LambdaRank theo (target_week, customer_idx)).
2. docs/MASTER_PLAN.md (xem tiêu chí GATE-REC-1 và GATE-REC-2).
3. docs/ARCHITECTURE.md (Mục 2.3) và docs/DATA_CONTRACTS.md (Mục 2.2 — Schema bảng gold/candidate_features).
4. src/metrics/recsys_metrics.py và configs/model_config.yaml.

YÊU CẦU THỰC THI:
- Hoàn thiện code trong `src/recsys/` và `tests/`.
- Khi tính đặc trưng tương đồng thị giác (`visual_affinity_score`), dùng hàm chia batch trong `src/recsys/features_gpu.py`.
- Khi huấn luyện LightGBM (`src/recsys/lgbm_ranker.py`), dùng `prepare_lgbm_query_frame` để group theo `(target_week, customer_idx)`, tune/early-stop trên Dev Week 103 và báo cáo cuối trên Final Week 104.
- Lưu kết quả `MAP@12`, `Recall@12`, `Candidate Recall@100` và `Cold-start Item Recall` vào `reports/tables/`, cập nhật `docs/STATE.md` + `docs/HANDOFF.md`.
```

---

## 4. Prompt Giao việc cho `Serving & UI Sub-Agent` (`WP-6`)

```text
Role: Full-Stack AI Serving & UI Sub-Agent
Nhiệm vụ của bạn là thực hiện [TASK-SRV-01 / TASK-SRV-02].

TRƯỚC KHI VIẾT CODE, BẮT BUỘC ĐỌC ĐÚNG THỨ TỰ:
1. AGENTS.md, docs/STATE.md và docs/HANDOFF.md.
2. docs/MASTER_PLAN.md (xem yêu cầu WP-6).
3. docs/DATA_CONTRACTS.md (Mục 3, 4, 5, 6 — đặc tả Qdrant, Redis idempotent keys, Kafka và REST API endpoints).
4. docs/INFRA_AND_COLAB_GUIDE.md (Mục 2 — Quy tắc đặt Detector & Vision Encoder trên GPU ONNX FP16, đặt Text Encoder, Two-Tower User Encoder & LightGBM trên CPU).

YÊU CẦU THỰC THI:
- Hoàn thiện FastAPI Backend tại `src/backend/main.py` (tách `/health` liveness và `/ready` readiness) và giao diện Streamlit 4 Tabs tại `src/frontend/app.py`.
- Viết integration test kiểm tra các endpoints phản hồi đúng schema trong `src/contracts/schemas.py`.
- Lưu kết quả đo độ trễ và VRAM thực tế vào `reports/tables/serving_latency.json` và cập nhật `docs/STATE.md` + `docs/HANDOFF.md`.
```
