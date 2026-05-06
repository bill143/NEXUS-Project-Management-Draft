DDC Consolidation Plan — NEXUS-Project-Management-Draft
Author: Generated via automated audit (Phase 3 of consolidation workstream) Date: 2026-05-02 Scope: Audit and port-strategy matrix for 23 DataDrivenConstruction (DDC) reference repositories targeting consolidation into a single application built on the NEXUS shell. Status: Draft — awaiting user approval before any code is written (Phase 4 gate).
________________________________________
1. Goal
Produce a single unified application — NEXUS-Project-Management-Draft — built on top of the NEXUS shell, organized into 7 modules plus 1 P0 submodule:
#	NEXUS Module	Purpose
1	Conversion & Ingestion	RVT/IFC/DWG/DGN/PDF → tabular data; ETL pipelines
2	Estimation & Takeoff	QTO, grouping rules, 4D/5D pipelines
3	Analysis & QA	Validation, quality reports, geometric grouping, EDA
4	Visualization	3D viewer, parametric dashboards, image rendering
5	AI/LLM	LLM-driven code generation, automated analysis, ML price prediction
6	Revit-Excel Bridge	Round-trip data flow between Revit and Excel
7	Sustainability / CO₂	Embodied-carbon tooling (GSA P100, Buy Clean Act) — P0 federal differentiator
P0 Submodule:
•	ML Price-Prediction — federal bid forecasting (pairs with SAM.gov / USAspending data); lives inside AI/LLM module
________________________________________
2. Audit Method
•	All 23 DDC repos enumerated; sizes pre-checked via gh api.
•	One repo (OpenConstructionEstimate-DDC-CWICR, 1555 MB) skipped per the >500 MB safety gate. The remaining 22 were shallow-cloned (--depth 1) into C:\repos\DDC_reference\ (total: 2.40 GB on disk).
•	For each cloned repo, the README was read directly. For data-analytics (no README), capabilities inferred from notebook filenames.
•	Categorization assigned by reading purpose statements and dependency stacks; port strategy chosen based on (a) license, (b) code quality, (c) dependency burden, (d) overlap with existing NEXUS scaffold.
________________________________________
3. Skipped Repo
Source Repo	Size	Reason	Recommended Action
OpenConstructionEstimate-DDC-CWICR	1555 MB	Exceeds 500 MB safety threshold	Resolved at §7 gate — sparse-checkout of /docs, /schemas, and /data/cwicr only, or full clone if confirmed.
________________________________________
4. Consolidation Matrix
Strategy legend — rewrite = port logic into native NEXUS Python/JS code; wrap = vendor or embed reference repo as-is and call it from NEXUS; discard = redundant or trivial, do not bring forward.
#	Source Repo	Size (GitHub / on-disk)	Language	Key Capability	Target NEXUS Module	Port Strategy	Priority
1	PDF-to-Excel	0.02 MB / 0.1 MB	Python (Jupyter)	Tabula-py PDF → multi-sheet Excel; trivial wrapper	Conversion & Ingestion (sub: PDF)	rewrite (small endpoint, ~50 LOC)	P2
2	Open-Estimation	0.85 MB / 0.66 MB	Excel templates only	OpenEstimator.xlsx + Grouping_rules_QTO.xlsx template assets (no code)	Estimation & Takeoff	wrap (import as data/template assets)	P1
3	QuantityTakeoff-Python	0.2 MB / 0.47 MB	Python (Dash)	Web QTO app — group elements from Revit/IFC tables, compute volumes by filter	Estimation & Takeoff	rewrite (port grouping/aggregation logic; UI redone in NEXUS frontend)	P1
4	QuantityTakeoff-JupyterNotebook	0.93 MB / 2.41 MB	Jupyter	Same as #3 but notebook form	Estimation & Takeoff	discard (duplicate of #3 — only retain unique pandas snippets if any)	P2
5	Quick-QTO	0.02 MB / 0.08 MB	Jupyter	~50-line batch QTO across folder of Excel exports	Estimation & Takeoff	rewrite (batch service that runs over a project queue)	P1
6	4D-5D-Pipeline	0.14 MB / 0.63 MB	Jupyter	4D/5D BIM pipeline notebook joining schedule + cost data to model	Estimation & Takeoff	rewrite (enhance existing v280_4d_schedule_eac module already migrated)	P0
7	Revit-IFC-Verification	0.14 MB / 0.15 MB	Python	Excel-driven validation script; outputs % completion + unique values per parameter	Analysis & QA	rewrite (merge with #8 into a single Validation/QA service)	P1
8	Checking-the-quality-of-Revit-and-IFC-projects	0.55 MB / 1.10 MB	Python (Jupyter + .py)	Larger version of #7 — Excel rules + PDF report generation; bundled UI exe builder	Analysis & QA	rewrite (merge with #7; drop UI-exe path; PDF reports via WeasyPrint or ReportLab)	P1
9	data-analytics	3.21 MB / 5.42 MB	Jupyter (5 notebooks)	Pandas + ChatGPT analysis recipes on Revit rme_basic_sample data; no README	Analysis & QA	discard as code; extract notebook recipes into /docs/recipes	P2
10	Geometric-Groups-by-Any-Property	0.02 MB / 0.08 MB	Jupyter	Group elements by any property; output geometry to .dae (Collada) per group	Analysis & QA / Visualization	rewrite (geometry-export utility; needs IfcOpenShell + Collada writer)	P1
11	ML-Price-Prediction-Model	3.83 MB / 11.73 MB	Jupyter (sklearn)	(a) Synthetic-data generator from 4 base CSVs → 50 fake projects; (b) sklearn regression model predicting project price from BOM-style CSV	AI/LLM (P0 submodule: ML Price-Prediction)	rewrite (proper Python package: data prep → train → inference REST API; add SAM.gov/USAspending feature columns for fed bid forecasting)	P0
12	CO2_calculating-the-embodied-carbon	0.23 MB / 0.18 MB	Jupyter	volume × emission-factor for each element group; carbon footprint per RVT/IFC project	Sustainability / CO₂	rewrite (proper module backed by EPD database table; align factors with EC3 / GSA P100 / Buy Clean Act categories)	P0
13	VisualBIM	0.03 MB / 0.12 MB	Python (Dash + Plotly)	Multidimensional point-cloud visualization of BIM project parameters; "DNA-style" project comparison	Visualization	rewrite (port concept to NEXUS frontend using Plotly.js or ECharts; backend serves project DataFrames)	P1
14	Revit-Data-Analysis-Streamlit-App	0.02 MB / 0.07 MB	Python (Streamlit)	Multi-page Streamlit app: upload Revit Excel, show profiling/EDA, histograms, correlation heatmaps	Visualization / Analysis & QA	rewrite (extract pandas profiling helpers; rebuild UI as NEXUS dashboard pages — drop Streamlit dep)	P1
15	Visualizing-Data-from-Excel	0.04 MB / 0.14 MB	Jupyter	Trivial pandas + matplotlib + seaborn from-Excel charts	Visualization	discard (subsumed by #14 and standard chart libs)	P2
16	Excel_to_Revit	0.01 MB / 0.07 MB	(placeholder)	README has 2 lines; no code	Revit-Excel Bridge	discard (#21 ImportExcelToRevit is the real implementation)	P2
17	Online3DViewer	26.2 MB / 43.97 MB	JavaScript (three.js)	Mature open-source web 3D viewer — imports OBJ, 3DS, STL, PLY, GLTF, OFF, 3DM, FBX, DAE, WRL, 3MF, IFC; MIT-licensed; built on three.js + web-ifc	Visualization	wrap (vendor in /frontend/vendor/online3dviewer or as npm dep; embed <canvas> in NEXUS viewer page)	P1
18	etl-collecting-data-from-revit-and-ifc-projects-for-analysis-an	0 MB / 0.03 MB	(placeholder)	Empty repo — README is 2 lines, no code	Conversion & Ingestion	discard (placeholder)	P2
19	Revit-IFC-Creating-images	42.14 MB / 100.88 MB	Python (Jupyter + .py)	noBIM-based image rendering from Revit/IFC without Autodesk API; outputs JPEG/PNG	Visualization	wrap initially (call existing script as a render service); later migrate to IfcOpenShell + offscreen Three.js render	P1
20	Examples-of-files-after-conversion	183.28 MB / 139.01 MB	Sample data	RVT/IFC sample files post-conversion in JSON, DAE, CSV, XML, XLS	(test fixtures)	wrap (import a curated subset into /backend/tests/fixtures/ddc_samples/; do not ship full 139 MB)	P2
21	ImportExcelToRevit	220.55 MB / 425.69 MB	C# (Revit API)	Revit add-in MSI (Revit 2020-2026) that pushes Excel-edited parameter values back into Revit	Revit-Excel Bridge	wrap (keep as separately-distributed MSI; NEXUS produces Excel in correct shape; document integration)	P1
22	CAD-BIM-to-Code-Automation-Pipeline-DDC-Workflow-with-LLM-ChatGPT	381.71 MB / 1667.59 MB	n8n JSON + bundled converters	n8n workflow JSON + bundled noBIM converters (RvtExporter / IfcExporter / DwgExporter / DgnExporter .exe) + LLM Python-code generator	AI/LLM + Conversion & Ingestion	rewrite (replace n8n with native NEXUS Celery/Prefect pipeline; vendor the .exe converters as bundled tools — license resolved at §7 gate)	P1
________________________________________
5. Cross-cutting Risks & Open Questions
5.1 noBIM converter licensing
Most repos depend on free-but-closed-source DDC converter executables (RvtExporter.exe, IfcExporter.exe, etc.) downloaded from cadbimconverter.com. Repo #22 bundles these binaries (1.67 GB on disk). Redistribution rights and deployment approach resolved at §7 gate.
5.2 Notebook → service migration cost
Of the 22 cloned repos, 9 are primarily Jupyter notebooks. Porting these to production services means:
•	Extracting cell-level logic into proper Python modules
•	Replacing pd.read_excel(...) patterns with NEXUS database queries
•	Replacing inline matplotlib with NEXUS chart components (or returning JSON for the frontend to render)
5.3 Three open-source dependencies worth standardizing on early
•	IfcOpenShell — for any IFC parsing we own
•	three.js (via Online3DViewer wrap) — for 3D viewing
•	scikit-learn / XGBoost — for ML Price-Prediction (P0 submodule)
5.4 OpenConstructionEstimate-DDC-CWICR (1555 MB)
Skipped per the safety gate. Likely contains the public Open Construction Estimate dataset and website assets. Sparse-checkout path and scope resolved at §7 gate.
________________________________________
6. Phase 5 Execution Order
P0 first (federal differentiators):
1.	Sustainability / CO₂ submodule (#12)
2.	4D/5D Pipeline enhancement (#6 → existing v280 module)
3.	ML Price-Prediction submodule (#11)
P1 then (highest reuse): 4. Validation/QA service (#7 + #8 merged) 5. QTO services (#3, #5) 6. Online3DViewer wrap (#17) 7. AI/LLM pipeline rewrite (#22) 8. Streamlit app port (#14) 9. VisualBIM port (#13) 10. Geometric grouping utility (#10) 11. ImportExcelToRevit integration (#21) 12. Revit-IFC image render (#19) 13. PDF→Excel ingestion (#1)
P2 last (templates, fixtures, docs): 14. Open-Estimation templates (#2) 15. Sample fixtures (#20) 16. Recipe extraction from #9 17. Discards confirmed: #4, #15, #16, #18
________________________________________
7. Approval Checkpoint (Phase 4 Gate)
Before any code is written or Phase 5 begins, confirm or amend:
•	Module assignments in §4
•	Port strategy decisions (especially wrap vs rewrite)
•	Priorities (P0/P1/P2) — particularly whether anything P1 should be promoted to P0
•	Decision on the 1555 MB skipped repo (§5.4) — sparse-checkout /docs + /schemas + /data/cwicr only, or full clone
•	Decision on noBIM converter binary redistribution (§5.1) — bundle in NEXUS or require user-side install
When you reply 
