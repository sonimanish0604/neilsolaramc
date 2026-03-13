from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.site import SiteInverter
from app.db.models.workorder import InverterReading, Media, WorkOrder
from app.services.geo_validation import validate_capture_location

ACCEPTED_WORKORDER_STATUSES = {"CUSTOMER_SIGNED", "CLOSED"}
NON_OPERATIONAL_STATUSES = {"OFFLINE", "FAULT", "UNAVAILABLE"}


@dataclass(frozen=True)
class GenerationComputation:
    previous_reading_kwh: float | None
    generation_delta_kwh: float | None
    is_baseline: bool
    is_anomaly: bool
    anomaly_reason: str | None


@dataclass(frozen=True)
class CaptureReadingInput:
    current_reading_kwh: float | None
    operational_status: str
    remarks: str | None
    photo_object_path: str
    photo_content_type: str
    photo_size_bytes: int
    site_latitude: float | None = None
    site_longitude: float | None = None
    device_latitude: float | None = None
    device_longitude: float | None = None
    device_accuracy_meters: float | None = None
    power_kw: float | None = None
    day_kwh: float | None = None


def to_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


def compute_generation(
    *,
    previous_reading_kwh: float | None,
    current_reading_kwh: float | None,
    operational_status: str,
) -> GenerationComputation:
    if current_reading_kwh is None:
        return GenerationComputation(
            previous_reading_kwh=previous_reading_kwh,
            generation_delta_kwh=None,
            is_baseline=False,
            is_anomaly=False,
            anomaly_reason=None,
        )

    if previous_reading_kwh is None:
        return GenerationComputation(
            previous_reading_kwh=None,
            generation_delta_kwh=None,
            is_baseline=True,
            is_anomaly=False,
            anomaly_reason=None,
        )

    if current_reading_kwh < previous_reading_kwh:
        return GenerationComputation(
            previous_reading_kwh=previous_reading_kwh,
            generation_delta_kwh=None,
            is_baseline=False,
            is_anomaly=True,
            anomaly_reason="Current reading is lower than the latest accepted reading",
        )

    if operational_status in NON_OPERATIONAL_STATUSES:
        return GenerationComputation(
            previous_reading_kwh=previous_reading_kwh,
            generation_delta_kwh=None,
            is_baseline=False,
            is_anomaly=False,
            anomaly_reason=None,
        )

    return GenerationComputation(
        previous_reading_kwh=previous_reading_kwh,
        generation_delta_kwh=current_reading_kwh - previous_reading_kwh,
        is_baseline=False,
        is_anomaly=False,
        anomaly_reason=None,
    )


def latest_accepted_reading(
    db: Session,
    *,
    inverter_id: UUID,
    current_workorder_id: UUID | None = None,
) -> InverterReading | None:
    stmt = (
        select(InverterReading)
        .join(WorkOrder, WorkOrder.id == InverterReading.workorder_id)
        .where(
            InverterReading.inverter_id == inverter_id,
            WorkOrder.status.in_(ACCEPTED_WORKORDER_STATUSES),
        )
        .order_by(
            WorkOrder.scheduled_at.desc(),
            InverterReading.captured_at.desc(),
            InverterReading.created_at.desc(),
        )
    )
    if current_workorder_id:
        stmt = stmt.where(InverterReading.workorder_id != current_workorder_id)
    return db.execute(stmt).scalars().first()


def list_site_inverters(db: Session, *, site_id: UUID, active_only: bool = True) -> list[SiteInverter]:
    stmt = select(SiteInverter).where(SiteInverter.site_id == site_id)
    if active_only:
        stmt = stmt.where(SiteInverter.is_active.is_(True))
    stmt = stmt.order_by(SiteInverter.display_name.asc(), SiteInverter.created_at.asc())
    return db.execute(stmt).scalars().all()


def get_site_inverter(db: Session, *, site_id: UUID, inverter_id: UUID) -> SiteInverter | None:
    return db.execute(
        select(SiteInverter).where(
            SiteInverter.site_id == site_id,
            SiteInverter.id == inverter_id,
        )
    ).scalar_one_or_none()


def get_workorder_inverter_reading(
    db: Session,
    *,
    workorder_id: UUID,
    inverter_id: UUID,
) -> InverterReading | None:
    return db.execute(
        select(InverterReading).where(
            InverterReading.workorder_id == workorder_id,
            InverterReading.inverter_id == inverter_id,
        )
    ).scalar_one_or_none()


