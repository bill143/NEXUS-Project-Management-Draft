# RFC 36 — NEXUS Project Directory module

**Status:** draft → ready for review
**Date:** 2026-05-13
**Author:** Claude Opus + Bill (brainstorm session)
**Related:**
- Memory `project_on_nexus_erp.md` (parked rebrand branch `d45fda1c` context)
- Memory `reference_railway_smtp_block.md` (use Resend HTTP API, not SMTP)
- Commit `067fb7f7` — Resend HTTP-API email backend (relied on by Wave 2 + 3)
- Commit `58f44bc7` — current user-detail slide-over (to be ported, not lost)
- Commit `1804a1bd` — `/auth/reset` flow (entry-point preserved by 301 redirect)

## 1. Why this RFC exists

O'Neill needs a federal-construction-grade directory: companies, federal bidder flags (SDVOSB / 8(a) / WOSB / HUBZone / MBE / DBE …), insurance certificate tracking with expiration alerts, distribution lists for project communications, and a single audit-grade place to manage all of it. Today, `users/` and `contacts/` exist as separate features; companies, bidder info, insurance, and distribution groups are absent.

This RFC specifies a new `frontend/src/features/directory/` module and a new `backend/app/modules/directory/` API surface that **replaces** the standalone Users and Contacts features by absorbing them into a unified `/directory` page.

## 2. Locked decisions (brainstorm session 2026-05-13)

| # | Decision | Rationale |
|---|---|---|
| L1 | `/directory` is the canonical surface. `features/users/UserManagementPage.tsx` and `features/contacts/` are deleted; their functionality is ported into `directory/tabs/UsersTab.tsx` and `directory/tabs/ContactsTab.tsx`. | User explicitly chose "replace" over "umbrella over existing" in confirmation step. |
| L2 | Old `/users` and `/contacts` routes return 301 redirects to `/directory?tab=users` / `?tab=contacts` for one release cycle. | Preserve bookmarks and external links during transition. |
| L3 | The recent slide-over (commit `58f44bc7`) and reset-password integration (commit `1804a1bd`) are **ported, not re-implemented**. No regression in user-management UX. | Both shipped within the last week; rebuilding from scratch would lose work. |
| L4 | Backend endpoints mount under `/api/v1/directory/*` via a new `backend/app/modules/directory/` module. Follows existing module-router convention (`backend/app/modules/<feature>/router.py`). | Matches `backend/app/modules/{users,contacts,reporting,...}` pattern. No `/api/` directory exists today. |
| L5 | Theme tokens (DM Serif Display + IBM Plex Sans + JetBrains Mono + dark navy CSS variables) are **scoped** to `[data-route="directory"]`, not applied globally. | Applying globally would re-skin every other module and force a full dark-mode migration. |
| L6 | Insurance expiration uses **Celery beat** (already wired via `celery[redis]>=5.4.0`, precedent in `backend/app/modules/reporting/cron.py`). Notifications send via **Resend HTTP API** (commit `067fb7f7`), never SMTP — Railway SMTP is blocked. | Reuse working infrastructure; avoid re-discovering the Railway block. |
| L7 | Distribution Groups in v1 include `POST /groups/{id}/send` for ad-hoc email send via Resend. Group becomes a referenceable mail list, usable elsewhere later. | User explicitly pulled this back into v1 scope. |
| L8 | Federal bidder certifications stored as 17 plain BOOLEAN columns on `directory_company_bidder_info` for v1. Cert numbers / expiration dates / issuing agency reserved for a follow-up schema upgrade (flagged in Risk R2). | Matches the original spec; structured cert metadata is a future enhancement. |
| L9 | `parked/rebrand-d45fda1c` resolution: cherry-pick salvageable rebrand-string commits onto a throwaway branch for inspection, then `git branch -D parked/rebrand-d45fda1c`. No merge — the branch is 1,865 deletions behind main. Performed in Wave 3 with explicit user confirmation at the deletion step. | Branch is unrecoverable as a merge target; salvage what's useful and stop carrying the parked-branch debt. |
| L10 | Deploys to production via `vercel --prod` are **manual** — user triggers after each wave lands and CI is green. No auto-deploy in the commit script. | User explicitly retained the deploy gate. |

