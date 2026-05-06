# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Sweep B — DDC subprocess wrapper coverage.

Tests use mock ``subprocess.run`` calls so no real DDC binaries need to
be installed in CI. The wrapper's contract is:

    * Missing input file → :class:`ValueError` (caller-error).
    * Missing binary → :class:`DDCConverterMissingError` with install
      hint pointing at ``docs/CONVERTERS.md``.
    * Subprocess timeout → :class:`DDCConverterTimeoutError` carrying
      the ``timeout`` value used.
    * Non-zero exit → :class:`DDCConverterError` with the binary's
      stderr in the message.
    * Successful run → :class:`ConverterResult` with the computed
      output path and captured stdout/stderr.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.converters.ddc_subprocess import (
    DDCConverterError,
    DDCConverterMissingError,
    DDCConverterTimeoutError,
    convert_with_ddc,
)


@pytest.fixture
def fake_input_file(tmp_path: Path) -> Path:
    """Create a placeholder .rvt file so the wrapper passes its
    "input exists" precondition."""
    p = tmp_path / "demo.rvt"
    p.write_bytes(b"fake rvt content")
    return p


@pytest.fixture
def fake_ddc_root(tmp_path: Path) -> Path:
    """Stand up a fake DDC install with the expected RvtExporter.exe."""
    root = tmp_path / "ddc_install"
    root.mkdir()
    (root / "RvtExporter.exe").write_bytes(b"")  # presence-only stub
    return root


def test_missing_input_file_raises_value_error(tmp_path: Path) -> None:
    bogus = tmp_path / "does-not-exist.rvt"
    with pytest.raises(ValueError, match="does not exist"):
        convert_with_ddc(bogus)


def test_missing_binary_raises_with_install_hint(
    fake_input_file: Path, tmp_path: Path,
) -> None:
    empty_root = tmp_path / "no_ddc"
    empty_root.mkdir()
    with patch.dict("os.environ", {"OE_DDC_CONVERTER_ROOT": str(empty_root)}):
        with pytest.raises(DDCConverterMissingError) as excinfo:
            convert_with_ddc(fake_input_file)
    assert "RvtExporter.exe" in str(excinfo.value)
    assert "docs/CONVERTERS.md" in str(excinfo.value)


def test_unsupported_suffix_raises_clean_error(tmp_path: Path) -> None:
    weird = tmp_path / "demo.xyz"
    weird.write_bytes(b"")
    with pytest.raises(DDCConverterError, match="No DDC converter"):
        convert_with_ddc(weird)


def test_subprocess_timeout_raises_timeout_error(
    fake_input_file: Path, fake_ddc_root: Path,
) -> None:
    """A subprocess that exceeds the budget surfaces a typed timeout error
    carrying the budget so the JobRun row can record it."""
    with patch.dict(
        "os.environ", {"OE_DDC_CONVERTER_ROOT": str(fake_ddc_root)},
    ), patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="RvtExporter.exe", timeout=2.0),
    ):
        with pytest.raises(DDCConverterTimeoutError) as excinfo:
            convert_with_ddc(fake_input_file, timeout_s=2.0)
    assert excinfo.value.timeout == 2.0
    assert "2.0" in str(excinfo.value)


def test_nonzero_exit_raises_with_stderr(
    fake_input_file: Path, fake_ddc_root: Path,
) -> None:
    fake_completed = MagicMock(
        returncode=2,
        stdout=b"",
        stderr=b"FATAL: license check failed",
    )
    with patch.dict(
        "os.environ", {"OE_DDC_CONVERTER_ROOT": str(fake_ddc_root)},
    ), patch("subprocess.run", return_value=fake_completed):
        with pytest.raises(DDCConverterError) as excinfo:
            convert_with_ddc(fake_input_file)
    assert "exit" in str(excinfo.value).lower()
    assert "license check failed" in str(excinfo.value)


def test_successful_run_returns_result_with_output_path(
    fake_input_file: Path, fake_ddc_root: Path,
) -> None:
    fake_completed = MagicMock(
        returncode=0,
        stdout=b"converted demo.rvt -> demo.xlsx\n",
        stderr=b"",
    )
    with patch.dict(
        "os.environ", {"OE_DDC_CONVERTER_ROOT": str(fake_ddc_root)},
    ), patch("subprocess.run", return_value=fake_completed):
        result = convert_with_ddc(fake_input_file)

    assert result.output_path.suffix == ".xlsx"
    assert result.output_path.stem == fake_input_file.stem
    assert "RvtExporter.exe" in result.binary.name
    assert result.duration_s >= 0
    assert "demo.xlsx" in result.stdout
    assert result.stderr == ""
