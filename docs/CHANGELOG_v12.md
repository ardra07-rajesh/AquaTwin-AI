# AquaTwin AI v12 — visual and ML reliability refresh

## Interface
- Added a hybrid premium-natural/command-centre theme: forest-green navigation, sage/off-white content surfaces, refined typography, responsive spacing and consistent panels.
- Rebuilt the Farm Dashboard around the configured 3D farm view, allocated-demand gauge, allocation treemap and zone inspection cards.
- Replaced grouped bar comparisons in Water Rescue and Cost & Performance with zone-level dot/dumbbell comparisons.
- Retained the daily rainfall column visualization because each column represents a forecast day's precipitation quantity.
- Removed unused legacy greenhouse/leaf/sidebar photographs. No photo, camera feed, or sensor display is fabricated.

## ML reliability
- Added `ml/model_runtime.py` to deserialize the bundled model and verify it with an actual one-row prediction.
- Replaced silent `except Exception: return None` behavior with an explicit diagnostic shown in Crop Intelligence.
- Added runtime version/path information and metadata inspection.
- Added an explicit model rebuild action using the bundled synthetic dataset. Retraining records Python, scikit-learn, Joblib, dataset hash and hold-out row counts.
- Preserved the crop-profile fallback and kept synthetic-data and non-field-validation caveats visible.

## Preserved v11 functionality
- All eight workspace sections remain: Farm Dashboard, Farm Twin, Crop Intelligence, Smart Irrigation Planner, Water Rescue, Smart Operations, Operations History, and Cost & Performance.
- Calculation services, weather API integration and fallback, pump estimates, SQLite history, manual actual-irrigation entry, exports, 3D farm, Sankey distribution and soil profile remain in place.

## Verification
- 31 automated tests passed.
- Python compilation passed.
- Bundled model deserialization and prediction smoke test passed in the build environment.
- Rebuild from the bundled synthetic data and reload smoke test passed.
- Dashboard figures and the 3D farm/Sankey/soil figures serialized successfully.
- Browser-based Streamlit run and live weather request could not be tested in this environment because Streamlit was unavailable and package-index DNS/network access failed. See `TEST_RESULTS.md`.