## 3. Architectural shape

```
frontend/src/features/directory/
├─ DirectoryPage.tsx                    # /directory route, applies data-route="directory"
├─ DirectoryTabs.tsx                    # tablist: Users | Contacts | Companies | Groups | Inactive
├─ tabs/
│   ├─ UsersTab.tsx                    # ports UserManagementPage logic; consumes features/users/api.ts
│   ├─ ContactsTab.tsx                 # ports contacts/ logic
│   ├─ CompaniesTab.tsx                # NEW
│   ├─ DistributionGroupsTab.tsx       # NEW
│   └─ InactiveTab.tsx                 # filtered views + Reactivate action
├─ slideovers/
│   ├─ AddEditUserSlideOver.tsx        # 3 tabs: Details | Employment | Login & Access
│   ├─ AddEditCompanySlideOver.tsx     # 5 tabs: General | Users | Bidder Info | Insurance | History
│   ├─ AddEditContactSlideOver.tsx
│   └─ AddDistributionGroupModal.tsx
├─ components/
│   ├─ DirectoryTable.tsx              # shared dense table: sticky header, hover, mono numerics, right-pinned actions
│   ├─ StatusBadge.tsx                 # dot + text + color (never color alone)
│   ├─ KpiRow.tsx                      # 4-up monospace counters with trend indicators
│   ├─ SlideOver.tsx                   # 300ms ease-out from right
│   └─ FederalCertBadges.tsx           # SDVOSB / 8(a) / WOSB visible trust signals
├─ api/
│   ├─ companies.ts
│   ├─ insurance.ts
│   ├─ groups.ts
│   └─ history.ts
├─ theme/
│   ├─ tokens.css                      # CSS variables, scoped under [data-route="directory"]
│   └─ fonts.css                       # @font-face for DM Serif / IBM Plex / JetBrains Mono
└─ utils/
    ├─ insurance-status.ts              # red/amber/green calc from expiration_date

backend/app/modules/directory/
├─ __init__.py
├─ router.py                            # registers sub-routers
├─ companies/
│   ├─ models.py, schemas.py, service.py, router.py
├─ insurance/
│   ├─ models.py, schemas.py, service.py, router.py, cron.py
├─ groups/
│   ├─ models.py, schemas.py, service.py, router.py
└─ audit/
    ├─ models.py, emit.py               # emit() helper called from PATCH paths
    └─ router.py                        # history queries

backend/alembic/versions/
└─ <hash>_directory_module_v1.py        # all new tables in a single migration (Wave 1+2 split as two migrations)
```

## 4. Data model

All new tables. No changes to existing `users` or `contacts` schemas — those tables continue to be the single source of truth for those entities and the new module reads them via SQLAlchemy relationships.

### 4.1 `directory_companies` (Wave 1)
```
id                    UUID PK
name                  VARCHAR(255) NOT NULL
abbreviated_name      VARCHAR(64)
dba                   VARCHAR(255)
address               VARCHAR(255)
city                  VARCHAR(128)
state                 VARCHAR(2)
zip                   VARCHAR(10)
phone                 VARCHAR(32)
fax                   VARCHAR(32)
email                 VARCHAR(255)
website               VARCHAR(255)
primary_contact_id    UUID FK → users.id NULL
entity_type           VARCHAR(64)        -- LLC, Corp, Sole Prop, etc.
license_number        VARCHAR(64)
labor_union           VARCHAR(128)
logo_url              VARCHAR(512)
tags                  JSONB DEFAULT '[]'
project_roles         JSONB DEFAULT '[]'
is_active             BOOLEAN DEFAULT TRUE
created_at            TIMESTAMPTZ DEFAULT NOW()
updated_at            TIMESTAMPTZ DEFAULT NOW()
created_by            UUID FK → users.id
```
Index: `(is_active, name)` for the active-companies table query.

