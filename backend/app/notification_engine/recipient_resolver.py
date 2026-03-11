from __future__ import annotations

def resolve_recipients(channel: str, payload: dict, recipient_roles: list[str]) -> list[str]:
    recipients: list[str] = []
    channel_key = channel.upper()

    for role in recipient_roles:
        role_key = role.lower()
        if channel_key == "EMAIL":
            if role_key == "customer_site_supervisor":
                _append_if_present(recipients, payload.get("site_supervisor_email"))
            elif role_key == "internal_supervisor":
                _append_if_present(recipients, payload.get("internal_supervisor_email"))
            elif role_key == "tenant_admin":
                _append_if_present(recipients, payload.get("tenant_admin_email"))
            elif role_key == "technician":
                _append_if_present(recipients, payload.get("technician_email"))
        elif channel_key in {"WHATSAPP", "SMS"}:
            if role_key == "customer_site_supervisor":
                _append_if_present(recipients, payload.get("site_supervisor_phone"))
            elif role_key == "internal_supervisor":
                _append_if_present(recipients, payload.get("internal_supervisor_phone"))
            elif role_key == "tenant_admin":
                _append_if_present(recipients, payload.get("tenant_admin_phone"))
            elif role_key == "technician":
                _append_if_present(recipients, payload.get("technician_phone"))

    return sorted(set(recipients))


def _append_if_present(target: list[str], value: str | None) -> None:
    if value and value.strip():
        target.append(value.strip())
