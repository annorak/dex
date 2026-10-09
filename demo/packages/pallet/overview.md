# Pallet HOA reviewed example

Prepared before the demo. This is an invented, simulated review, not a live onboarding result.

Snapshot pallet-v1 is as of 2026-09-30. The accounting database stores communities, company-wide unique vendors, and invoices.
Use invoices.balance_cents, in whole US cents, for the amount owed. O means open and C means closed, paid in full.
These rules are documented in evidence/ap_process.md items 1-3 and confirmed by employee review pallet-employee-1.
Join invoices to vendors on vendor_id. Resolve a community by exact name. See queries/identity.sql and queries/answer.sql.
Supported lookup: unpaid_invoices_by_community. There are no open questions for this lookup.
The engineer approved the saved queries and three passing checks in pallet-engineer-1. Results are in checks/results.json.
Limits: fixed invented snapshot only; no historical balances, live permissions, or live freshness guarantees.
