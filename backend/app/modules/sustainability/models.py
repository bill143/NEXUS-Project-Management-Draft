"""Sustainability / CO₂ ORM models.

Tables:
    oe_sustainability_epd          — emission-factor catalog (EPD entries).
    oe_sustainability_element_group — per-project element groups with volumes.
    oe_sustainability_report        — calculated carbon footprint per project.
"""

import uuid
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import GUID, Base


class EmissionFactor(Base):
    """An EPD entry (Environmental Product Declaration / emission factor).

    One row per ``(material, region, source)`` triple. Factors are stored as
    kg CO₂-eq per unit (typically per m³ for volumes, per kg for masses).
    """

    __tablename__ = "oe_sustainability_epd"

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    buy_clean_category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="m3")
    factor_kgco2e: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False, default="US")
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<EmissionFactor {self.code} {self.factor_kgco2e}{self.unit}>"


class ElementGroup(Base):
    """A group of project elements sharing a material/category, with summed volume."""

    __tablename__ = "oe_sustainability_element_group"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_category: Mapped[str] = mapped_column(String(64), nullable=False)
    epd_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="m3")
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    def __repr__(self) -> str:
        return f"<ElementGroup {self.name} {self.quantity}{self.unit}>"


class CarbonReport(Base):
    """A carbon-footprint snapshot computed for a project at a point in time."""

    __tablename__ = "oe_sustainability_report"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Embodied Carbon Report")
    total_kgco2e: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, default=Decimal(0))
    by_category: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    by_buy_clean_category: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
    methodology: Mapped[str] = mapped_column(
        String(64), nullable=False, default="GSA-P100-2023"
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<CarbonReport project={self.project_id} total={self.total_kgco2e}>"
