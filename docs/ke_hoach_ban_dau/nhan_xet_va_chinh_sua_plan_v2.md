# ĐÁNH GIÁ CHI TIẾT & BẢN HIỆU CHỈNH KỸ THUẬT TỪ PLAN v2 (OPUS 5.5) LÊN PLAN v3 (PRODUCTION-READY)

> **Tài liệu đối chiếu:**
> - Bản gốc v1: [`plan_v1.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/ke_hoach_ban_dau/plan_v1.md)
> - Bản nâng cấp v2 (Opus 5.5): [`plan_v2_opus55.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/ke_hoach_ban_dau/plan_v2_opus55.md)
> - **Mục tiêu của file này:** Ghi nhận toàn bộ ưu điểm cần giữ lại của Plan v2, chỉ rõ **7 điểm nghẽn kỹ thuật / bộ nhớ / vận hành** khi chạy thực tế trên phần cứng cá nhân (**RTX 4060 8GB VRAM + 24GB RAM + Colab Pro+ 200 CU**), và chốt phương án chỉnh sửa cuối cùng để đưa vào hệ thống tài liệu làm việc chính thức (`docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`).

---

## 1. Đánh giá tổng quan về Plan v2 của Opus 5.5

| Tiêu chí đánh giá | Điểm số | Nhận xét |
| :--- | :---: | :--- |
| **Tư duy Nghiên cứu & Thực nghiệm (Methodology)** | **9.5 / 10** | Triết lý **Baseline-first + Decision Gates** là cực kỳ xuất sắc. Loại bỏ hoàn toàn việc "bịa số trước khi làm" của v1; bổ sung giao thức đánh giá 3 tầng cho bài toán *Street-to-Shop* vốn không có nhãn sẵn trong H&M. |
| **Lựa chọn Dataset & Xử lý Dữ liệu** | **9.5 / 10** | Chọn **H&M** làm trục chính và đổi từ ModaNet sang **Fashionpedia** (Hugging Face) cho Object Detection là quyết định rất chuẩn xác. Bắt đúng các lỗi mất số `0` đầu của `article_id` và độ nặng của chuỗi hex `customer_id`. |
| **Kiến trúc Mô hình (CV + RecSys)** | **9.0 / 10** | Chuyển từ công thức cộng trọng số chọn tay `w1..w4` sang lộ trình **Heuristic $\rightarrow$ ALS $\rightarrow$ LightGBM LambdaRank $\rightarrow$ Two-Tower Neural Retrieval (có Visual Feature)** bám sát chuẩn kiến trúc thắng giải Kaggle H&M và hệ thống thực tế. |
| **Khả năng thực thi trên Phần cứng (24GB RAM / 8GB VRAM)** | **7.5 / 10** | Có 7 điểm nghẽn ngầm về dung lượng RAM khi tạo bảng feature LightGBM, VRAM khi train Two-Tower, cấu hình mạng Kafka trong Docker và khối lượng gán nhãn tay cần phải sửa lại để không bị đứng máy hoặc vỡ tiến độ. |

---

## 2. Những điểm xuất sắc của Plan v2 được GIỮ NGUYÊN 100%

1. **Nguyên tắc Baseline-first & Decision Gates:**
   - Tuần 1 dựng hệ thống chạy thông suốt End-to-End bằng **Model Pre-trained Zero-shot + Thuật toán Heuristic RecSys** (không tốn 1 Compute Unit nào để train).
   - Mọi bước Fine-tune (YOLO11, SigLIP-2 LoRA) và Deep Learning (Two-Tower) đều phải vượt qua **Decision Gate** có ngưỡng đo đạc cụ thể.
   - Tôn trọng **kết quả âm (Negative Results)**: Nếu fine-tune trên ảnh catalog H&M làm giảm chất lượng trên ảnh chụp thực tế tại Việt Nam (do overfit vào nền trắng phòng studio), sử dụng kỹ thuật nội suy trọng số **WiSE-FT** ($\theta = \alpha \theta_{\text{ft}} + (1-\alpha)\theta_{\text{zs}}$) hoặc giữ bản zero-shot và phân tích nguyên nhân trong báo cáo.