### 4.2 `directory_company_bidder_info` (Wave 2)
```
company_id            UUID PK FK → directory_companies.id ON DELETE CASCADE
authorized_bidder     BOOLEAN DEFAULT FALSE
union_member          BOOLEAN DEFAULT FALSE
sbe                   BOOLEAN DEFAULT FALSE  -- Small Business
prevailing_wage       BOOLEAN DEFAULT FALSE
aabe                  BOOLEAN DEFAULT FALSE  -- African American
abe                   BOOLEAN DEFAULT FALSE  -- Asian American
hbe                   BOOLEAN DEFAULT FALSE  -- Hispanic
nabe                  BOOLEAN DEFAULT FALSE  -- Native American
wbe                   BOOLEAN DEFAULT FALSE  -- Women's
dbe                   BOOLEAN DEFAULT FALSE  -- Disadvantaged
hub                   BOOLEAN DEFAULT FALSE  -- Historically Underutilized
mbe                   BOOLEAN DEFAULT FALSE  -- Minority
sdvosb                BOOLEAN DEFAULT FALSE  -- Service-Disabled Vet-Owned Small Bus
eight_a               BOOLEAN DEFAULT FALSE  -- 8(a)
affirmative_action    BOOLEAN DEFAULT FALSE
cbe                   BOOLEAN DEFAULT FALSE  -- Certified Business Enterprise
prequalified          BOOLEAN DEFAULT FALSE
trades                JSONB DEFAULT '[]'     -- selected trade list
cost_codes            JSONB DEFAULT '[]'     -- selected cost codes
comments              JSONB DEFAULT '[]'     -- [{author_id, text, attachments[], rating, created_at}]
rating                SMALLINT               -- aggregate rating 1-5, NULL if unrated
updated_at            TIMESTAMPTZ DEFAULT NOW()
```

### 4.3 `directory_company_insurance` (Wave 2)
```
id                    UUID PK
company_id            UUID FK → directory_companies.id ON DELETE CASCADE
type                  VARCHAR(64) NOT NULL  -- General Liability, Auto, Workers Comp, etc.
status                VARCHAR(32) DEFAULT 'pending'  -- pending | active | expired | exempt
exempt                BOOLEAN DEFAULT FALSE
info_received_at      DATE
policy_number         VARCHAR(128)
provider              VARCHAR(255)
limit_amount          NUMERIC(14,2)
effective_date        DATE
expiration_date       DATE
send_notification     BOOLEAN DEFAULT TRUE
additional_insured    TEXT
notes                 TEXT
attachments           JSONB DEFAULT '[]'
last_notified_at      TIMESTAMPTZ          -- prevent duplicate 30d/60d emails
created_at            TIMESTAMPTZ DEFAULT NOW()
updated_at            TIMESTAMPTZ DEFAULT NOW()
```
Index: `(expiration_date)` for the cron's range query. Partial index `WHERE send_notification = TRUE AND status != 'exempt'`.

### 4.4 `directory_groups` (Wave 3)
```
id                    UUID PK
name                  VARCHAR(128) UNIQUE NOT NULL
description           TEXT
is_active             BOOLEAN DEFAULT TRUE
created_by            UUID FK → users.id
created_at            TIMESTAMPTZ DEFAULT NOW()
updated_at            TIMESTAMPTZ DEFAULT NOW()
```

### 4.5 `directory_group_members` (Wave 3)
```
id                    UUID PK
group_id              UUID FK → directory_groups.id ON DELETE CASCADE
member_kind           VARCHAR(8) NOT NULL CHECK (member_kind IN ('user','contact'))
user_id               UUID FK → users.id NULL
contact_id            UUID FK → contacts.id NULL
CHECK ((member_kind = 'user' AND user_id IS NOT NULL AND contact_id IS NULL)
    OR (member_kind = 'contact' AND contact_id IS NOT NULL AND user_id IS NULL))
```
Plus a unique partial-expression index to prevent duplicate members:
```sql
CREATE UNIQUE INDEX directory_group_members_unique
  ON directory_group_members (group_id, member_kind, COALESCE(user_id, contact_id));
```

