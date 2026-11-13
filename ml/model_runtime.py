"""Safe, diagnosable loading and smoke-testing for the bundled ML artifact."""
from __future__ import annotations

import warnings
import math
from pathlib import Path

import pandas as pd
import joblib


def load_model_artifact(model_path: str | Path):
    """Return ``(model, diagnostic)`` after deserializing and predicting once.

    A diagnostic is returned for both failures and compatibility warnings; it is
    never silently discarded. The smoke-test uses the exact input column names
    expected by the shipped model pipeline.
    """
    path = Path(model_path)
    if not path.is_file():
        return None, f"Model file was not found at: {path.resolve()}"

    probe = pd.DataFrame([{
        "crop": "Rice",
        "soil_moisture_percent": 34.0,
        "temperature_c": 29.0,
        "humidity_percent": 55.0,
        "light_hours": 7.0,
    }])

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = joblib.load(path)
            if not callable(getattr(model, "predict", None)):
                raise TypeError("Loaded artifact does not expose a callable predict() method.")
            prediction = model.predict(probe)
            if len(prediction) != 1 or not math.isfinite(float(prediction[0])):
                raise ValueError("Model smoke-test returned an empty or non-finite prediction.")
        warning_text = " | ".join(
            f"{item.category.__name__}: {item.message}" for item in caught
        )
        return model, warning_text or None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
