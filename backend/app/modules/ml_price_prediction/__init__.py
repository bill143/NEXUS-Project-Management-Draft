"""ML Price-Prediction module — federal bid forecasting.

V1.0 (this release): port DDC ``ML-Price-Prediction-Model`` sklearn regression
as-is. Train a model from CSV-shaped project data (one row per project,
columns = aggregated parameter values, target = project price), predict
prices for new project rows.

V1.1 (later): augment feature space with SAM.gov / USAspending columns
(awarded value, agency, NAICS, set-aside type, place of performance) for
true federal bid forecasting. Deliberately NOT in v1.0 per amendment 2.
"""


async def on_startup() -> None:
    """Module startup hook — register permissions."""
    from app.modules.ml_price_prediction.permissions import (
        register_ml_price_prediction_permissions,
    )

    register_ml_price_prediction_permissions()
