# ĐỀ CƯƠNG & KẾ HOẠCH TRIỂN KHAI ĐỒ ÁN LIÊN MÔN (COMPUTER VISION + BIG DATA + RECSYS)

- **Tên đề tài (Tiếng Việt):** Hệ thống Tìm kiếm Hình ảnh và Gợi ý Thời trang Đa phương thức Thời gian thực trên Kiến trúc Data Lakehouse.
- **Tên đề tài (Tiếng Anh - Dùng cho CV/GitHub):** *End-to-End Multimodal Visual Search & Real-Time Personalized Recommendation System on Lakehouse Architecture*.
- **Thời gian thực hiện:** 4 Tuần (30 Ngày).
- **Cấu hình phần cứng mục tiêu:** Laptop/PC cá nhân (GPU NVIDIA RTX 4060 8GB VRAM, RAM 16GB–32GB, SSD NVMe) chạy qua Docker Compose kết hợp Kaggle/Colab cho các tác vụ huấn luyện nặng.

---

## PHẦN 1: DANH SÁCH DATASET CHÍNH THỨC, LINK TẢI & PHÂN TÍCH SCHEMA

Đề tài sử dụng **1 bộ Dataset cốt lõi (H&M)** kết nối xuyên suốt cả Computer Vision, Big Data và Recommendation System, kết hợp **1 bộ Dataset bổ trợ (ModaNet / DeepFashion2)** để huấn luyện mô hình Object Detection cắt vùng trang phục, và **1 tập dữ liệu tự chụp tại Việt Nam** dùng riêng cho bước External Evaluation & Live Demo.

---

### 1. Dataset Cốt lõi: H&M Personalized Fashion Recommendations (Kaggle)

Đây là bộ dữ liệu thực tế từ tập đoàn thời trang H&M, có sự liên kết khóa ngoại (`article_id` và `customer_id`) hoàn hảo giữa **105.100 bức ảnh** và **31,78 triệu dòng lịch sử giao dịch**.

- **Link trang chủ kiểm chứng:** [https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data)
- **Lệnh tải trực tiếp bằng Kaggle CLI:**
  ```bash
  kaggle competitions download -c h-and-m-personalized-fashion-recommendations
  ```
