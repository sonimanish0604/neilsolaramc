from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy import select

from app.db.models.notification import NotificationTemplate, TenantNotificationSetting
from app.db.session import get_admin_db


def main() -> None:
    tenant_id_raw = os.getenv("TENANT_ID")
    if not tenant_id_raw:
        raise SystemExit("TENANT_ID is required")

    tenant_id = UUID(tenant_id_raw)
    event_type = os.getenv("NOTIF_EVENT_TYPE", "work_order.submitted_for_approval")
    template_key = os.getenv("NOTIF_TEMPLATE_KEY", "approval_pending_v1")

    with get_admin_db() as db:
        setting = db.execute(
            select(TenantNotificationSetting).where(
                TenantNotificationSetting.tenant_id == tenant_id,
                TenantNotificationSetting.event_type == event_type,
            )
        ).scalar_one_or_none()
        if not setting:
            setting = TenantNotificationSetting(
                tenant_id=tenant_id,
                event_type=event_type,
                enabled=True,
                channels_json=["EMAIL"],
                recipient_roles_json=["customer_site_supervisor"],
                template_key=template_key,
            )
            db.add(setting)
        else:
            setting.enabled = True
            setting.channels_json = ["EMAIL"]
            setting.recipient_roles_json = ["customer_site_supervisor"]
            setting.template_key = template_key

        template = db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.template_key == template_key,
                NotificationTemplate.channel == "EMAIL",
            )
        ).scalar_one_or_none()
        if not template:
            template = NotificationTemplate(
                tenant_id=tenant_id,
                template_key=template_key,
                channel="EMAIL",
                subject="Approval pending for {{site_name}}",
                body=(
                    "Your AMC report is ready for {{site_name}}.\n"
                    "Report PDF: {{report_url}}\n"
                    "Please review and sign: {{approval_url}}\n"
                    "Link expiry: {{expires_at}}"
                ),
                is_active=True,
            )
            db.add(template)
        else:
            template.subject = "Approval pending for {{site_name}}"
            template.body = (
                "Your AMC report is ready for {{site_name}}.\n"
                "Report PDF: {{report_url}}\n"
                "Please review and sign: {{approval_url}}\n"
                "Link expiry: {{expires_at}}"
            )
            template.is_active = True

        db.commit()
    print("Notification defaults bootstrapped")


if __name__ == "__main__":
    main()
