# HƯỚNG DẪN CHẠY JOB TRÊN GOOGLE COLAB PRO+ (GPU L4) & TỰ ĐỘNG TẮT RUNTIME

> **Đọc kỹ trước khi bật GPU trên Colab:** [`docs/INFRA_AND_COLAB_GUIDE.md`](../docs/INFRA_AND_COLAB_GUIDE.md)

## Quy trình 4 Cell Chuẩn cho Mọi Notebook trên Colab Pro+ (L4 GPU)

### Cell 1: Kết nối Google Drive & Giải nén Dataset vào Ổ SSD Nội bộ `/content/local_data`
*(Tuyệt đối không đọc hàng chục nghìn file ảnh trực tiếp từ `/content/drive`!)*
```python
from google.colab import drive
drive.mount("/content/drive")

!mkdir -p /content/local_data
!cp /content/drive/MyDrive/btl_cv_bigdata/datasets/fashionpedia_yolo.tar /content/local_data/
!tar -xf /content/local_data/fashionpedia_yolo.tar -C /content/local_data/
```

### Cell 2: Clone / Pull Codebase & Cài đặt Thư viện
```python
%cd /content
!git clone https://github.com/<your-username>/fashion-lakehouse-recsys.git || (cd fashion-lakehouse-recsys && git pull)
%cd /content/fashion-lakehouse-recsys
!pip install -q -r requirements-colab.txt
```

### Cell 3 & 4: Huấn luyện + Xuất ONNX FP16 + Tự động Ngắt Runtime (`runtime.unassign()`)
```python
from google.colab import runtime
from ultralytics import YOLO

SAVE_DIR = "/content/drive/MyDrive/btl_cv_bigdata/checkpoints/yolo11m"

try:
    model = YOLO("yolo11m.pt")
    model.train(
        data="/content/local_data/fashionpedia.yaml",
        epochs=60,
        imgsz=640,
        batch=32,
        device=0,
        amp=True,
        patience=15,
        save_period=1,
        project=SAVE_DIR,
        name="run_v1",
    )
    # Xuất ngay sang ONNX FP16 (~40MB) để tải về Laptop RTX 4060 chạy mượt
    best_model = YOLO(f"{SAVE_DIR}/run_v1/weights/best.pt")
    best_model.export(format="onnx", imgsz=640, half=True, simplify=True)
finally:
    print("Hoàn tất huấn luyện & xuất ONNX. Tự động ngắt Colab Runtime để bảo toàn Compute Units!")
    runtime.unassign()
```
