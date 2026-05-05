"""NEXUS Precon module.

Implements the locked architectural decisions from
``00_BUILD_CONTRACT_LOCKED.md`` (dated 2026-05-03).

This module is a workflow-orchestration layer on top of OpenConstructionERP.
It owns five new tables (``oe_nexus_precon_*``) and never writes directly to
any other module's tables — all cross-module operations go through OCERP
service-layer APIs.
"""
