from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.workorders import InverterReadingCaptureIn
from app.services.geo_validation import validate_capture_location


def test_geo_validation_returns_geo_unverified_when_site_coordinates_are_missing():
    result = validate_capture_location(
        site_latitude=None,
        site_longitude=None,
        device_latitude=19.0760,
        device_longitude=72.8777,
        device_accuracy_meters=10.0,
    )
    assert result.status == "geo_unverified"
    assert result.reason == "missing_site_coordinates"
    assert result.distance_to_site_meters is None


def test_geo_validation_returns_missing_device_location_when_device_coordinates_are_missing():
    result = validate_capture_location(
        site_latitude=19.0760,
        site_longitude=72.8777,
        device_latitude=None,
        device_longitude=None,
        device_accuracy_meters=None,
    )
    assert result.status == "missing_device_location"
    assert result.reason == "device_latitude_or_longitude_missing"
    assert result.distance_to_site_meters is None


def test_geo_validation_returns_low_accuracy_for_noisy_device_location():
    result = validate_capture_location(
        site_latitude=19.0760,
        site_longitude=72.8777,
        device_latitude=19.0761,
        device_longitude=72.8778,
        device_accuracy_meters=150.0,
    )
    assert result.status == "low_accuracy"
    assert "exceeds" in (result.reason or "")
    assert result.distance_to_site_meters is None


def test_geo_validation_returns_outside_site_boundary_when_distance_exceeds_threshold():
    result = validate_capture_location(
        site_latitude=19.0760,
        site_longitude=72.8777,
        device_latitude=19.0900,
        device_longitude=72.8777,
        device_accuracy_meters=10.0,
    )
    assert result.status == "outside_site_boundary"
    assert result.distance_to_site_meters is not None
    assert result.distance_to_site_meters > 200.0


def test_geo_validation_returns_verified_when_capture_is_within_threshold():
    result = validate_capture_location(
        site_latitude=19.0760,
        site_longitude=72.8777,
        device_latitude=19.0765,
        device_longitude=72.8780,
        device_accuracy_meters=10.0,
    )
    assert result.status == "verified"
    assert result.reason is None
    assert result.distance_to_site_meters is not None


def test_capture_payload_rejects_partial_device_coordinates():
    with pytest.raises(ValidationError):
        InverterReadingCaptureIn(
            inverter_id="11111111-1111-1111-1111-111111111111",
            current_reading_kwh=100.0,
            device_latitude=19.0760,
            device_longitude=None,
            operational_status="OPERATIONAL",
            photo_object_path="media/inverter-1.jpg",
            photo_content_type="image/jpeg",
            photo_size_bytes=1234,
        )


def test_capture_payload_rejects_accuracy_without_coordinates():
    with pytest.raises(ValidationError):
        InverterReadingCaptureIn(
            inverter_id="11111111-1111-1111-1111-111111111111",
            current_reading_kwh=100.0,
            device_accuracy_meters=10.0,
            operational_status="OPERATIONAL",
            photo_object_path="media/inverter-1.jpg",
            photo_content_type="image/jpeg",
            photo_size_bytes=1234,
        )
