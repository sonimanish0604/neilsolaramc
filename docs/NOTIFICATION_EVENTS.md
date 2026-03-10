# Notification Event Catalog (Phase B)

Canonical event names for notification routing:

- `work_order.created`
- `work_order.assigned`
- `work_order.submitted_for_approval`
- `work_order.completed`
- `work_order.approved`
- `work_order.rejected`
- `pm_visit_due`
- `ticket.created`

## Event Envelope

```json
{
  "event_id": "evt_1001",
  "event_type": "work_order.completed",
  "tenant_id": "tenant_01",
  "entity_id": "wo_1024",
  "entity_type": "work_order",
  "payload": {
    "site_name": "ABC Textile Plant",
    "technician_name": "Ramesh Kumar",
    "report_link": "https://example.com/report/1024"
  },
  "created_at": "2026-03-07T18:00:00Z"
}
```

## Rule Mapping Example

```json
{
  "tenant_id": "tenant_01",
  "event_type": "work_order.completed",
  "enabled": true,
  "channels": ["EMAIL"],
  "recipient_roles": ["internal_supervisor", "customer_site_supervisor"],
  "template_key": "maintenance_completion_v1"
}
```