2. **Thẩm định & Xử lý Dataset:**
   - **H&M:** Bắt buộc ép kiểu `article_id` thành `string` cố định 10 ký tự (pad `'0'` ở đầu) ngay từ khi đọc CSV; ánh xạ `customer_id` (64-char hex) sang `customer_idx` (`int32`) ở tầng Silver.
   - **Kiểm tra tỉ lệ khung hình (Aspect Ratio) của bộ `hm256x256`:** Kiểm tra ngay ở Ngày 1 xem ảnh có bị bóp vuông làm biến dạng quần áo không. Nếu bị méo, dùng script tự động resize giữ nguyên tỉ lệ + pad viền trắng (`Letterbox padding`).
   - **Fashionpedia (12 lớp cốt lõi):** Dùng bản parquet trên Hugging Face (`detection-datasets/fashionpedia`) để huấn luyện Detector cắt riêng từng món đồ (bao gồm cả giày, túi, mũ, kính mắt mà DeepFashion2 không có).
   - **Không ép `product_code` làm Hard Positive trong hàm Loss chính:** Vì các `article_id` cùng `product_code` là cùng kiểu dáng nhưng **khác màu**. Chỉ dùng `product_code` để loại bỏ False Negatives trong cùng 1 mini-batch và làm chỉ số đánh giá phụ (`R@10-style`).
3. **Giao thức đánh giá 3 tầng cho Computer Vision:**
   - **Tầng A (In-domain):** Chia tập `articles` theo `product_code` (85% Train / 7.5% Val / 7.5% Test). Đo `T2I Recall@K` và `I2I Precision@K` (theo loại và theo loại + màu).
   - **Tầng B (Automated Proxy Street-to-Shop):** Cắt các vùng trang phục từ tập `val` của Fashionpedia, truy vấn vào catalog H&M trên Qdrant và đo `CatConsistency@10` (% kết quả nằm đúng tập `product_type_name` tương ứng).
   - **Tầng C (Real-world Vietnamese Street Set):** Đánh giá `nDCG@10` và `P@10` với thang điểm 0–3 và độ đồng thuận `Cohen's Kappa`.

---

## 3. 7 Điểm Nghẽn Kỹ Thuật trong Plan v2 và Cách Sửa trong Plan v3

### Chỉnh sửa #1: Chống tràn RAM (OOM) ở bước Sinh Ứng Viên & Tính Feature cho LightGBM (`B6_candidates` & `B7_features`)
* **Vấn đề trong Plan v2:**
  H&M có **1.371.980 khách hàng**. Nếu sinh 100 ứng viên/khách cho toàn bộ tập khách hàng (hoặc lấy mẫu ngẫu nhiên 20% trên toàn bộ khách hàng mà phần lớn không mua gì trong tuần nhãn), bảng dữ liệu huấn luyện sẽ có hàng chục triệu đến hơn trăm triệu dòng $\times$ 50 cột $\rightarrow$ tràn bộ nhớ WSL2 (16GB RAM). Hơn nữa, tính feature `cosine(v_item, mean(v_user_recent_5))` bằng PySpark UDF cho hàng chục triệu dòng sẽ cực chậm do nghẽn cổ chai JVM $\leftrightarrow$ Python.
* **Giải pháp trong Plan v3:**
  1. **Chỉ tạo tập huấn luyện/đánh giá Ranker trên nhóm `Active Users` (khách hàng thực sự phát sinh giao dịch trong tuần nhãn):**
     Trong bất kỳ tuần nào của H&M, chỉ có khoảng **65.000 – 75.000 khách hàng** thực sự mua hàng. Trong thuật toán học xếp hạng `LambdaRank`, một nhóm (query group / customer) mà tất cả các ứng viên đều có `label = 0` sẽ có đạo hàm bằng $0$ và không đóng góp gì cho việc học của cây quyết định!
     Khi chỉ lấy ~70.000 khách hàng có mua hàng $\times$ 100 ứng viên = **~7 triệu dòng**, cả PySpark lẫn LightGBM chạy trên laptop 24GB RAM chỉ mất **vài phút** và tốn chưa tới 4GB RAM.
  2. **Tính Feature Tương đồng Thị giác (`visual_affinity_score`) bằng PyTorch trên GPU RTX 4060:**
     Thay vì dùng PySpark UDF, viết module `src/recsys/features_gpu.py` nạp ma trận vector ảnh $105.542 \times 768$ (chỉ nặng ~162MB ở chuẩn FP16) vào VRAM RTX 4060, tính vector trung bình 5 món gần nhất của khách và nhân tích vô hướng theo batch cho 7 triệu cặp `(customer_idx, article_idx)` — thời gian chạy thực tế **< 3 giây**.

