"""Tests for the ddc_profiling EDA helpers.

Skipped on minimal installs without [analytics] extras (pandas).
"""

from __future__ import annotations

import pytest

_HAS_PANDAS = True
try:  # pragma: no cover - import-only
    import numpy  # noqa: F401
    import pandas  # noqa: F401
except ImportError:
    _HAS_PANDAS = False


pytestmark = pytest.mark.skipif(
    not _HAS_PANDAS,
    reason="requires [analytics] extras (pandas, numpy)",
)


@pytest.fixture
def sample_rows():
    return [
        {"Category": "OST_Walls", "Volume": 12.5, "Mark": "W1"},
        {"Category": "OST_Walls", "Volume": 7.5, "Mark": "W2"},
        {"Category": "OST_Walls", "Volume": None, "Mark": ""},
        {"Category": "OST_Doors", "Volume": 0.5, "Mark": "D1"},
        {"Category": "OST_Doors", "Volume": 0.5, "Mark": "D2"},
    ]


def test_column_summary_reports_total_missing_unique(sample_rows):
    from app.modules.ddc_profiling.service import column_summary

    result = column_summary(sample_rows)
    by_col = {r["column"]: r for r in result}
    assert by_col["Category"]["total"] == 5
    assert by_col["Category"]["missing"] == 0
    assert by_col["Category"]["unique"] == 2
    assert by_col["Volume"]["missing"] == 1
    assert by_col["Mark"]["missing"] == 1  # empty string also counts


def test_column_summary_top_values(sample_rows):
    from app.modules.ddc_profiling.service import column_summary

    result = column_summary(sample_rows, top_n=3)
    by_col = {r["column"]: r for r in result}
    cat_top = {entry["value"]: entry["count"] for entry in by_col["Category"]["top"]}
    assert cat_top == {"OST_Walls": 3, "OST_Doors": 2}


def test_column_summary_empty_input_returns_empty():
    from app.modules.ddc_profiling.service import column_summary

    assert column_summary([]) == []


def test_histogram_bins_numeric_column(sample_rows):
    from app.modules.ddc_profiling.service import histogram_bins

    result = histogram_bins(sample_rows, column="Volume", bins=4)
    assert result["column"] == "Volume"
    assert len(result["bins"]) == 4
    total_count = sum(b["count"] for b in result["bins"])
    assert total_count == 4  # 4 numeric values (one None excluded)
    assert result["min"] == 0.5
    assert result["max"] == 12.5


def test_histogram_bins_missing_column_flag(sample_rows):
    from app.modules.ddc_profiling.service import histogram_bins

    result = histogram_bins(sample_rows, column="DoesNotExist")
    assert result["missing_column"] is True
    assert result["bins"] == []


def test_category_bar_data_top_n(sample_rows):
    from app.modules.ddc_profiling.service import category_bar_data

    result = category_bar_data(sample_rows, column="Category", top_n=10)
    labels = {entry["label"]: entry["count"] for entry in result["data"]}
    assert labels == {"OST_Walls": 3, "OST_Doors": 2}


def test_correlation_matrix_skips_non_numeric(sample_rows):
    from app.modules.ddc_profiling.service import correlation_matrix

    matrix = correlation_matrix(sample_rows)
    # Only Volume is numeric; trivial 1x1 matrix
    assert "Volume" in matrix
    assert "Category" not in matrix
    assert matrix["Volume"]["Volume"] == 1.0


def test_missing_value_map_sorted_by_pct_desc(sample_rows):
    from app.modules.ddc_profiling.service import missing_value_map

    items = missing_value_map(sample_rows)
    # Volume and Mark each have 1 missing of 5 → 20%; Category 0
    pcts = [r["missing_pct"] for r in items]
    assert pcts == sorted(pcts, reverse=True)
    by_col = {r["column"]: r for r in items}
    assert by_col["Volume"]["missing_pct"] == 20.0
    assert by_col["Category"]["missing_pct"] == 0.0
