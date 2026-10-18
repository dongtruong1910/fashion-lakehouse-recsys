"""Stage 1 CV: Garment Detector wrapper supporting Zero-shot (YOLO-World) and Fine-tuned YOLO11 ONNX FP16."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from src.contracts.schemas import BoundingBoxDetection
from src.utils.config import get_class_mapping_config, get_model_config


def resolve_detector_class_from_model_names(
    cls_id: int,
    model_names: dict[int, str] | list[str] | None,
    fashion12_map: dict[int, str],
    fashionpedia_to_detector: dict[str, str] | None = None,
) -> str:
    """Validate and map a predicted class ID using the checkpoint's actual class ontology (Finding A04).

    Raises:
        RuntimeError: If a generic COCO checkpoint (e.g. class 0 == 'person') is used without fashion12 alignment.
    """
    valid_fashion12 = set(fashion12_map.values())
    if model_names is None:
        return fashion12_map.get(cls_id, "other")

    if isinstance(model_names, list):
        names_dict = {i: str(n) for i, n in enumerate(model_names)}
    else:
        names_dict = {int(k): str(v) for k, v in model_names.items()}

    # Detect unadapted COCO80 checkpoints (where class 0 is 'person')
    if names_dict.get(0, "").strip().lower() == "person":
        raise RuntimeError(
            "Detector ontology mismatch (Finding A04): Loaded checkpoint uses COCO classes "
            "(id 0 = 'person') instead of the 12 Fashionpedia garment classes. "
            "Use a trained fashion12 checkpoint or a YOLO-World model with set_classes()."
        )

    raw_name = names_dict.get(cls_id, "").strip()
    if raw_name in valid_fashion12:
        return raw_name
    if fashionpedia_to_detector and raw_name in fashionpedia_to_detector:
        return fashionpedia_to_detector[raw_name]
    if set(names_dict.values()).issubset(valid_fashion12 | {"other"}):
        return fashion12_map.get(cls_id, "other")

    raise RuntimeError(
        f"Detector ontology mismatch (Finding A04): Unrecognized class '{raw_name}' (id={cls_id}) "
        f"not in 12 core fashion classes {sorted(valid_fashion12)}."
    )


class GarmentDetector:
    """Unified interface for detecting and cropping 12 core fashion garment categories."""

    def __init__(self, weights_path: str | Path | None = None, device: str = "cuda") -> None:
        self.model_cfg = get_model_config()["cv"]["detector"]
        self.class_cfg = get_class_mapping_config()
        self.id_to_class: dict[int, str] = {
            int(k): v for k, v in self.class_cfg["detector_classes"].items()
        }
        self.fp_to_detector: dict[str, str] = dict(
            self.class_cfg.get("fashionpedia_to_detector", {})
        )
        self.weights_path = str(weights_path or self.model_cfg["zeroshot_model"])
        self.device = device
        self._model: Any = None

    def load(self) -> None:
        """Lazily load Ultralytics YOLO/YOLO-World or ONNX Runtime session and configure classes."""
        from ultralytics import YOLO

        self._model = YOLO(self.weights_path)
        if "world" in Path(self.weights_path).name.lower() and hasattr(self._model, "set_classes"):
            ordered_classes = [self.id_to_class[i] for i in sorted(self.id_to_class)]
            self._model.set_classes(ordered_classes)

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
            device=self.device,
            verbose=False,
        )
        detections: list[BoundingBoxDetection] = []
        if not results or len(results[0].boxes) == 0:
            return detections

        model_names = getattr(results[0], "names", None) or getattr(self._model, "names", None)
        boxes = results[0].boxes
        for idx in range(len(boxes)):
            cls_id = int(boxes.cls[idx].item())
            det_class = resolve_detector_class_from_model_names(
                cls_id=cls_id,
                model_names=model_names,
                fashion12_map=self.id_to_class,
                fashionpedia_to_detector=self.fp_to_detector,
            )
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