### Chỉnh sửa #2: Thiết kế lại mạng Two-Tower (L4) để vừa khít 8GB VRAM của RTX 4060
* **Vấn đề trong Plan v2:**
  Plan v2 thiết kế `User Tower` nhận chuỗi lịch sử `N = 30` món chạy qua `Item Tower` dùng chung rồi qua `Transformer 2 lớp`, huấn luyện với `batch_size = 2048–4096`. Với $4096 \times 30 = 122.880$ lần chạy `Item Tower` trong 1 bước forward/backward, đồ thị tính toán sẽ vượt quá 8GB VRAM của RTX 4060.
* **Giải pháp trong Plan v3:**
  1. Giới hạn chiều dài lịch sử gần nhất ở mức **`N = 10` đến `15` món** (đủ phản ánh sở thích ngắn hạn và trung hạn).
  2. Thay Transformer 2 lớp bằng **1 lớp Lightweight Multi-Head Attention + Time-Decay Pooling** và đặt `batch_size = 512` hoặc `1024` với `AMP (fp16/bf16)`.
  3. Đóng băng (freeze) bảng vector ảnh CLIP/SigLIP dưới dạng `nn.Embedding.from_pretrained(..., freeze=True)` trong VRAM (162MB), chỉ huấn luyện tầng chiếu `Linear(768 -> 64)` và các bảng embedding thuộc tính. Mức tiêu thụ VRAM thực tế chỉ khoảng **2.2 – 3.0 GB**, chạy cực nhanh trên RTX 4060.

### Chỉnh sửa #3: Sửa lỗi cấu hình mạng Kafka trong `docker-compose.yml`
* **Vấn đề trong Plan v2:**
  Container `kafka` chỉ khai báo `KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092`. Khi container `kafka-ui` hoặc `backend` kết nối vào `kafka:9092`, broker trả về địa chỉ `localhost:9092` làm container client tự gọi vào chính nó và báo lỗi `Connection Refused`.
* **Giải pháp trong Plan v3:**
  Cấu hình chuẩn **Dual Listeners** trong `docker-compose.yml`:
  - `INTERNAL://kafka:29092` (cho giao tiếp nội bộ giữa các container Docker: `kafka-ui`, `api`).
  - `EXTERNAL://localhost:9092` (cho PySpark Streaming, Event Simulator và các script chạy trên máy host WSL2).

### Chỉnh sửa #4: Chiến lược Lưu trữ Lakehouse (Local Delta Lake làm mặc định + MinIO tùy chọn)
* **Vấn đề trong Plan v2:**
  Đẩy toàn bộ 31,8 triệu dòng giao dịch và bảng tính năng qua giao thức mạng `s3a://` vào container MinIO trên cùng một máy cá nhân vừa ngốn thêm 1GB RAM, vừa chậm hơn 3–5 lần do HTTP serialization, lại dễ phát sinh lỗi xung đột thư viện `hadoop-aws`.
* **Giải pháp trong Plan v3:**
  - Dùng **Delta Lake lưu trực tiếp trên Filesystem của WSL2** (`data/lakehouse/{bronze,silver,gold}`) làm chế độ mặc định. Delta Lake vẫn đảm bảo 100% tính năng ACID, Time Travel, Schema Enforcement, Partitioning và `OPTIMIZE ZORDER BY` nhưng đạt tốc độ đọc/ghi nguyên bản của ổ SSD NVMe và tốn **0MB RAM nền**.
  - Đưa `minio` vào Docker Compose dưới dạng profile tùy chọn (`--profile s3`) để dùng khi cần chạy bài test so sánh hiệu năng `Local Delta vs. S3A MinIO Delta` phục vụ báo cáo môn Big Data.

### Chỉnh sửa #5: Hợp nhất mô hình LightGBM Offline & Online thành 1 Mô hình Duy nhất (Chống Training-Serving Skew)
* **Vấn đề trong Plan v2:**
  Plan v2 tách 1 mô hình LightGBM Offline (40–60 features) và 1 mô hình LightGBM Online (chỉ dùng features trong Redis). Duy trì 2 mô hình và 2 pipeline trích xuất đặc trưng khác nhau rất tốn công và dễ gây sai lệch kết quả.
* **Giải pháp trong Plan v3:**
  - Huấn luyện **1 mô hình LightGBM LambdaRank duy nhất** với bộ **~25 đặc trưng tinh gọn, mạnh nhất**.
  - Toàn bộ bảng `Item Static & Historical Features` của 105.542 sản phẩm chỉ nặng **~15MB** dưới dạng Parquet $\rightarrow$ nạp thẳng vào bộ nhớ RAM của FastAPI khi khởi động server.
  - Khi có request `/recommend/{customer_id}`, FastAPI lấy `User Profile + Recent Session` từ Redis (< 2ms), ghép với bảng `Item Features` có sẵn trong RAM, tính nhanh các đặc trưng tương tác cho ~100 ứng viên bằng Polars/NumPy (< 5ms) và chấm điểm bằng chính mô hình LightGBM đó!

