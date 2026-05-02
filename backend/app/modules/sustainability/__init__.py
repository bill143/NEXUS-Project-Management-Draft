"""Sustainability / CO₂ module — embodied-carbon calculation aligned with GSA P100 + Buy Clean Act.

Ported from DDC ``CO2_calculating-the-embodied-carbon`` (notebook) and rebuilt
as a proper service module. Multiplies element-group volumes (or masses) by
emission factors from a curated EPD (Environmental Product Declaration)
database to produce per-project, per-phase, per-category embodied-carbon
reports compatible with US federal Buy Clean Act category rollups.
"""


async def on_startup() -> None:
    """Module startup hook — register permissions and validation rules."""
    from app.modules.sustainability.permissions import register_sustainability_permissions
    from app.modules.sustainability.validators import register_sustainability_rules

    register_sustainability_permissions()
    register_sustainability_rules()
