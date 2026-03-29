# Spec

## Request
Redesign the Peganyx company website into a more modern, premium, trustworthy, high-conversion website with working pages and Vercel-ready delivery

## Goal
Build a shippable Peganyx v2 website that looks significantly better than the current site and can be previewed on Vercel

## In scope
- Stable backend contract for site content needed by home/services/about/contact pages
- Healthcheck endpoint for deployment verification
- Contact/get-started form submission endpoint with validation and deterministic error behavior
- Vercel-safe server-side behavior using stateless API routes

## Out of scope
- CRM integration
- Newsletter tooling
- Authenticated admin/CMS
- Durable database-backed lead storage

## Acceptance criteria
1. FE can consume a stable content API for the core Peganyx pages.
2. QA can validate contact form success/failure behavior with predictable status codes and payloads.
3. Healthcheck succeeds on the required `/api/health` path.

## Risks
- No durable lead persistence until a CRM/database integration is chosen.
- Content is currently code-backed rather than CMS-managed.
- Admin/auth flows are intentionally deferred.

## Recommended lanes
- Spec / PM
- UI/UX
- Frontend
- Backend
- QA
- Ops / Sec
