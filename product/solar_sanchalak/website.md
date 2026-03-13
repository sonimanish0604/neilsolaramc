# Solar Sanchalak Website Narrative

## Objective

This website should function as a standalone product site for **Solar Sanchalak**, distinct from the parent EPC-services website.

The core goal is to convince investors, cloud-credit reviewers, and product evaluators that:

- this is a real software platform, not a services brochure
- the product is grounded in first-hand operating experience
- meaningful backend and workflow depth already exists
- the product addresses a painful and recurring operational problem in solar AMC
- the architecture has clear room to scale into adjacent maintenance verticals later

This page should help solve the exact concern raised by Google:

- the parent company site advertises EPC services and hardware
- this dedicated product page must clearly present a software platform
- it must show how the product works, why it matters, the business model direction, and who is building it

## Tone

Use a restrained, confident, product-led tone.

Avoid:

- startup hype
- vague “AI platform” language
- claims that sound ahead of what is actually built
- generic enterprise-software filler
- mixing this page with solar installation, hardware sales, or EPC service marketing

The right tone is:

- credible
- domain-experienced
- technically grounded
- operationally specific

---

## Core positioning

### Primary statement

Solar Sanchalak is an AI-assisted field operations and evidence platform for solar AMC teams.

It helps solar EPC and maintenance operators digitize site execution, capture structured field evidence, generate signed reports, improve approval turnaround, and build a trustworthy historical record across customers and sites.

### Secondary statement

The MVP is solar-AMC-focused, but the architecture is intentionally being shaped so the same workflow model can extend into other field-service and infrastructure-maintenance categories over time.

### Parent-company credibility statement

This product is being built by **Nogginhaus Energy India Limited**, a solar EPC company with first-hand AMC execution experience across multiple customers and multi-site operations since 2018.

This matters because the software is being designed from real operating pain, not from second-hand assumptions.

---

## What the page must communicate

By the end of the page, a reviewer should understand:

1. what Solar Sanchalak is
2. what pain it solves
3. why the team is qualified to build it
4. what has already been built
5. how AI is used in a practical way
6. why the product has broader platform potential
7. how the business could become a standalone SaaS product

---

## Website structure

Use one primary page with these sections:

1. Hero
2. Problem
3. Why this team is building it
4. How the product works
5. What is already delivered
6. AI-assisted evidence layer
7. Offline and cloud architecture
8. Why this matters commercially
9. Business model direction
10. Core team / company background
11. Expansion thesis
12. Closing statement

Important:

- no contact form
- no “request access” funnel
- no EPC-service CTA
- no hardware or installation-services messaging

This should feel like a dedicated software-product page.

---

## Section 1 - Hero

### Title

Solar Sanchalak

### Subtitle

AI-assisted field operations infrastructure for solar AMC.

### Supporting copy

Solar Sanchalak is a mobile-first workflow and evidence platform for solar maintenance teams. It combines field capture, offline-capable execution, signed reporting, approval workflows, and cloud-native auditability into one operating layer for AMC operations.

### Small badge

Built from real EPC and AMC operating experience

### Hero proof points

- digital work-order execution
- offline-capable field capture
- signed PDF reporting
- approval and notification workflow
- inverter-reading and generation foundation
- AI-assisted OCR and geo-validation in active development

### Hero intent

The hero should make the page look like a serious product website, not a corporate services page.

---

## Section 2 - Problem

### Title

Solar AMC work is operationally real, but the evidence layer is still weak.

### Copy

For many EPC and AMC operators, maintenance execution is still managed through a fragmented combination of:

- paper checklists
- handwritten readings
- photos stored on technician phones
- WhatsApp follow-up
- manual report preparation
- physically reviewed paperwork before payment approval

This creates multiple real-world problems:

- service proof is hard to verify
- customer approvals are delayed
- EPC vendor payments get delayed because paperwork review takes time
- field teams repeat manual effort
- multi-site historical retrieval becomes painful
- analytics and reporting remain incomplete or unreliable

