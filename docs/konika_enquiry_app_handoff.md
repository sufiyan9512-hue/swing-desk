# Konika Cross-Factory Enquiry Coordination App: Handoff

Purpose: paste or attach this file (plus the requirements PDF) into a new Claude session or account to continue without losing context. Source spec: `Cross-Factory_Enquiry_Coordination_App_Requirements_and_Claude_Code_Handover.pdf` (36 pages, dated 27 Nov 2026, author Rohit Baid). The PDF is the source of truth; this file is a summary plus the plan.

User language: Hinglish (Hindi in Roman script). Replies should be short and direct.

## Status
- No app code exists yet. Only the spec was read and summarised.
- Do NOT build inside the `swing-desk` repo. That repo is an unrelated NSE swing-trading data project. Create a new repo (suggested: `konika-enquiry-app`) and put the PDF in `docs/requirements.pdf`.
- Claude accounts cannot be merged (unverified, likely). Chat history does not transfer. This file replaces the context.

## Problem
Konika's elastic business: 5 factories, 3 companies, 4 units (Konika Intima, Konika Tapes, Konika Elastics knitted, Konika Elastics woven), 4 merchant communication centres. Enquiries land with the wrong merchant or salesperson and get passed around on WhatsApp. Result: delays, no recorded commitments, lost follow-ups, no management view.

Goal: one mobile-first app where an enquiry is logged once (with photos), tagged to the right factory or person (or sent to a central assigner), the merchant commits a date, samples move through weaving, dyeing and value addition queues, and everyone sees status, follow-ups and courier tracking.

Targets to confirm: first response within 4 working hours; nothing unassigned for more than 1 working day; at least 85% of samples dispatched on or before the committed date; conversion visible by factory, merchant, salesperson, customer and brand.

## Users and roles (a user can hold several roles, scoped to factories)
Group admin (Rohit Baid); Unit MDs (Rohit Intima, Mohit Tapes, Shruti Elastics knitted, Mukesh Elastics woven); Business development head (to be named; sees everything, can assign and reassign, cannot approve samples or change commitments); Assigner (Akash); Head merchants (Intima, Tapes only); Merchants (3 per unit, placeholder names); Sales calling team; Field salespeople (Delhi, Mumbai, Jaipur, Tirupur, Bangalore, Sri Lanka, USA agent); Sampling owners (Ritu Intima weaving, Sunil Tapes weaving, Shruti knitting, Sahin woven weaving); Dyeing owner (Vikas, Intima, serves all units); Value-addition owner (Sufiyan, Intima, serves all units); Lab coordinators (Jigar Intima lab, Sudarshan Tapes lab); Dispatch staff (added later by merchants); Customer contacts (portal).

## Core flow
1. Quick-add enquiry (photo, customer, brand, type, a few parameters). Types: Order, Sample approval, Price quote, Development, Availability check. Several elastic lines per enquiry. Numbering ENQ-YYMM-####, lines -01, -02.
2. Tag to factory or person, or "Not sure" to the assigner queue. Any business head can also assign. First assignment wins (atomic). Reassign needs a reason.
3. Owner merchant accepts and commits date, price, MOQ. Changing a committed date needs a reason; history is kept and slippage measured.
4. Cross-factory: owner merchant owns the whole enquiry and is the only contact for sales and customer. A supplying merchant at another factory makes one line, commits a date and quotes an internal price. The owner sets the customer price. Default: supplying factory sends sample to owner via an inter-factory transfer (Sent then Received, challan, quantity, variance flagged). Urgent direct dispatch needs the owner to switch the line to Direct dispatch with a reason, and the supplier must tick the customer's must-check checklist and upload a packed photo.
5. Sample job: stage route (weaving/knitting/jacquard, dyeing with lab dip, value addition, packing). Each stage has target, committed and actual dates. A stage starts only when the previous one is done and any inbound transfer is received. Late stages shift downstream targets and mark the line "at risk". New-development jobs need approval (head merchant in Intima and Tapes, MD in the two Elastics units). Regular articles skip approval. No separate QC stage.
6. Lab: a lab-report-required flag per line, tests chosen from a master, brand manual uploaded, AI pre-fills the test sheet ("From manual, please confirm"), a person confirms, the lab enters results with auto Pass/Fail, the lab coordinator approves, a Konika PDF is generated. Lab runs in parallel and never holds dispatch. Default lab is where the sample is finished; Elastics samples go to the Intima lab; the owner or coordinator can move a test with a reason.
7. Follow-up and courier: a follow-up date is mandatory before Dispatched (default delivery plus 5 working days). Outcomes: Approved, Rejected (reason), Revision (opens the next round R2), On hold, No response (3 of these escalate to the business head). Approved converts to an order line with ERP order number. Courier plus AWB with tracking-link templates.
8. Customer portal (first release): OTP login, upload photos or documents, simplified status tracker, courier details, sample feedback form, message thread. Customers see only their own company's customer-safe fields.

