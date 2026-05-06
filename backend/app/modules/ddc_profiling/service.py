"""Pandas-backed profiling/EDA service.

Public API takes a list-of-dicts (one dict per row, like a CSV/Excel
import) and returns plain Python data structures suitable for JSON
serialisation. Pandas is imported lazily; if it isn't installed the
caller gets a clear error instead of a vague ImportError.

Functions:

* :func:`column_summary`       — per-column count / missing / unique / top values
* :func:`histogram_bins`       — numeric column → list of bin (edge, count) pairs
* :func:`category_bar_data`    — categorical column → top-N (label, count)
* :func:`correlation_matrix`   — square dict-of-dicts of pearson coefficients
* :func:`missing_value_map`    — per-column missing percentage
"""

from __future__ import annotations

from typing import Any


class AnalyticsExtrasMissing(RuntimeError):
    """Raised when pandas is needed but not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Profiling requires the [analytics] extras (pandas + numpy). "
            "Install via: pip install 'nexus[analytics]'",
        )


def _df(rows: list[dict[str, Any]]):
    try:
        import pandas as pd
    except ImportError as e:
        raise AnalyticsExtrasMissing() from e
    return pd.DataFrame(rows)


def column_summary(rows: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    """Per-column total, missing, missing_pct, unique, dtype, top-N values."""
    if not rows:
        return []
    df = _df(rows)
    out: list[dict[str, Any]] = []
    total = int(len(df))
    for col in df.columns:
        s = df[col]
        missing = int(s.isna().sum() + (s.astype("string") == "").sum())
        unique = int(s.nunique(dropna=True))
        top_vals = (
            s.dropna()
            .astype(str)
            .replace("", float("nan"))
            .dropna()
            .value_counts()
            .head(top_n)
            .to_dict()
        )
        out.append(
            {
                "column": col,
                "dtype": str(s.dtype),
                "total": total,
                "missing": missing,
                "missing_pct": round(missing / total * 100, 2) if total else 0.0,
                "unique": unique,
                "top": [{"value": k, "count": int(v)} for k, v in top_vals.items()],
            },
        )
    return out


def histogram_bins(
    rows: list[dict[str, Any]],
    column: str,
    bins: int = 10,
) -> dict[str, Any]:
    """Numeric column → list of (left_edge, right_edge, count) entries.

    Non-numeric entries in the column are dropped before binning.
    """
    df = _df(rows)
    if column not in df.columns:
        return {"column": column, "bins": [], "missing_column": True}
    try:
        import numpy as np
        import pandas as pd
    except ImportError as e:  # pragma: no cover
        raise AnalyticsExtrasMissing() from e

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return {"column": column, "bins": []}

    counts, edges = np.histogram(series.values, bins=bins)
    return {
        "column": column,
        "bins": [
            {
                "left": float(edges[i]),
                "right": float(edges[i + 1]),
                "count": int(counts[i]),
            }
            for i in range(len(counts))
        ],
        "min": float(series.min()),
        "max": float(series.max()),
        "mean": float(series.mean()),
    }


def category_bar_data(
    rows: list[dict[str, Any]],
    column: str,
    top_n: int = 10,
) -> dict[str, Any]:
    """Categorical column → top-N (label, count) entries."""
    df = _df(rows)
    if column not in df.columns:
        return {"column": column, "data": [], "missing_column": True}
    counts = df[column].astype("string").dropna().value_counts().head(top_n)
    return {
        "column": column,
        "data": [{"label": str(label), "count": int(c)} for label, c in counts.items()],
    }


def correlation_matrix(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Pearson correlation matrix across numeric columns only."""
    df = _df(rows)
    try:
        import pandas as pd
    except ImportError as e:  # pragma: no cover
        raise AnalyticsExtrasMissing() from e

    numeric_cols = [c for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().any()]
    if not numeric_cols:
        return {}
    coerced = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    corr = coerced.corr().fillna(0.0)
    return {
        c1: {c2: round(float(corr.loc[c1, c2]), 4) for c2 in corr.columns}
        for c1 in corr.index
    }


def missing_value_map(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-column missing percentage, sorted desc.

    Useful to drive a missing-value heatmap on the frontend.
    """
    if not rows:
        return []
    df = _df(rows)
    total = len(df)
    items: list[dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        missing = int(s.isna().sum() + (s.astype("string") == "").sum())
        items.append(
            {
                "column": col,
                "missing": missing,
                "missing_pct": round(missing / total * 100, 2) if total else 0.0,
            },
        )
    items.sort(key=lambda r: -r["missing_pct"])
    return items
