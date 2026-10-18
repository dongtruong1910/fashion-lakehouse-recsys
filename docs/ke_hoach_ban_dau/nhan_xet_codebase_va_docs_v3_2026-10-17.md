# NHẬN XÉT CHI TIẾT CODEBASE VÀ TÀI LIỆU PLAN v3 — 2026-10-17

> **Phạm vi:** Review source code, tests, configs, cấu hình hạ tầng và tài liệu vận hành của dự án CV × Big Data × RecSys.
>
> **Mốc bằng chứng:** Audit ngày 2026-10-17, Git HEAD `7da8232`; kết quả probe lưu lúc `2026-10-17T20:37:58+07:00`, seed `42`. File Markdown này tổng hợp lại đầy đủ nhận định của lượt review đó theo yêu cầu người dùng.
>
> **Trạng thái:** Các phát hiện A01–A20 vẫn `OPEN` tại thời điểm ghi nhận; chưa sửa implementation. Những phương án thay đổi split, phạm vi hoặc acceptance criteria trong file này là **đề xuất**, chưa thay thế các quy tắc hiện hành.
>
> **Vai trò tài liệu:** Hồ sơ review nằm trong `ke_hoach_ban_dau/`, không phải đặc tả triển khai mới. Khi chốt điều chỉnh, cần cập nhật tài liệu vận hành tương ứng.

Bằng chứng có cấu trúc: [codebase_review_2026-10-17.json](../../reports/tables/codebase_review_2026-10-17.json).

