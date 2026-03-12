from __future__ import annotations

import hashlib

from app.services import report_storage
from app.services.report_generator import ReportRenderContext, generate_report_pdf
from app.services.report_storage import load_report_pdf


def test_generate_report_pdf_local_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(report_storage.settings, "report_storage_backend", "LOCAL")
    monkeypatch.setattr(report_storage.settings, "local_reports_dir", str(tmp_path))

    generated = generate_report_pdf(
        "wo-local-1",
        report_version=1,
        context=ReportRenderContext(
            site_name="Demo Site",
            visit_status="SATISFACTORY",
            brand_label="NEIL",
            include_customer_signature=False,
            checklist_answers={"a": True, "b": False},
        ),
    )

    assert generated.gcs_object_path.startswith("local://reports/wo-local-1/v1.pdf")
    pdf_bytes = load_report_pdf(generated.gcs_object_path)
    assert pdf_bytes.startswith(b"%PDF")
    assert generated.sha256 == hashlib.sha256(pdf_bytes).hexdigest()
    assert generated.pass_count == 1
    assert generated.fail_count == 1


def test_generate_report_pdf_hash_changes_by_version_or_signature(monkeypatch, tmp_path):
    monkeypatch.setattr(report_storage.settings, "report_storage_backend", "LOCAL")
    monkeypatch.setattr(report_storage.settings, "local_reports_dir", str(tmp_path))

    base = generate_report_pdf(
        "wo-local-2",
        report_version=1,
        context=ReportRenderContext(site_name="Site A", include_customer_signature=False),
    )
    signed = generate_report_pdf(
        "wo-local-2",
        report_version=2,
        context=ReportRenderContext(site_name="Site A", include_customer_signature=True),
    )

    assert base.sha256 != signed.sha256


def test_generate_report_pdf_supports_generation_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(report_storage.settings, "report_storage_backend", "LOCAL")
    monkeypatch.setattr(report_storage.settings, "local_reports_dir", str(tmp_path))

    generated = generate_report_pdf(
        "wo-local-3",
        report_version=1,
        context=ReportRenderContext(
            site_name="Generation Site",
            visit_status="SATISFACTORY",
            generation_total_kwh=754.7,
            generation_summary_rows=[
                {
                    "display_name": "INV-01",
                    "previous_reading_kwh": 1000.0,
                    "current_reading_kwh": 1754.7,
                    "generation_delta_kwh": 754.7,
                    "is_baseline": False,
                    "is_anomaly": False,
                }
            ],
        ),
    )

    pdf_bytes = load_report_pdf(generated.gcs_object_path)
    assert pdf_bytes.startswith(b"%PDF")
