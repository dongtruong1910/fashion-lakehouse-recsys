"""Download and verify the Fashionpedia dataset from Hugging Face into `data/raw/fashionpedia`.

Features:
  - Resumable download: Supports HTTP Range headers. If network drops or script is stopped,
    it resumes downloading from the exact byte where it was interrupted.
  - Automatic retry: Automatically retries on network drops/timeouts with exponential backoff.
  - Skips already completed files: Will not re-download files that already exist with correct size.
  - Integrity verification: Uses pyarrow to inspect row counts, schema, and bounding box structure.
  - Generates verifiable report: Saves statistics to reports/tables/fashionpedia_download_summary.json.

Dataset source:
  `detection-datasets/fashionpedia` on Hugging Face (~3.24 GB, 46 fine-grained classes, Parquet format).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any

import requests
from tqdm import tqdm
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("download_fashionpedia")

HF_API_DATASET_URL = "https://huggingface.co/api/datasets/{repo_id}"
HF_RESOLVE_URL = "https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"


def load_target_dir_from_config(config_path: str = "configs/paths.yaml") -> Path:
    """Load the configured fashionpedia_dir from paths.yaml, falling back to data/raw/fashionpedia."""
    cfg_file = Path(config_path)
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            target = cfg.get("raw", {}).get("fashionpedia_dir")
            if target:
                return Path(target)
        except Exception as e:
            logger.warning("Failed to parse %s: %s. Using default directory.", config_path, e)
    return Path("data/raw/fashionpedia")


def fetch_remote_file_list(repo_id: str, max_retries: int = 5) -> list[dict[str, Any]]:
    """Fetch list of files and sizes from Hugging Face dataset metadata API."""
    url = HF_API_DATASET_URL.format(repo_id=repo_id)
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            siblings = data.get("siblings", [])
            return siblings
        except Exception as e:
            logger.warning("Attempt %d/%d to fetch file list failed: %s", attempt, max_retries, e)
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)
    return []


def download_file_resumable(
    url: str,
    dest_path: Path,
    expected_size: int | None = None,
    chunk_size: int = 1024 * 1024,  # 1 MB chunks
    max_retries: int = 30,
    base_retry_delay: float = 3.0,
) -> Path:
    """Download a single file with resume capability and auto-retry on disconnection."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_name(f"{dest_path.name}.part")

    # If completed file already exists and size matches
    if dest_path.exists():
        current_size = dest_path.stat().st_size
        if expected_size is None or current_size == expected_size:
            logger.info("File already complete: %s (%.2f MB). Skipping.", dest_path.name, current_size / 1024**2)
            return dest_path
        else:
            logger.warning("Existing file %s size (%d) != expected (%d). Re-downloading.", dest_path.name, current_size, expected_size)
            dest_path.unlink()

    downloaded_bytes = temp_path.stat().st_size if temp_path.exists() else 0

    if downloaded_bytes > 0:
        logger.info("Resuming %s from byte %d (%.2f MB)...", dest_path.name, downloaded_bytes, downloaded_bytes / 1024**2)

    total_size = expected_size

    for attempt in range(1, max_retries + 1):
        headers = {}
        if downloaded_bytes > 0:
            headers["Range"] = f"bytes={downloaded_bytes}-"

        try:
            with requests.get(url, headers=headers, stream=True, timeout=(15, 90)) as resp:
                if resp.status_code == 416:
                    # Range not satisfiable; likely file already complete
                    if total_size is not None and downloaded_bytes >= total_size:
                        temp_path.replace(dest_path)
                        logger.info("Finished %s via existing temp file.", dest_path.name)
                        return dest_path
                    else:
                        # Reset and restart from 0
                        downloaded_bytes = 0
                        if temp_path.exists():
                            temp_path.unlink()
                        continue

                resp.raise_for_status()

                # Check if server accepted range
                is_resume = (resp.status_code == 206)
                if not is_resume and downloaded_bytes > 0:
                    logger.warning("Server did not accept Range header; restarting %s from 0.", dest_path.name)
                    downloaded_bytes = 0

                content_len = resp.headers.get("Content-Length")
                if total_size is None and content_len is not None:
                    total_size = int(content_len) + (downloaded_bytes if is_resume else 0)

                mode = "ab" if is_resume else "wb"
                progress_total = total_size if total_size else None

                with open(temp_path, mode) as f, tqdm(
                    desc=dest_path.name,
                    total=progress_total,
                    initial=downloaded_bytes,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    leave=True,
                ) as pbar:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
                            downloaded_bytes += len(chunk)

            # Check completion
            if total_size is None or downloaded_bytes >= total_size:
                temp_path.replace(dest_path)
                logger.info("Successfully downloaded: %s (%.2f MB)", dest_path.name, downloaded_bytes / 1024**2)
                return dest_path
            else:
                raise ConnectionError(f"Incomplete download: got {downloaded_bytes} bytes out of {total_size}")

        except (requests.exceptions.RequestException, ConnectionError, OSError) as err:
            logger.warning(
                "Network interruption while downloading %s (Attempt %d/%d): %s",
                dest_path.name,
                attempt,
                max_retries,
                err,
            )
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to download {dest_path.name} after {max_retries} attempts. Last error: {err}"
                ) from err

            sleep_seconds = min(60.0, base_retry_delay * (1.3 ** min(attempt - 1, 10)))
            logger.info("Retrying in %.1f seconds...", sleep_seconds)
            time.sleep(sleep_seconds)
            if temp_path.exists():
                downloaded_bytes = temp_path.stat().st_size

    raise RuntimeError(f"Unexpected termination for {dest_path.name}")