Tài liệu đối chiếu: [AGENTS.md](../../AGENTS.md), [STATE.md](../STATE.md), [HANDOFF.md](../HANDOFF.md), [MASTER_PLAN.md](../MASTER_PLAN.md), [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [INFRA_AND_COLAB_GUIDE.md](../INFRA_AND_COLAB_GUIDE.md), [SUBAGENT_PROMPTS.md](../SUBAGENT_PROMPTS.md), [README.md](../../README.md).

## 1. Kết luận tổng thể

**Hướng thiết kế tốt, nhưng repo hiện chưa đủ ổn để chạy full dữ liệu hoặc triển khai nhiều nhánh độc lập.** Đây là bộ khung có một số utilities, model wrappers và thuật toán đã viết, chưa có hệ thống end-to-end được kiểm chứng.

Có ba lớp vấn đề cần phân biệt:

1. **Lỗi implementation hiện hữu:** Chia sai tuần, group LambdaRank sai, smoke ghi đè dữ liệu chính, diễn giải nhãn detector sai, history rỗng sinh NaN, validation thiếu và cấu hình persistence Kafka chưa đúng.
2. **Lỗi hoặc khoảng trống trong thiết kế:** Chưa tách dev/final, giao thức CV chưa đủ cụ thể, clock replay/live trộn chung, Redis session có hai writer, contracts giữa các tài liệu mâu thuẫn.
3. **Chức năng chưa triển khai:** API/UI, streaming thực tế, full ETL, huấn luyện, benchmark và tích hợp. Những phần này chưa hoàn thành là phù hợp với giai đoạn WP-0, nhưng không nên mô tả là đã hoàn thiện hoặc production-ready.

**Không cần thay toàn bộ kiến trúc hay đổi tên thư mục để giải quyết.** Cần làm chắc correctness, evaluation và contracts, sau đó xây một luồng nhỏ chạy xuyên suốt trước khi mở rộng.

## 2. Những điểm tốt nên giữ

| Điểm thiết kế | Giá trị thực tế |
| :--- | :--- |
| Baseline-first và Decision Gates | Tạo mốc so sánh trước khi đầu tư huấn luyện; cho phép giữ baseline nếu mô hình phức tạp không cải thiện. |
| H&M làm trục dữ liệu, Fashionpedia bổ trợ detector | Giữ được một catalog và lịch sử giao dịch chung để nối CV với RecSys. |
| Retrieval → ranking | Phân biệt bài toán tìm ứng viên với xếp hạng; có chỗ đo Candidate Recall trước khi đổ lỗi cho ranker. |
| Quy tắc giữ `article_id` 10 ký tự | Ngăn lỗi join, đường dẫn ảnh và đồng bộ vector khi mất số 0 đầu. |
| `customer_idx` và lọc active users | Đúng hướng tiết kiệm bộ nhớ; cần đo trên pipeline thật thay vì khẳng định trước mức RAM/thời gian. |
| Feature chỉ dùng dữ liệu trước tuần nhãn | Là nguyên tắc quan trọng nhất để kết quả RecSys có ý nghĩa. |
| Local Delta mặc định, MinIO tùy chọn | Hợp lý cho một máy cá nhân; tránh biến object storage thành dependency bắt buộc cho mọi bước. |
| Tách CV/Data/RecSys/Serving, có STATE/HANDOFF/contracts | Có nền để điều phối công việc và truy vết trách nhiệm. |
| Giữ lịch sử kế hoạch | Bảo toàn lý do lựa chọn và các phương án đã cân nhắc. |
| Metrics Registry dùng `[TBD]` | Trung thực với trạng thái chưa thực nghiệm; cần áp dụng cùng nguyên tắc cho bảng VRAM, latency và CU ở các file khác. |

## 3. Phạm vi kiểm tra và giới hạn bằng chứng

### 3.1. Những gì đã chạy ở lượt audit

| Kiểm tra | Kết quả đã ghi nhận | Ý nghĩa và giới hạn |
| :--- | :--- | :--- |
| `python -m unittest discover -s tests -v` bằng venv hiện có | 6/6 PASS, 11.413 giây | Chỉ những trường hợp đang có trong unittest; không chứng minh toàn bộ hệ thống đúng. |
| Script kiểm liên kết Markdown | 66 links/13 Markdown files PASS sau cập nhật journal của lượt audit | Đây là số tại snapshot trước khi tạo file review Markdown này. |
| `ast.parse` | 37/37 file Python hợp lệ cú pháp | Không kiểm dependency, runtime hay logic. |
| `docker compose config --quiet` | Exit 0 | Chỉ kiểm cấu hình parse được; có cảnh báo access denied khi đọc Docker user config. |
| `python -m pytest tests/` | Không chạy được: `No module named pytest` | Không được mô tả là pytest pass. |
| Probe ngày/tuần | 16/09/2020 → 103; 17–22/09 → 104 | Tái hiện phép tính đang dùng trong code bằng thư viện ngày của Python. |
| Probe group LightGBM | Group hiện tại `[4]`; đúng phải `[2, 2]` | Dùng stub để bắt tham số Dataset; chưa train bằng LightGBM thật. |
| Probe UserTower CPU eval | History rỗng → 64/64 chiều NaN | Đã chạy module PyTorch thật trên tensor nhỏ. |
| Probe contracts | Constructor nhận các giá trị trái hợp đồng | Kiểm đường constructor trực tiếp; chưa kiểm validation của FastAPI. |
| Probe detector | COCO `person → top`, `handbag → other` | Giả lập output detector để kiểm logic mapping; không đo mAP. |
| Probe aspect ratio | Ảnh đã kéo méo vẫn pass heuristic viền trắng | Ảnh tổng hợp; chứng minh heuristic không đủ để kết luận giữ tỉ lệ. |
| Probe Candidate Recall | List → 1.0; iterator cùng dữ liệu → 0.0 | Lỗi utility đã tái hiện. |
| Probe setuptools discovery | Tự nhận package `backend`, `contracts`, `cv`… dưới `src/` | Chưa build/install wheel; cấu hình discovery không khớp namespace import. |

### 3.2. Những gì chưa kiểm chứng

Tại snapshot audit, `data/raw/` chưa có, `models/` chỉ có file giữ thư mục và `reports/tables/` chỉ có file giữ thư mục trước khi tạo kết quả review.

Chưa khởi động Docker, chưa kiểm image pull, network hoặc persistence thực tế; chưa chạy Spark/Delta, ingest dataset, train model, benchmark retrieval/ranking, xuất và chạy ONNX, kiểm API/UI hay load test end-to-end.

Không cài thêm thư viện, không tải dữ liệu/model, không sửa source/config/requirements. Thay đổi có sẵn ở MASTER_PLAN được giữ nguyên.

Các số từ probe là **bằng chứng lỗi trên dữ liệu nhỏ hoặc tổng hợp**, không phải kết quả chất lượng hay hiệu năng của hệ thống.

## 4. Danh sách 20 phát hiện

Quy ước ưu tiên:

- **P1:** Cần xử lý trước khi chạy dữ liệu/model phụ thuộc hoặc trước khi triển khai phân hệ theo đặc tả liên quan.
- **P2:** Cần xử lý để kết quả tái lập, vận hành rõ ràng và báo cáo đúng; có thể sắp theo milestone của phân hệ.
- Loại bằng chứng được ghi riêng để phân biệt lỗi đã chạy tái hiện với kết luận từ source hoặc vấn đề thiết kế.

### A01 — P1 — Lịch tuần validation đang sai

**Vị trí:** [b1_clean_silver.py](../../spark_jobs/batch/b1_clean_silver.py), dòng 32–36; [paths.yaml](../../configs/paths.yaml), dòng 15–19; [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), quy ước `week_num`.

Code dùng:

```python
floor((t_dat - date(2018, 9, 20)).days / 7)
```

Kết quả tái tính:

| Ngày | Week hiện tại |
| :--- | ---: |
| 2020-09-15 | 103 |
| 2020-09-16 | 103 |
| 2020-09-17 | 104 |
| 2020-09-22 | 104 |

Contract yêu cầu toàn bộ 16–22/09 thuộc tuần 104. Nếu train lọc tuần 101–103 và validation lọc tuần 104, ngày đầu validation sẽ vào train, đồng thời validation chỉ còn sáu ngày.

**Đề xuất:** Định nghĩa một hàm date-to-week dùng chung, neo theo khoảng tuần đã chốt. Ví dụ có thể neo vào ngày đầu tuần 104, nhưng phải kiểm cả các tuần trước thay vì cộng một hằng số để chữa riêng ngày cuối. Feature vẫn phải lọc bằng điều kiện ngày `t_dat < label_start`.

**Kiểm chứng khi sửa:** Test mọi ngày trong tuần validation, ngày trước/sau biên và quan hệ giữa week label với cutoff feature. Chưa chạy Spark thật trong audit.

### A02 — P1 — LambdaRank gom nhiều tuần của cùng khách thành một query

**Vị trí:** [lgbm_ranker.py](../../src/recsys/lgbm_ranker.py), dòng 68–72; [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), schema candidate features.

Code sort và group chỉ theo `customer_idx`. Một khách có mặt ở tuần 101 và 102 là hai bài toán xếp hạng khác nhau, với lịch sử và nhãn khác nhau.

Probe một khách, hai tuần, hai ứng viên/tuần thu được group sizes `[4]`; đúng phải là `[2, 2]`. Đây là bằng chứng ở tham số truyền cho Dataset qua stub, chưa phải thí nghiệm train LightGBM.

**Đề xuất:**

- Query key = `(target_week, customer_idx)`.
- Khóa duy nhất của hàng = `(target_week, customer_idx, article_id)`.
- Sort các hàng liên tiếp theo query trước khi tính group sizes.
- Kiểm tổng group sizes bằng số hàng.
- Phân biệt nhóm toàn nhãn 0 có thể bỏ khi train với candidate miss phải được giữ là thất bại trong đánh giá toàn pipeline.

Nguồn đối chiếu: [LightGBM Dataset group](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Dataset.html).

### A03 — P1 — Smoke B0 có thể ghi đè Bronze đầy đủ

**Vị trí:** [b0_ingest_bronze.py](../../spark_jobs/batch/b0_ingest_bronze.py), dòng 31–39 và 45–48.

`--smoke-test` chỉ giới hạn 5.000 dòng nhưng giữ `mode("overwrite")` và cùng output path với full run. Chạy smoke sau full ETL sẽ thay nội dung Bronze chính bằng mẫu nhỏ.

**Đề xuất:** Smoke dùng data root riêng hoặc output tường minh, có kiểm tra từ chối ghi smoke vào đường dẫn chính. Manifest ghi rõ chế độ, input, số dòng và output.

Đường chạy B1 cũng cần bảo toàn/version mapping: hiện mapping được tạo lại từ khách xuất hiện trong input rồi overwrite. Khi dùng mẫu khác hoặc thêm khách, dense indices có thể thay đổi; model/vector/cache cũ không thể được dùng như vẫn cùng mapping.

**Kiểm chứng khi sửa:** Chạy full fixture nhỏ, chạy smoke sau đó và xác nhận output chính không đổi. Không thực hiện ghi đè hay chạy Spark trong audit.

### A04 — P1 — Detector áp mapping fashion12 cho checkpoint COCO

**Vị trí:** [detector.py](../../src/cv/detector.py), dòng 20–31 và 46–60; [model_config.yaml](../../configs/model_config.yaml), dòng 39–42.

Mặc định `train_model` là `yolo11m.pt`, một checkpoint pretrained COCO80. Wrapper lại coi class IDs của mọi checkpoint là IDs của 12 lớp fashion.

Probe output giả lập:

| Nhãn nguồn COCO | Nhãn wrapper trả |
| :--- | :--- |
| `0: person` | `top` |
| `26: handbag` | `other` |

Output hợp lệ hình thức nhưng sai ngữ nghĩa. `zeroshot_model` chưa được chọn trong đường mặc định; chưa có thiết lập class prompts tương ứng cho YOLO-World. Constructor nhận `device` nhưng chưa truyền vào `predict()`.

**Đề xuất:** Phân biệt checkpoint pretrained, zero-shot và fashion12 đã train. Kiểm `model.names`/metadata ontology, từ chối model không khớp; truyền device tường minh.

**Giới hạn:** Chưa tải checkpoint hoặc đo accuracy; đã kiểm logic mapping bằng giả lập và đối chiếu [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/).

### A05 — P1 — UserTower trả NaN khi lịch sử rỗng

**Vị trí:** [two_tower.py](../../src/recsys/two_tower.py), dòng 112–124; [test_metrics_and_ids.py](../../tests/test_metrics_and_ids.py), test Two-Tower.

Khi `history_padding_mask` toàn `True`, attention không có key hợp lệ và output sinh NaN. `denom.clamp(min=1)` không giải quyết vì `NaN * 0` vẫn là NaN.

Probe CPU eval có một hàng history rỗng cho **64/64 chiều NaN**. Điều này ngăn truy vấn vector cho cold-start user và có thể làm loss hỏng nếu mẫu đó đi vào train.

**Đề xuất:** Tách hàng rỗng trước attention, dùng representation/fallback được quy định rõ như profile/age hoặc popularity.

**Kiểm chứng khi sửa:** Batch có cả hàng rỗng và không rỗng, batch hoàn toàn rỗng, vector và loss hữu hạn. Test hiện tại mới kiểm shape/norm trên history có dữ liệu.

### A06 — P1 — Contracts dataclass chưa kiểm đầy đủ dữ liệu

**Vị trí:** [schemas.py](../../src/contracts/schemas.py), dòng 34–56 và 75–78; [test_metrics_and_ids.py](../../tests/test_metrics_and_ids.py), dòng 132.

Tài liệu gọi là Pydantic schemas nhưng implementation dùng standard dataclass. `Literal` và type hints không tự validate constructor trực tiếp.

Constructor đã nhận đồng thời:

```python
FashionEvent(
    event_id="not-a-uuid",
    event_time="yesterday",
    ingest_time="tomorrow",
    customer_id="x",
    article_id="0108775015",
    event_type="delete",
    source="unknown",
    price=float("nan"),
    sales_channel_id=999,
)
```

Giá NaN vượt qua điều kiện chỉ kiểm `price < 0`. Payload Qdrant nhận `article_id="0108775015"` cùng `product_code="9999999"`; logic pad cũng có thể giữ chuỗi không phải chữ số. Test `cust_demo` hiện còn xác nhận một identity trái hợp đồng hex 64 ký tự.

**Đề xuất:** Một cơ chế validation nhất quán ở các biên producer/offline/API; kiểm enum, UUID, timestamp có timezone, customer identity, số hữu hạn và product prefix. Nếu hỗ trợ demo/session identity khác customer H&M, cần đặc tả riêng thay vì âm thầm nới contract.

**Giới hạn:** Finding này áp dụng constructor trực tiếp. Chưa cài/chạy FastAPI nên không kết luận FastAPI cũng bỏ qua validation Literal.

### A07 — P1 — Kafka chưa ghi log vào volume đã mount

**Vị trí:** [docker-compose.yml](../../docker-compose.yml), dòng 36–53.

Compose mount `/var/lib/kafka/data` nhưng thiếu `KAFKA_LOG_DIRS`. Đối chiếu đúng source image Apache Kafka 3.9.0: wrapper tạo `server.properties` từ env được truyền vào, defaults script chỉ thêm cluster ID, và log directory mặc định là `/tmp/kafka-logs`.

Như vậy message log và metadata có thể nằm trong filesystem container thay vì bind mount; xóa/tạo lại container có thể làm mất dữ liệu dù thư mục volume còn.

**Đề xuất:** Đặt `KAFKA_LOG_DIRS=/var/lib/kafka/data`, sau đó kiểm produce → recreate → consume, bao gồm metadata.

**Loại bằng chứng:** Source/config đã đối chiếu; chưa chạy Docker recreate. Compose parse pass không xác nhận persistence.

Nguồn: [Kafka wrapper 3.9.0](https://raw.githubusercontent.com/apache/kafka/3.9.0/core/src/main/scala/kafka/docker/KafkaDockerWrapper.scala), [configureDefaults](https://raw.githubusercontent.com/apache/kafka/3.9.0/docker/resources/common-scripts/configureDefaults), [ServerLogConfigs](https://raw.githubusercontent.com/apache/kafka/3.9.0/server-common/src/main/java/org/apache/kafka/server/config/ServerLogConfigs.java), [Dockerfile](https://raw.githubusercontent.com/apache/kafka/3.9.0/docker/jvm/Dockerfile).

### A08 — P1 — Replay 2020 và UI hiện tại dùng chung watermark

**Vị trí:** [ARCHITECTURE.md](../ARCHITECTURE.md), dòng 84–88; [event_simulator.py](../../src/streaming/event_simulator.py), dòng 29–36; [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), Kafka schema.

Replay giữ `event_time` năm 2020, UI dùng thời gian UTC hiện tại. Đặc tả đưa cả hai qua cùng topic/query và watermark 10 phút trên `event_time`.

Khi UI làm watermark tiến đến hiện tại, các bản ghi replay lịch sử đến sau có thể bị coi là quá trễ và bị loại ở stateful aggregation. Gắn `source` đơn thuần không tách state/watermark.

**Đề xuất:** Tách replay/live thành topic/query/checkpoint/Redis namespace độc lập; hoặc định nghĩa clock mô phỏng hiện tại và giữ ngày lịch sử trong trường riêng.

Timestamp giờ/phút/giây sinh ngẫu nhiên phải tiếp tục được ghi rõ là giả lập. Nếu muốn replay theo event-time, cần quy định thứ tự sau khi sinh timestamp.

**Đo latency:** Dùng thời điểm ingest/produce/sink phù hợp; không lấy `now - event_time` của giao dịch lịch sử.

Nguồn: [Spark Structured Streaming](https://spark.apache.org/docs/3.5.6/structured-streaming-programming-guide.html). Đây là lỗi thiết kế chưa được chạy integration.

### A09 — P1 — Redis session có hai writer và sink chưa có idempotency

**Vị trí:** [ARCHITECTURE.md](../ARCHITECTURE.md), dòng 89; [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), Redis và API events.

Contract cho API cập nhật recent session ngay, rồi architecture cho Spark cập nhật cùng danh sách. Một click có thể bị thêm hai lần dù chưa có retry.

`foreachBatch` mặc định at-least-once. Redis pipeline tăng hiệu quả gửi lệnh nhưng không tự ngăn ghi trùng hoặc xử lý partial failure.

Cửa sổ 15m/1m tạo nhiều window cho một event, trong khi key `trend:15m` chưa xác định window nào đang được publish, replace/increment ra sao và xóa item hết hạn thế nào.

**Đề xuất:**

- Một writer cho session hoặc dedup `event_id` dùng chung, nguyên tử.
- Quy định snapshot trending theo window/version; thay điểm tuyệt đối thay vì cộng lại vô điều kiện.
- Xác định checkpoint/run/batch identity và hành vi khi restart.
- Test duplicate delivery, retry sau partial write và hết hạn window.
- Kafka partition key chỉ bảo toàn thứ tự append trong partition; không tự bảo đảm thứ tự `event_time` của event đến muộn.

Nguồn: [Spark foreachBatch](https://spark.apache.org/docs/3.5.6/structured-streaming-programming-guide.html#using-foreach-and-foreachbatch).

### A10 — P1 — Chưa tách dữ liệu chọn mô hình và báo cáo cuối

**Vị trí:** [MASTER_PLAN.md](../MASTER_PLAN.md), TASK-CV-02 và TASK-REC-04; [ARCHITECTURE.md](../ARCHITECTURE.md), dòng 99; [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), split train/validation; [model_config.yaml](../../configs/model_config.yaml), early stopping.

Tuần 104 đang dùng cho đánh giá, early stopping và decision gates nhưng chưa có final holdout riêng. Tune nhiều lần rồi báo điểm trên cùng tuần sẽ làm kết quả mang tính model selection.

CV còn mâu thuẫn: MASTER_PLAN benchmark trên Val, ARCHITECTURE ghi Test. Fashionpedia và VN set chưa có quy tắc đóng băng dev/final đủ rõ.

**Phương án đề xuất, chưa áp dụng:**

| Nhánh | Train | Dev/chọn mô hình | Final |
| :--- | :--- | :--- | :--- |
| RecSys | Các tuần sớm hơn dev | Một tuần trước khoảng cuối | Giữ 16–22/09/2020 không dùng tune |
| H&M CV | Product groups train | Product groups val | Product groups test đã khóa |
| Fashionpedia | Phần train | Tách dev từ train | Giữ official val cho báo cáo cuối nếu chọn protocol này |
| VN | Không mặc định dùng để train | Một tập query phát triển | Query final tách theo ảnh gốc/người/outfit |

Nếu áp dụng phương án này cần cập nhật AGENTS/MASTER_PLAN/contracts/config cho nhất quán; không âm thầm đổi ý nghĩa tuần validation.

Mọi tuần phải có candidates, features và model snapshots theo cutoff của riêng tuần đó. Candidate generation không được dùng nhãn tương lai hoặc chèn positive validation vào candidate list để làm đẹp điểm.

### A11 — P1 — Protocol CV và pooled evaluation chưa đủ chặt

**Vị trí:** [MASTER_PLAN.md](../MASTER_PLAN.md), TASK-CV-02/CV-06; [class_mapping.yaml](../../configs/class_mapping.yaml), dòng 1–2; [cv_metrics.py](../../src/metrics/cv_metrics.py), dòng 22–40.

Các tên metric đã có nhưng thiếu quy tắc tạo query, gallery và relevance:

- T2I: Cần qrels rõ, query tiếng Việt/Anh, gallery size và quy tắc relevant.
- I2I: Phải loại chính article query; quy định vai trò các biến thể cùng product_code.
- CatConsistency: Nếu filter theo chính lớp đáp án trước khi đo thì metric có thể gần 100% do filter. Nên đo unfiltered, dùng ground-truth class để chấm.
- Crop: GT bbox là phép chẩn đoán encoder; predicted bbox mới phản ánh detector → search. Cần ghi cả miss detection.
- VN: Tất cả model cần cùng query split, cùng pool nhãn khử trùng lặp, chấm mù, cùng rubric và cùng IDCG.

Probe utility:

```text
ndcg_at_k([1])                         = 1.0
ndcg_at_k([1], [3, 3, 3, 1])          = 0.06515852978097801
```

Đây là ví dụ tổng hợp cho thấy dùng ideal từ riêng list trả về có thể gây so sánh sai. Hàm có tham số pool, nên cần bắt buộc caller đánh giá VN truyền common pool.

Tập VN 50 ảnh nên được xem là pilot cho tới khi có phân bố lớp, số query đủ relevant items và cách báo cáo bất định. Chỉ số CatConsistency đúng lớp chưa chứng minh đúng kiểu dáng, màu hoặc mức tương thích phối đồ.

### A12 — P1 — Các tài liệu chính mâu thuẫn về contracts tích hợp

**Vị trí:** [MASTER_PLAN.md](../MASTER_PLAN.md), [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [paths.yaml](../../configs/paths.yaml), [model_config.yaml](../../configs/model_config.yaml).

| Thành phần | MASTER_PLAN | Contract/architecture/config khác |
| :--- | :--- | :--- |
| Silver partition | `t_dat` | `week_num` |
| Feature table | `silver/lgbm_train_features`, 45 cột | `gold/candidate_features` hoặc `gold/ranker_dataset`, khoảng 25 feature |
| Qdrant Two-Tower | Collection `customer_history_tower` | `hm_products.two_tower_emb` |
| Streaming window | 5 phút | 15 phút, trượt 1 phút |
| Session key | `user:{customer_idx}:recent_clicks`, TTL 24h | `user:{customer_id}:recent`, TTL 7 ngày |
| Outfit API | `POST /outfit-recommend` | `GET /api/v1/outfit/{article_id}` |
| Encoder thứ ba | Marqo FashionSigLIP | FashionCLIP trong config, khác checkpoint và dimension |
| H&M split artifact | `product_splits.json` | `hm_split_v1.parquet` trong paths config |
| YOLO artifact | `yolo11m_fashion12.onnx` | `yolo11m_fashion_fp16.onnx` trong paths config |

Hậu quả là các agent có thể tuân thủ những file khác nhau nhưng tạo ra các module không kết nối được.

**Đề xuất:** DATA_CONTRACTS và schema được validate giữ tên chuẩn; plan/config/prompt tham chiếu nhất quán. Chốt tầng sở hữu, primary keys, cutoff, nullable/default policy và consumer.

Cần bổ sung contracts cho `article_idx`, mapping categorical indices, padding/OOV, version mapping và encoder fingerprint. Không chỉ đổi tên đường dẫn rồi coi là đã giải quyết kiến trúc.

`StringType(10)` trong mô tả Spark cũng cần viết chính xác: dùng StringType và kiểm độ dài/range riêng; declaration này không tự thực thi quy tắc ID 10 chữ số.

### A13 — P2 — Resource claims chưa đo và chính sách dtype/provider mâu thuẫn

**Vị trí:** [INFRA_AND_COLAB_GUIDE.md](../INFRA_AND_COLAB_GUIDE.md), dòng 11–71 và phần Colab SSH; [AGENTS.md](../../AGENTS.md), quy tắc 6; [features_gpu.py](../../src/recsys/features_gpu.py), dòng 45–78; [requirements.txt](../../requirements.txt), ONNX Runtime.

Tài liệu gọi bảng VRAM/latency là số thực tế và khẳng định bảo đảm 100% fit, trong khi chưa có artifact benchmark xác nhận. Các câu extract 105K trong vài phút, 7M pairs dưới vài giây, LightGBM cực nhẹ hoặc toàn backend khoảng 1.1GB cần chuyển thành ước lượng/mục tiêu.

**Rủi ro bộ nhớ cụ thể:**

- Code visual feature dùng FP32, khác mô tả FP16.
- Catalog 105.542 × 768 × FP32 là 324.225.024 bytes; đây mới là bảng gốc.
- Một tensor 7M × 768 × FP32 là **21.504.000.000 bytes**, trước các tensor tạm.
- Nhánh NumPy fallback đang gather toàn bộ candidate vectors cùng lúc, chưa batching.
- GPU gather/history/temporaries cũng cần đo peak; kích thước bảng embedding gốc không đủ để suy ra peak VRAM.

Những số trên là phép tính kích thước, không phải memory benchmark.

**Chính sách serving đề xuất:**

| Thành phần | Provider/dtype cần kiểm chứng |
| :--- | :--- |
| Detector, vision encoder | GPU FP16, có kiểm parity và peak memory |
| Text/user encoder CPU | FP32 hoặc INT8 sau validation |
| LightGBM | Native Booster CPU |

Không nên yêu cầu mọi model FP16 một cách đồng loạt. Requirements hiện chọn ORT CPU, extra CV chọn ORT GPU; cần một phương án cài rõ ràng.

**Colab:** CU/time/GPU availability cần ghi là dự toán phụ thuộc runtime. FAQ phân biệt hạn chế remote control của free/no-positive-CU với paid còn CU; câu SSH luôn vi phạm là quá rộng. Cloudflare tunnel cũng không tự thay đổi điều kiện sử dụng hoặc biến các cấu hình SSH mẫu thành cấu hình đã kiểm chứng.

**Kiểm chứng khi sửa:** Ghi warmup, batch, số crop/request, concurrency, process VRAM/RSS, peak allocated/reserved và CU thực tế.

Nguồn: [ORT float16](https://onnxruntime.ai/docs/performance/model-optimizations/float16.html), [Colab FAQ](https://research.google.com/colaboratory/faq.html).

### A14 — P2 — Quickstart và packaging chưa tái lập được môi trường chạy

**Vị trí:** [README.md](../../README.md), dòng 91–99; [pyproject.toml](../../pyproject.toml); [config.py](../../src/utils/config.py), dòng 10–19; [requirements.txt](../../requirements.txt).

README tạo venv rồi chạy test nhưng thiếu bước cài dependencies. Snapshot venv kế thừa global có torch/NumPy nhưng thiếu nhiều runtime libraries.

Setuptools discovery thực tế:

```text
package_dir = {'': 'src'}
packages = [
  'backend', 'contracts', 'cv', 'frontend',
  'metrics', 'recsys', 'streaming', 'utils'
]
```

Code lại dùng `from src...`; `spark_jobs` và configs ngoài package chưa được đóng gói đúng. Chạy từ checkout root có thể che lỗi này.

Đây là lỗi discovery nhận src-layout không khớp cách import, không phải kết luận “multiple top-level packages”. Chưa build/install wheel để kiểm runtime cuối.

**Đề xuất:** Chọn một đường cài chuẩn, explicit package discovery/data files, lock hoặc constraints cho môi trường đã smoke. Kiểm import và config resolution từ ngoài repo root.

Giữ global PyTorch CUDA đang có; chỉ bổ sung dependency thiếu và tránh resolver thay torch ngoài chủ đích. Thống nhất ORT CPU/GPU giữa các đường setup. Các dependency chỉ có lower bound cũng cần pin lại theo phiên bản đã kiểm chứng trước khi công bố reproducibility.

Nguồn: [setuptools package discovery](https://setuptools.pypa.io/en/stable/userguide/package_discovery.html).

### A15 — P2 — Heuristic viền trắng không xác nhận bảo toàn aspect ratio

**Vị trí:** [check_hm256_aspect_ratio.py](../../scripts/check_hm256_aspect_ratio.py), dòng 21–28 và 53–65; [resize_hm_aspect_pad.py](../../scripts/resize_hm_aspect_pad.py); [MASTER_PLAN.md](../MASTER_PLAN.md), TASK-02.

Probe tạo ảnh portrait 100×200, nền trắng và vùng màu ở giữa, sau đó kéo trực tiếp thành 256×256. Ảnh đã méo nhưng vẫn pass “có letterbox”.

Do ảnh catalog có thể vốn có nền trắng, viền trắng không chứng minh ảnh đã resize đúng. `USE_DIRECTLY` là kết luận quá mạnh.

Script resize hiện chỉ có helper function, không CLI/main; chạy file không xử lý dataset. Pad ảnh đã kéo méo cũng không khôi phục tỉ lệ gốc.

**Đề xuất:** Gọi kết quả là white-border heuristic, có trạng thái inconclusive; đối chiếu ảnh gốc cùng ID hoặc metadata nguồn. Nếu resize, dùng ảnh gốc, input/output riêng và CLI batch rõ ràng. Lưu seed, timestamp và sample IDs; không diễn giải một mẫu heuristic thành kiểm định hình học chắc chắn.

### A16 — P2 — Qdrant bỏ qua tương thích embedding khi collection đã tồn tại

**Vị trí:** [qdrant_indexer.py](../../src/cv/qdrant_indexer.py), dòng 34–45.

`ensure_collection()` thấy tên collection tồn tại là return, không kiểm dimension, distance hay model revision.

Đổi từ SigLIP 768D sang CLIP 512D có thể lỗi ở upsert/query. Hai encoder cùng dimension vẫn thuộc hai embedding spaces khác nhau và không thể trộn tùy ý.

**Đề xuất:** Version collection theo encoder revision/preprocessing fingerprint, kiểm schema, index và validate collection mới trước khi chuyển alias. Query encoder phải dùng đúng fingerprint của catalog.

**Giới hạn:** Kết luận từ source; chưa chạy server Qdrant thật.

### A17 — P2 — SigLIP text padding chưa theo preprocessing pretrained

**Vị trí:** [embedder.py](../../src/cv/embedder.py), dòng 85–87; [model_config.yaml](../../configs/model_config.yaml), active encoder.

`padding=True` pad tới độ dài lớn nhất trong batch, khác fixed padding `padding="max_length", max_length=64` được hướng dẫn cho SigLIP/SigLIP2.

**Đề xuất:** Processor settings theo từng checkpoint, không dùng một cấu hình mặc định cho mọi model. Pin phiên bản đã kiểm và thử cùng câu khi encode riêng/encode chung với câu dài hơn trước benchmark.

**Giới hạn:** Chưa có Transformers/model local, nên chưa đo mức giảm retrieval hay kết luận mọi batch đều sai.

Không ghi nhận pixel FP32/model FP16 như một lỗi đã xác nhận: implementation pretrained có thể tự cast pixel values sang dtype của patch embedding; cần đọc đúng model/version trước khi kết luận.

Nguồn: [SigLIP2 preprocessing](https://huggingface.co/docs/transformers/model_doc/siglip2).

### A18 — P2 — Candidate Recall tiêu thụ iterator ground truth hai lần

**Vị trí:** [recsys_metrics.py](../../src/metrics/recsys_metrics.py), dòng 74–85.

Signature cho phép `Iterable`, nhưng code gọi `set(items)` khi lọc valid users rồi đọc lại iterable để chấm.

```python
candidate_recall_at_k({"u": ["A"]}, {"u": ["A"]})        # 1.0
candidate_recall_at_k({"u": iter(["A"])}, {"u": ["A"]})  # 0.0
```

**Đề xuất:** Materialize ground-truth set đúng một lần, hoặc giới hạn interface thành reusable collection. Test hai biểu diễn phải cho cùng kết quả.

Chưa có bảng đánh giá dự án bị xác nhận sai vì lỗi này; finding áp dụng utility hiện hữu.

### A19 — P2 — Two-Tower, cold-start và feature parity được hứa vượt implementation

**Vị trí:** [two_tower.py](../../src/recsys/two_tower.py), [MASTER_PLAN.md](../MASTER_PLAN.md), TASK-REC-05; [ARCHITECTURE.md](../ARCHITECTURE.md), dòng 121–129.

Ba ablation đang không khớp:

| MASTER_PLAN | Code hiện tại |
| :--- | :--- |
| ID + metadata | ID-only |
| Thêm visual | ID + metadata |
| Thêm time-decay attention | ID + metadata + visual |

UserTower không nhận position hoặc elapsed-time input. Probe đảo thứ tự history ở eval cho sai khác tối đa khoảng `4.47e-08`, tức cùng representation trong sai số FP32. Đây là bộ tổng hợp theo tập ở đường hiện tại; chưa đáp ứng biến thể temporal đã nêu.

ItemTower luôn cần ID embedding, chưa có đường OOV/content-only rõ ràng. Bổ sung vector ảnh không tự chứng minh đã giải quyết cold-start item.

Dùng cùng một file LightGBM cho offline/online cũng chưa loại bỏ training-serving skew: offline chủ yếu purchase history, online có click/session/trending. Cần thống nhất cả candidate sources, feature formulas, freshness, default values và mapping.

**Đề xuất:** Chốt ablation trước train, có ID masking/OOV/content-only, định nghĩa nhóm cold-start tại từng cutoff và fallback cho new user. Dùng shared feature specification/builder và parity fixture offline/online cho cùng input.

Bỏ các câu “giải quyết triệt để” hoặc “loại bỏ hoàn toàn” cho đến khi có phép đo tương ứng.

### A20 — P2 — Ngôn ngữ trạng thái và timeline đang vượt mức hoàn thành

**Vị trí:** [MASTER_PLAN.md](../MASTER_PLAN.md), tiêu đề/WP-1/WP-6; [ARCHITECTURE.md](../ARCHITECTURE.md), tiêu đề; [HANDOFF.md](../HANDOFF.md), bàn giao 09:35; [main.py](../../src/backend/main.py), dòng 29–90; [s1_stream_processor.py](../../spark_jobs/streaming/s1_stream_processor.py).

API trả list rỗng và `accepted` nhưng chưa có business operation; health chưa kiểm dependency; stream processor mới khai báo schema. Đây là chức năng chưa triển khai, không nên đếm từng placeholder thành một defect riêng.

Tuy nhiên, các câu “production-ready”, “codebase đã hoàn thiện” và “sẵn sàng” không phản ánh giới hạn đó. `TASK-00 DONE` chỉ nên hiểu là đã tạo scaffold, không xác nhận correctness mọi module.

Kế hoạch hứa baseline end-to-end tuần 1 nhưng API/UI nằm ở tuần 6. Có nguy cơ từng nhánh làm lâu rồi mới phát hiện không nối được.

**Đề xuất:**

- Ghi “thiết kế mục tiêu v3/scaffold” và phân biệt implemented/proposed/unverified.
- Tách liveness với readiness; endpoint chưa có nghiệp vụ trả trạng thái chưa sẵn sàng/chưa triển khai rõ ràng.
- Đưa API/UI tối thiểu vào milestone đầu.
- Chỉ chọn một nhánh nâng cao giữa fine-tune encoder và Two-Tower sau baseline.
- Cho phép `SKIPPED/NOT_RUN` kèm lý do khi gate không mở; không buộc biến mọi TBD thành số.
- Ghi nhận negative results và lý do giữ baseline.

## 5. Những nhận định bổ sung cần đưa vào lần chỉnh tài liệu

### 5.1. Cohen's Kappa có trường hợp không xác định

Trong [cv_metrics.py](../../src/metrics/cv_metrics.py), hai người chấm luôn cùng một category được trả kappa = 1 khi `1 - p_e` gần 0.

Ở trường hợp không có biến thiên nhãn, công thức kappa có mẫu số 0. Nên báo `undefined/N/A` cùng observed agreement và phân bố nhãn; không diễn giải thành mức đồng thuận hoàn hảo đã được đo có ý nghĩa.

Test hiện tại chỉ kiểm hai người đồng ý trên nhiều nhãn, chưa kiểm trường hợp suy biến này.

### 5.2. Decision Gates cần đủ cụ thể để ra quyết định

- Gate LoRA đang trộn điều kiện **cho phép thử nghiệm** với điều kiện **chấp nhận mô hình sau thử nghiệm**.
- “Tăng 2%” phải nói rõ tăng tương đối hay điểm phần trăm.
- “Vượt trội”, “rõ rệt”, “đáng kể” cần ngưỡng hoặc quy tắc đánh giá đã chốt.
- Không đặt threshold dựa vào final test sau khi xem kết quả.
- Gate giữ Two-Tower cần cân cả Recall/MAP, tài nguyên, latency và chi phí bảo trì.
- LightGBM thua heuristic không tự chứng minh leakage: phải kiểm candidates, features, labels, query grouping và baseline trước.

Các threshold hiện có là chỉ tiêu thiết kế, chưa phải kết quả đo.

### 5.3. Proxy basket và outfit compatibility cần gọi đúng tên

Giỏ `(customer_idx, t_dat)` là proxy basket theo khách/ngày. Cùng ngày mua hai món khác loại chưa chứng minh chúng thuộc một outfit tương thích.

Có thể dùng cross-category co-purchase cho demo, nhưng cần mô tả đó là heuristic/rule-based recommendation. Nếu muốn khẳng định chất lượng phối đồ, cần nhãn hoặc giao thức đánh giá phù hợp.

Giữ rõ nguồn sự kiện: giao dịch lịch sử H&M và các tương tác UI/giả lập có semantics khác nhau. Không diễn giải số click giả lập thành hành vi người dùng thật đã quan sát.

### 5.4. Protocol RecSys cần tách đúng mục đích lọc user

Active-user filtering hữu ích để tạo bảng train có nhãn và giảm bộ nhớ. Nó không thay thế fallback cho toàn bộ user mà hệ thống serving phải phục vụ.

Cần ghi rõ population/mẫu số của MAP/Recall, xử lý user thiếu predictions, candidate misses và cold-start cohorts. Nếu chỉ báo kết quả trên khách mua trong tuần nhãn, phải mô tả đúng population đó.

### 5.5. Mapping và dữ liệu lỗi cần được kiểm trước normalize

`lpad` không tự chứng minh ID hợp lệ; cần kiểm null, non-digit và chuỗi quá dài trước khi chuẩn hóa để tránh biến dữ liệu lỗi thành ID có hình thức hợp lệ.

Mapping customer/article/category phải có version và được dùng nhất quán giữa tables, model, vector index và Redis. Chạy lại pipeline trên subset không được làm các artifact cũ dùng nhầm dense indices mới.

### 5.6. Prompt và quyền sửa tài liệu chung cần thống nhất

[SUBAGENT_PROMPTS.md](../SUBAGENT_PROMPTS.md) chưa giữ đầy đủ mandatory reading order cho mọi role; một số prompt thiếu MASTER_PLAN/HANDOFF.

Bảng scope giới hạn thư mục của chuyên gia nhưng Golden Rule lại bắt cập nhật STATE/HANDOFF. Nên nói rõ tài liệu dùng chung do chuyên gia đề xuất/cập nhật theo phần riêng và Lead tích hợp, để tránh vừa vi phạm scope vừa thiếu bàn giao.

### 5.7. Test pass hiện tại chưa đủ để kết luận nền tảng đã đúng

Sáu unittest kiểm nhiều happy paths nhưng chưa bao phủ lỗi biên đã phát hiện. Hai Markdown test function không được unittest discover chạy tự động; cần gọi script riêng hoặc dùng pytest.

Các regression test nên ưu tiên theo hậu quả:

1. Biên ngày và cutoff.
2. Query grouping nhiều tuần.
3. Smoke isolation.
4. Ontology model.
5. Empty history và OOV.
6. Invalid event/payload.
7. Iterator ground truth.
8. Retry/restart sink.
9. Shared qrels/IDCG và offline/online feature parity.

Không cần viết test chỉ để tăng số lượng; mỗi test phải bảo vệ một hành vi hoặc lỗi có ý nghĩa.

## 6. Thứ tự điều chỉnh đề xuất

### Bước 1 — Sửa correctness trước dữ liệu thật

Ưu tiên A01–A07: lịch tuần, ranker groups, smoke isolation, detector ontology, empty-history NaN, validation và Kafka log directory.

Điều kiện hoàn thành là có regression evidence tương ứng, không chỉ thay code rồi chạy lại sáu test cũ.

### Bước 2 — Khóa contracts và evaluation

Thống nhất tên bảng/key/API/artifact, query keys và mapping versions. Chốt train/dev/final, query/gallery/qrels, common pool và cách tính metric.

Bản quyết định được duyệt cần đi vào AGENTS/MASTER_PLAN/DATA_CONTRACTS/config và STATE, không chỉ tồn tại trong file lịch sử này.

### Bước 3 — Làm setup tái lập và một luồng nhỏ end-to-end

Một milestone tối thiểu có thể gồm:

- Ingest fixture/mẫu nhỏ vào lakehouse với đúng schema.
- Một baseline recommendation và một encoder đã xác nhận preprocessing.
- Index/query Qdrant; đọc/ghi Redis theo contracts.
- API/UI tối thiểu hiển thị kết quả thật, readiness phản ánh đúng dependency.
- Event đi qua Kafka và sink đã xác định semantics.

Chỉ mở rộng sau khi chứng minh input/output của các module nối được với nhau.

### Bước 4 — Kiểm streaming bằng failure cases

Tách replay/live clocks; kiểm duplicate, late events, retry sau partial write, checkpoint restart, snapshot trending và persistence qua container recreate.

Latency benchmark phải tách các mốc produce/ingest/process/sink/render phù hợp; không lấy timestamp lịch sử làm mốc độ trễ hiện tại.

### Bước 5 — Smoke tài nguyên, chạy full và lưu evidence

Đo RAM/VRAM/time/CU trên cấu hình thật, có batch size/concurrency/warmup. Chunk cả NumPy fallback. Sau đó mới chạy full và lưu JSON/CSV cùng seed, timestamp, config/model revision và population.

Các giới hạn 8GB/24GB/1.5GB là ngân sách hoặc gate cần kiểm, không phải kết luận đã fit.

### Bước 6 — Chọn một nhánh nâng cao

Giữ lộ trình heuristic → ALS → LightGBM khi evidence ủng hộ. Chỉ chọn một trong fine-tune encoder hoặc Two-Tower làm trọng tâm nâng cao ban đầu.

Nếu thử nghiệm không cải thiện, báo kết quả âm và giữ hệ thống đơn giản hơn. Phần detector cần được cân theo yêu cầu môn học và baseline thực tế; không mặc định phải train mọi model đã liệt kê.

## 7. Tiêu chí để coi repo sẵn sàng bước tiếp

- Các lỗi P1 thuộc bước sắp chạy đã sửa và có kiểm chứng.
- Một lịch tuần và cutoff policy chung.
- Contracts giữa code/config/docs thống nhất, IDs/mappings có semantics rõ.
- Dev/final độc lập, protocol đánh giá đủ tái lập.
- Setup không thay global PyTorch CUDA ngoài chủ đích.
- Một vertical slice trả kết quả thật.
- Streaming có clock, ownership và retry semantics rõ.
- VRAM/latency/CU được ghi là mục tiêu/ước lượng hoặc có artifact đo tương ứng.
- STATE phân biệt implemented/proposed/unverified; nhánh bỏ qua có lý do.

Đánh giá hiện tại là **giữ hướng kiến trúc, củng cố nền tảng và thu phạm vi trước khi tăng độ phức tạp**. Không có đủ bằng chứng để công bố MAP, Recall, mAP, latency hoặc mức VRAM của hệ thống hoàn chỉnh ở thời điểm audit.

## 8. Nguồn và khả năng truy vết

- [codebase_review_2026-10-17.json](../../reports/tables/codebase_review_2026-10-17.json): 20 finding IDs, probe outputs, môi trường, seed/timestamp, source hashes và giới hạn kiểm chứng.
- [STATE.md](../STATE.md): trạng thái vận hành; các lỗi review vẫn còn mở.
- [HANDOFF.md](../HANDOFF.md): nhật ký review và bàn giao.
- [Spark Structured Streaming](https://spark.apache.org/docs/3.5.6/structured-streaming-programming-guide.html): watermark và foreachBatch.
- [LightGBM Dataset](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Dataset.html): query groups.
- [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/): ontology checkpoint pretrained.
- [Hugging Face SigLIP2](https://huggingface.co/docs/transformers/model_doc/siglip2): text preprocessing.
- [ONNX Runtime float16](https://onnxruntime.ai/docs/performance/model-optimizations/float16.html): giới hạn dtype/provider.
- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html): giới hạn tài nguyên và phạm vi hạn chế remote control.
- [setuptools package discovery](https://setuptools.pypa.io/en/stable/userguide/package_discovery.html): package layout.
- Source Kafka đúng tag 3.9.0 được dẫn trực tiếp tại A07.

Các nguồn ngoài đã được đối chiếu trong lượt audit. File này lưu kết luận tại snapshot đó; cần kiểm lại phiên bản/runtime khi triển khai hoặc thay dependency.
