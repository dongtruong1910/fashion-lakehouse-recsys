"""Stage 1 CV: Garment Detector wrapper supporting Zero-shot (YOLO-World) and Fine-tuned YOLO11 ONNX FP16."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from src.contracts.schemas import BoundingBoxDetection
from src.utils.config import get_class_mapping_config, get_model_config


class GarmentDetector:
    """Unified interface for detecting and cropping 12 core fashion garment categories."""

    def __init__(self, weights_path: str | Path | None = None, device: str = "cuda") -> None:
        self.model_cfg = get_model_config()["cv"]["detector"]
        self.class_cfg = get_class_mapping_config()
        self.id_to_class: dict[int, str] = {
            int(k): v for k, v in self.class_cfg["detector_classes"].items()
        }
        self.weights_path = str(weights_path or self.model_cfg["train_model"])
        self.device = device
        self._model: Any = None

    def load(self) -> None:
        """Lazily load Ultralytics YOLO or ONNX Runtime session."""
        from ultralytics import YOLO

        self._model = YOLO(self.weights_path)

    def detect(
        self,
        image: Image.Image,
        conf_threshold: float | None = None,
        iou_threshold: float | None = None,
    ) -> list[BoundingBoxDetection]:
        """Run garment detection on a PIL Image and return standardized BoundingBoxDetection items."""
        if self._model is None:
            self.load()

        conf = conf_threshold if conf_threshold is not None else self.model_cfg["conf_threshold"]
        iou = iou_threshold if iou_threshold is not None else self.model_cfg["iou_threshold"]

        results = self._model.predict(
            source=image,
            conf=conf,
            iou=iou,
            imgsz=self.model_cfg["imgsz"],
            verbose=False,
        )
        detections: list[BoundingBoxDetection] = []
        if not results or len(results[0].boxes) == 0:
            return detections

        boxes = results[0].boxes
        for idx in range(len(boxes)):
            cls_id = int(boxes.cls[idx].item())
            det_class = self.id_to_class.get(cls_id, "other")
            score = float(boxes.conf[idx].item())
            x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[idx].tolist()]
            detections.append(
                BoundingBoxDetection(
                    box_id=idx,
                    detector_class=det_class,  # type: ignore[arg-type]
                    confidence=round(score, 4),
                    bbox_xyxy=(x1, y1, x2, y2),
                )
            )
        return detections

    @staticmethod
    def crop_box(image: Image.Image, bbox_xyxy: tuple[float, float, float, float]) -> Image.Image:
        """Crop a garment region from the original image with safe boundary clamping."""
        w, h = image.size
        x1, y1, x2, y2 = bbox_xyxy
        x1_c = max(0, int(round(x1)))
        y1_c = max(0, int(round(y1)))
        x2_c = min(w, int(round(x2)))
        y2_c = min(h, int(round(y2)))
        if x2_c <= x1_c or y2_c <= y1_c:
            return image
        return image.crop((x1_c, y1_c, x2_c, y2_c))
