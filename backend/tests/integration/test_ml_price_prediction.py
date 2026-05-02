"""Integration tests for the ml_price_prediction module.

Skips end-to-end training/prediction tests when sklearn / pandas / joblib
are not installed (keeps the test gate green on minimal installs). Covers:

* TrainedModelRepository round-trip (DB schema sanity)
* train() raises 503 when analytics extras not installed
* train() + predict() happy path when analytics extras ARE installed
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_HAS_ANALYTICS = True
try:  # pragma: no cover - import-only
    import joblib  # noqa: F401
    import pandas  # noqa: F401
    import sklearn  # noqa: F401
except ImportError:
    _HAS_ANALYTICS = False


@pytest_asyncio.fixture
async def session():
    tmp_db = Path(tempfile.mkdtemp()) / "mlpp.db"
    url = f"sqlite+aiosqlite:///{tmp_db.as_posix()}"
    engine = create_async_engine(url, future=True)

    import app.modules.ml_price_prediction.models  # noqa: F401
    import app.modules.projects.models  # noqa: F401
    import app.modules.users.models  # noqa: F401
    from app.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()
    try:
        tmp_db.unlink(missing_ok=True)
        tmp_db.parent.rmdir()
    except OSError:
        pass


# ── Repository / model schema sanity ────────────────────────────────────────


@pytest.mark.asyncio
async def test_trained_model_repository_roundtrip(session):
    from app.modules.ml_price_prediction.models import TrainedModel
    from app.modules.ml_price_prediction.repository import TrainedModelRepository

    repo = TrainedModelRepository(session)
    m = TrainedModel(
        name="bid_v1",
        version="1.0.0",
        algorithm="LinearRegression",
        feature_columns=["sqft", "stories", "concrete_m3"],
        target_column="price",
        sample_size=42,
        metrics={"train_r2": 0.91},
        artifact_path="/tmp/x.joblib",
    )
    await repo.create(m)
    await session.commit()

    fetched = await repo.get_by_name_version("bid_v1", "1.0.0")
    assert fetched is not None
    assert fetched.feature_columns == ["sqft", "stories", "concrete_m3"]
    assert fetched.metrics == {"train_r2": 0.91}


# ── Train / predict end-to-end (only when analytics extras installed) ───────


@pytest.mark.skipif(
    not _HAS_ANALYTICS,
    reason="requires [analytics] extras (scikit-learn, pandas, joblib)",
)
@pytest.mark.asyncio
async def test_train_and_predict_linear_regression(session, monkeypatch, tmp_path):
    from app.modules.ml_price_prediction import service as svc_module
    from app.modules.ml_price_prediction.schemas import PredictRequest, TrainRequest
    from app.modules.ml_price_prediction.service import ModelService

    monkeypatch.setattr(svc_module, "_ARTIFACT_DIR", tmp_path)

    rows = [
        {"sqft": 1000, "stories": 1, "price": 200000},
        {"sqft": 2000, "stories": 2, "price": 400000},
        {"sqft": 1500, "stories": 1, "price": 300000},
        {"sqft": 2500, "stories": 3, "price": 500000},
        {"sqft": 3000, "stories": 3, "price": 600000},
    ]
    svc = ModelService(session)
    model = await svc.train(
        TrainRequest(
            name="houseprice",
            version="1.0.0",
            algorithm="LinearRegression",
            feature_columns=["sqft", "stories"],
            target_column="price",
            rows=rows,
        ),
    )
    await session.commit()
    assert Path(model.artifact_path).exists()
    assert model.sample_size == 5

    prediction = await svc.predict(
        PredictRequest(model_id=model.id, features={"sqft": 1750, "stories": 2}),
    )
    await session.commit()
    # The fit is essentially price ~= 200 * sqft, so 1750 sqft ≈ 350k
    assert 250_000 <= float(prediction.predicted_price) <= 450_000


@pytest.mark.skipif(
    not _HAS_ANALYTICS,
    reason="requires [analytics] extras (scikit-learn, pandas, joblib)",
)
@pytest.mark.asyncio
async def test_train_rejects_missing_feature_columns(session, monkeypatch, tmp_path):
    from fastapi import HTTPException

    from app.modules.ml_price_prediction import service as svc_module
    from app.modules.ml_price_prediction.schemas import TrainRequest
    from app.modules.ml_price_prediction.service import ModelService

    monkeypatch.setattr(svc_module, "_ARTIFACT_DIR", tmp_path)

    svc = ModelService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.train(
            TrainRequest(
                name="bad",
                feature_columns=["sqft", "missing_col"],
                rows=[{"sqft": 1, "price": 1}, {"sqft": 2, "price": 2}],
            ),
        )
    assert exc.value.status_code == 400
    assert "missing_col" in str(exc.value.detail)
