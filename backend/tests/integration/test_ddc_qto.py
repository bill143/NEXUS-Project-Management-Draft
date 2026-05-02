"""Tests for the ddc_qto grouping + aggregation service.

Pure-function tests (no DB fixture needed). Covers:
* group_and_aggregate happy path with multiple group keys + sum columns
* count-by-group
* numeric coercion of stringy values like "12.5" or "1,234.5"
* missing quantity columns default to 0
* where filter narrows input
* batch_summarize per-file + combined roll-up
* group_by validation
"""

from __future__ import annotations

import pytest

from app.modules.ddc_qto.service import (
    _coerce_number,
    batch_summarize,
    group_and_aggregate,
)


# ── _coerce_number ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 0.0),
        ("", 0.0),
        ("   ", 0.0),
        (12, 12.0),
        (12.5, 12.5),
        ("12.5", 12.5),
        ("1,234.5", 1234.5),
        ("12.5 m3", 12.5),
        ("12.5 m³", 12.5),
        ("not a number", 0.0),
        (True, 1.0),
        (False, 0.0),
        ("-7.25", -7.25),
    ],
)
def test_coerce_number(value, expected):
    assert _coerce_number(value) == expected


# ── group_and_aggregate ─────────────────────────────────────────────────────


def test_group_and_aggregate_single_key_volume_sum():
    elements = [
        {"Type": "Brick 200", "Volume": 10},
        {"Type": "Brick 200", "Volume": 5},
        {"Type": "Concrete 300", "Volume": 20},
    ]
    result = group_and_aggregate(
        elements, group_by=["Type"], sum_columns=["Volume"],
    )
    by_type = {r["Type"]: r for r in result}
    assert by_type["Brick 200"]["count"] == 2
    assert by_type["Brick 200"]["Volume"] == 15.0
    assert by_type["Concrete 300"]["count"] == 1
    assert by_type["Concrete 300"]["Volume"] == 20.0


def test_group_and_aggregate_multi_key_sorts_by_count_desc():
    elements = [
        {"Category": "OST_Walls", "Type": "A", "Volume": 1},
        {"Category": "OST_Walls", "Type": "A", "Volume": 1},
        {"Category": "OST_Walls", "Type": "A", "Volume": 1},
        {"Category": "OST_Walls", "Type": "B", "Volume": 5},
    ]
    result = group_and_aggregate(
        elements, group_by=["Category", "Type"], sum_columns=["Volume"],
    )
    # Type A has 3 elements, Type B has 1 — A first
    assert [r["Type"] for r in result] == ["A", "B"]
    assert result[0]["count"] == 3
    assert result[0]["Volume"] == 3.0


def test_group_and_aggregate_missing_quantity_treated_as_zero():
    elements = [
        {"Type": "X", "Volume": 10},
        {"Type": "X"},  # no Volume column at all
        {"Type": "X", "Volume": None},
        {"Type": "X", "Volume": ""},
    ]
    [result] = group_and_aggregate(elements, group_by=["Type"], sum_columns=["Volume"])
    assert result["count"] == 4
    assert result["Volume"] == 10.0


def test_group_and_aggregate_with_where_filter():
    elements = [
        {"Category": "OST_Walls", "Volume": 10},
        {"Category": "OST_Walls", "Volume": 5},
        {"Category": "OST_Doors", "Volume": 99},
    ]
    result = group_and_aggregate(
        elements,
        group_by=["Category"],
        sum_columns=["Volume"],
        where={"Category": "OST_Walls"},
    )
    assert len(result) == 1
    assert result[0]["Category"] == "OST_Walls"
    assert result[0]["Volume"] == 15.0


def test_group_and_aggregate_where_accepts_list_for_in_match():
    elements = [
        {"Cat": "A", "V": 1},
        {"Cat": "B", "V": 1},
        {"Cat": "C", "V": 1},
    ]
    result = group_and_aggregate(
        elements, group_by=["Cat"], sum_columns=["V"], where={"Cat": ["A", "B"]},
    )
    assert {r["Cat"] for r in result} == {"A", "B"}


def test_group_and_aggregate_default_sum_columns_volume_area_length():
    elements = [
        {"T": "X", "Volume": 10, "Area": 2, "Length": 5},
        {"T": "X", "Volume": 5, "Area": 1, "Length": 2.5},
    ]
    [result] = group_and_aggregate(elements, group_by=["T"])
    # default sum_columns = Volume, Area, Length
    assert result["Volume"] == 15.0
    assert result["Area"] == 3.0
    assert result["Length"] == 7.5


def test_group_and_aggregate_empty_group_by_raises():
    with pytest.raises(ValueError, match="group_by"):
        group_and_aggregate([], group_by=[])


def test_group_and_aggregate_empty_input_returns_empty():
    assert group_and_aggregate([], group_by=["X"]) == []


# ── batch_summarize ─────────────────────────────────────────────────────────


def test_batch_summarize_per_file_and_combined_rollup():
    files = {
        "project_a.xlsx": [
            {"Category": "OST_Walls", "Volume": 10},
            {"Category": "OST_Walls", "Volume": 5},
        ],
        "project_b.xlsx": [
            {"Category": "OST_Walls", "Volume": 100},
            {"Category": "OST_Doors", "Volume": 1},
        ],
    }
    result = batch_summarize(
        files, group_by=["Category"], sum_columns=["Volume"],
    )
    assert set(result["per_file"].keys()) == {"project_a.xlsx", "project_b.xlsx"}
    a_walls = next(r for r in result["per_file"]["project_a.xlsx"] if r["Category"] == "OST_Walls")
    assert a_walls["Volume"] == 15.0
    combined_walls = next(
        r for r in result["combined"] if r["Category"] == "OST_Walls"
    )
    assert combined_walls["Volume"] == 115.0
    assert combined_walls["count"] == 3


def test_batch_summarize_empty_files_dict_returns_empty():
    result = batch_summarize({}, group_by=["X"])
    assert result == {"per_file": {}, "combined": []}
