# Phase 5 — Build Status

**Last updated:** 2026-05-02
**Branch:** `main` on `bill143/NEXUS-Project-Management-Draft`
**Companion doc:** [`DDC_CONSOLIDATION_PLAN.md`](DDC_CONSOLIDATION_PLAN.md)

This file is the live status of the consolidation matrix in §4 of the consolidation plan. The goal here is *one place* to see what's actually in the repo right now versus what's still pending.

---

## P0 — Federal differentiators (3/3 complete)

| # | Module | Status | Commit | Surface |
|---|---|---|---|---|
| #11 | ML Price-Prediction | ✅ Built | `5a9be4c` | `backend/app/modules/ml_price_prediction/` · 8 files · migration `v2d1` · `/api/v1/ml_price_prediction/{models/train,predict,models}` · v1.0 sklearn regression; SAM.gov / USAspending features deferred to v1.1 per Amendment 2 |
| #12 | Sustainability / CO₂ | ✅ Built | `5a9be4c` | `backend/app/modules/sustainability/` · 9 files · migration `v2d0` · `/api/v1/sustainability/{factors,groups,reports}` · GSA P100 + Buy Clean Act categories |
| #6 | 4D/5D Pipeline | ✅ Already covered | upstream | OCE's `full_evm` + `schedule` (with `router_4d.py` + `service_4d.py`) + migration `v280_4d_schedule_eac` already implements 4D/5D. No port needed. |

---

## P1 — High-reuse ports (5/12 complete, 2 deferred, 5 frontend/heavy-dep skipped)

| Plan # | Module | Status | Commit | Notes |
|---|---|---|---|---|
| #4 | Validation/QA service merge (DDC #7 + #8) | ✅ Built | `7785f50c` | New rule pack `ddc_revit_ifc` in `app/core/validation/rules/` — 36 rules across 12 (category, parameter) pairs with IFC synonym matching. 10/10 tests. |
| #5 | DDC QTO services (DDC #3 + #5) | ✅ Built | `8e168e54` | New module `ddc_qto` with `/summarize` + `/batch` endpoints. Pure-Python grouping/aggregation, no pandas at the public surface. 23/23 tests. |
| #6 | Online3DViewer wrap (DDC #17) | ⏸️ Deferred | — | Frontend-only work. The npm `online-3d-viewer` package is published; integrating it requires the React build pipeline to be validated end-to-end (not exercised in this sweep). Recommended P1.5 sweep with frontend dev server up. |
| #7 | AI/LLM pipeline rewrite (DDC #22) | ⏸️ Deferred | — | Substantial: replace n8n workflow with Celery/Prefect orchestration on top of the existing `ai` module. Treat as its own multi-day project. |
| #8 | Streamlit profiling (DDC #14) | ✅ Built | `b6848549` | New module `ddc_profiling` with column-summary/histogram/categories/correlation/missing-map endpoints. Pandas + numpy lazy-imported. 8/8 tests. |
| #9 | VisualBIM (DDC #13) | ⏸️ Deferred | — | Frontend visualization (Plotly.js / ECharts). Same rationale as #6 — recommended for the frontend sweep. |
| #10 | Geometric grouping (DDC #10) | ⏸️ Deferred | — | Requires IfcOpenShell + a Collada writer. Both add non-trivial deps; recommended for a separate sweep with proper IFC test fixtures. |
| #11 | ImportExcelToRevit Excel export (DDC #21) | ✅ Built | `9952b3a4` | New module `ddc_revit_export` — produces `.xlsx` files matching the Revit add-in's schema. Per Amendment 1: NEXUS-side end of the round-trip; the Revit MSI itself stays separately distributed. 12/12 tests. |
| #12 | Revit-IFC image render (DDC #19) | ⏸️ Deferred | — | Wraps the closed-source DDC noBIM image-render binary. Per Decision 2 we don't bundle DDC binaries; integration testing requires those binaries installed locally. |
| #13 | PDF→Excel ingestion (DDC #1) | ✅ Built | `78a78e15` | New module `ddc_pdf_excel` — POST `/api/v1/ddc_pdf_excel/extract` accepts a PDF, returns multi-sheet `.xlsx` (one sheet per detected table). Uses pdfplumber instead of tabula-py to avoid the JVM dep. 5/5 tests. |