### 4.6 `directory_audit_log` (Wave 3)
```
id                    UUID PK
entity_type           VARCHAR(32) NOT NULL  -- 'company' | 'bidder_info' | 'insurance' | 'group'
entity_id             UUID NOT NULL
action                VARCHAR(16) NOT NULL  -- 'create' | 'update' | 'delete' | 'reactivate'
field_changed         VARCHAR(64)
from_value            JSONB
to_value              JSONB
actor_id              UUID FK → users.id
created_at            TIMESTAMPTZ DEFAULT NOW()
```
Index: `(entity_type, entity_id, created_at DESC)` for the history-tab query.

## 5. API surface

All endpoints under `/api/v1/directory/*`. Auth via existing JWT middleware. RBAC: new role permissions `directory.read`, `directory.write`, `directory.admin`. Migration adds these to the existing role matrix; admins inherit all.

```
# Companies
GET    /companies/                       ?active=true&q=&page=&page_size=
POST   /companies/
GET    /companies/{id}
PATCH  /companies/{id}
DELETE /companies/{id}                   # soft-delete: sets is_active=false

# Bidder Info (1:1 with company)
GET    /companies/{id}/bidder-info
PUT    /companies/{id}/bidder-info       # upsert
POST   /companies/{id}/bidder-info/comments
DELETE /companies/{id}/bidder-info/comments/{comment_id}

# Insurance
GET    /companies/{id}/insurance/
POST   /companies/{id}/insurance/
GET    /companies/{id}/insurance/{cert_id}
PATCH  /companies/{id}/insurance/{cert_id}
DELETE /companies/{id}/insurance/{cert_id}

# Distribution groups
GET    /groups/                          ?active=true&q=
POST   /groups/
GET    /groups/{id}
PATCH  /groups/{id}
DELETE /groups/{id}
GET    /groups/{id}/members
POST   /groups/{id}/members              # body: {member_kind, user_id|contact_id}
DELETE /groups/{id}/members/{member_kind}/{member_id}
POST   /groups/{id}/send                 # body: {subject, html, text?} → Resend

# History / audit
GET    /companies/{id}/history           ?since=&page=
GET    /audit/                           ?entity_type=&entity_id=&actor_id=

# Imports / exports
POST   /companies/import                 # multipart CSV
POST   /users/import                     # multipart CSV (proxies to existing users module)
GET    /companies/export.csv
GET    /users/export.csv
GET    /imports/templates/companies.csv  # static download
GET    /imports/templates/people.csv     # static download
```

Existing `/api/v1/users/*` and `/api/v1/contacts/*` endpoints continue to serve `UsersTab` and `ContactsTab` — no breakage.

## 6. Theme tokens

`frontend/src/features/directory/theme/tokens.css`:

```css
[data-route="directory"] {
  --bg-base:         #0A0E1A;
  --bg-surface:      #111827;
  --bg-elevated:     #1C2333;
  --border-subtle:   #1F2937;
  --border-strong:   #374151;
  --text-primary:    #E5E7EB;
  --text-secondary:  #9CA3AF;
  --text-muted:      #6B7280;
  --accent-primary:  #3B82F6;
  --accent-secondary:#F59E0B;
  --status-active:   #10B981;
  --status-warn:     #F59E0B;
  --status-danger:   #EF4444;
  --font-display:    'DM Serif Display', serif;
  --font-body:       'IBM Plex Sans', system-ui, sans-serif;
  --font-mono:       'JetBrains Mono', ui-monospace, monospace;

  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-body);
}
[data-route="directory"] h1,
[data-route="directory"] h2 { font-family: var(--font-display); }
[data-route="directory"] .mono,
[data-route="directory"] td.numeric,
[data-route="directory"] .id,
[data-route="directory"] .date,
[data-route="directory"] .phone { font-family: var(--font-mono); }
```

Fonts loaded via `frontend/src/features/directory/theme/fonts.css` using `@font-face` with WOFF2 files self-hosted under `frontend/public/fonts/` (no Google Fonts CDN — keeps Vercel edge cache deterministic and works in air-gapped staging).

## 7. Three-wave delivery plan

