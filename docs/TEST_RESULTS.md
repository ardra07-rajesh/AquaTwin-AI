# AquaTwin AI v12 verification record

Verification performed in the package build environment on 5 November 2026.

## Automated checks

| Check | Result |
|---|---|
| `python -m pytest -q` | **31 passed** |
| `python -m compileall -q app.py agriculture database ml optimization economics data_engine ui tests` | **Passed** |
| Bundled ML artifact deserialization | **Passed** |
| Bundled ML one-row prediction smoke test | **Passed** |
| Rebuild model from included dataset using the current Python environment | **Passed** |
| Reload rebuilt model and repeat prediction smoke test | **Passed** |
| Six-zone planning calculation and allocation conservation | **Passed** through planner tests |
| 3D farm figure and planned-water Sankey | **Passed** through visualization tests |
| Dashboard allocation treemap and coverage gauge creation/JSON serialization | **Passed** |
| SQLite configuration, plan, actual irrigation and weather persistence | **Passed** through persistence tests |
| No-stock-photography active UI check | **Passed** — unused legacy image files were removed and asset compatibility constants are empty |

### ML artifact verification environment

- Python: 3.13.5
- scikit-learn: 1.8.0
- Joblib: 1.5.3
- Model type: `Pipeline` containing `HistGradientBoostingRegressor`
- Training rows: 2,400
- Hold-out rows: 600
- Training data: `data/raw/legacy_irrigation_dataset.csv` (synthetic)
- Field validation: not performed

The training/evaluation run uses a fixed 80/20 split with `random_state=42`. Its metrics characterize fit to the generated dataset only. Retraining writes model runtime and dataset provenance to `models/model_metadata.json`.

## UI/runtime checks not completed

- A browser-based Streamlit startup and click-through test was **not run** because Streamlit is not installed in the package build environment. Installing it was attempted, but the package index could not be reached due DNS/network unavailability.
- A live Open-Meteo request was **not run** from this environment. The application retains request timeouts, error handling, caching and manual rainfall fallback.
- Hardware, pump-curve, sensor and field agronomy validation were **not performed**. No physical monitoring or control integration is included.

## Target-machine acceptance checklist

1. In the project folder, run `python -m pip install -r requirements.txt` in the same Python environment used to launch Streamlit.
2. Run `python -m streamlit run app.py` and visit all eight workspace sections.
3. On Crop Intelligence, confirm the model status says loaded and smoke-tested. If it does not, inspect the exact exception and use the explicit rebuild action only if appropriate.
4. Confirm the dashboard's 3D farm geometry, demand-coverage gauge, allocation treemap and zone cards match the active configuration and calculated plan.
5. Generate a plan and shortage scenario; verify Farm Twin, Sankey, shortage comparison and saved plan values remain consistent.
6. Rotate and zoom the 3D farm scene; inspect each zone.
7. Fetch Open-Meteo data using actual farm coordinates, then test manual fallback with network unavailable.
8. Save a plan, enter an actual irrigation record, restart, and verify planned and actual values remain separate.
9. Exercise CSV and JSON exports for plans, actual irrigation and weather records.
10. Compare nominal pump estimates with the installed pump's curve and measured electricity before operational use.

## Interpretation

This release improves interface hierarchy and chart selection but does not change the underlying agronomic limitations: soil values are manual, crop demand is estimated, weather is forecast data, water allocation is planned, pump energy is nominally estimated, and the ML dataset is synthetic. The 3D farm is schematic geometry generated from the configured zones; it is not an aerial image, surveyed GIS map, sensor feed or evidence of physical irrigation.