## Line statuses
Draft, New (open pool), Tagged, Accepted, Info needed, Committed, In sampling, Dispatched, Delivered awaiting feedback, Revision, Approved, Converted to order, Closed lost/rejected.

## SLAs (working hours 10:00 to 19:00, 6 days a week, weekly off per unit, Tuesday default)
- Tagged but not accepted in 4h: remind assignee. At 8h: escalate to head merchant (MD in Elastics units). One working day later: MD.
- Committed date passed with no dispatch: overdue flag and escalation, then the MD one working day later.
- Follow-up overdue: remind salesperson. Overdue by 3 days: escalate to head merchant or MD.
- Inter-factory transfer not received within 1 working day: flag both merchants.

## Visibility rules (enforced on the server, never only in the UI; use Postgres RLS or equivalent)
- A factory-tagged line is visible only to that factory's users, its business head, the owning salesperson and admin.
- Open-pool and unclear enquiries: assigner, all MDs, business development head.
- Cross-factory enquiries: everything including prices is visible to both factories' merchants and business heads.
- Process roles (dyeing, value addition, dispatch, lab, sampling) see only their queue jobs and NEVER receive price fields; strip prices from API responses, not only the screen.
- Salespeople see only their own enquiries. Customers use separate API endpoints returning only customer-safe fields. Reassigned lines stay read-only history for the old factory.
- Prices (target, quoted, internal) are visible to salespeople, merchants, business heads and admin only.

## Category routing
Intimate wear and dyed elastic go to Intima. Yarn-dyed and underwear go to Tapes. Insert, surgical/orthopaedic, gym support and footwear go to Elastics or Tapes (sender or assigner picks). Between the two Elastics units: knitted goes to Shruti's unit, woven to Mukesh's. Dyeing process and printing, debossing, silicone coating all go to Intima.

## Data model (entities)
Enquiry, EnquiryLine, Attachment, Assignment, Commitment, SampleJob, SampleStage, FollowUp, Shipment, Transfer, SupportingLineRequest, Comment, Notification, AuditLog, CustomerContact, CustomerMessage, CustomerStatusMap, CustomerNote, SampleFeedback, TestMaster, BrandTestProtocol, LabRequirement, LabResult, LabReport, Lab. Masters: Factory, Department, User, Role, Customer, Brand, Category, ValueAdditionType, Courier, Reason, SLA settings. Full field lists are in section 4 of the PDF.

## Tech stack (suggested, final choice open)
Next.js + TypeScript PWA (installable on phones and desktops), PostgreSQL with Prisma or Drizzle plus RLS (Supabase acceptable), S3-compatible storage (MinIO), phone OTP auth (mock OTP in dev), web push (WhatsApp Business API in phase 2), cron or queue for SLA checks and digest, Docker deploy on the Konika Intima server (Aditya hosts; needs domain, HTTPS, static IP or tunnel, nightly backups with a tested restore). Claude API reads uploaded brand manuals and returns structured JSON with page references, always saved as a draft for human confirmation. ERP is MS SQL Server on a Windows server: read-only sync in phase 3 through a small sync service, never direct writes. English UI only.

