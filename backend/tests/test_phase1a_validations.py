from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.routes.workorders import _can_transition
from app.schemas.approvals import CustomerSignIn
from app.schemas.workorders import WorkOrderSubmit


def _valid_submit_payload():
    return {
        "visit_status": "SATISFACTORY",
        "summary_notes": "All good",
        "inverter_readings": [],
        "net_meter": {"net_kwh": 1.0, "imp_kwh": 2.0, "exp_kwh": 3.0},
        "checklist_answers": {"solar_module_clean": {"value": "YES"}},
        "media": [
            {
                "item_key": "net_meter_readings",
                "object_path": "media/workorder/net-meter-1.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 1024,
            }
        ],
        "tech_signature": {
            "signer_name": "Tech One",
            "signer_phone": "+919999999999",
            "signature_object_path": "signatures/tech-signature.png",
        },
    }


def test_workorder_submit_accepts_valid_payload():
    payload = _valid_submit_payload()
    model = WorkOrderSubmit(**payload)
    assert model.visit_status == "SATISFACTORY"


def test_workorder_submit_rejects_missing_net_meter_photo():
    payload = _valid_submit_payload()
    payload["media"] = []
    with pytest.raises(ValidationError):
        WorkOrderSubmit(**payload)


def test_workorder_submit_rejects_more_than_20_photos():
    payload = _valid_submit_payload()
    payload["media"] = [
        {
            "item_key": "net_meter_readings" if i == 0 else "misc",
            "object_path": f"media/workorder/photo-{i}.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 100 + i,
        }
        for i in range(21)
    ]
    with pytest.raises(ValidationError):
        WorkOrderSubmit(**payload)


def test_workorder_submit_rejects_non_png_tech_signature():
    payload = _valid_submit_payload()
    payload["tech_signature"]["signature_object_path"] = "signatures/tech-signature.jpg"
    with pytest.raises(ValidationError):
        WorkOrderSubmit(**payload)


def test_customer_sign_rejects_non_png_signature():
    with pytest.raises(ValidationError):
        CustomerSignIn(
            signer_name="Customer A",
            signer_phone="+919888888888",
            signature_object_path="signatures/customer-signature.jpg",
        )


def test_workorder_transition_rules():
    assert _can_transition("SCHEDULED", "IN_PROGRESS")
    assert _can_transition("CUSTOMER_SIGNED", "CLOSED")
    assert not _can_transition("SCHEDULED", "CLOSED")
    assert not _can_transition("IN_PROGRESS", "CLOSED")