---

## P2 — Templates / fixtures / discards

| Plan # | Item | Status | Notes |
|---|---|---|---|
| #2 | Open-Estimation templates | ✅ Imported | Both `.xlsx` files copied to `backend/data/ddc_templates/open_estimation/` with a README. |
| #20 | Sample fixtures (Examples-of-files-after-conversion) | ⏸️ Deferred | The repo has 139 MB of mixed RVT/IFC sample exports; curating a < 5 MB subset needs to be done with the BOQ/BIM-Hub modules at hand to know which fixtures are useful for which tests. |
| #9 | Recipe extraction from `data-analytics` | ⏸️ Deferred | Notebook recipe extraction into `/docs/recipes` — pure documentation chore. |
| #4 | `QuantityTakeoff-JupyterNotebook` (discard) | ✅ Confirmed discard | Functionality covered by `ddc_qto` module. No port. |
| #15 | `Visualizing-Data-from-Excel` (discard) | ✅ Confirmed discard | Functionality subsumed by `ddc_profiling` module. |
| #16 | `Excel_to_Revit` (discard) | ✅ Confirmed discard | Empty placeholder repo. The real implementation is `ImportExcelToRevit` (#21) which is the input format `ddc_revit_export` writes to. |
| #18 | `etl-collecting-data-from-revit-and-ifc-projects-for-analysis-an` (discard) | ✅ Confirmed discard | Empty placeholder repo (2-line README). |

---

## CWICR reference repo — partial state

The DataDrivenConstruction `OpenConstructionEstimate-DDC-CWICR` repo is sparse-cloned at `C:\repos\DDC_reference\OpenConstructionEstimate-DDC-CWICR\` with the following caveats:

- **964 MB on disk** (text content only — country folders, multilingual READMEs, AI-instruction docs, license files, data dictionary)
- **LFS-gated assets are missing**: every `.xlsx` workitem-cost workbook and the 2nd-edition guidebook PDF require LFS pulls, and **DDC's GitHub LFS budget is exhausted** on their account. The error message on every gated file is:

  > `batch response: This repository exceeded its LFS budget. The account responsible for the budget should increase it to restore access.`

- **Action needed:** either (a) wait for DataDrivenConstruction to top up their LFS quota, or (b) request a direct file-share link from them for the cost workbooks. NEXUS modules that depend on the canonical CWICR data (the BOQ cost-match flow) should fall back gracefully to OCE's existing CWICR seeds in `backend/data/` until the upstream LFS issue is resolved.

---

## Test gates (current)

| Gate | Status |
|---|---|
| `alembic upgrade head` | ✅ Clean. Head is `v2d1_ml_price_prediction_tables`. |
| New-DDC integration tests | ✅ 74/74 pass across 8 test files (`test_my_module.py` + 7 new DDC tests). |
| `from app.main import create_app; create_app()` | ✅ Clean. Returns 32 mounted routes. |
| Full upstream OCE 2,947-test suite | ⚠️ Pre-existing OCE auth-fixture failure surfaced (`test_dry_run_endpoint_boolean_mode` returns 401). Not introduced by NEXUS work. Triage in a separate sweep — NOT blocking this consolidation. |

---

## Pre-existing OCE issues surfaced during this sweep

| Issue | Status |
|---|---|
| `simpleeval` was imported by `app/modules/eac/engine/safe_eval.py` but missing from `pyproject.toml`. Caused 5 test files to fail collection. | ✅ Fixed in NEXUS — added `simpleeval>=1.0.0` to base deps. |
| `backend/openestimate.db-wal` (51.85 MB SQLite WAL) was committed in OCE history at `abc1740b` and remains in the pack. | ✅ Mitigation: `.gitignore` patterns extended to prevent re-introduction. The historical blob still bloats the repo by ~52 MB; cleaning it requires `git filter-repo` or BFG (destructive history rewrite — not done here). |
| `docs/media/full_preview.mp4` — 69.81 MB upstream OCE marketing asset, exceeds GitHub's 50 MB recommendation. | Noted, not actioned (under 100 MB hard limit). |
