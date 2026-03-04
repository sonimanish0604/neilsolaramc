from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib


@dataclass
class GeneratedReport:
    gcs_object_path: str
    sha256: str
    pass_count: int
    fail_count: int
    generated_at_iso: str


def generate_report_placeholder(workorder_id: str) -> GeneratedReport:
    """
    MVP placeholder. Later: render HTML -> PDF, upload to GCS, return object path + hash.
    """
    now = datetime.now(timezone.utc).isoformat()
    fake_pdf_bytes = f"PDF for workorder {workorder_id} at {now}".encode("utf-8")
    sha = hashlib.sha256(fake_pdf_bytes).hexdigest()
    return GeneratedReport(
        gcs_object_path=f"reports/{workorder_id}/report.pdf",
        sha256=sha,
        pass_count=0,
        fail_count=0,
        generated_at_iso=now,
    )