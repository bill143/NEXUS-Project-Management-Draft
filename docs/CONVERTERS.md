# External CAD/BIM Converters — Install Guide

NEXUS-Project-Management-Draft uses the **DataDrivenConstruction (DDC) cad2data converters** to extract structured quantities from Revit (`.rvt`), IFC, AutoCAD (`.dwg`), and MicroStation (`.dgn`) files into the canonical Excel/JSON format consumed by the BOQ, BIM-Hub, DWG-Takeoff, Cost-Match, and (new) Sustainability/CO₂ modules.

## Why these aren't in this repo

The DDC converters are **closed-source** and ship under their own EULA, which carries Open Design Alliance (ODA) pass-through obligations for the DWG/DGN paths. We do **not** redistribute the binaries here. You download them once, install locally, and NEXUS calls them via CLI.

**Files we never commit** (enforced via `.gitignore`):

```
*.exe   *.dll   *.so
datadrivenlibs/
DDC_WINDOWS_Converters/
DDC_LINUX_Converters/
RvtExporter*   IfcExporter*   DwgExporter*   DgnExporter*
```

## Where NEXUS expects the converters

NEXUS modules look for the converter binaries at this default path on Windows:

```
C:\Converters\datadrivenlibs\
├── RvtExporter.exe   ← Revit 2015–2026
├── IfcExporter.exe   ← IFC 2x3 / 4 / 4.1 / 4.3
├── DwgExporter.exe   ← AutoCAD .dwg
└── DgnExporter.exe   ← MicroStation .dgn
```

On Linux, the equivalent path is `/opt/datadrivenlibs/` with the same filenames (no `.exe` suffix).

You can override the search path via the env var:

```
NEXUS_DDC_CONVERTERS_DIR=C:\my\path\to\converters
```

## Install steps

1. Visit **https://datadrivenconstruction.io/index.php/convertors/** (or **https://cadbimconverter.com**).
2. Download the converter pack matching your OS and Revit/IFC versions.
3. Unzip into the directory above. Verify the four `.exe` (or Linux equivalent) files are present.
4. (Windows only) Whitelist the folder in Windows Defender if real-time scanning interferes with batch conversion runs.
5. Restart the NEXUS backend so the converter-discovery service re-scans the path.

## Verifying the install

After install:

```bash
# Backend health endpoint reports converter availability per format.
curl http://localhost:8000/api/v1/admin/converters/status

# Expected JSON: {"rvt": "ok", "ifc": "ok", "dwg": "ok", "dgn": "ok"}
```

If any format is reported `"missing"`, the corresponding takeoff/QA flow will return HTTP 503 with an explanatory message and a link back to this document.

## License notes

- DDC converter binaries are governed by their **own license** (not AGPL-3.0). Read the EULA before redistribution.
- The DWG/DGN paths internally use Open Design Alliance (ODA) libraries; ODA's pass-through terms forbid most redistribution scenarios — assume you cannot ship these binaries with derivative products.
- NEXUS calls the converters as a separate process; their license does not contaminate NEXUS's AGPL-3.0 codebase under typical interpretations of the GNU FAQ on aggregating non-free programs at the OS level. Consult counsel for your specific deployment.

## What if a user can't install converters?

NEXUS still works. The fallbacks per format:

- **IFC** — `ifcopenshell` (Apache-2.0) is bundled as a Python dependency. Slower than DDC's native exporter but covers the IFC path entirely without the closed-source binary.
- **PDF** — `pdfplumber` + `tabula-py` handle PDF takeoff and PDF→Excel without DDC.
- **DWG / DGN / RVT** — no open-source alternative covers these; the relevant takeoff endpoints will return HTTP 503 and the UI shows an "Install converters" CTA pointing to this document.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `503 converters not found` for any format | Default path not present and `NEXUS_DDC_CONVERTERS_DIR` not set | Install per steps above, or set env var |
| Conversion times out after 300s | Large file (>500 MB) | Bump `NEXUS_DDC_CONVERTER_TIMEOUT_SECONDS` (default 300) |
| `Access denied` on Windows | Defender quarantined the .exe | Whitelist the converters folder |
| RVT export fails with "Revit version unsupported" | DDC pack predates your Revit version | Re-download latest pack from `datadrivenconstruction.io` |
