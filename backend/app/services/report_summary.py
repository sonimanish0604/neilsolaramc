from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.site import SiteInverter
from app.db.models.workorder import InverterReading, Media, Report, WorkOrder
from app.services.inverter_readings import list_site_inverters, to_float


@dataclass(frozen=True)
class GenerationSummaryRow:
    inverter_id: UUID
    inverter_code: str
    display_name: str
    previous_reading_kwh: float | None
    current_reading_kwh: float | None
    generation_delta_kwh: float | None
    is_baseline: bool
    is_anomaly: bool
    anomaly_reason: str | None
    operational_status: str | None
    remarks: str | None
    photo_object_path: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "inverter_id": str(self.inverter_id),
            "inverter_code": self.inverter_code,
            "display_name": self.display_name,
            "previous_reading_kwh": self.previous_reading_kwh,
            "current_reading_kwh": self.current_reading_kwh,
            "generation_delta_kwh": self.generation_delta_kwh,
            "is_baseline": self.is_baseline,
            "is_anomaly": self.is_anomaly,
            "anomaly_reason": self.anomaly_reason,
            "operational_status": self.operational_status,
            "remarks": self.remarks,
            "photo_object_path": self.photo_object_path,
        }


@dataclass(frozen=True)
class WorkOrderGenerationSummary:
    workorder_id: UUID
    site_id: UUID
    generation_total_kwh: float
    baseline_inverter_count: int
    anomaly_count: int
    inverters: list[GenerationSummaryRow]

    def snapshot(self) -> dict[str, Any]:
        return {
            "workorder_id": str(self.workorder_id),
            "site_id": str(self.site_id),
            "generation_total_kwh": self.generation_total_kwh,
            "baseline_inverter_count": self.baseline_inverter_count,
            "anomaly_count": self.anomaly_count,
            "inverters": [row.as_dict() for row in self.inverters],
        }


def build_workorder_generation_summary(db: Session, *, workorder: WorkOrder) -> WorkOrderGenerationSummary:
    inverters = list_site_inverters(db, site_id=workorder.site_id, active_only=True)
    readings = db.execute(
        select(InverterReading).where(InverterReading.workorder_id == workorder.id)
    ).scalars().all()
    readings_by_inverter_id = {reading.inverter_id: reading for reading in readings}

    reading_ids = [reading.id for reading in readings]
    media_by_reading_id: dict[UUID, Media] = {}
    if reading_ids:
        media_rows = db.execute(select(Media).where(Media.inverter_reading_id.in_(reading_ids))).scalars().all()
        media_by_reading_id = {media.inverter_reading_id: media for media in media_rows if media.inverter_reading_id}

    rows: list[GenerationSummaryRow] = []
    generation_total_kwh = 0.0
    baseline_inverter_count = 0
    anomaly_count = 0
    if not inverters:
        for reading in readings:
            media = media_by_reading_id.get(reading.id)
            delta = to_float(reading.generation_delta_kwh)
            if delta is not None and not reading.is_anomaly:
                generation_total_kwh += delta
            if reading.is_baseline:
                baseline_inverter_count += 1
            if reading.is_anomaly:
                anomaly_count += 1
            rows.append(
                GenerationSummaryRow(
                    inverter_id=reading.inverter_id,
                    inverter_code=str(reading.inverter_id),
                    display_name=f"Inverter {str(reading.inverter_id)[:8]}",
                    previous_reading_kwh=to_float(reading.previous_reading_kwh),
                    current_reading_kwh=to_float(reading.current_reading_kwh or reading.total_kwh),
                    generation_delta_kwh=delta,
                    is_baseline=bool(reading.is_baseline),
                    is_anomaly=bool(reading.is_anomaly),
                    anomaly_reason=reading.anomaly_reason,
                    operational_status=reading.operational_status,
                    remarks=reading.remarks,
                    photo_object_path=media.gcs_object_path if media else None,
                )
            )
        return WorkOrderGenerationSummary(
            workorder_id=workorder.id,
            site_id=workorder.site_id,
            generation_total_kwh=generation_total_kwh,
            baseline_inverter_count=baseline_inverter_count,
            anomaly_count=anomaly_count,
            inverters=rows,
        )

    for inverter in inverters:
        reading = readings_by_inverter_id.get(inverter.id)
        media = media_by_reading_id.get(reading.id) if reading else None
        delta = to_float(reading.generation_delta_kwh) if reading else None
        if delta is not None and not (reading and reading.is_anomaly):
            generation_total_kwh += delta
        if reading and reading.is_baseline:
            baseline_inverter_count += 1
        if reading and reading.is_anomaly:
            anomaly_count += 1

        rows.append(
            GenerationSummaryRow(
                inverter_id=inverter.id,
                inverter_code=inverter.inverter_code,
                display_name=inverter.display_name,
                previous_reading_kwh=to_float(reading.previous_reading_kwh) if reading else None,
                current_reading_kwh=to_float(reading.current_reading_kwh) if reading else None,
                generation_delta_kwh=delta,
                is_baseline=bool(reading.is_baseline) if reading else False,
                is_anomaly=bool(reading.is_anomaly) if reading else False,
                anomaly_reason=reading.anomaly_reason if reading else None,
                operational_status=reading.operational_status if reading else None,
                remarks=reading.remarks if reading else None,
                photo_object_path=media.gcs_object_path if media else None,
            )
        )

    return WorkOrderGenerationSummary(
        workorder_id=workorder.id,
        site_id=workorder.site_id,
        generation_total_kwh=generation_total_kwh,
        baseline_inverter_count=baseline_inverter_count,
        anomaly_count=anomaly_count,
        inverters=rows,
    )


def report_generation_summary(report: Report) -> WorkOrderGenerationSummary | None:
    payload = report.generation_snapshot_json or {}
    if not payload:
        return None
    rows = [
        GenerationSummaryRow(
            inverter_id=UUID(row["inverter_id"]),
            inverter_code=row["inverter_code"],
            display_name=row["display_name"],
            previous_reading_kwh=row.get("previous_reading_kwh"),
            current_reading_kwh=row.get("current_reading_kwh"),
            generation_delta_kwh=row.get("generation_delta_kwh"),
            is_baseline=bool(row.get("is_baseline", False)),
            is_anomaly=bool(row.get("is_anomaly", False)),
            anomaly_reason=row.get("anomaly_reason"),
            operational_status=row.get("operational_status"),
            remarks=row.get("remarks"),
            photo_object_path=row.get("photo_object_path"),
        )
        for row in payload.get("inverters", [])
    ]
    return WorkOrderGenerationSummary(
        workorder_id=UUID(payload["workorder_id"]),
        site_id=UUID(payload["site_id"]),
        generation_total_kwh=float(payload.get("generation_total_kwh", 0.0)),
        baseline_inverter_count=int(payload.get("baseline_inverter_count", 0)),
        anomaly_count=int(payload.get("anomaly_count", 0)),
        inverters=rows,
    )