def download_fashionpedia(
    repo_id: str = "detection-datasets/fashionpedia",
    target_dir: Path | str = "data/raw/fashionpedia",
    val_only: bool = False,
    max_retries: int = 10,
) -> Path:
    """Download Fashionpedia parquet files and metadata with auto-resume and auto-retry."""
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    logger.info("Querying Hugging Face repository '%s'...", repo_id)
    siblings = fetch_remote_file_list(repo_id)

    files_to_download: list[dict[str, Any]] = []
    for item in siblings:
        rfilename = item.get("rfilename", "")
        # Filter files
        if val_only:
            if rfilename.startswith("data/val") or rfilename in ("README.md", "dataset_infos.json"):
                files_to_download.append(item)
        else:
            if rfilename.startswith("data/") or rfilename in ("README.md", "dataset_infos.json"):
                files_to_download.append(item)

    logger.info("Found %d files to download in '%s' (val_only=%s).", len(files_to_download), repo_id, val_only)

    for idx, item in enumerate(files_to_download, 1):
        rfilename = item["rfilename"]
        expected_size = item.get("size")
        dest_file = target_path / rfilename
        url = HF_RESOLVE_URL.format(repo_id=repo_id, filename=rfilename)

        logger.info("[%d/%d] Processing %s...", idx, len(files_to_download), rfilename)
        download_file_resumable(
            url=url,
            dest_path=dest_file,
            expected_size=expected_size,
            max_retries=max_retries,
        )

    logger.info("All files downloaded to %s.", target_path)
    return target_path


def verify_downloaded_dataset(dataset_dir: Path | str) -> dict[str, Any]:
    """Verify integrity of downloaded parquet files and return summary statistics."""
    dir_path = Path(dataset_dir)
    parquet_files = sorted(dir_path.glob("data/*.parquet"))

    if not parquet_files:
        parquet_files = sorted(dir_path.glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {dir_path} or {dir_path / 'data'}")

    total_bytes = 0
    file_stats = []
    train_rows = 0
    val_rows = 0
    schema_fields: list[str] = []

    try:
        import pyarrow.parquet as pq
        has_pyarrow = True
    except ImportError:
        has_pyarrow = False
        logger.warning("pyarrow not installed; row-level inspection will be skipped.")

    for pf in parquet_files:
        size = pf.stat().st_size
        total_bytes += size
        stat_item: dict[str, Any] = {
            "file_name": pf.name,
            "rel_path": str(pf.relative_to(dir_path)).replace("\\", "/"),
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
        }

        if has_pyarrow:
            try:
                parquet_meta = pq.read_metadata(str(pf))
                num_rows = parquet_meta.num_rows
                stat_item["num_rows"] = num_rows
                stat_item["num_columns"] = parquet_meta.num_columns
                if not schema_fields:
                    schema_fields = [parquet_meta.schema.names[i] for i in range(len(parquet_meta.schema.names))]

                if "train" in pf.name:
                    train_rows += num_rows
                elif "val" in pf.name:
                    val_rows += num_rows
            except Exception as e:
                logger.error("Failed reading metadata of %s: %s", pf.name, e)
                stat_item["error"] = str(e)

        file_stats.append(stat_item)

    # Check sample row if pyarrow is present
    sample_info: dict[str, Any] = {}
    if has_pyarrow and parquet_files:
        try:
            import pyarrow.parquet as pq
            first_pf = parquet_files[0]
            table = pq.read_table(str(first_pf))
            sample_info = {
                "inspected_file": first_pf.name,
                "column_names": table.column_names,
                "first_row_image_id": int(table["image_id"][0].as_py()) if "image_id" in table.column_names else None,
                "objects_schema": str(table.schema.field("objects").type) if "objects" in table.column_names else None,
            }
        except Exception as e:
            logger.warning("Sample row inspection error: %s", e)

    summary: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_dir": str(dir_path).replace("\\", "/"),
        "total_files": len(file_stats),
        "total_size_bytes": total_bytes,
        "total_size_gb": round(total_bytes / (1024**3), 3),
        "total_train_rows": train_rows,
        "total_val_rows": val_rows,
        "total_rows": train_rows + val_rows,
        "schema_fields": schema_fields,
        "sample_inspection": sample_info,
        "files": file_stats,
    }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Resumable download for Fashionpedia dataset.")
    parser.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="Target directory to store dataset. If omitted, read from configs/paths.yaml.",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default="detection-datasets/fashionpedia",
        help="Hugging Face dataset repository ID.",
    )
    parser.add_argument(
        "--val-only",
        action="store_true",
        help="Download only validation parquet shards.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=30,
        help="Maximum retry attempts on network disruption.",
    )
    parser.add_argument(
        "--save-summary",
        type=str,
        default="reports/tables/fashionpedia_download_summary.json",
        help="Path to save JSON summary report.",
    )
    args = parser.parse_args()

    if args.target_dir:
        target_dir = Path(args.target_dir)
    else:
        target_dir = load_target_dir_from_config()

    logger.info("Destination directory: %s", target_dir)

    try:
        download_fashionpedia(
            repo_id=args.repo_id,
            target_dir=target_dir,
            val_only=args.val_only,
            max_retries=args.max_retries,
        )
    except Exception as e:
        logger.error("Download failed: %s", e)
        sys.exit(1)

    logger.info("Verifying downloaded dataset...")
    try:
        summary = verify_downloaded_dataset(target_dir)
        logger.info("Verification succeeded!")
        logger.info(
            "Summary: %d files, %.2f GB, Train rows: %d, Val rows: %d, Total rows: %d",
            summary["total_files"],
            summary["total_size_gb"],
            summary["total_train_rows"],
            summary["total_val_rows"],
            summary["total_rows"],
        )

        if args.save_summary:
            out_path = Path(args.save_summary)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info("Saved verification summary to %s", out_path)

    except Exception as e:
        logger.error("Verification failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
