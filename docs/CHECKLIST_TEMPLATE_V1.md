# Checklist Template V1 – AMC Visit (On-Grid Rooftop Solar Plant)

Source: Digitized from existing AMC paper form (Nogginhaus Energy India Limited).

Template Code: AMC_ON_GRID_V1  
Version: 1  
Applies to: All Sites (dynamic inverter count)

---

# SECTION 1: SITE INFORMATION (Auto-Filled)

These fields are not user-editable during visit:

- tenant_name
- customer_name
- site_name
- site_address
- plant_capacity_kw
- visit_date (auto timestamp)
- technician_name (from JWT)

---

# SECTION 2: INVERTER READINGS (Dynamic Per Site)

For each inverter configured under the site:

Fields (per inverter):

- power_kw        (NUMBER, optional but recommended)
- day_kwh         (NUMBER, optional but recommended)
- total_kwh       (NUMBER, optional but recommended)

Validation:
- At least 1 inverter must exist per site.
- Values must be >= 0.

Photo Requirement:
- Optional (can attach photo of inverter display).
- Count contributes to global max photos per visit (default 20).

---

# SECTION 3: NET METER READING (MANDATORY)

Item Key: net_meter_readings

Fields:
- net_kwh  (NUMBER, REQUIRED)
- imp_kwh  (NUMBER, REQUIRED)
- exp_kwh  (NUMBER, REQUIRED)

Photo:
- REQUIRED (at least 1 photo)
- Must be tagged to item_key = "net_meter_readings"

Validation:
- All 3 numeric fields must be entered.
- At least 1 photo attached.

---

# SECTION 4: SOLAR MODULE & INVERTER CHECKS

## 4.1 Solar Module Cleanliness
item_key: solar_module_clean
input_type: YES_NO
required: true
is_photo_required: false

## 4.2 Inverter Cabling
item_key: inverter_cabling
input_type: AC_DC
required: true
is_photo_required: false

## 4.3 Inverter Operational Status
item_key: inverter_status
input_type: ON_OFF
required: true
is_photo_required: false

---

# SECTION 5: STRUCTURE & SAFETY CHECKS

All items below:
- input_type: PASS_FAIL
- required: true
- is_photo_required: false (but optional photos allowed)

## 5.1 Structure Condition
item_key: structure_condition

## 5.2 Earthing
item_key: earthing_status

## 5.3 Lightning Arrester
item_key: lightning_arrester_status

## 5.4 Online Monitoring System
item_key: monitoring_system_status

## 5.5 Conduit Pipe
item_key: conduit_pipe_status

## 5.6 ACDB & Array Junction Box
item_key: acdb_ajb_status

For each PASS_FAIL item:
Technician can also enter:
- notes (TEXT, optional)

---

# SECTION 6: VISIT SUMMARY (MANDATORY)

## 6.1 Overall Visit Status
item_key: visit_status
input_type: ENUM
values:
- SATISFACTORY
- NEEDS_ATTENTION
- CRITICAL
required: true

## 6.2 Summary Notes
item_key: visit_summary_notes
input_type: TEXT
required: false

---

# SECTION 7: MEDIA RULES

Global Constraints:
- Maximum photos per visit: 20 (enforced by plan_limits)
- At least 1 photo required for net_meter_readings
- All photos stored in GCS
- Each photo linked to:
  - workorder_id
  - item_key (nullable if general)

---

# SECTION 8: SIGNATURES (Mandatory)

## 8.1 Technician Signature
Required at submission.
Fields:
- signer_name (auto from user profile)
- signer_phone (auto from user profile)
- signature (drawn on device)
- timestamp

## 8.2 Customer Site Supervisor Signature
Captured via approval link.
Fields:
- signer_name (entered)
- signer_phone (entered)
- signature (drawn)
- timestamp
- IP + user-agent logged (best effort)

---

# PASS / FAIL COUNTING LOGIC

PASS_FAIL items:
- Count total PASS
- Count total FAIL

YES_NO logic:
- YES = PASS
- NO = FAIL

ON_OFF logic:
- ON = PASS
- OFF = FAIL

AC_DC logic:
- AC/DC does not count toward pass/fail; informational only

Net meter + inverter readings:
- Informational; not counted in pass/fail

---

# REPORT STRUCTURE (PDF)

Header:
- Company name
- Customer name
- Site
- Capacity
- Visit date
- Technician name

Section 1: Inverter Readings Table
Section 2: Net Meter Readings + Photo
Section 3: Checklist Results Table (PASS/FAIL highlighted)
Section 4: Visit Summary
Section 5: Signatures (Tech + Customer)
Footer:
- Report Version
- Generated timestamp
- SHA256 hash