def upsert_workorder_inverter_reading(
    db: Session,
    *,
    tenant_id: UUID,
    workorder: WorkOrder,
    inverter: SiteInverter,
    capture: CaptureReadingInput,
    captured_at_iso: str,
) -> InverterReading:
    reading = get_workorder_inverter_reading(db, workorder_id=workorder.id, inverter_id=inverter.id)
    previous = latest_accepted_reading(db, inverter_id=inverter.id, current_workorder_id=workorder.id)
    previous_reading_kwh = to_float(previous.current_reading_kwh or previous.total_kwh) if previous else None
    current_reading_kwh = capture.current_reading_kwh
    computed = compute_generation(
        previous_reading_kwh=previous_reading_kwh,
        current_reading_kwh=current_reading_kwh,
        operational_status=capture.operational_status,
    )
    geo_validation = validate_capture_location(
        site_latitude=capture.site_latitude,
        site_longitude=capture.site_longitude,
        device_latitude=capture.device_latitude,
        device_longitude=capture.device_longitude,
        device_accuracy_meters=capture.device_accuracy_meters,
    )

    if reading is None:
        reading = InverterReading(
            tenant_id=tenant_id,
            workorder_id=workorder.id,
            inverter_id=inverter.id,
        )
        db.add(reading)

    reading.power_kw = capture.power_kw
    reading.day_kwh = capture.day_kwh
    reading.total_kwh = current_reading_kwh
    reading.current_reading_kwh = current_reading_kwh
    reading.previous_reading_kwh = computed.previous_reading_kwh
    reading.generation_delta_kwh = computed.generation_delta_kwh
    reading.is_baseline = computed.is_baseline
    reading.is_anomaly = computed.is_anomaly
    reading.anomaly_reason = computed.anomaly_reason
    reading.device_latitude = capture.device_latitude
    reading.device_longitude = capture.device_longitude
    reading.device_accuracy_meters = capture.device_accuracy_meters
    reading.distance_to_site_meters = geo_validation.distance_to_site_meters
    reading.geo_validation_status = geo_validation.status
    reading.geo_validation_reason = geo_validation.reason
    reading.operational_status = capture.operational_status
    reading.remarks = capture.remarks
    reading.captured_at = captured_at_iso
    db.flush()

    db.execute(delete(Media).where(Media.inverter_reading_id == reading.id))
    db.add(
        Media(
            tenant_id=tenant_id,
            workorder_id=workorder.id,
            inverter_reading_id=reading.id,
            item_key=f"inverter_reading:{inverter.inverter_code}",
            media_type="PHOTO",
            gcs_object_path=capture.photo_object_path,
            content_type=capture.photo_content_type,
            size_bytes=capture.photo_size_bytes,
        )
    )
    db.flush()
    return reading


def ensure_site_inverter_capture_complete(
    db: Session,
    *,
    workorder: WorkOrder,
) -> list[str]:
    configured = list_site_inverters(db, site_id=workorder.site_id, active_only=True)
    if not configured:
        return []

    captured_rows = db.execute(
        select(InverterReading).where(InverterReading.workorder_id == workorder.id)
    ).scalars().all()
    captured_by_inverter_id = {row.inverter_id: row for row in captured_rows}

    errors: list[str] = []
    for inverter in configured:
        reading = captured_by_inverter_id.get(inverter.id)
        if reading is None:
            errors.append(f"Missing reading for inverter {inverter.display_name}")
            continue

        if (
            reading.operational_status == "OPERATIONAL"
            and reading.current_reading_kwh is None
        ):
            errors.append(f"Operational inverter {inverter.display_name} requires current_reading_kwh")
        elif reading.current_reading_kwh is None and reading.operational_status not in NON_OPERATIONAL_STATUSES:
            errors.append(f"Inverter {inverter.display_name} must be captured or marked non-operational")
        if (
            reading.current_reading_kwh is None
            and reading.operational_status in NON_OPERATIONAL_STATUSES
            and not (reading.remarks and reading.remarks.strip())
        ):
            errors.append(f"Non-operational inverter {inverter.display_name} requires remarks")
    return errors


def active_inverter_ids(inverters: Iterable[SiteInverter]) -> set[UUID]:
    return {inverter.id for inverter in inverters if inverter.is_active}
