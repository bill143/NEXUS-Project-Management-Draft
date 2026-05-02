# Pipelines — Architecture & Authoring Guide

NEXUS pipelines replace DDC's n8n-based AI workflows with a native
LangGraph + Celery hybrid that lives inside the FastAPI process.

This doc is the entry point for anyone authoring a new pipeline,
debugging an existing one, or evaluating the architecture for a new
DDC workflow port.

## Architecture overview

```
HTTP request
    │
    ▼
FastAPI route (app/pipelines/<name>/router.py)
    │ creates oe_job_run row (status=started)
    ▼
PipelineRuntime.execute(name, payload, job_run_id)
    │ injects LLMDispatcher into the graph state
    ▼
LangGraph compiled graph (app/pipelines/<name>/graph.py)
    │ runs nodes in topology order
    ├── parse_description    → LLMDispatcher.call(HARD)      (Claude Opus)
    ├── classify_items       → LLMDispatcher.call(CLASSIFY)  (Gemini Flash)
    ├── search_cost_db       → deterministic (no LLM)
    └── estimate_total       → LLMDispatcher.call(HARD)      (Claude Opus)
    │
    ▼
Runtime writes telemetry onto oe_job_run
    │ pipeline_name, llm_tier_used, total_tokens, total_cost_usd
    │ status=success / failed
    ▼
Response body: { job_run_id, work_items, classified_items, estimate, … }
```

## Architecture decisions (Sweep B)

1. **Orchestrator: LangGraph + Celery hybrid.** LangGraph runs the AI
   agent flows (LLM reasoning, classification, cost estimation). Celery
   handles deterministic backend tasks (file conversion subprocess
   calls, DB writes, report generation). This keeps each tool focused:
   LangGraph for graph topology, Celery for queue-bound work.
2. **Sync now, async later.** Pipelines run inline in the request
   coroutine for v1.0. The runtime already inserts an `oe_job_run` row
   so observers can poll `/api/v1/jobs/{id}` for telemetry. Switching
   to dispatch-by-job-id is a future change to the route only — the
   pipeline graph and node functions don't move.
3. **Tier dispatch for LLM provider selection.** Three tiers route to
   different default models so cheap classification work doesn't burn
   Opus credit. See `app/core/pipelines/llm_dispatch.py`.
