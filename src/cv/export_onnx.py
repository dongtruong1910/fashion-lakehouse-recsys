"""ONNX FP16 Export & Verification utility for fitting models into RTX 4060 8GB VRAM.

See `docs/INFRA_AND_COLAB_GUIDE.md` (Section 2) for the 5-Layer Model Fitting Strategy.
"""

from __future__ import annotations

from pathlib import Path


def export_yolo_to_onnx(
    pt_weights_path: str | Path,
    imgsz: int = 640,
    half: bool = True,
) -> Path:
    """Export trained Ultralytics YOLO11 weights (.pt) to ONNX Runtime format (FP16 by default)."""
    from ultralytics import YOLO

    model = YOLO(str(pt_weights_path))
    exported_path = model.export(format="onnx", imgsz=imgsz, half=half, simplify=True)
    return Path(exported_path)