Each wave is **one commit on `main`**, pushed to `origin/main`, then user manually runs `cd frontend && vercel --prod --yes`.

### Wave 1 — Foundation, shell, Users + Contacts replacement, Companies General
**Backend:**
- `directory_companies` migration
- `backend/app/modules/directory/companies/` (model, schema, service, router)
- Module router mounted under `/api/v1/directory/`
- RBAC: `directory.read`, `directory.write`, `directory.admin` permissions added; admin role inherits

**Frontend:**
- Self-hosted fonts under `public/fonts/`
- `directory/theme/tokens.css` + `fonts.css`
- `DirectoryPage.tsx` + `DirectoryTabs.tsx`
- `UsersTab.tsx` — port of existing `UserManagementPage.tsx` including the slide-over from commit `58f44bc7` and the admin password-reset action
- `ContactsTab.tsx` — port of existing contacts components
- `CompaniesTab.tsx` + `AddEditCompanySlideOver.tsx` with **only** the General tab populated; the other four slide-over tabs render placeholders ("Coming in Wave 2/3") with disabled state
- `KpiRow`, `DirectoryTable`, `StatusBadge`, `SlideOver` components
- Top-toolbar buttons: **Wave 1 ships only Add User + Add Company.** Bulk Add / Import People / Import Companies / Export render with `disabled` state and a "Available in Wave 3" tooltip — they become functional in Wave 3 when the import/export endpoints land.
- App router: `/directory` registered; `/users` and `/contacts` rewritten to 301 → `/directory?tab=...`
- Delete `features/users/UserManagementPage.tsx` and `features/contacts/` after grep-verifying no other imports

**Tests:**
- Backend: pytest integration for companies CRUD + RBAC matrix entry
- Frontend: `tsc --noEmit` green, `npm run build` green
- Manual: visit `/directory`, switch tabs, create one company, verify 301 redirect from `/users`

**Definition of done:** commit `feat(directory): wave 1 — shell + users/contacts port + companies general` lands on `main`; user deploys; smoke test passes on prod.

### Wave 2 — Bidder Info, Insurance with cron + email
**Backend:**
- `directory_company_bidder_info`, `directory_company_insurance` migrations
- `backend/app/modules/directory/insurance/cron.py` — Celery beat job, daily 08:00 server TZ:
  - Query certs WHERE `send_notification = TRUE AND status != 'exempt' AND expiration_date IS NOT NULL`
  - Bucket into 60-day and 30-day groups; suppress if `last_notified_at` is within the same threshold window
  - Send digest via Resend HTTP API (`backend/app/core/email.py` already wraps the client) to (a) the company's `primary_contact.email`, and (b) members of an "Insurance Watchers" distribution group if one exists (graceful no-op if absent — relies on Wave 3 for full functionality but does not block Wave 2)
  - Stamp `last_notified_at = NOW()`
- Bidder-info upsert + insurance CRUD routers

**Frontend:**
- Bidder Info tab: 17 cert checkboxes in a 2-column grid with grouped section headers (Federal / State / Status). Trades & cost-codes multi-selects fetch from existing catalog endpoints. Comments thread with attachment upload, star rating.
- Insurance tab: dense table with the spec'd columns. `expiration_date` cell rendered:
  - **RED** (`--status-danger`) if expired or expires within 30 days
  - **AMBER** (`--status-warn`) if expires within 60 days but more than 30
  - default if > 60 days or no date
  - Computed client-side via `utils/insurance-status.ts`; backend returns the raw date
- "Add Project Insurance" slide-over form
- `FederalCertBadges` component displayed on the Companies tab row when bidder-info flags are set

**Tests:**
- Backend: pytest for the cron job's bucketing + suppression logic; integration test mocking Resend
- Frontend: snapshot tests for the date-color logic at -1, +1, +29, +31, +59, +61 day deltas
- Manual: create a cert expiring in 25 days, run cron locally (`celery -A app.core.celery beat` with sped-up schedule), confirm email lands in Resend's test inbox

**Definition of done:** commit `feat(directory): wave 2 — bidder info + insurance with cron + email`; deploy; manual prod smoke test.

