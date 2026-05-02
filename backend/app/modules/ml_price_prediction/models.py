"""ML Price-Prediction ORM models.

Tables:
    oe_ml_price_prediction_model      — registered trained models.
    oe_ml_price_prediction_prediction — cached prediction results.
"""

import uuid
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import GUID, Base


class TrainedModel(Base):
    """A trained sklearn regression model registered with the system."""

    __tablename__ = "oe_ml_price_prediction_model"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False, default="LinearRegression")
    feature_columns: Mapped[list] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=list, server_default="[]"
    )
    target_column: Mapped[str] = mapped_column(String(64), nullable=False, default="price")
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    metrics: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=dict, server_default="{}"
    )
    sample_size: Mapped[int] = mapped_column(nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<TrainedModel {self.name} v{self.version} ({self.algorithm})>"


class Prediction(Base):
    """A cached prediction result."""

    __tablename__ = "oe_ml_price_prediction_prediction"

    model_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_ml_price_prediction_model.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    features: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=dict, server_default="{}"
    )
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)

    def __repr__(self) -> str:
        return f"<Prediction model={self.model_id} price={self.predicted_price}>"
