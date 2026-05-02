"""DDC data-profiling helpers — port of the Revit Data Analysis Streamlit App.

Extracts the Streamlit app's pandas-EDA logic (column stats, histograms,
bar-chart data, correlation matrix, missing-value heatmap) into a
stateless service module. The Streamlit-specific UI is dropped — NEXUS
serves the underlying numbers as JSON, the existing dashboards module
renders them.

Pandas is lazy-imported inside each function so this module imports
cleanly even on minimal installs without the [analytics] extras. The
endpoints return 503 with an install hint if pandas is missing.
"""


async def on_startup() -> None:
    from app.modules.ddc_profiling.permissions import register_ddc_profiling_permissions

    register_ddc_profiling_permissions()
