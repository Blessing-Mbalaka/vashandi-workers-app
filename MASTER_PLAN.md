# Vashandi Master Plan

## Current Foundation
- Dynamic trade and subcategory management is live through Django admin.
- Registration now supports identity verification with admin approval before login.
- Profiles now support both individuals and companies.
- African country and currency reference data is seeded into the platform.

## What Was Added In This Phase
- Required certified ID upload during registration.
- Admin review workflow for account verification.
- Company profile fields:
  - `company_name`
  - `company_website`
  - `vat_number`
- African country directory with currency metadata.
- Profile editing for country, company details, and verification re-submission.
- Currency-aware service, job, RFQ, and invoice display paths.
- Project Tracker workflow:
  - trackers tied to awarded jobs
  - client-defined phases and tasks
  - provider execution plans
  - client approval signatures
  - phase release status tracking
  - dispute escalation to admin
  - public evidence upload per phase

## Recommended Next Phase
1. Public provider and company pages
   - Add a shareable public profile URL for every provider/company.
   - Show services, reviews, verification badge, website, country, and VAT details where appropriate.

2. Verification hardening
   - Add document type rules and size limits.
   - Store verification files in cloud object storage for production.
   - Add audit history for approval and rejection decisions.

3. Multi-currency business logic
   - Keep item-level native currency as implemented now.
   - Add exchange-rate conversion for analytics so totals across countries are meaningful.
   - Add currency choice per invoice only if you want providers billing in a different currency from profile default.

4. Provider onboarding controls
   - Require verification before creating services, not only before login, if you want a stricter marketplace.
   - Add compliance checklist fields for regulated sectors like healthcare and engineering.

5. Marketplace trust layer
   - Add verified badges on cards and profile pages.
   - Add document expiry reminders for IDs, licenses, and certificates.
   - Add optional business registration number alongside VAT.

6. Deployment readiness
   - Move secrets out of `settings.py` into environment variables.
   - Configure media storage, backups, HTTPS, logging, and production email settings.
   - Add CI to run tests and migrations automatically before deploy.

## Suggested Deployment Checklist
- Switch SMTP credentials to environment variables.
- Set `DEBUG = False` in production.
- Use a managed database instead of local SQLite.
- Use S3, Azure Blob, or similar for uploaded verification files.
- Add domain, SSL, and static/media serving.
- Add admin-only moderation SOP for verification review.
- Add admin SOP for dispute resolution and phase-release overrides.

## Project Tracker Suggestions
1. Add real escrow or payment integration later
   - current implementation tracks release state by phase
   - actual money movement should come through Stripe, Paynow, Flutterwave, or another supported flow

2. Add richer signatures
   - current signatures are typed sign-off strings
   - next step can be drawn signatures on canvas plus PDF agreement export

3. Add per-task media galleries
   - current workflow supports phase evidence upload
   - next step can support multiple images per phase and per task

4. Add admin resolution commands in Django admin
   - approve provider
   - uphold client complaint
   - release held phase
   - dismiss unreasonable dispute

5. Add client acceptance criteria templates
   - phase checklist
   - quality standard checkboxes
   - required handover files

## Important Product Suggestion
- Cross-country pricing analytics should not be treated as a single number without conversion.
- Right now the app can display the correct currency per user and per record.
- The next clean step is an exchange-rate service plus normalized reporting currency.

## Nice-To-Have After Launch
- Company logo uploads.
- Public company portfolio/gallery.
- Staff accounts under one company.
- Sector-specific verification rules.
- Country-aware tax handling for invoices.
