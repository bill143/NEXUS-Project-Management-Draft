# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Subprocess wrapper around the DDC binary converters.

Decision 4 of Sweep B: pipelines should accept either pre-converted
tabular data (``.xlsx`` / ``.csv``) or raw CAD/BIM files. When given a
raw file, the pipeline shells out to the matching DDC converter; when
given a tabular file, the wrapper is bypassed entirely.

The wrapper enforces three invariants the call sites rely on:

    1. Binary presence is verified BEFORE the subprocess call. If the
       converter is missing, the caller gets :class:`DDCConverterMissingError`
       with the exact path and a pointer at ``docs/CONVERTERS.md`` —
       not an opaque ``FileNotFoundError`` from the OS layer.
    2. Subprocess wall-clock is bounded. The default 300 s matches the
       Celery task hard-timeout in :mod:`app.core.jobs`; pipelines that
       run inside a request should pass a tighter value.
    3. ``stdout`` and ``stderr`` are captured (UTF-8 with replacement
       on bad bytes — DDC binaries on Windows emit cp1251 occasionally)
       so failures land on the JobRun row in a debuggable shape.

The wrapper does NOT bundle the binaries. Operators install them under
``C:\\Converters\\datadrivenlibs\\`` (DDC's default install path) or
override via ``OE_DDC_CONVERTER_ROOT``.
"""

from __future__ import annotations

import logging
import os
import subprocess  # noqa: S404 — wrapper purpose is to invoke an external binary
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# Default install location matches the path baked into the DDC docs.
# The wrapper resolves env override → arg → default in that order so
# CI can point at a stub without recompiling.
_DEFAULT_DDC_ROOT = r"C:\Converters\datadrivenlibs"

# Suffix → binary mapping. Keys are lowercase so callers don't have to
# normalise extensions before calling :func:`convert_with_ddc`.
_BINARY_BY_SUFFIX: dict[str, str] = {
    ".rvt": "RvtExporter.exe",
    ".ifc": "IfcExporter.exe",
    ".dwg": "DwgExporter.exe",
    ".dgn": "DgnExporter.exe",
}


class DDCConverterError(RuntimeError):
    """Base exception — the converter ran but did not produce a result.

    Subclassed by the more specific failure modes below. Catch the base
    in router code that wants to translate any converter problem into
    a single 5xx response shape.
    """


class DDCConverterMissingError(DDCConverterError):
    """The expected ``.exe`` was not found on disk.

    Distinguishes "operator forgot to install DDC" from "the install is
    there but the file is corrupt" — both are 500-class errors but the
    error message guides ops to a different fix.
    """


class DDCConverterTimeoutError(DDCConverterError):
    """The converter exceeded its wall-clock budget.

    Carries the ``timeout`` value used so the failing JobRun row can
    record exactly how long the wrapper waited before killing the child.
    """

    def __init__(self, message: str, *, timeout: float) -> None:
        super().__init__(message)
        self.timeout = timeout


@dataclass(frozen=True)
class ConverterResult:
    """Outcome of a successful converter run.

    Attributes:
        binary: Absolute path to the ``.exe`` that was invoked.
        output_path: Absolute path of the file the converter produced.
            DDC binaries write next to the input by convention, so the
            wrapper computes this rather than relying on the binary to
            print it.
        duration_s: Wall-clock seconds the subprocess took, rounded to
            millisecond granularity.
        stdout: UTF-8 decoded stdout (may be empty for silent runs).
        stderr: UTF-8 decoded stderr.
    """

    binary: Path
    output_path: Path
    duration_s: float
    stdout: str
    stderr: str


def _ddc_root() -> Path:
    """Resolve the DDC install root from env, falling back to the default."""
    return Path(os.environ.get("OE_DDC_CONVERTER_ROOT", _DEFAULT_DDC_ROOT))


def _binary_for(input_path: Path) -> Path:
    """Map an input path's suffix to its DDC binary path.

    Raises:
        DDCConverterError: The suffix has no DDC binary mapping.
    """
    suffix = input_path.suffix.lower()
    if suffix not in _BINARY_BY_SUFFIX:
        msg = (
            f"No DDC converter for suffix {suffix!r} "
            f"(supported: {sorted(_BINARY_BY_SUFFIX)})"
        )
        raise DDCConverterError(msg)
    return _ddc_root() / _BINARY_BY_SUFFIX[suffix]


def convert_with_ddc(
    input_path: str | os.PathLike[str],
    *,
    timeout_s: float = 300.0,
    extra_args: list[str] | None = None,
) -> ConverterResult:
    """Invoke the DDC binary that matches ``input_path``'s suffix.

    Args:
        input_path: A file the DDC binary should convert. Suffix is
            mapped to the binary; supported suffixes are ``.rvt``,
            ``.ifc``, ``.dwg``, ``.dgn``.
        timeout_s: Wall-clock budget for the subprocess. Defaults to
            300 s, the same hard limit Celery tasks have. Pipelines
            running inside an HTTP request should pass a tighter value.
        extra_args: Optional flags appended after the input path. The
            DDC binaries accept a position-only signature in normal
            use; this hook exists for the rare case (custom output
            directory) where extra flags are needed.

    Returns:
        :class:`ConverterResult` with the output path and captured
        stdout/stderr.

    Raises:
        DDCConverterMissingError: The ``.exe`` is not on disk.
        DDCConverterTimeoutError: Subprocess exceeded ``timeout_s``.
        DDCConverterError: Non-zero exit status, or unsupported suffix.
    """
    import time

    input_p = Path(input_path).resolve()
    if not input_p.exists():
        # Bubbled as a regular ValueError, not DDCConverterError, so
        # caller code can distinguish bad-input from missing-toolchain.
        msg = f"Input file does not exist: {input_p}"
        raise ValueError(msg)

    binary = _binary_for(input_p)
    if not binary.exists():
        msg = (
            f"DDC converter binary not found: {binary}. "
            "Install the DDC converters under "
            f"{_ddc_root()} or set OE_DDC_CONVERTER_ROOT. "
            "See docs/CONVERTERS.md for installation instructions."
        )
        raise DDCConverterMissingError(msg)

    cmd: list[str] = [str(binary), str(input_p)]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running DDC converter: %s", " ".join(cmd))
    start = time.perf_counter()
    try:
        completed = subprocess.run(  # noqa: S603 — args are validated paths and operator-controlled extras
            cmd,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        msg = (
            f"DDC converter timed out after {timeout_s}s "
            f"(input={input_p.name}, binary={binary.name})"
        )
        logger.error(msg)
        raise DDCConverterTimeoutError(msg, timeout=timeout_s) from exc

    duration_s = round(time.perf_counter() - start, 3)
    stdout = completed.stdout.decode("utf-8", errors="replace") if completed.stdout else ""
    stderr = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""

    if completed.returncode != 0:
        msg = (
            f"DDC converter exited with code {completed.returncode} "
            f"(input={input_p.name}, binary={binary.name}). "
            f"stderr: {stderr[:500]}"
        )
        logger.error(msg)
        raise DDCConverterError(msg)

    # DDC binaries emit ``<basename>.xlsx`` in the input directory by
    # convention. Compute the path so callers don't have to parse stdout.
    output_path = input_p.with_suffix(".xlsx")

    return ConverterResult(
        binary=binary,
        output_path=output_path,
        duration_s=duration_s,
        stdout=stdout,
        stderr=stderr,
    )
