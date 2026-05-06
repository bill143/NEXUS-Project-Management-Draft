# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""DDC binary-converter wrappers — Sweep B Decision 4.

Wraps the four DDC command-line converters (``RvtExporter.exe``,
``IfcExporter.exe``, ``DwgExporter.exe``, ``DgnExporter.exe``) so
LangGraph nodes and Celery tasks can invoke them without each one
re-implementing path-resolution, timeout handling, and error reporting.

Per Decision 2 of the prior sweep, the binaries themselves are NOT
bundled with NEXUS — they remain DDC-licensed. The wrapper expects
operators to install them under ``C:\\Converters\\datadrivenlibs\\`` (the
DDC default) or set ``OE_DDC_CONVERTER_ROOT`` to override.
"""

from app.core.converters.ddc_subprocess import (
    DDCConverterError,
    DDCConverterMissingError,
    DDCConverterTimeoutError,
    convert_with_ddc,
)

__all__ = [
    "DDCConverterError",
    "DDCConverterMissingError",
    "DDCConverterTimeoutError",
    "convert_with_ddc",
]