The key insight is that this is not just a paperwork problem.

It is an operations, cash-flow, and data-quality problem.

---

## Section 3 - Why this team is building it

### Title

Built from first-hand field experience, not theory.

### Copy

Solar Sanchalak is being built by Nogginhaus Energy India Limited, a solar EPC company that has already executed AMC work across multiple customers and sites since 2018.

The team has direct exposure to the practical issues technicians and supervisors face in the field, including:

- inconsistent site evidence
- delayed paperwork review
- reading capture mistakes
- approval friction
- slow payment cycles tied to document validation
- poor historical retrieval when customers raise questions later

This should be presented as one of the strongest reasons the product exists:

the software is being shaped by real operational pain, not invented top-down.

---

## Section 4 - How the product works

### Title

A closed-loop workflow from field visit to customer-approved record.

### Copy

Solar Sanchalak should be explained as a workflow chain:

1. supervisor creates and assigns a work order
2. technician executes checklist tasks in the field
3. photos, signatures, and inverter evidence are captured as part of the workflow
4. backend generates structured reports and approval state
5. customer-side review and sign-off completes the operational proof loop
6. records remain available for retrieval, reporting, and future analysis

### Important framing

The product is not a generic form builder.

Its value comes from:

- workflow control
- evidence quality
- approval traceability
- historical auditability

---

## Section 5 - What is already delivered

### Title

This is not a concept. Major workflow foundations are already delivered.

### Copy

The website should clearly show that meaningful software work has already shipped.

Delivered capabilities already include:

- multi-tenant backend and user-role foundations
- work-order and technician workflow foundations
- technician submission path
- digital signature ingestion
- PDF report generation
- approval-link and customer sign-off workflow
- notification-engine foundation with Mailgun operational for MVP
- retry-aware messaging and report hardening
- correlation IDs across critical execution paths
- inverter inventory and reading-capture foundation
- generation delta and anomaly logic
- Cloud Run deployment and CI/CD automation

### Suggested visual grouping

Group into:

- Workflow
- Evidence
- Reporting
- Reliability
- Infrastructure

### Important phrasing

Use words like:

- delivered
- implemented
- operational foundation
- active delivery roadmap

Avoid implying that every future reporting and AI feature is already production-complete.

---

## Section 6 - AI-assisted evidence layer

### Title

AI is being applied where it reduces field friction and improves evidence trust.

### Copy

The AI story must be practical, not decorative.

The active product direction includes:

- OCR-assisted extraction of inverter serial numbers during asset registration
- OCR-assisted extraction of inverter reading values during service visits
- confidence scoring and review-required handling
- geo-validation of field evidence relative to the site
- mobile capture designed to support offline or weak-network field conditions
- on-device assist strategy using ML Kit where appropriate for field UX

### Important framing

AI in this product is:

- assistive
- workflow-specific
- evidence-oriented
- review-aware

It should not be framed as:

- autonomous plant intelligence
- fully automated decision making
- replacement for human operational review

### Key language

Solar Sanchalak uses AI to make field evidence capture faster, cleaner, and more reliable.

---

## Section 7 - Offline and cloud architecture

### Title

Offline-capable mobile execution with a cloud-native system of record.

### Copy

This section should show technical maturity.

Key architecture points:

- technicians may work in weak-network environments
- mobile workflow needs to continue even when connectivity is inconsistent
- draft/offline workflow layers exist to support field execution
- on-device assistance can improve capture UX
- Cloud Storage stores files and evidence assets
- Postgres remains the authoritative system of record for finalized business data
- backend APIs validate, persist, and report on accepted records

### Critical wording

Postgres is the final source of truth.
Offline and mobile sync layers are working layers, not the final ledger.

This is important because it signals disciplined product architecture rather than a loosely coupled mobile prototype.

---

## Section 8 - Why this matters commercially

### Title

The value is not only better field UX. It is faster verification, better reporting, and cleaner payment flow.

### Copy

This section should connect product behavior to business outcomes.