4. **DDC binary converters: subprocess, never bundled.** The wrapper at
   `app/core/converters/ddc_subprocess.py` shells out to the operator's
   DDC install (`C:\Converters\datadrivenlibs\` by default, override
   via `OE_DDC_CONVERTER_ROOT`). The `.exe` files remain DDC-licensed
   and are not redistributed with NEXUS.

## LLM tier policy

| Tier | Default provider / model | Use cases | Env override |
|------|--------------------------|-----------|--------------|
| `HARD` | Claude Opus 4.7 | Cost estimation, multi-step reasoning, parsing | `OE_LLM_TIER_HARD_PROVIDER`, `OE_LLM_TIER_HARD_MODEL` |
| `CLASSIFY` | Gemini 2.5 Flash | MasterFormat / NRM tagging, taxonomy lookups | `OE_LLM_TIER_CLASSIFY_PROVIDER`, `OE_LLM_TIER_CLASSIFY_MODEL` |
| `FALLBACK` | GPT-4o | Used automatically when the preferred tier has no API key or is rate-limited | `OE_LLM_TIER_FALLBACK_PROVIDER`, `OE_LLM_TIER_FALLBACK_MODEL` |

API keys are read from environment variables (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `GEMINI_API_KEY`). No SDK dependencies — the
dispatcher reuses the existing `app.modules.ai.ai_client.call_ai`
HTTP shim so all provider quirks are handled in one place.

## Celery vs. LangGraph: which one for what?

| Use LangGraph when… | Use Celery when… |
|---------------------|------------------|
| Step is an LLM call | Step shells out to a subprocess (CAD converter, ffmpeg, …) |
| Step's output shape depends on prior steps' outputs | Step writes a large file or persists a DB row that other workflows depend on |
| You want to fan-out across nodes | The work is heavy enough to monopolise a worker for minutes |
| You need streaming intermediate state | The caller doesn't need streaming progress — only success/failure |

For the rare hybrid case (LangGraph node that needs Celery work):
submit a job from the node via `app.core.job_runner.submit_job` and
await the result on the JobRun row. The opposite path (Celery task
running a LangGraph graph) uses `PipelineRuntime.execute` directly.

## Authoring a new pipeline

1. Drop a package under `backend/app/pipelines/<name>/`:

   ```
   text_to_cost_estimate/
   ├── __init__.py        ← imports manifest, calls register_pipeline
   ├── manifest           ← exposed as the package's top-level attribute
   ├── graph.py           ← build_graph() returning a compiled LangGraph
   ├── nodes.py           ← async node functions (state → state update)
   ├── schemas.py         ← Pydantic request/response models
   └── router.py          ← FastAPI router with the public endpoint
   ```

2. Define a `PipelineManifest`:

   ```python
   from app.core.pipelines import LLMTier, PipelineManifest, register_pipeline
   from app.pipelines.<name>.graph import build_graph

   manifest = PipelineManifest(
       name="<name>",
       version="1.0.0",
       display_name="...",
       description="...",
       category="ai",
       graph_factory=build_graph,
       tier_map={"node_a": LLMTier.HARD, "node_b": LLMTier.CLASSIFY},
       timeout_seconds=120,
   )
   register_pipeline(manifest)
   ```

3. Append the new pipeline to `app/pipelines/_mount.py`'s `_PIPELINES`
   list. The mount helper is called once during app startup; one entry
   per pipeline.

4. Write tests in `backend/tests/integration/test_<name>.py`. Use a
   `_FakeDispatcher` (see `tests/integration/test_text_to_cost_estimate.py`)
   so no real LLM calls happen in CI.

## JobRun extension columns

Migration `v2f0_pipeline_runs_extension` adds four nullable columns to
`oe_job_run`:

- `pipeline_name` — manifest name (denormalised for dashboard filtering)
- `llm_tier_used` — last tier the dispatcher hit (`hard` / `classify` /
  `fallback`)
- `total_tokens` — sum of provider-reported tokens across the run
- `total_cost_usd` — heuristic blended cost estimate (informational)

All four are nullable so non-pipeline JobRun rows continue to
round-trip without backfill.

## DDC binary converter wrapper

`app/core/converters/ddc_subprocess.py` is a thin subprocess wrapper
for the four DDC converters (`RvtExporter.exe`, `IfcExporter.exe`,
`DwgExporter.exe`, `DgnExporter.exe`).

```python
from app.core.converters import convert_with_ddc

result = convert_with_ddc(
    "C:\\projects\\foo.rvt",
    timeout_s=300,
)
print(result.output_path)   # → C:\projects\foo.xlsx
print(result.duration_s)
```

Failure modes:

- `DDCConverterMissingError` — the `.exe` is not installed at the
  configured root. Error message points at `docs/CONVERTERS.md`.
- `DDCConverterTimeoutError` — subprocess exceeded the wall-clock
  budget. Carries the `timeout` value used.
- `DDCConverterError` — non-zero exit status; the binary's stderr is
  preserved in the message.

Operators install the DDC binaries under `C:\Converters\datadrivenlibs\`
or set `OE_DDC_CONVERTER_ROOT` to override.

## Sweep B status

| Component | Status |
|-----------|--------|
| Celery foundation | Already shipped in v260; Sweep B added `app/core/tasks/` for pipeline-flavoured handlers |
| LangGraph foundation | ✅ Sweep B |
| LLM tier dispatcher | ✅ Sweep B |
| DDC subprocess wrapper | ✅ Sweep B |
| `text_to_cost_estimate` pipeline | ✅ Sweep B |
| JobRun extension columns | ✅ Sweep B (migration v2f0) |
| Other 5 DDC pipelines (workflows #1–5, #6.2, #7) | Deferred to subsequent sweeps |
| Excel/HTML report generation | Deferred |
| Email/notification dispatch | Deferred |

## Next sweeps

- **Sweep C**: Port DDC workflow #1 (CAD/BIM ingestion → canonical
  format). Exercises the subprocess wrapper end-to-end.
- **Sweep D**: Port the cost-DB Qdrant integration into
  `search_cost_db`, replacing the in-memory rate table.
- **Sweep E**: Async-by-job-id route variant. The pipeline graph and
  nodes don't change; only the route shape and the `submit_job`
  dispatch path.
