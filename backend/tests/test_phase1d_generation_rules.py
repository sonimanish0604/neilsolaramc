from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.workorders import InverterReadingCaptureIn
from app.services.inverter_readings import compute_generation


def test_capture_requires_reading_for_operational_inverter():
    with pytest.raises(ValidationError):
        InverterReadingCaptureIn(
            inverter_id="11111111-1111-1111-1111-111111111111",
            current_reading_kwh=None,
            operational_status="OPERATIONAL",
            photo_object_path="media/inverter-1.jpg",
            photo_content_type="image/jpeg",
            photo_size_bytes=1234,
        )


def test_capture_requires_remarks_when_reading_is_missing():
    with pytest.raises(ValidationError):
        InverterReadingCaptureIn(
            inverter_id="11111111-1111-1111-1111-111111111111",
            current_reading_kwh=None,
            operational_status="OFFLINE",
            photo_object_path="media/inverter-1.jpg",
            photo_content_type="image/jpeg",
            photo_size_bytes=1234,
        )


def test_capture_allows_non_operational_inverter_without_reading_when_remarks_present():
    payload = InverterReadingCaptureIn(
        inverter_id="11111111-1111-1111-1111-111111111111",
        current_reading_kwh=None,
        operational_status="OFFLINE",
        remarks="Display was blank",
        photo_object_path="media/inverter-1.jpg",
        photo_content_type="image/jpeg",
        photo_size_bytes=1234,
    )
    assert payload.operational_status == "OFFLINE"


def test_generation_baseline_when_no_previous_reading_exists():
    result = compute_generation(
        previous_reading_kwh=None,
        current_reading_kwh=10500.0,
        operational_status="OPERATIONAL",
    )
    assert result.is_baseline is True
    assert result.generation_delta_kwh is None
    assert result.is_anomaly is False


def test_generation_delta_when_current_reading_increases():
    result = compute_generation(
        previous_reading_kwh=10500.0,
        current_reading_kwh=10825.4,
        operational_status="OPERATIONAL",
    )
    assert result.is_baseline is False
    assert result.is_anomaly is False
    assert result.generation_delta_kwh == pytest.approx(325.4)


def test_generation_marks_anomaly_when_current_reading_goes_backwards():
    result = compute_generation(
        previous_reading_kwh=10825.4,
        current_reading_kwh=10700.0,
        operational_status="OPERATIONAL",
    )
    assert result.is_anomaly is True
    assert result.generation_delta_kwh is None
    assert "lower" in (result.anomaly_reason or "").lower()