Solar AMC operators need more than a checklist app.

They need software that helps:

- reduce delays in customer-side document review
- speed up internal proof validation
- support smoother EPC vendor payment cycles
- reduce dependence on manual paper verification
- create a stronger base for analytics and service performance reporting

This commercial framing is important because it links the product to real operational and financial friction.

---

## Section 9 - Business model direction

### Title

A B2B SaaS product built from an operator problem.

### Copy

Because Google explicitly asked for business-model clarity, the site should include a dedicated section that explains the product business in simple terms.

Recommended framing:

Solar Sanchalak is being developed as a software product for solar EPC and AMC operators managing recurring field-maintenance workflows across customers and sites.

Suggested business-model language:

- B2B SaaS for solar EPC and AMC operators
- software subscription tied to operational usage, organization scope, or site footprint
- future upside from advanced analytics, reporting, and workflow extensions

### Important caution

If exact pricing is not finalized, do not invent pricing numbers.

It is enough to communicate:

- software product
- recurring operational use case
- multi-site operator value
- analytics/reporting expansion potential

---

## Section 10 - Core team / company background

### Title

Built by a team with direct solar operations context.

### Copy

This section should distinguish the product from the EPC-services site without hiding the operating credibility behind it.

Recommended messaging:

- Solar Sanchalak is being built by Nogginhaus Energy India Limited
- the company has direct experience in solar EPC and AMC execution
- the product emerged from repeated operational friction observed in the field
- the team understands both technician workflow reality and management/reporting needs

### Team guidance

If the page includes named people, keep it concise:

- founder / product lead
- operations / domain experience
- engineering / platform execution

If named team bios are not ready yet, a compact company-background block is acceptable for now.

---

## Section 11 - Expansion thesis

### Title

Solar is the wedge, not the ceiling.

### Copy

The platform should be described as solar-first and architecture-conscious.

Shared workflow patterns across infrastructure maintenance include:

- work assignment
- field evidence capture
- geo and context validation
- operator review
- report generation
- historical retrieval
- compliance and auditability

That means Solar Sanchalak can begin with solar AMC while preserving long-term expansion potential into adjacent maintenance categories later.

### Important caution

Keep this grounded.

The website should say:

- built for solar first
- designed with extensibility in mind

It should not say:

- already built for every vertical
- ready to serve all infrastructure categories today

---

## Section 12 - Closing statement

### Title

A product shaped by real field operations, with credible software depth.

### Copy

Solar Sanchalak should close with a clear investor takeaway:

This is an emerging software platform built from a real operating workflow, with meaningful backend and reporting foundations already delivered, and with a practical AI-assisted evidence layer actively being added.

The current focus remains solar AMC.

That focus is a strength, because it grounds the product in a concrete wedge with real operational urgency.

---

## Design direction

The page should feel:

- product-led
- disciplined
- domain-aware
- technically credible
- investor-readable

It should not feel:

- like an EPC brochure
- like a generic SaaS landing template
- like an AI demo page
- like a lead-capture form

Prefer:

- concise but high-signal copy
- strong problem-to-product logic
- delivery proof over promises
- clear architecture framing
- restrained but confident investor language

---

## Notes for implementation

When the next version of `site/index.html` is written, make these changes relative to the current page:

- strengthen the hero around AI-assisted field operations infrastructure
- add an explicit “why this team is building it” section
- add the payment-approval and paperwork-delay dimension to the problem statement
- strengthen delivered-capabilities proof using Phase 1B, 1C, and 1D
- add a business-model section because Google specifically asked for it
- add a company-background/core-team section
- keep the site free of contact forms and request-access flows
- keep the product site visually separate from EPC-services messaging

---

## End state

After reading the final page, an investor or cloud-credit reviewer should conclude:

- the product solves a real and recurring industry problem
- the founding context is authentic and operationally grounded
- meaningful technical progress already exists
- the software has workflow depth beyond simple digitization
- AI is being applied in a practical and believable way
- the product has credible platform potential beyond the first wedge