### Wave 3 — Distribution Groups (with send), Inactive, History, parked-branch cleanup
**Backend:**
- `directory_groups`, `directory_group_members`, `directory_audit_log` migrations
- Groups CRUD + members CRUD + `POST /groups/{id}/send` (resolves emails by joining users + contacts, calls Resend, returns send report)
- Audit log emit hooks injected into company / bidder-info / insurance / group PATCH paths
- History endpoint for company detail

**Frontend:**
- `DistributionGroupsTab.tsx` + `AddDistributionGroupModal.tsx` with member multi-select (users + contacts in one combined picker)
- "Send" action on group rows → modal: subject + HTML editor (TipTap, already in deps) + send button
- `InactiveTab.tsx`: three sub-sections (Inactive Users / Contacts / Companies) with Reactivate action and construction-themed empty state illustration (SVG, self-authored, 4KB max)
- History sub-tab populated in `AddEditCompanySlideOver`; renders audit log with diff display
- Final toolbar polish: Export dropdown, Import templates with download links
- CSV import (companies + people) with column-mapping preview, then commit

**Parked branch resolution (executed during Wave 3, with explicit user step):**
1. `git diff main..parked/rebrand-d45fda1c -- '*.md' '*.tsx' | grep -E "NEXUS|OpenConstructionERP"` — identify rebrand strings worth salvaging
2. If any found, `git cherry-pick <commit>` from parked onto `main` (likely commit `bc0222e3` for branding strings, manual conflict resolution against current files)
3. **User confirmation step before delete**
4. `git branch -D parked/rebrand-d45fda1c` — local only; no remote push to delete

**Tests:**
- Backend: pytest for groups send (mocked Resend), audit emit on update
- Frontend: e2e for create-group → add-members → send flow
- Integration: assert reactivate flow restores `is_active=true` and emits audit row

**Definition of done:** commit `feat(directory): wave 3 — groups + inactive + history + branch cleanup`; deploy; full /directory walkthrough passes.

## 8. Quality gates (per wave, in order)

For each wave, before commit:
- [ ] `cd frontend && npx tsc --noEmit` exits 0
- [ ] `cd frontend && npm run build` exits 0
- [ ] `cd backend && pytest tests/integration/test_directory_*` exits 0
- [ ] `cd backend && alembic upgrade head` runs cleanly against a fresh DB
- [ ] `cd backend && alembic downgrade -1 && alembic upgrade head` round-trips
- [ ] Manual: page renders, primary action works, no console errors
- [ ] Aesthetic checklist:
  - All colors via CSS variables (no inline `#hex` outside `tokens.css`)
  - Three-font typography confirmed in DevTools
  - Status badges = dot + text + color
  - Tables sticky-header + row hover + monospace numerics + right-pinned actions
  - Insurance dates RED/AMBER coloring verified at boundary values
  - Empty states have CTAs
  - Slide-overs animate 300ms ease-out from right

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Porting `UserManagementPage` loses behavior. The page has 709 lines and was modified in the last two commits. | Diff-test approach: keep the old component in `_archived/` for one commit, port, then delete in a follow-up commit after verifying parity in staging. |
| R2 | 17 BOOLEAN cert columns lose per-cert metadata (number, expiration, issuing agency). | Documented in L8 as known limitation; structured `{cert_no, expires_on, agency}` upgrade is a future RFC. For v1, the boolean columns match the spec exactly. |
| R3 | Theme scoped to `[data-route="directory"]` only — wrapped existing Users/Contacts components may have hardcoded `bg-white text-black` Tailwind classes that look broken in the dark shell. | Wave 1 includes a Tailwind audit of the ported user/contact components; uses Tailwind's `dark:` variant gated by a `.directory-dark` class on the wrapper, OR overrides via `[data-route="directory"] .bg-white { background: var(--bg-surface); }` cascade. Decided during implementation, not in spec. |
| R4 | Celery beat schedule conflicts with the existing `reporting/cron.py` job. | Inspect `backend/app/core/celery.py` beat schedule before adding the insurance job; offset run time by at least 5 min from existing jobs. |
| R5 | Distribution group `POST /send` is a powerful broadcast primitive — accidental "Send to All Subs" could spam vendors. | Send action requires explicit `directory.admin` permission (not `.write`). Send modal shows recipient count + sample addresses with a confirm checkbox before the API call. Audit log records every send with recipient list. |
| R6 | 301 redirects from `/users` → `/directory?tab=users` may break deep links in saved Slack messages or in-app notification emails. | Wave 1 grep for `/users` and `/contacts` literals across `frontend/`, `backend/`, and recent email templates. Any internal references updated in the same commit. Public bookmarks rely on the 301. |
| R7 | The parked-branch cherry-pick may have merge conflicts because main has moved 1.4MB of diff past it. | Conflict resolution is manual and human-supervised. If salvage is non-trivial, abandon the cherry-pick — the rebrand strings can be re-typed in 10 minutes if needed. |
| R8 | Vercel preview deploys may not exercise the Celery cron path (Celery beat runs only in the Railway worker pod). | Cron tested via local `celery -A app.core.celery beat -l info` + a sped-up `CELERYBEAT_SCHEDULE` override; Wave 2 includes a Railway worker pod health check. |
| R9 | Capturing SSN on the user form is a serious data-protection liability — encrypted-at-rest, access-controlled, retention-policied. Most construction admin workflows don't need it stored, just verified once for I-9. | Wave 1 implementation default: render the SSN field as **write-only, never read back**; store as a one-way hash with a flag "on file" rather than the cleartext value. Surface this decision to user before Wave 1 commit. |

