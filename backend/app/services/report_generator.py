from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.report_storage import save_report_pdf


@dataclass
class GeneratedReport:
    gcs_object_path: str
    sha256: str
    pass_count: int
    fail_count: int
    generated_at_iso: str


@dataclass
class ReportRenderContext:
    site_name: str | None = None
    visit_status: str | None = None
    brand_label: str | None = None
    logo_object_path: str | None = None
    include_customer_signature: bool = False
    summary_notes: str | None = None
    checklist_answers: dict[str, Any] | None = None
    generation_total_kwh: float | None = None
    generation_summary_rows: list[dict[str, Any]] | None = None


def generate_report_pdf(
    workorder_id: str,
    *,
    report_version: int,
    context: ReportRenderContext | None = None,
) -> GeneratedReport:
    ctx = context or ReportRenderContext()
    now = datetime.now(timezone.utc)
    generated_at_iso = now.isoformat()
    pass_count, fail_count = _count_checklist(ctx.checklist_answers or {})
    pdf_bytes = _render_pdf_bytes(
        workorder_id=workorder_id,
        report_version=report_version,
        generated_at_iso=generated_at_iso,
        context=ctx,
        pass_count=pass_count,
        fail_count=fail_count,
    )
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    object_path = save_report_pdf(
        workorder_id=workorder_id,
        report_version=report_version,
        pdf_bytes=pdf_bytes,
    )
    return GeneratedReport(
        gcs_object_path=object_path,
        sha256=sha,
        pass_count=pass_count,
        fail_count=fail_count,
        generated_at_iso=generated_at_iso,
    )


def generate_report_placeholder(
    workorder_id: str,
    context: ReportRenderContext | None = None,
    *,
    report_version: int = 1,
) -> GeneratedReport:
    """
    Backward-compatible wrapper kept for existing callers/tests.
    Internally it now generates and stores a real PDF.
    """
    return generate_report_pdf(
        workorder_id,
        report_version=report_version,
        context=context,
    )


def _count_checklist(answers: dict[str, Any]) -> tuple[int, int]:
    passed = 0
    failed = 0
    for value in answers.values():
        if isinstance(value, bool):
            if value:
                passed += 1
            else:
                failed += 1
            continue
        if isinstance(value, str):
            norm = value.strip().lower()
            if norm in {"ok", "pass", "passed", "yes", "true", "satisfactory"}:
                passed += 1
            elif norm in {"fail", "failed", "no", "false", "critical", "needs_attention"}:
                failed += 1
    return passed, failed


def _render_pdf_bytes(
    *,
    workorder_id: str,
    report_version: int,
    generated_at_iso: str,
    context: ReportRenderContext,
    pass_count: int,
    fail_count: int,
) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, y, context.brand_label or "NEIL Solar AMC")

    y -= 22
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y, "Service Visit Report")
    y -= 14
    pdf.drawString(40, y, f"WorkOrder ID: {workorder_id}")
    y -= 14
    pdf.drawString(40, y, f"Report Version: {report_version}")
    y -= 14
    pdf.drawString(40, y, f"Generated At (UTC): {generated_at_iso}")
    y -= 20

    pdf.line(40, y, width - 40, y)
    y -= 20

    rows = [
        ("Site", context.site_name or "-"),
        ("Visit Status", context.visit_status or "-"),
        ("Pass Count", str(pass_count)),
        ("Fail Count", str(fail_count)),
        (
            "Generation Total (kWh)",
            f"{context.generation_total_kwh:.2f}" if context.generation_total_kwh is not None else "-",
        ),
        ("Customer Signature Included", "Yes" if context.include_customer_signature else "No"),
        ("Logo Path", context.logo_object_path or "-"),
    ]
    if context.summary_notes:
        rows.append(("Summary Notes", context.summary_notes))

    pdf.setFont("Helvetica", 10)
    for label, value in rows:
        if y < 80:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(40, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        for line in _wrap_text(str(value), max_chars=90):
            pdf.drawString(180, y, line)
            y -= 14
            if y < 80:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 10)

    y -= 10
    if y < 100:
        pdf.showPage()
        y = height - 50

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Sections")
    y -= 16
    pdf.setFont("Helvetica", 10)
    for line in [
        "1. Header and workorder summary",
        "2. Checklist observations",
        "3. Meter and inverter readings",
        "4. Inverter generation summary",
        "5. Technician and customer signatures",
        "6. Footer and generation metadata",
    ]:
        pdf.drawString(52, y, line)
        y -= 14

    generation_rows = context.generation_summary_rows or []
    if generation_rows:
        pdf.showPage()
        y = height - 50
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Inverter Generation Summary")
        y -= 20
        pdf.setFont("Helvetica", 10)
        for row in generation_rows:
            label = row.get("display_name") or row.get("inverter_code") or "Inverter"
            current = _display_number(row.get("current_reading_kwh"))
            previous = _display_number(row.get("previous_reading_kwh"))
            delta = "Baseline established" if row.get("is_baseline") else _display_number(row.get("generation_delta_kwh"))
            if row.get("is_anomaly"):
                delta = "Anomaly"
            line = f"{label}: prev {previous} | current {current} | generation {delta}"
            for wrapped in _wrap_text(line, max_chars=95):
                pdf.drawString(40, y, wrapped)
                y -= 14
                if y < 80:
                    pdf.showPage()
                    y = height - 50
                    pdf.setFont("Helvetica", 10)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _wrap_text(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _display_number(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)
