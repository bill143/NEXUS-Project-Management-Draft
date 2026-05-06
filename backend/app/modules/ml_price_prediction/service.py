"""Business logic for ml_price_prediction.

V1.0 ports DDC's notebook-based sklearn regression as-is:

* Training: caller provides rows (each row = one historical project) with
  ``feature_columns`` + ``target_column``. We fit either ``LinearRegression``
  or ``RandomForestRegressor`` (default), serialise via ``joblib``, and
  register the model.
* Prediction: caller provides a feature dict for a new project; we load the
  model artefact, predict, and persist a ``Prediction`` row.

sklearn / pandas / numpy are imported **lazily** inside each method so the
module imports cleanly even when the [analytics] extra is not installed
(e.g. minimal test runs).
"""

import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ml_price_prediction.models import Prediction, TrainedModel
from app.modules.ml_price_prediction.repository import (
    PredictionRepository,
    TrainedModelRepository,
)
from app.modules.ml_price_prediction.schemas import PredictRequest, TrainRequest

_ARTIFACT_DIR = Path("data/ml_models")


def _ensure_dir() -> None:
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _build_estimator(algorithm: str):  # noqa: ANN202
    """Return a fresh sklearn estimator for the given algorithm name.

    Lazy-imports sklearn so the module is importable even without the
    ``[analytics]`` optional dependency installed.
    """
    if algorithm == "LinearRegression":
        from sklearn.linear_model import LinearRegression

        return LinearRegression()
    if algorithm == "RandomForestRegressor":
        from sklearn.ensemble import RandomForestRegressor

        return RandomForestRegressor(n_estimators=50, random_state=42)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported algorithm: {algorithm}",
    )


class ModelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.models = TrainedModelRepository(session)
        self.predictions = PredictionRepository(session)

    async def train(self, req: TrainRequest) -> TrainedModel:
        try:
            import joblib
            import pandas as pd
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Training requires the [analytics] extras "
                    "(scikit-learn, pandas, joblib). Install via: "
                    "pip install 'nexus[analytics]'"
                ),
            ) from e

        df = pd.DataFrame(req.rows)
        missing_features = [c for c in req.feature_columns if c not in df.columns]
        if missing_features:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing feature columns: {missing_features}",
            )
        if req.target_column not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing target column: {req.target_column}",
            )

        X = df[req.feature_columns].fillna(0).values
        y = df[req.target_column].fillna(0).values

        estimator = _build_estimator(req.algorithm)
        estimator.fit(X, y)
        try:
            train_score = float(estimator.score(X, y))
        except (ValueError, TypeError):
            train_score = 0.0

        existing = await self.models.get_by_name_version(req.name, req.version)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model {req.name}@{req.version} already exists",
            )

        model = TrainedModel(
            name=req.name,
            version=req.version,
            algorithm=req.algorithm,
            feature_columns=list(req.feature_columns),
            target_column=req.target_column,
            sample_size=int(len(df)),
            metrics={"train_r2": train_score},
        )
        await self.models.create(model)
        await self.session.flush()

        _ensure_dir()
        artifact = _ARTIFACT_DIR / f"{model.id}.joblib"
        joblib.dump(estimator, artifact)
        model.artifact_path = str(artifact)
        await self.session.flush()
        return model

    async def predict(self, req: PredictRequest) -> Prediction:
        model = await self.models.get(req.model_id)
        if model is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
        if not model.artifact_path or not Path(model.artifact_path).exists():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Model artefact missing on disk",
            )

        try:
            import joblib
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="joblib not installed (install [analytics] extras)",
            ) from e

        estimator = joblib.load(model.artifact_path)
        feature_vector = [
            float(req.features.get(col, 0) or 0) for col in model.feature_columns
        ]
        try:
            raw = estimator.predict([feature_vector])[0]
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prediction failed: {e}",
            ) from e

        prediction = Prediction(
            model_id=model.id,
            project_id=req.project_id,
            features=req.features,
            predicted_price=Decimal(str(round(float(raw), 4))),
            confidence=None,
        )
        return await self.predictions.create(prediction)

    async def list_models(self) -> list[TrainedModel]:
        return await self.models.list_all()

    async def get_model(self, model_id: uuid.UUID) -> TrainedModel:
        model = await self.models.get(model_id)
        if model is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
        return model
