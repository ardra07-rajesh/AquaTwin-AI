from pathlib import Path

from ml.model_runtime import load_model_artifact


def test_bundled_model_loads_and_passes_prediction_smoke_test():
    root = Path(__file__).resolve().parents[1]
    model, diagnostic = load_model_artifact(root / "models" / "legacy_water_model.joblib")
    assert model is not None, diagnostic
    assert callable(model.predict)
    assert diagnostic is None or isinstance(diagnostic, str)


def test_missing_model_returns_clear_diagnostic(tmp_path):
    model, diagnostic = load_model_artifact(tmp_path / "not-present.joblib")
    assert model is None
    assert diagnostic
    assert "not found" in diagnostic.lower()
