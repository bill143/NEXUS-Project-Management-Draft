# Batch 4b — Backend security cross-cuts audit (2026-05-13)

Read-only audit of the security-relevant core modules listed in
`docs/audits/2026-05-13-full-pass-baseline.md` Batch 4 scope:

- `app/core/permissions.py` — RBAC
- `app/core/crypto.py` — at-rest secret encryption
- `app/core/sanitize.py` — input/output HTML sanitisation
- `app/core/upload_guards.py` — multipart upload safety
- `app/core/url_safety.py` — SSRF protection
- `app/core/rate_limiter.py` — abuse limiter
- `app/core/csv_safety.py` — CSV/XLSX formula-injection protection
- `app/core/file_signature.py` — magic-byte type detection
- `app/modules/users/schemas.py` — auth schemas (covered by 4a)

The single broken security-related unit test (`test_default_role_is_editor`)
was fixed in Batch 4a / PR #32 — schema default is `'viewer'` (least
privilege), test asserted `'editor'`; test was stale.

## Verdict

**No real security bugs to fix.** Every file shows defence-in-depth,
OWASP awareness, and thoughtful trade-offs. The 2026-05-09 QA report's
PASS verdicts on RBAC + Auth + Security posture continue to hold.

## Per-file notes

### `permissions.py`

- Hierarchical `admin > manager > editor > viewer` with explicit
  `ROLE_HIERARCHY` rank map.
- `ROLE_ALIASES` keeps the canonical `Role` enum small while accepting
  industry-specific titles (`estimator`, `quantity_surveyor`, `qs`).
  `superuser`/`owner` resolve to `admin`; `readonly`/`guest` to `viewer`.
- `_resolve_role` accepts any case, falls back to alias map, returns
  `None` for unknowns — caller controls the fail-closed behaviour.
- **Recent reinforcement (commit `fe11b1b`)**: CI now runs an RBAC matrix
  test. Good.

### `crypto.py`

- Fernet symmetric encryption keyed off `settings.jwt_secret` + fixed
  salt → no new env var needed; rotation tracks JWT rotation.
- **Key-rotation behaviour is correct**: if a token can't be decrypted
  (`InvalidToken`), the function returns `None` rather than passing
  garbage on to a remote provider. Legacy plaintext rows (no Fernet
  prefix `gAAAAA…`) pass through unchanged — so the encryption was
  added without breaking pre-encryption data at rest.

### `sanitize.py`

- Two-tier stripper: `strip_dangerous_html` (input layer, only kills
  `<script>`/`<iframe>`/event handlers/`javascript:` URIs but leaves
  literal `<` alone) and `strip_all_html_tags` (output layer, removes
  every tag, decodes a small entity subset).
- Preserves construction text like `"beam <200mm section"` verbatim
  because the regex requires a tag-name lead character after `<`.
- `_BLOCK_TAG_RE` + `_BLOCK_TAG_UNTERMINATED_RE` + `_BLOCK_TAG_OPEN_RE`
  together close the "unterminated `<script>` at EOF" bypass that a lot
  of homegrown sanitisers miss.
- `reject_control_chars` is a *raising* helper (NUL/bell/BS/etc. → 400)
  — better than silently stripping because that would hide upstream
  encoding bugs.

### `upload_guards.py`

- Only currently active guard: `reject_if_xlsx_bomb` — sums uncompressed
  entry sizes via `zipfile.infolist()` before openpyxl materialises the
  sheet. Default cap 50 MB. Returns silently for non-zip payloads so the
  downstream parser produces the natural error.
- **Hardening opportunity (not a bug)**: there's no equivalent guard
  for plain ZIP, IFC-zip, GLB-zip, or DOCX/PPTX uploads. If any of
  those endpoints accept user uploads and let an XML parser materialise
  the contents, a similar bomb attack works. Worth surveying in
  Batch 7 (CAD/BIM) when we look at the IFC upload path.

### `url_safety.py`

- **Two-layer SSRF protection**: sync `validate_external_url` (cheap,
  for Pydantic validators) + async `resolve_and_validate_external_url`
  (DNS lookup + recheck right before dispatch).
- Blocks `localhost`, `169.254.169.254`, `metadata.google.internal`,
  `metadata.goog`, IPv6 cloud metadata, plus any IP in loopback /
  private / link-local / multicast / reserved / unspecified ranges.
