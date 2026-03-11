from __future__ import annotations

from pathlib import Path
import os

from app.core.config import settings

try:
    from google.cloud import storage
except Exception:  # pragma: no cover
    storage = None


_STORAGE_LOCAL = "LOCAL"
_STORAGE_GCS = "GCS"
_STORAGE_AUTO = "AUTO"


def save_report_pdf(*, workorder_id: str, report_version: int, pdf_bytes: bytes) -> str:
    object_name = f"reports/{workorder_id}/v{report_version}.pdf"
    backend = _resolve_backend()
    if backend == _STORAGE_GCS:
        if storage is None:
            raise RuntimeError("google-cloud-storage dependency is missing")
        if not settings.gcs_reports_bucket:
            raise RuntimeError("GCS_REPORTS_BUCKET is required for report storage backend=GCS")
        client = storage.Client()
        bucket = client.bucket(settings.gcs_reports_bucket)
        blob = bucket.blob(object_name)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")
        return f"gcs://{settings.gcs_reports_bucket}/{object_name}"

    base = Path(settings.local_reports_dir)
    file_path = base / object_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(pdf_bytes)
    return f"local://{object_name}"


def load_report_pdf(object_path: str) -> bytes:
    object_path = (object_path or "").strip()
    if object_path.startswith("gcs://"):
        if storage is None:
            raise RuntimeError("google-cloud-storage dependency is missing")
        bucket_name, object_name = _parse_gcs_path(object_path)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        return blob.download_as_bytes()

    if object_path.startswith("local://"):
        rel = object_path[len("local://") :]
    else:
        rel = object_path
    file_path = Path(settings.local_reports_dir) / rel
    if not file_path.exists():
        raise FileNotFoundError(f"Report file not found: {file_path}")
    return file_path.read_bytes()


def _resolve_backend() -> str:
    raw = (settings.report_storage_backend or "").strip().upper()
    if raw in {_STORAGE_LOCAL, _STORAGE_GCS}:
        return raw
    if raw not in {"", _STORAGE_AUTO}:
        raise RuntimeError(f"Unsupported REPORT_STORAGE_BACKEND: {raw}")

    # Auto mode:
    # - use GCS on Cloud Run if report bucket is configured
    # - use local file storage elsewhere
    if settings.gcs_reports_bucket and os.getenv("K_SERVICE"):
        return _STORAGE_GCS
    return _STORAGE_LOCAL


def _parse_gcs_path(path: str) -> tuple[str, str]:
    # format: gcs://bucket/object/path.pdf
    remainder = path[len("gcs://") :]
    if "/" not in remainder:
        raise RuntimeError(f"Invalid GCS path: {path}")
    bucket, object_name = remainder.split("/", 1)
    if not bucket or not object_name:
        raise RuntimeError(f"Invalid GCS path: {path}")
    return bucket, object_name
