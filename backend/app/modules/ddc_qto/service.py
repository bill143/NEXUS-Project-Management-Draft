"""DDC QTO grouping + aggregation logic.

Pure-Python (no pandas dependency at the public surface) so this stays
importable in minimal-install scenarios. The internal implementation uses
``itertools.groupby`` after a sort, which is O(n log n) and adequate for
project sizes up to ~1M elements.

Public API:

* :func:`group_and_aggregate` — given elements + a grouping spec, return a
  list of group summaries (one per distinct group key). Handles optional
  filters and arbitrary numeric ``sum_columns``.
* :func:`batch_summarize` — same operation across many element lists (one
  per file in DDC's "folder of Excel exports" pattern), returning per-file
  results plus a combined-across-files roll-up.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _coerce_number(value: Any) -> float:
    """Best-effort numeric coercion. Strings like '1,234.5' and '12 m³' work.

    Empty / None / un-parseable values return 0.0 (matches DDC behavior —
    missing quantities are treated as zero rather than crashing the rollup).
    """
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    s = s.replace(",", "").replace(" ", "")
    # Strip a trailing unit like "m3", "m²", "m³", "kg" — DDC exports occasionally include them
    digits = []
    seen_dot = False
    for ch in s:
        if ch.isdigit():
            digits.append(ch)
        elif ch == "." and not seen_dot:
            digits.append(ch)
            seen_dot = True
        elif ch == "-" and not digits:
            digits.append(ch)
        else:
            break
    if not digits or digits == ["-"]:
        return 0.0
    try:
        return float("".join(digits))
    except ValueError:
        return 0.0


def _matches_filter(element: dict[str, Any], where: dict[str, Any] | None) -> bool:
    if not where:
        return True
    for key, expected in where.items():
        actual = element.get(key)
        if isinstance(expected, list | tuple | set):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def group_and_aggregate(
    elements: list[dict[str, Any]],
    group_by: list[str],
    sum_columns: list[str] | None = None,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Group ``elements`` by ``group_by`` keys and aggregate.

    Args:
        elements: list of element dicts (one per Revit/IFC element)
        group_by: list of column names to group by, in priority order
        sum_columns: list of numeric columns to sum within each group.
            Defaults to ``["Volume", "Area", "Length"]`` — the canonical
            DDC quantity columns.
        where: optional pre-filter as a ``{column: value}`` or
            ``{column: [v1, v2, ...]}`` mapping.

    Returns:
        List of group summaries, each containing the group keys, a ``count``,
        and one entry per ``sum_columns`` element, sorted by ``count`` desc.

    Example:
        >>> elements = [
        ...     {"Category": "OST_Walls", "Type": "Brick 200", "Volume": 12.5},
        ...     {"Category": "OST_Walls", "Type": "Brick 200", "Volume": 7.5},
        ...     {"Category": "OST_Walls", "Type": "Concrete 300", "Volume": 30.0},
        ... ]
        >>> result = group_and_aggregate(
        ...     elements,
        ...     group_by=["Category", "Type"],
        ...     sum_columns=["Volume"],
        ... )
        >>> # [
        ... #   {"Category": "OST_Walls", "Type": "Concrete 300", "count": 1, "Volume": 30.0},
        ... #   {"Category": "OST_Walls", "Type": "Brick 200",    "count": 2, "Volume": 20.0},
        ... # ]
    """
    if not group_by:
        raise ValueError("group_by must contain at least one column")
    cols = sum_columns or ["Volume", "Area", "Length"]

    buckets: dict[tuple[Any, ...], dict[str, float | int]] = defaultdict(
        lambda: dict.fromkeys(["count", *cols], 0),
    )

    for elem in elements:
        if not _matches_filter(elem, where):
            continue
        key = tuple(elem.get(g) for g in group_by)
        bucket = buckets[key]
        bucket["count"] = int(bucket["count"]) + 1
        for c in cols:
            bucket[c] = float(bucket[c]) + _coerce_number(elem.get(c))

    results: list[dict[str, Any]] = []
    for key, bucket in buckets.items():
        row: dict[str, Any] = dict(zip(group_by, key, strict=False))
        row["count"] = int(bucket["count"])
        for c in cols:
            row[c] = round(float(bucket[c]), 6)
        results.append(row)

    results.sort(key=lambda r: (-int(r["count"]), tuple(str(r.get(g, "")) for g in group_by)))
    return results


def batch_summarize(
    file_elements: dict[str, list[dict[str, Any]]],
    group_by: list[str],
    sum_columns: list[str] | None = None,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run ``group_and_aggregate`` across many files and roll up.

    Args:
        file_elements: ``{filename: [element, ...]}`` — one entry per source
            Excel/JSON export, matching the Quick-QTO "folder of files" flow.
        group_by, sum_columns, where: forwarded to :func:`group_and_aggregate`.

    Returns:
        ``{
            "per_file": {filename: [group_summary, ...]},
            "combined": [group_summary, ...]   # rolled up across all files
        }``
    """
    cols = sum_columns or ["Volume", "Area", "Length"]
    per_file: dict[str, list[dict[str, Any]]] = {}
    combined: list[dict[str, Any]] = []
    for filename, elements in file_elements.items():
        per_file[filename] = group_and_aggregate(elements, group_by, cols, where)
        combined.extend(elements)
    return {
        "per_file": per_file,
        "combined": group_and_aggregate(combined, group_by, cols, where),
    }
