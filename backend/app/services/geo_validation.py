from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6_371_000.0
DEFAULT_MAX_SITE_DISTANCE_METERS = 200.0
DEFAULT_MAX_DEVICE_ACCURACY_METERS = 100.0


@dataclass(frozen=True)
class GeoValidationResult:
    status: str
    reason: str | None
    distance_to_site_meters: float | None


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad
    a = sin(d_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_METERS * c


def validate_capture_location(
    *,
    site_latitude: float | None,
    site_longitude: float | None,
    device_latitude: float | None,
    device_longitude: float | None,
    device_accuracy_meters: float | None,
    max_site_distance_meters: float = DEFAULT_MAX_SITE_DISTANCE_METERS,
    max_device_accuracy_meters: float = DEFAULT_MAX_DEVICE_ACCURACY_METERS,
) -> GeoValidationResult:
    if site_latitude is None or site_longitude is None:
        return GeoValidationResult(
            status="geo_unverified",
            reason="missing_site_coordinates",
            distance_to_site_meters=None,
        )

    if device_latitude is None or device_longitude is None:
        return GeoValidationResult(
            status="missing_device_location",
            reason="device_latitude_or_longitude_missing",
            distance_to_site_meters=None,
        )

    if device_accuracy_meters is not None and device_accuracy_meters > max_device_accuracy_meters:
        return GeoValidationResult(
            status="low_accuracy",
            reason=f"device_accuracy_meters_exceeds_{int(max_device_accuracy_meters)}",
            distance_to_site_meters=None,
        )

    distance_meters = haversine_meters(site_latitude, site_longitude, device_latitude, device_longitude)
    rounded_distance = round(distance_meters, 2)
    if rounded_distance > max_site_distance_meters:
        return GeoValidationResult(
            status="outside_site_boundary",
            reason=f"distance_to_site_meters_exceeds_{int(max_site_distance_meters)}",
            distance_to_site_meters=rounded_distance,
        )

    return GeoValidationResult(
        status="verified",
        reason=None,
        distance_to_site_meters=rounded_distance,
    )