## Phases
- Phase 1 (about 11 to 12 weeks): masters, OTP login, enquiry capture, tagging and open pool, visibility and price hiding, commitments, sample jobs and queues, follow-ups, shipments, comments, notifications (push and email), SLA escalations, daily digest, customer portal, cross-factory coordination, lab module.
- Phase 2: WhatsApp notifications, factory and group dashboards, KPIs, Excel reports, product catalogue and ERP customer sync.
- Phase 3: customer portal extras, courier tracking API with auto Delivered, department capacity limits, parallel stages.

## Still to confirm
Names for merchants, head merchants, business development head, calling team and field salespeople. Stage lead times (placeholders: weaving 3, knitting 3, dyeing 2, value addition 2, lab 2 working days). Domain name and whether the server runs Windows or Linux.

## Recommended plan (agreed in chat)
1. New repo, PDF in `docs/requirements.pdf`, this file as `HANDOFF.md`.
2. Milestone 0 (single session, sequential): propose the DB schema, role model, RLS visibility and price-hiding model, and API contract. Wait for the owner's OK before scaffolding. One session alone owns schema changes.
3. Milestone 1: scaffold, migrations, seed data (4 units, users with placeholder names, a few customers and brands), phone OTP auth with mock OTP. Then enquiry capture, assigner queue, owner merchant with supporting lines, commitments. Write automated tests that prove the section 6 rules and the phase 1 acceptance criteria.
4. Milestone 2: sample jobs with the approval rule, cross-factory stage routes, department queues, inter-factory transfers, lab module with AI manual reading.
5. Milestone 3: follow-ups and shipments. Milestone 4: notifications, SLA escalations, daily digest. Milestone 5: customer portal with separate customer-safe endpoints and tests that customers only see their own company's records.
6. Parallel sessions only after Milestone 0 is approved. Safe split: core backend in one session and the customer portal or lab module in another, each on its own branch or worktree. Merge after each milestone and rerun the visibility tests.
7. After each milestone, give a short summary of what is done, how to run it, and what is needed from the owner. Ask before adding any paid third-party service.

## Prompt to paste into the new Claude Code session (from the PDF, section 13)
You are building the Konika Cross-Factory Enquiry Coordination App described in the attached requirements document. Read the whole document first, especially the decisions table in section 13. Build Phase 1 from section 12 as a mobile-first PWA using the stack in section 11 (Next.js + TypeScript + PostgreSQL), packaged with Docker for Konika's own server and installable on phones and desktops. The UI is English only. Start by proposing the database schema from section 4 and the role, visibility and price-hiding model from sections 2 and 6, and wait for my OK. Then scaffold the project, migrations, seed data (the 4 units and users from the organisation table in section 2, keeping placeholder names like "Intima Merchant 1", plus a few customers and brands), and auth with phone OTP (a mock OTP in dev). Build in this order: (1) enquiry capture, the assigner queue, owner merchant with supporting lines from other factories, and commitments; (2) sample jobs with the approval rule, cross-factory stage routes, department queues and inter-factory transfers (section 6A), and the lab module with AI reading of brand manuals (section 7A); (3) follow-ups and shipments; (4) notifications, SLA escalations and the daily digest. Enforce visibility and price hiding on the server, and write automated tests that prove the section 6 rules and the phase 1 acceptance criteria. Keep an audit log on every write. Then build the customer portal from section 8A as step (5), with separate customer API endpoints that return only customer-safe fields, and tests proving customers see only their own company's records. After each milestone, give me a short summary of what's done and how to run it, plus anything you need from me. Ask before adding paid third-party services.