- **DNS rebinding is genuinely addressed** — the async path resolves
  every A/AAAA record and rejects if *any* resolves to a blocked
  range. This is the layer most homegrown SSRF validators miss.
- `UnsafeUrlError` subclasses `ValueError` so Pydantic validators get
  the right 422 surface without an adapter.

### `rate_limiter.py`

- In-memory sliding-window with `threading.Lock`. Per-key bucket;
  cleans expired timestamps on each check.
- Reads `AI_RATE_LIMIT` / `API_RATE_LIMIT` / `LOGIN_RATE_LIMIT` from
  settings; fallback defaults (10/100/10 per minute).
- **Documents the `X-Forwarded-For` trust caveat clearly** (line 32-36):
  prefers XFF first entry behind a proxy, but notes "MUST strip or
  overwrite at the edge proxy before requests reach the app — see
  `deploy/docker/nginx.conf` for the standard template". This is the
  right model.
- **Known limitation** (already in the docstring): in-process state
  doesn't survive restart and doesn't shard across replicas. Notes
  Redis-based replacement for production. Not a bug — a documented
  deployment-time choice. Worth confirming in Batch 19 that the
  production deploy actually has nginx-side XFF normalisation.

### `csv_safety.py`

- OWASP CSV-injection protection. Prepends `'` if a string starts with
  `=`, `+`, `-`, `@`, `\t`, or `\r`. Tab and CR are included because
  Excel strips leading whitespace before parsing.
- **Deliberately does NOT mutate at rest** — sanitises only at export
  boundary. Right call: a stored value `=cmd|'/c calc'!A0` could be
  legitimate text the user expects to re-import, and round-tripping
  matters more than over-sanitising.
- `Any`-typed input means callers can apply unconditionally — numbers,
  `Decimal`, `None`, arbitrary objects pass through untouched.

### `file_signature.py`

- Pure stdlib (no `python-magic` / `libmagic`). Reads ≤16 bytes.
- Covers every format the app accepts: PDF / PNG / JPEG / GIF / WebP /
  ZIP (xlsx, docx, pptx, GLB) / OLE (legacy Office, RVT) / IFC step /
  DWG.
- The PDF and IFC detectors strip a small leading BOM/whitespace prefix
  before matching, so scanners that emit BOM don't break detection.
- Returns symbolic tokens (`"pdf"`, `"zip"`, `"ifc"`) rather than MIME
  strings — caller matches against a known small set, which is harder
  to bypass than MIME-string equality.

## Cross-references confirmed

- **2026-05-09 QA report Item 4 (RBAC)**: PASS. Confirmed unchanged —
  the matrix CI added in commit `fe11b1b` keeps this honest.
- **2026-05-09 QA report Item 5 (Auth edge cases)**: PASS. Schema
  validators in `app/modules/users/schemas.py` enforce min-length,
  pattern, and role whitelist. Recent commit `4bd83bb` cemented the
  "never-admin on self-register" bootstrap policy in the docstring.
- **2026-05-09 QA report Item 7b (Resend email)**: PASS. Verified in
  commit `067fb7f`. SMTP fallback still present.
- **2026-05-09 QA report Item 6 (schema drift)**: still FAIL — that's
  Batch 5's responsibility.

## What was NOT covered in this audit

- `app/modules/users/service.py` (password hash flow, JWT issue/verify,
  session handling) — needs its own deeper pass because of size + the
  blast radius. Recommend treating it as a focused mini-batch if any
  concern surfaces.
- `app/middleware/` — auth / tenant / CORS middlewares. Same reason.
- Live RBAC probe against a running app — would require a Docker-up
  environment that this sandbox doesn't have. The 2026-05-09 QA
  report's live probe already verified anonymous → 401 and role-mismatch
  → 403. The RBAC matrix CI test (commit `fe11b1b`) replays that on
  every PR.

## Recommendation

**No code change needed in this batch.** The audit doc is the
deliverable. Mark Batch 4 done and move to Batch 5 (Alembic migrations
+ schema drift), which has 38 documented drift events from `alembic
check` and is the only remaining open finding from the 2026-05-09 QA
report.

If you want a deeper pass on `app/modules/users/service.py` and the
middlewares, that should be its own batch — call it Batch 4c — rather
than bundled into this read-only audit.