## 9.5 Field-level UI mapping (reference for implementation)

The original product brief (this conversation, 2026-05-13) enumerates exact field lists for two complex slide-overs that are not duplicated in this RFC. `writing-plans` will pull from the original brief; backend schemas hold canonical column lists; UI fields map onto those columns plus a few computed/derived fields.

**`AddEditUserSlideOver` (3 tabs):**
- Tab 1 *Details:* Title, Email, Phone, Phone 2, Cell, Employee ID, DOB, SSN (masked input, stored hashed if collected at all — see R9), DL#, Crews multi-select, Address with map preview
- Tab 2 *Employment:* Hire Date, Release Date, Wage Rate ($/hr), Billing Rate ($/hr), Burden Rate ($/hr), Tags, Emergency Contact name/relationship/phone
- Tab 3 *Login & Access:* Role, Manage Company Roles (module permissions), Username (=email), Notification preferences (Email/Push/SMS toggles), Default Cost Code, Time-Card direct toggle, Viewable Projects (All/Some), Show in Crew Schedule, Employee Tasks color

**`AddEditCompanySlideOver` (5 tabs):**
- Tab 1 *General:* fields from §4.1
- Tab 2 *Users:* people assigned to current project vs. not assigned (two sections, project context comes from a `?project_id=` query param)
- Tab 3 *Bidder Info:* 17 cert checkboxes from §4.2 + trades + cost codes + comments + rating
- Tab 4 *Insurance:* columns from §4.3 + RED/AMBER status calc + "Add Project Insurance" action
- Tab 5 *Change History:* §4.6 query rendered as audit table

**Gap to flag during implementation:** Tab 1 of `AddEditUserSlideOver` mentions a *Crews multi-select*. There is no `crews` schema in `backend/app/modules/` today. Wave 1 will either (a) add a minimal `crews` table (likely scope creep) or (b) render the Crews picker disabled with a "Coming soon" note pending its own RFC. Decided during Wave 1 implementation; flagged here so it isn't a surprise.

## 10. Out of scope (v1)

- Auto `vercel --prod` (user-locked decision L10)
- Structured per-cert metadata for federal certifications (Risk R2)
- A global app-wide dark mode (Decision L5)
- Procore-style mixed-use distribution groups (project-team assignment via groups) — v1 is email distribution only
- Tag indexing — `tags JSONB` is good enough until query patterns demand a tag table
- SMS / push notifications for insurance — email-only for v1
- Federal cert verification against SAM.gov / SBA DSBS APIs — manual entry only
