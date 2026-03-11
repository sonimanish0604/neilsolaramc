from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.workorder import Report, ReportJob
from app.services.approval_tokens import iso_utc, now_utc, parse_iso
from app.services.report_generator import generate_report_placeholder


TERMINAL_REPORT_JOB_STATUSES = {"SUCCEEDED", "DEAD"}


@dataclass(frozen=True)
class ReportJobRunResult:
    job: ReportJob
    report: Report | None


def build_idempotency_key(*, workorder_id: UUID, is_final: bool) -> str:
    suffix = "final" if is_final else "draft"
    nonce = secrets.token_hex(6)
    return f"{workorder_id}:{suffix}:{nonce}"


def compute_report_retry_at(attempt_count: int) -> str:
    multiplier = max(1, 2 ** max(0, attempt_count - 1))
    delay = settings.report_job_backoff_seconds * multiplier
    return iso_utc(now_utc() + timedelta(seconds=delay))


def enqueue_report_job(
    db: Session,
    *,
    tenant_id: UUID,
    workorder_id: UUID,
    is_final: bool,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
    simulate_failures: int = 0,
) -> ReportJob:
    key = idempotency_key or build_idempotency_key(workorder_id=workorder_id, is_final=is_final)

    existing = db.execute(
        select(ReportJob).where(
            ReportJob.workorder_id == workorder_id,
            ReportJob.idempotency_key == key,
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    job = ReportJob(
        tenant_id=tenant_id,
        workorder_id=workorder_id,
        job_type="FINAL" if is_final else "DRAFT",
        status="QUEUED",
        idempotency_key=key,
        correlation_id=correlation_id,
        max_attempts=settings.report_job_max_attempts,
        attempt_count=0,
        simulate_failures_remaining=simulate_failures if settings.app_env != "prod" else 0,
    )
    db.add(job)
    db.flush()
    return job


def run_report_job(db: Session, *, job: ReportJob, force: bool = False) -> ReportJobRunResult:
    if job.status == "SUCCEEDED":
        report = None
        if job.generated_report_id:
            report = db.execute(select(Report).where(Report.id == job.generated_report_id)).scalar_one_or_none()
        return ReportJobRunResult(job=job, report=report)

    if job.status == "DEAD":
        return ReportJobRunResult(job=job, report=None)

    if not force and job.next_retry_at and parse_iso(job.next_retry_at) > now_utc():
        return ReportJobRunResult(job=job, report=None)

    job.status = "RUNNING"
    job.started_at = iso_utc(now_utc())
    job.attempt_count += 1

    try:
        if job.simulate_failures_remaining > 0:
            job.simulate_failures_remaining -= 1
            raise RuntimeError("simulated transient report generation failure")

        generated = generate_report_placeholder(str(job.workorder_id))

        current_version = db.execute(
            select(Report.report_version)
            .where(Report.workorder_id == job.workorder_id)
            .order_by(desc(Report.report_version))
        ).scalars().first()

        report = Report(
            tenant_id=job.tenant_id,
            workorder_id=job.workorder_id,
            report_version=(current_version or 0) + 1,
            pdf_gcs_object_path=generated.gcs_object_path,
            pdf_sha256=generated.sha256,
            pass_count=generated.pass_count,
            fail_count=generated.fail_count,
            generated_at=generated.generated_at_iso,
            is_final=(job.job_type == "FINAL"),
        )
        db.add(report)
        db.flush()

        job.generated_report_id = report.id
        job.status = "SUCCEEDED"
        job.completed_at = iso_utc(now_utc())
        job.next_retry_at = None
        job.last_error = None
        db.flush()

        return ReportJobRunResult(job=job, report=report)
    except Exception as exc:
        job.last_error = str(exc)[:1000]
        if job.attempt_count >= job.max_attempts:
            job.status = "DEAD"
            job.next_retry_at = None
        else:
            job.status = "FAILED"
            job.next_retry_at = compute_report_retry_at(job.attempt_count)
        db.flush()
        return ReportJobRunResult(job=job, report=None)


def retry_report_job(db: Session, *, job: ReportJob) -> ReportJobRunResult:
    if job.status not in {"FAILED", "DEAD"}:
        return ReportJobRunResult(job=job, report=None)

    if job.status == "DEAD":
        job.status = "FAILED"
        job.attempt_count = 0
        job.next_retry_at = iso_utc(now_utc())

    return run_report_job(db, job=job, force=True)