- **Bản thu gọn ảnh (256x256) nếu muốn tải nhanh để test pipeline trước (1.5 GB thay vì 34 GB):**
  - Link 1 (256x256): [https://www.kaggle.com/datasets/odins0n/hm256x256](https://www.kaggle.com/datasets/odins0n/hm256x256)

#### A. Chi tiết bảng `articles.csv` (105.542 dòng × 25 cột)
Bảng chứa toàn bộ thông tin định danh, phân cấp danh mục, màu sắc, chất liệu/họa tiết và mô tả văn bản của từng sản phẩm.

| Tên cột | Kiểu dữ liệu | Số giá trị duy nhất (Unique) | Ví dụ thực tế | Mục đích sử dụng trong Hệ thống |
| :--- | :--- | :--- | :--- | :--- |
| `article_id` | `string` (10 số) | 105.542 | `"0108775015"` | **Khóa chính (Primary Key)**. Ánh xạ trực tiếp tới file ảnh `images/010/0108775015.jpg` và bảng giao dịch. |
| `product_code` | `string` (7 số) | 47.224 | `"0108775"` | Mã mẫu thiết kế gốc (các `article_id` cùng `product_code` là cùng 1 kiểu áo/quần nhưng khác màu). Rất hữu ích để gom nhóm *Hard Positives* khi train Contrastive Learning. |
| `prod_name` | `string` | 45.875 | `"Strap top"` | Tên hiển thị sản phẩm trên giao diện Frontend. |
| `product_type_no` / `product_type_name` | `int` / `string` | **131 classes** | `253` / `"Vest top"`, `"Trousers"`, `"Boots"` | **Nhãn mục tiêu số 1 (Target Label 1)** để huấn luyện nhánh phân loại (Classification Head) của mô hình CV và làm bộ lọc (Metadata Filter) trong Vector DB Qdrant. |
| `product_group_name` | `string` | **19 classes** | `"Garment Upper body"`, `"Garment Lower body"`, `"Shoes"` | Nhóm trang phục cấp cao. Dùng để ánh xạ 1-1 với các class đầu ra của mô hình YOLO Object Detection (Áo, Quần, Giày, Túi). |
| `graphical_appearance_no` / `graphical_appearance_name` | `int` / `string` | **30 classes** | `"Solid"`, `"Stripe"`, `"Denim"`, `"Check"` | **Nhãn mục tiêu số 2 (Target Label 2)** cho bài toán Multi-task CV (nhận diện họa tiết/chất liệu vải từ ảnh). |
| `colour_group_code` / `colour_group_name` | `int` / `string` | **50 classes** | `"Black"`, `"Dark Blue"`, `"Beige"` | **Nhãn mục tiêu số 3 (Target Label 3)** cho bài toán Multi-task CV và lọc màu sắc khi tìm kiếm. |
| `perceived_colour_value_name` | `string` | 8 classes | `"Dark"`, `"Dusty Light"`, `"Bright"` | Sắc độ màu cảm nhận (tối, sáng, trầm/vintage). |
| `index_group_name` | `string` | 5 classes | `"Ladieswear"`, `"Menswear"`, `"Divided"`, `"Sport"` | Phân khúc giới tính / dòng sản phẩm chính. |
| `section_name` & `garment_group_name` | `string` | 57 & 21 classes | `"Denim"`, `"Knitwear"`, `"Dressed"` | Đặc trưng phân loại (Categorical Features) đưa vào mô hình Reranking (LightGBM/CatBoost) ở tầng RecSys. |
| `detail_desc` | `string` | 43.404 (416 null) | `"Jersey top with narrow shoulder straps..."` | **Mô tả văn bản chi tiết**. Dùng để ghép cặp `(Image, Text)` khi **Fine-tune mô hình Multimodal (OpenCLIP)** phục vụ tìm kiếm kết hợp Ảnh + Văn bản. |

#### B. Chi tiết bảng `transactions_train.csv` (31.788.324 dòng × 5 cột)
Bảng log sự kiện mua hàng thực tế trong suốt 2 năm (từ `2018-09-20` đến `2020-09-22`). Đây là "xương sống" cho môn **Big Data** và **Recommendation System**.

| Tên cột | Kiểu dữ liệu | Ví dụ thực tế | Mục đích sử dụng trong Big Data & RecSys |
| :--- | :--- | :--- | :--- |
| `t_dat` | `date` (`YYYY-MM-DD`) | `"2020-09-15"` | Dùng để chia cửa sổ thời gian (Time-based Split) trong **PySpark Batch** và làm mốc thời gian phát lại sự kiện (Event Replayer) vào **Apache Kafka**. |
| `customer_id` | `string` (64-char hex) | `"000058a12d5b43e6..."` | Định danh người dùng. Dùng để xây dựng ma trận tương tác User-Item (ALS / BPR) và theo dõi lịch sử phiên (Session History) trong **Redis**. |
| `article_id` | `string` (10 số) | `"0663713001"` | Định danh sản phẩm. Cầu nối trực tiếp giữa log giao dịch trong Spark/Kafka với Vector ảnh trong Qdrant. |
| `price` | `float` | `0.0508305` | Giá trị giao dịch (đã chuẩn hóa). Dùng trong Spark để tính *User Purchasing Power* (khả năng chi tiêu trung bình của khách) và doanh thu theo thời gian thực. |
| `sales_channel_id` | `int` (`1` hoặc `2`) | `2` (Online), `1` (Store) | Kênh bán hàng. Dùng để phân tích hành vi đa kênh (Omnichannel Analytics) trong Spark Streaming. |

#### C. Chi tiết bảng `customers.csv` (1.371.980 dòng × 7 cột)
Bảng thông tin nhân khẩu học và trạng thái thành viên của 1,37 triệu khách hàng.

| Tên cột | Kiểu dữ liệu | Ví dụ thực tế | Mục đích sử dụng trong Big Data & RecSys |
| :--- | :--- | :--- | :--- |
| `customer_id` | `string` (64-char hex) | `"000058a12d5b43e6..."` | Khóa chính nối với `transactions_train.csv`. |
| `age` | `float` | `22.0` | **Đặc trưng cực kỳ quan trọng cho bài toán Cold-Start**: Dùng Spark tính Top sản phẩm thịnh hành theo từng nhóm tuổi (`18-24`, `25-34`, `35-50`...) để gợi ý cho khách hàng mới. |
| `club_member_status` | `string` | `"ACTIVE"`, `"PRE-CREATE"` | Phân tầng nhóm khách hàng trung thành. |
| `fashion_news_frequency` & `Active` | `string` / `float` | `"Regularly"` / `1.0` | Đặc trưng đầu vào (User Features) cho tầng Ranking của hệ thống gợi ý. |
| `postal_code` | `string` (hex) | `"52043ee2162cf5aa7..."` | Dùng trong Spark Batch để gom nhóm xu hướng mua sắm theo vùng địa lý. |

#### D. Thư mục `images/` (105.100 file ảnh `.jpg`)
- **Cấu trúc thư mục:** Chia theo 3 chữ số đầu của `article_id` (từ `images/010/` đến `images/095/`).
- **Mục đích:** Dùng để huấn luyện mô hình trích xuất đặc trưng thị giác (Visual Feature Extractor / Multimodal CLIP), sau đó trích xuất thành 105.100 vector đẩy vào Vector Database (**Qdrant**).

---

### 2. Dataset Bổ trợ cho môn Computer Vision: ModaNet / DeepFashion2 (Object Detection)

**Tại sao cần thêm bộ này?** Ảnh trong H&M đa phần là ảnh chụp từng món đồ rời rạc. Khi người dùng tải lên một bức ảnh chụp toàn thân ngoài đời thực (street style), nếu đưa cả bức ảnh chứa cả người, cảnh vật, áo, quần, giày vào trích xuất 1 vector duy nhất thì độ chính xác sẽ giảm mạnh. Do đó, cần huấn luyện **YOLOv8/YOLO11** trên tập dữ liệu thời trang đường phố có sẵn nhãn Bounding Box để **tự động phát hiện và cắt (crop) riêng từng món đồ** (Áo, Quần, Váy, Giày/Boots, Túi xách) trước khi tìm kiếm.

- **Lựa chọn 1 (Khuyên dùng vì nhẹ, chuẩn COCO, tải nhanh): ModaNet Dataset**
  - **Quy mô:** **55.176 ảnh thời trang đường phố** (Street Fashion) được gán nhãn Bounding Box & Polygon chuẩn xác cho **13 lớp trang phục**: `bag`, `belt`, `boots`, `footwear`, `outer` (áo khoác), `dress`, `sunglasses`, `pants` (quần dài/jeans), `top` (áo trong), `shorts`, `skirt`, `headwear`, `scarf/tie`.
  - **Link GitHub chính thức (eBay Research):** [https://github.com/eBay/modanet](https://github.com/eBay/modanet)
  - **Link tải trực tiếp trên Kaggle:** [https://www.kaggle.com/datasets/agrigorev/modanet-dataset](https://www.kaggle.com/datasets/agrigorev/modanet-dataset)
- **Lựa chọn 2 (Nếu muốn tập dữ liệu lớn hơn): DeepFashion2 (Bản đã convert sang YOLO/DataFrame trên Kaggle)**
  - **Link GitHub gốc:** [https://github.com/switchablenorms/DeepFashion2](https://github.com/switchablenorms/DeepFashion2)
  - **Link Kaggle (sẵn sàng huấn luyện):** [https://www.kaggle.com/datasets/thusharanair/deepfashion2-original-with-dataframes](https://www.kaggle.com/datasets/thusharanair/deepfashion2-original-with-dataframes)
- **Lựa chọn 3:**
  - **Link Huggingface (sẵn sàng huấn luyện):** [https://huggingface.co/datasets/detection-datasets/fashionpedia](https://huggingface.co/datasets/detection-datasets/fashionpedia)


---

### 3. Tập Dữ liệu Tự thu thập (Self-Collected Vietnamese Streetwear Evaluation Set)

- **Quy mô:** Tự chụp hoặc thu thập **100 bức ảnh** thực tế tại Việt Nam (bạn bè, ảnh feedback khách hàng trên Shopee/Instagram với đa dạng góc chụp, ánh sáng, phong cách như quần jeans bootcut, giày Chelsea boots, áo sơ mi khoác ngoài...).
- **Mục đích:** Không dùng để train (vì quá ít), mà dùng làm **Benchmark Thực tế (Out-of-Distribution Evaluation)** trong báo cáo và chạy **Live Demo** trước hội đồng bảo vệ.

---

## PHẦN 2: KIẾN TRÚC TỔNG THỂ HỆ THỐNG (END-TO-END SYSTEM ARCHITECTURE)

Hệ thống được thiết kế theo sự kết hợp giữa **Kiến trúc Lakehouse (Kappa/Lambda)** cho Big Data và **Kiến trúc Two-Stage Retrieval & Ranking** kết hợp **Visual Pipeline** cho AI/RecSys:

```
+---------------------------------------------------------------------------------------------------+
|                                  1. COMPUTER VISION PIPELINE                                      |
|                                                                                                   |
|  [Ảnh User tải lên] ---> [Stage 1: YOLOv8m Fashion Detector] ---> Cắt (Crop) từng món:            |
|                          (Train trên ModaNet: 13 classes)         (Áo, Quần, Giày Boots, Túi)     |
|                                                                           |                       |
|                                                                           v                       |
|  [Text Query (Tùy chọn)] -----------------------------------> [Stage 2: Fine-tuned OpenCLIP]      |
|  ("màu đen dáng rộng")                                        (Hoặc Multi-Task ConvNeXt-Tiny)     |
|                                                                           |                       |
|                                                                           v                       |
|                                                               [Vector Embedding 512-dim]          |
+---------------------------------------------------------------------------|-----------------------+
                                                                            |
+---------------------------------------------------------------------------|-----------------------+
|                                  2. BIG DATA LAKEHOUSE PIPELINE           |                       |
|                                                                           |                       |
|  (A) BATCH LAYER (31.78M rows transactions + 105k articles):              |                       |
|      [MinIO S3 (Raw CSV/Images)]                                          |                       |
|            |                                                              |                       |
|            v                                                              |                       |
|      [Apache Spark Batch (PySpark)]                                       |                       |
|       +-- Clean & Lưu chuẩn Parquet/Delta Lake                            |                       |
|       +-- Tính Item Popularity theo Tuổi, Mùa, Giá                        |                       |
|       +-- Tính Ma trận Item-to-Item Co-occurrence (Mua cùng nhau)         |                       |
|       +-- Huấn luyện Collaborative Filtering (Spark MLlib ALS)            |                       |
|            |                                                              |                       |
|            +----------------------------+                                 |                       |
|                                         |                                 |                       |
|  (B) SPEED LAYER (Real-time Streaming): |                                 |                       |
|      [Event Simulator] ---> [Apache Kafka (Topic: user-events)]           |                       |
|                                         |                                 |                       |
|                                         v                                 |                       |
|                             [Spark Structured Streaming]                  |                       |
|                              +-- Sliding Window (15p, 1h): Trending Score |                       |
|                              +-- Cập nhật Lịch sử 10 click gần nhất       |                       |
|                                         |                                 |                       |
+-----------------------------------------|---------------------------------|-----------------------+
                                          |                                 |
+-----------------------------------------v---------------------------------v-----------------------+
|                                  3. SERVING & HYBRID RECSYS LAYER                                 |
|                                                                                                   |
|      +----------------------------------+         +----------------------------------------+      |
|      |   REDIS (Online Feature Store)   |         |        QDRANT (Vector Database)        |      |
|      | - Real-time Trending Items       |         | - 105.100 Image Vectors (HNSW Index)   |      |
|      | - User Session History           |         | - Payload: product_type, color, price  |      |
|      | - Precomputed Co-occurrence      |         +----------------------------------------+      |
|      +----------------------------------+                             |                           |
|                       |                                               |                           |
|                       +-----------------------+-----------------------+                           |
|                                               |                                                   |
|                                               v                                                   |
|                        [FASTAPI BACKEND: TWO-STAGE HYBRID RANKER]                                 |
|                        1. Candidate Generation: Lấy Top-100 từ Qdrant + ALS                       |
|                        2. Reranking: Kết hợp Cosine Sim + Trending + Co-occurrence + User Age     |
|                                               |                                                   |
|                                               v                                                   |
|                        [FRONTEND UI: Tìm kiếm bằng Ảnh/Text + Gợi ý Cá nhân hóa + Dashboard]      |
+---------------------------------------------------------------------------------------------------+
```

---

## PHẦN 3: KẾ HOẠCH TRIỂN KHAI CHI TIẾT TRONG 1 THÁNG (30 NGÀY)

Kế hoạch được chia làm **4 Tuần (4 Sprints)**, đảm bảo mỗi tuần bạn đều có sản phẩm chạy được (Deliverable) để báo cáo tiến độ cho giảng viên cả hai môn.

---

### TUẦN 1 (Ngày 1 – Ngày 7): Khởi tạo Hạ tầng Data Lake, EDA & Huấn luyện Model CV số 1 (Fashion Object Detection)

**Mục tiêu Tuần 1:** Dựng xong hạ tầng lưu trữ đối tượng (MinIO), khám phá dữ liệu 31,7 triệu dòng bằng PySpark, và hoàn thành mô hình Computer Vision đầu tiên (YOLOv8 phát hiện vùng trang phục).

#### Ngày 1 – 2: Thiết lập Môi trường, Tải Dataset & Dựng tầng Storage (MinIO)
- **Công việc cụ thể:**
  1. Tạo cấu trúc thư mục dự án chuẩn Production (`cv_models/`, `spark_jobs/`, `kafka_streaming/`, `backend/`, `frontend/`, `docker/`).
  2. Viết `docker-compose.yml` giai đoạn 1 gồm: **MinIO** (Object Storage thay thế AWS S3) và **Qdrant** (Vector DB).
  3. Dùng Kaggle CLI tải bộ **H&M** và **ModaNet**.
  4. Viết script đẩy các file `.csv` gốc và ảnh lên bucket `hm-lakehouse` trên MinIO.
- **Đầu ra nghiệm thu (Deliverable):** Container MinIO chạy ổn định ở cổng `9000/9001`, dữ liệu truy cập được qua giao thức `s3a://`.

#### Ngày 3 – 4: Phân tích Khám phá Dữ liệu lớn (Big Data EDA) & Chuyển đổi Parquet bằng PySpark
- **Công việc cụ thể:**
  1. Khởi tạo phiên làm việc **PySpark** cục bộ (`spark.driver.memory = 8g`).
  2. Đọc file `transactions_train.csv` (31.788.324 dòng). Thực hiện kiểm tra Missing Values, phân phối số lượng giao dịch theo ngày/tháng, quy luật *Long-tail distribution* (20% sản phẩm chiếm 80% lượt mua).
  3. **Tối ưu Big Data (Điểm cộng lớn khi bảo vệ):** Chuyển đổi toàn bộ `transactions_train.csv`, `articles.csv`, `customers.csv` từ định dạng CSV sang định dạng cột **Apache Parquet** (có phân vùng `partitionBy("Year", "Month")`) lưu xuống MinIO.
  4. Đo đạc và ghi vào báo cáo: Dung lượng lưu trữ giảm ~70%, tốc độ truy vấn Spark SQL tăng gấp 8–12 lần so với đọc CSV thô.
- **Đầu ra nghiệm thu:** Notebook/Script PySpark ETL + Bảng so sánh Benchmark hiệu năng đọc CSV vs Parquet.

#### Ngày 5 – 7: Huấn luyện Model CV 1 – Phát hiện Trang phục (YOLOv8m / YOLO11m trên ModaNet)
- **Công việc cụ thể:**
  1. Viết script chuyển đổi nhãn COCO của bộ **ModaNet** (55.176 ảnh) sang định dạng YOLO. Gom gọn 13 lớp gốc về **7 lớp cốt lõi** khớp với hệ thống danh mục của H&M: `top`, `outer`, `pants`, `shorts`, `skirt`, `dress`, `footwear` (gộp `boots` + `footwear`), `bag`.
  2. Chia tập dữ liệu: 80% Train – 10% Validation – 10% Test.
  3. Huấn luyện mô hình **YOLOv8m** (hoặc **YOLO11m**) trong 50 epochs (Image size `640x640`, Batch size `16` hoặc `32` với Mixed Precision `AMP=True` trên RTX 4060 hoặc Kaggle 2xT4).
  4. Xuất mô hình tốt nhất (`best.pt`) sang định dạng **ONNX Runtime (`best.onnx`, FP16)** để tăng tốc độ suy luận gấp 2–3 lần.
- **Đầu ra nghiệm thu:** Trọng số `yolo_fashion_detector.onnx`, biểu đồ Precision-Recall Curve, Confusion Matrix và bảng điểm `mAP@50`, `mAP@50:95` trên tập Test phục vụ báo cáo môn Computer Vision.

---

### TUẦN 2 (Ngày 8 – Ngày 14): Huấn luyện Model CV số 2 (Multimodal / Metric Learning) & Vector Indexing (Qdrant)

**Mục tiêu Tuần 2:** Giải quyết trái tim của môn Computer Vision — xây dựng mô hình trích xuất đặc trưng (Embedding) có khả năng hiểu cả hình ảnh trang phục lẫn thuộc tính văn bản, sau đó đánh chỉ mục toàn bộ 105.100 sản phẩm vào Vector Database.

#### Ngày 8 – 10: Xây dựng & Fine-tune Mô hình Trích xuất Đặc trưng (Representation Learning)
Bạn có thể chọn **1 trong 2 hướng sau** (hoặc làm cả 2 để so sánh trong báo cáo môn CV thì chắc chắn điểm tối đa):

- **Hướng A (Multimodal Contrastive Learning – Khuyên dùng):** Fine-tune **OpenCLIP (`ViT-B/32`)**
  1. Tạo câu mô tả tổng hợp cho mỗi ảnh trong `articles.csv` theo mẫu:
     `"A studio photo of a {colour_group_name} {graphical_appearance_name} {product_type_name} in {index_group_name}. {detail_desc}"`.
  2. Chia 105.100 sản phẩm có ảnh theo `product_code` (tránh Data Leakage giữa các màu của cùng 1 mẫu áo): 90.000 Train – 7.500 Val – 7.600 Test.
  3. Dùng kỹ thuật **LoRA (Low-Rank Adaptation)** hoặc mở khóa 2 block cuối của Vision/Text Encoder để fine-tune OpenCLIP với hàm mất mát **Symmetric InfoNCE Loss** trong 10 epochs (chạy rất nhanh trên RTX 4060 với FP16).
- **Hướng B (Multi-Task Metric Learning CNN/ConvNeXt):**
  1. Dùng backbone **ConvNeXt-Tiny** hoặc **ResNet50-IBN**.
  2. Thiết kế đầu ra gồm 1 lớp Embedding 512 chiều (huấn luyện bằng **SupCon Loss / Triplet Loss** với `product_code` là nhãn cụm) + 3 nhánh Classification dự đoán đồng thời: `product_type_name` (131 lớp), `colour_group_name` (50 lớp), `graphical_appearance_name` (30 lớp).
- **Đầu ra nghiệm thu:** Model checkpoint đã fine-tune + Bảng so sánh chỉ số `Recall@1`, `Recall@5`, `Recall@10` giữa **Pre-trained gốc (Baseline)** và **Fine-tuned Model của bạn** (thường tăng từ 8–15% Recall).

#### Ngày 11 – 12: Batch Feature Extraction (Trích xuất 105.100 Vector)
- **Công việc cụ thể:**
  1. Xuất mô hình Vision Encoder sang **ONNX / TorchScript**.
  2. Viết script chạy Batch Inference (Batch size = 128) quét qua toàn bộ 105.100 ảnh H&M, chuẩn hóa vector theo chuẩn $L_2$-norm ($\Vert{}\mathbf{v}\Vert{}_2 = 1$).
  3. Lưu toàn bộ kết quả ra định dạng Parquet (`article_embeddings.parquet`: gồm `article_id` và mảng `vector[512]`) trên MinIO để tái sử dụng cho cả Spark và Qdrant.
- **Đầu ra nghiệm thu:** File `article_embeddings.parquet` (~210 MB) chứa đầy đủ 105.100 vector chuẩn hóa.

#### Ngày 13 – 14: Đánh chỉ mục vào Qdrant Vector Database & Tối ưu HNSW
- **Công việc cụ thể:**
  1. Tạo Collection `hm_fashion_items` trong **Qdrant** với cấu hình: `size = 512`, `distance = Cosine`.
  2. Nạp 105.100 vector kèm **Payload (Metadata)**: `article_id`, `prod_name`, `product_group_name`, `product_type_name`, `colour_group_name`, `graphical_appearance_name`, `index_group_name`, `image_url` (đường dẫn MinIO).
  3. Đánh Payload Index cho các trường `product_group_name`, `colour_group_name`, `index_group_name` để hỗ trợ **Filtered ANN Search** (ví dụ: khi YOLO cắt ra một đôi giày, chỉ tìm vector trong nhóm `Shoes`).
  4. Thực nghiệm bật **Scalar Quantization (`int8`)** trong Qdrant, đo đạc mức giảm RAM (giảm 75%) và tốc độ truy vấn (`< 10ms` cho Top-50).
- **Đầu ra nghiệm thu:** Hệ thống tìm kiếm bằng ảnh và bằng câu lệnh text chạy thông suốt từ đầu đến cuối qua script test.

---

### TUẦN 3 (Ngày 15 – Ngày 21): Xây dựng Pipeline Big Data (Spark Batch + Kafka + Spark Streaming + Redis)

**Mục tiêu Tuần 3:** Hoàn thiện phần cốt lõi của môn Big Data và Recommendation System — kết hợp phân tích lịch sử dài hạn (Batch 31,7 triệu dòng) với xử lý luồng sự kiện thời gian thực (Speed Layer).

#### Ngày 15 – 17: Tầng Batch Layer – Khai phá 31,7 Triệu Giao dịch bằng Apache Spark
- **Công việc cụ thể:**
  1. **Job PySpark 1 (Demographic & Seasonal Popularity):** Kết nối `transactions.parquet`, `customers.parquet` và `articles.parquet`. Tính toán Top-100 sản phẩm bán chạy nhất theo từng nhóm tuổi (`16-22`, `23-30`, `31-45`, `46+`) và theo từng tháng để giải quyết bài toán **Cold-Start** (khách hàng mới chưa có lịch sử).
  2. **Job PySpark 2 (Item-to-Item Co-occurrence Matrix - "Mua cùng nhau"):** Gom các sản phẩm được cùng 1 `customer_id` mua trong cùng 1 ngày `t_dat` thành các giỏ hàng (Baskets). Dùng PySpark tính điểm đồng xuất hiện (Cosine / Lift / Jaccard trên giỏ hàng) để tìm ra Top-20 sản phẩm hay được phối cùng nhau nhất cho mỗi `article_id` (ví dụ: mua quần jeans bootcut này thì hay mua kèm đôi boots nào).
  3. **Job PySpark 3 (Collaborative Filtering với Spark MLlib ALS):** Chuyển đổi lịch sử mua hàng thành dạng Implicit Feedback (số lần mua có trọng số suy giảm theo thời gian $w = e^{-\lambda \Delta t}$). Huấn luyện mô hình **Alternating Least Squares (ALS)** với `rank = 64` trên tập giao dịch.
- **Đầu ra nghiệm thu:** 3 bảng kết quả lưu xuống tầng Gold của MinIO (Parquet) và đồng bộ các khóa tra cứu nhanh sang **Redis**.

#### Ngày 18 – 19: Tầng Speed Layer – Giả lập Luồng Sự kiện với Apache Kafka
- **Công việc cụ thể:**
  1. Bổ sung **Apache Kafka (chế độ KRaft - không cần ZooKeeper để nhẹ RAM)** và **Redis** vào `docker-compose.yml`.
  2. Tạo topic `fashion-user-events` với 4 partitions.
  3. Viết `event_simulator.py`: Đọc dữ liệu từ `transactions_train.csv` theo trình tự thời gian, biến đổi thành luồng sự kiện thời gian thực bắn vào Kafka với tốc độ tùy chỉnh (1.000 – 5.000 events/giây).
  4. Cấu trúc bản tin JSON trong Kafka:
     ```json
     {
       "event_id": "uuid-v4",
       "timestamp": "2026-10-15T10:15:30Z",
       "customer_id": "000058a12d5b43e6...",
       "article_id": "0706016001",
       "event_type": "view_or_purchase",
       "price": 0.0338,
       "sales_channel_id": 2
     }
     ```
- **Đầu ra nghiệm thu:** Kafka Producer bắn mượt hàng nghìn bản tin/giây, kiểm tra được trên Kafka UI.

#### Ngày 20 – 21: Xử lý Luồng Thời gian thực với Spark Structured Streaming & Redis Sink
- **Công việc cụ thể:**
  1. Viết ứng dụng **Spark Structured Streaming** tiêu thụ dữ liệu từ topic `fashion-user-events`.
  2. Thiết lập **Watermarking (10 phút)** và **Sliding Window (Cửa sổ 15 phút, trượt mỗi 1 phút)** để tính điểm thịnh hành thời gian thực (**Real-time Trending Score**) cho từng sản phẩm và từng nhóm danh mục.
  3. Cập nhật đồng thời danh sách **10 sản phẩm vừa tương tác gần nhất (Recent Session Clicks)** của từng `customer_id` vào **Redis** (dùng cấu trúc `LIST` hoặc `SORTED SET` với TTL 24 giờ).
- **Đầu ra nghiệm thu:** Khi chạy Simulator, dữ liệu trong Redis tự động nhảy số mỗi phút; có đầy đủ ảnh chụp Spark UI (Streaming Query Statistics, Input Rate vs Processing Rate) cho báo cáo Big Data.

---

### TUẦN 4 (Ngày 22 – Ngày 30): Tích hợp Hybrid RecSys, Backend API, Giao diện Demo & Hoàn thiện Báo cáo

**Mục tiêu Tuần 4:** Khớp nối toàn bộ CV + Big Data + RecSys thành một ứng dụng hoàn chỉnh, đánh giá bằng bộ ảnh tự chụp tại Việt Nam và đóng gói báo cáo.

#### Ngày 22 – 24: Xây dựng FastAPI Backend & Thuật toán Hybrid Two-Stage Reranking
- **Công việc cụ thể:**
  1. Xây dựng Backend bằng **FastAPI** (tải sẵn model YOLOv8 ONNX và OpenCLIP ONNX vào GPU/CPU khi khởi động).
  2. **API 1 – `/api/v1/visual-search` (Tìm kiếm Đa phương thức kết hợp Cá nhân hóa):**
     - Nhận ảnh người dùng tải lên (+ câu mô tả text tùy chọn, ví dụ *"đổi sang màu nâu"* + `customer_id`).
     - **Bước 1:** YOLOv8 phát hiện các món đồ trong ảnh (Áo, Quần, Giày). Người dùng chọn món muốn tìm (hoặc tìm tất cả).
     - **Bước 2:** OpenCLIP trích xuất vector $\mathbf{v}_{img}$ (nếu có thêm text thì trộn vector $\mathbf{v}_{query} = \alpha \mathbf{v}_{img} + (1-\alpha)\mathbf{v}_{text}$).
     - **Bước 3 (Retrieval):** Truy vấn Qdrant (lọc theo đúng nhóm đồ YOLO nhận diện được) để lấy **Top-100 ứng viên** có điểm tương đồng thị giác $S_{\text{visual}}$ cao nhất.
     - **Bước 4 (Hybrid Reranking - Điểm ăn tiền kết hợp 2 môn):** Chấm điểm lại 100 ứng viên bằng công thức kết hợp tín hiệu từ cả CV và Big Data (lấy từ Redis):
       $$\text{Score}(u, i) = w_1 \cdot S_{\text{visual}}(q, i) + w_2 \cdot S_{\text{trending\_realtime}}(i) + w_3 \cdot S_{\text{session\_affinity}}(u, i) + w_4 \cdot S_{\text{age\_pop}}(u, i)$$
       *(Trong đó $S_{\text{session\_affinity}}$ là độ tương đồng trung bình giữa ứng viên $i$ với 5 món đồ mà user $u$ vừa click gần nhất trong Redis).*
  3. **API 2 – `/api/v1/recommend/outfit` (Gợi ý Phối đồ - Complete the Look):**
     - Dựa trên ma trận Co-occurrence từ Spark Batch kết hợp Vector tương đồng, gợi ý các món đồ khác nhóm (ví dụ: đang xem Quần $\rightarrow$ gợi ý Áo và Giày Boots đi kèm).
- **Đầu ra nghiệm thu:** Swagger UI (`/docs`) chạy mượt mọi API với độ trễ tổng thể dưới `150ms`.

#### Ngày 25 – 26: Xây dựng Frontend UI & Real-time Big Data Dashboard
- **Công việc cụ thể:**
  1. Xây dựng giao diện trực quan (bằng **React / Next.js** hoặc **Streamlit / Gradio** tùy thế mạnh của bạn) gồm **2 màn hình chính**:
     - **Màn hình 1 (E-Commerce & Visual Search):** Cho phép chọn tài khoản khách hàng (để thấy sự thay đổi cá nhân hóa), tải ảnh ngoài đời thực lên $\rightarrow$ Hiển thị ảnh có vẽ khung Bounding Box của YOLO $\rightarrow$ Hiển thị danh sách sản phẩm giống nhất kèm giải thích (*"Khớp 94% thị giác + Đang thuộc Top 10 Trending trong 15 phút qua"*).
     - **Màn hình 2 (Real-time Big Data Monitor):** Biểu đồ cập nhật trực tiếp từ Redis/Spark: Lưu lượng sự kiện/giây từ Kafka, Top sản phẩm đang bùng nổ lượt xem, phân bố doanh thu theo kênh Online/Offline.
- **Đầu ra nghiệm thu:** Giao diện hoàn chỉnh sẵn sàng quay video demo.

#### Ngày 27 – 28: Đánh giá Thực nghiệm (Evaluation) trên Tập Test & Tập Ảnh Tự chụp Việt Nam
- **Công việc cụ thể:**
  1. Chụp/thu thập **100 bức ảnh trang phục thực tế tại Việt Nam** (đủ các góc chụp, ánh sáng trong nhà/ngoài trời).
  2. Chạy đánh giá toàn diện và xuất ra 3 bảng số liệu chuẩn học thuật đưa vào báo cáo:
     - **Bảng 1 (Môn CV):** So sánh mAP của YOLOv8 và Recall@K của OpenCLIP trước/sau khi Fine-tune; so sánh trường hợp *Có dùng YOLO cắt vùng đồ* vs *Không dùng YOLO (đưa cả ảnh gốc vào CLIP)*.
     - **Bảng 2 (Môn RecSys):** So sánh chỉ số **MAP@12 (Mean Average Precision @ 12 - chuẩn của cuộc thi H&M)** trên tập Validation tuần cuối giữa: (1) Random/Popular Baseline, (2) Chỉ dùng Spark ALS, (3) Kết hợp Hybrid (Visual + Co-occurrence + Real-time Trending).
     - **Bảng 3 (Môn Big Data):** Biểu đồ Benchmark thông lượng (Throughput events/sec), độ trễ (Latency ms) và dung lượng lưu trữ (CSV vs Parquet).
- **Đầu ra nghiệm thu:** Đầy đủ bảng biểu, đồ thị thực nghiệm chất lượng cao.

#### Ngày 29 – 30: Đóng gói Docker Compose, Viết Báo cáo 2 Môn & Cập nhật CV
- **Công việc cụ thể:**
  1. Gộp toàn bộ hệ thống vào 1 file `docker-compose.yml` duy nhất và viết `README.md` có sơ đồ kiến trúc, ảnh GIF demo.
  2. Tách báo cáo theo trọng tâm từng môn:
     - **Báo cáo môn CV:** Nhấn mạnh vào kiến trúc 2 tầng (YOLOv8 Detection + Fine-tuned OpenCLIP/ConvNeXt), hàm Loss, kỹ thuật Augmentation, tối ưu ONNX FP16 và kết quả Ablation Study (Có/Không có YOLO crop).
     - **Báo cáo môn Big Data:** Nhấn mạnh vào kiến trúc Kappa/Lambda Lakehouse, tối ưu lưu trữ Parquet trên MinIO, xử lý phân tán 31,78 triệu dòng với PySpark, luồng Kafka + Spark Structured Streaming (Watermarking, Sliding Window) và tích hợp Vector DB Qdrant + Redis.

---

## PHẦN 4: CẤU HÌNH DOCKER COMPOSE TỐI ƯU CHO LAPTOP CÁ NHÂN (16GB - 32GB RAM)

Để chạy mượt cả hệ thống trên một máy mà không bị tràn RAM, bạn sử dụng cấu hình giới hạn tài nguyên dưới đây:

```yaml
version: '3.8'

services:
  # 1. Object Storage (Data Lake)
  minio:
    image: minio/minio:latest
    container_name: hm-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password123
    command: server /data --console-address ":9001"
    volumes:
      - ./data/minio:/data
    deploy:
      resources:
        limits:
          memory: 1G

  # 2. Vector Database (Lưu 105.100 vector ảnh 512 chiều)
  qdrant:
    image: qdrant/qdrant:latest
    container_name: hm-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    deploy:
      resources:
        limits:
          memory: 2G

  # 3. Message Broker (Kafka KRaft Mode - Không cần ZooKeeper)
  kafka:
    image: bitnami/kafka:3.7
    container_name: hm-kafka
    ports:
      - "9092:9092"
    environment:
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka:9093
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      - KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_HEAP_OPTS=-Xmx1G -Xms512M
    deploy:
      resources:
        limits:
          memory: 1.5G

  # 4. Online Feature Store & Real-time Cache
  redis:
    image: redis:7.2-alpine
    container_name: hm-redis
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          memory: 600M
```

---

## PHẦN 5: GỢI Ý CÁCH VIẾT DỰ ÁN NÀY VÀO CV (TIẾNG ANH CHUẨN ATS)

Khi hoàn thành đồ án này, bạn có thể đưa thẳng vào mục **Projects** trong CV ứng tuyển các vị trí **AI Engineer (CV / RecSys)** hoặc **Data Engineer** như sau:

> **Multimodal Visual Search & Real-Time Fashion Recommendation System** | *PyTorch, YOLOv8, OpenCLIP, Apache Spark, Kafka, Qdrant, Redis, FastAPI, Docker*
> - **Two-Stage Computer Vision Pipeline:** Built an automated visual search pipeline combining a fine-tuned **YOLOv8** detector (trained on **55K+ ModaNet** street images to localize 7 garment categories) with a fine-tuned **OpenCLIP (ViT-B/32)** encoder across **105K+ H&M catalog images**, improving Top-5 retrieval Recall by **14.2%** over zero-shot baselines and achieving **<25ms** GPU inference via **ONNX Runtime (FP16)**.
> - **Scalable Lakehouse & Stream Processing:** Engineered a batch and streaming data pipeline on **MinIO (S3)**, **Apache Kafka**, and **Spark Structured Streaming** to process **31.7M+ historical user transactions**, utilizing **Parquet** partitioning (reducing query latency by **8.5x**) and sliding-window aggregations to compute real-time trending scores and user session features in **Redis**.
> - **Hybrid Two-Stage Recommendation Engine:** Designed a low-latency (**<120ms** end-to-end) serving backend in **FastAPI** that retrieves visual & collaborative candidates via **Qdrant HNSW** vector search (**int8 quantization**) and reranks items using real-time behavioral signals from Redis, boosting **MAP@12** on temporal validation splits.