### Chỉnh sửa #6: Giảm tải bước Gán nhãn Tập ảnh Việt Nam bằng Kỹ thuật IR Pooling
* **Vấn đề trong Plan v2:**
  Chấm điểm tay cho 150–200 ảnh $\times$ Top-10 $\times$ 5 cấu hình Ablation $\times$ 2 người chấm = hàng nghìn cặp ảnh, rất dễ làm đình trệ tiến độ ở Tuần 3.
* **Giải pháp trong Plan v3:**
  - Thu thập **60–80 ảnh thực tế chất lượng cao tại Việt Nam** (phân bố đều qua các nhóm trang phục chính) — hoàn toàn đủ ý nghĩa thống kê để tính `nDCG@10`, `P@10` và `Cohen's Kappa`.
  - Áp dụng kỹ thuật **IR Pooling (Chuẩn TREC)**: Với mỗi ảnh truy vấn, lấy Top-10 kết quả từ tất cả các cấu hình cần so sánh, **gộp lại và loại bỏ các `article_id` trùng lặp**, xáo trộn ngẫu nhiên (ẩn tên mô hình) trên công cụ chấm điểm Streamlit. Người chấm chỉ cần chấm 1 lần duy nhất cho mỗi cặp `(query_id, article_id)`, kết quả được lưu vào SQLite/JSON để chấm điểm tự động cho mọi mô hình.

### Chỉnh sửa #7: Tinh gọn danh sách Benchmark Zero-shot ở Tuần 1
* **Vấn đề trong Plan v2:**
  Chạy 5 mô hình zero-shot khác nhau trên 105.100 ảnh chỉ trong Ngày 6 (Tuần 1) là quá tải.
* **Giải pháp trong Plan v3:**
  - Chốt **3 mô hình đại diện rõ rệt nhất** cho bước Benchmark Zero-shot bắt buộc:
    1. `openai/clip-vit-base-patch32` (Baseline đa phương thức kinh điển).
    2. `google/siglip2-base-patch16-224` (Baseline hiện đại của Google, hỗ trợ **đa ngôn ngữ bao gồm tiếng Việt**).
    3. `Marqo/marqo-fashionSigLIP` hoặc `patrickjohncyh/fashion-clip` (Baseline chuyên biệt cho miền thời trang).
  - Các mô hình chỉ có nhánh ảnh như `DINOv2` được chuyển sang mục mở rộng tùy chọn nếu còn thời gian.

---

## 4. Chuyển giao sang Hệ thống Làm việc Chính thức

Kể từ bước này, thư mục `docs/ke_hoach_ban_dau/` được đóng băng như **hồ sơ thảo luận ban đầu**. Toàn bộ quá trình triển khai của bạn, của Lead Agent và các Sub-Agents sẽ tuân theo hệ thống tài liệu vận hành chính thức tại:

1. [`AGENTS.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/AGENTS.md) — Quy tắc điều phối giữa Lead Agent và các Sub-Agents.
2. [`docs/MASTER_PLAN.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/MASTER_PLAN.md) — Kế hoạch thực thi chi tiết (Plan v3) chia theo các Work Packages và Decision Gates.
3. [`docs/ARCHITECTURE.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/ARCHITECTURE.md) — Kiến trúc kỹ thuật chi tiết đã áp dụng 7 bản vá trên.
4. [`docs/DATA_CONTRACTS.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/DATA_CONTRACTS.md) — Chuẩn hóa Schema dữ liệu, tên cột, khóa Redis, Qdrant Payload và REST API.
5. [`docs/INFRA_AND_COLAB_GUIDE.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/INFRA_AND_COLAB_GUIDE.md) — Chiến lược kết hợp Laptop RTX 4060 $\leftrightarrow$ Colab Pro+, xử lý mô hình lớn (ONNX FP16/INT8, Device Placement) và quy trình kết nối/đồng bộ không tốn CU.
6. [`docs/STATE.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/STATE.md) & [`docs/HANDOFF.md`](file:///D:/G/BT,BTL,NCKH/BTL/BTL%20CV%20BigData/docs/HANDOFF.md) — Bảng theo dõi trạng thái trực tiếp và nhật ký bàn giao giữa các Agent.
