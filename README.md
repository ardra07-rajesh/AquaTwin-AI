# AquaTwin AI v12 — Smart Agriculture & Irrigation Decision Support

AquaTwin AI v12 refreshes the existing v10 Streamlit application. It preserves the original crop-demand estimation, weighted/proportional water allocation, Water Rescue scenarios, Open-Meteo weather integration, pump runtime/energy estimate, ML bundle and reports, while connecting these calculations to an interactive farm model and persistent operational records.

## Run locally

Python 3.10 or newer is recommended.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens in the browser at the local Streamlit URL printed by the command. It can run without an external weather service; weather-informed planning requires internet access.

## What changed in v12

| Area | Implemented behaviour |
|---|---|
| Farm Dashboard | Zone demand, planned allocation, unmet demand, urgency ranking, action notes and plan saving. |
| Farm Twin | Rotatable/zoomable Plotly 3D farm scene with crop beds/rows, reservoir, pump, main and branch pipelines, zone labels and plan-derived allocation overlays. Select a zone to inspect its calculated inputs and outputs. |
| Water distribution | Sankey flow map uses the same allocation litres as the planner. The route is explicitly a plan visualization, not proof of physical flow. |
| Soil cross-section | Estimated layer profile and calculated net irrigation depth from manual surface moisture and planned allocation. Depth values are schematic assumptions, not depth-sensor measurements. |
| Crop Intelligence | Preserves crop/stage demand calculations, hydroponic reservoir rules, pH/EC checks and the legacy ML model. Adds synthetic hold-out permutation feature importance and provenance disclosure. |
| Irrigation Planner | Editable/validated zone configuration, urgency-ranked sequence, pump-hour feasibility, energy/electricity/water-cost estimates, optional parallel-pump comparison and persistent plan snapshots. |
| Water Rescue | 10%, 20%, 30%, 50% and custom shortage scenarios; recalculated zone allocations, unmet demand and revised farm/water-route views. |
| Smart Operations | Current conditions and seven-day forecast through Open-Meteo, forecast timestamp, daily temperature/humidity/rain probability/wind, manual fallback, effective-rainfall assumptions and pump calculations. |
| Operations History | Append-only SQLite plan, shortage, configuration, weather and manual actual-irrigation records. A saved plan does not become completed irrigation automatically. |
| Exports | CSV and JSON exports for current plans, plan history and actual irrigation entries. |

## Architecture

- `app.py` — Streamlit navigation and user interaction.
- `agriculture/decision_engine.py` — crop demand, water allocation, schedules and pump estimates.
- `agriculture/planner.py` — validates zone configuration and orchestrates crop demand, selected rainfall credit and allocation.
- `agriculture/farm_visualization.py` — 3D farm scene, water Sankey and estimated soil-profile figures.
- `database/db.py` — SQLAlchemy/SQLite models and persistence helpers.
- `ml/model_runtime.py` — model deserialization, one-row prediction smoke test and explicit load diagnostics.
- `ml/train.py` — repeatable environment-local retraining/evaluation from the bundled synthetic dataset.
- `models/legacy_water_model.joblib`, `models/metrics.json`, `models/model_metadata.json` — retained legacy model, synthetic hold-out results and provenance/compatibility metadata.
- `data/raw/legacy_irrigation_dataset.csv` — synthetic model training data; it is not field data.
- `ui/styles.py` and `ui/dashboard_figures.py` — hybrid premium-natural/command-centre theme and dashboard figures built from current plan outputs. The active interface uses calculation-driven Plotly views, not stock farm photographs.

The SQLite database is created at `aquatwin.db` in the project directory. `database.db.init_db()` uses additive `create_all` table initialization: existing v10 tables are retained and missing application tables are created. Back up the database file before replacing project versions or making manual schema changes.

## Data provenance and calculation boundaries

- **Manual input:** soil moisture, crop stage, cultivated area, reservoir level/capacity, pump flow/power, electricity tariff, farm coordinates and manually entered actual delivery records.
- **External forecast:** Open-Meteo current and daily weather-model data. It is regional forecast output, not a farm rain-gauge or weather-station measurement. The last successful fetch is timestamped and stored.
- **Estimated values:** crop water demand, urgency scores, effective-rainfall credit, depth profile, root-zone layer gradient, pump runtime, electricity use and cost.
- **Planned values:** zone water allocation, sequence and pipeline/Sankey flows. A plan is not a record that water has been delivered.
- **Synthetic data:** the legacy ML training dataset is synthetic. Its test metrics and permutation importance only describe performance on a synthetic hold-out sample and do not establish field accuracy.
- **Not connected:** physical soil probes, depth sensors, rain gauges, flow meters, electricity meters, pump control hardware, automated valves, leak detection and automatic irrigation are not implemented.

The soil-depth illustration uses a simple decreasing layer gradient from the entered surface-moisture value; it is a visual estimate, not a calibrated soil-water transport model. Effective rainfall is a simplified selected-day credit: forecast precipitation is reduced by the entered effective fraction and forecast probability, applied only to soil zones and capped at estimated zone demand. Historical observed rainfall is not ingested into this calculation, avoiding double counting of an unprovided observed rainfall series.

Pump runtime uses allocated litres divided by operator-entered nominal flow. Energy uses rated kW × estimated runtime. Parallel pump estimates add the entered flow and rated power and are valid only if the actual hydraulic arrangement allows parallel operation. They are not measured pump curves or electrical readings.

## Tests and verification

```bash
python -m pytest -q
```

The v12 build verification record is in [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md). The automated suite covers the v10 decision engine behaviours, allocation conservation, input validation, rainfall-credit boundaries, pump estimates, visual object generation, Sankey planned-litre values and SQLite configuration/plan/actual/weather persistence.

The build environment did not have Streamlit installed and could not reach the package index, so a browser-based app startup and live Open-Meteo request were not claimed as tested. Install the dependencies and complete the target-machine acceptance checklist before using the prototype in field operations.

## Known limitations

AquaTwin AI is decision-support software, not an autonomous irrigation controller or a field-validated agronomic prescription. Crop coefficients, moisture thresholds, urgency weights, hydroponic top-up heuristics, soil depth gradients and effective rainfall fractions require local calibration. Weather forecast quality depends on model coverage and forecast horizon. Rated-power pump estimates can differ from measured electricity and actual delivery due to pump curves, head, pressure, wear and pipe losses. No water savings, yield improvements or financial benefits are claimed without a measured baseline and independently recorded outcomes.


## v12 visual and ML reliability updates

- The Farm Dashboard now prioritizes the calculation-driven 3D farm twin, a demand-coverage gauge, an allocation treemap, and zone inspection cards instead of a generic grouped bar chart.
- Water Rescue and Cost & Performance use zone-level dot/dumbbell comparisons in place of grouped bars. The weather rainfall chart remains a column chart because daily precipitation is a quantity-by-day series.
- The unused legacy greenhouse/leaf/lettuce/sidebar photographs were removed. No stock image is used to imply a camera feed, plant observation, or real farm condition.
- ML loading is validated with a one-row prediction. Failures show the exact exception rather than silently returning `None`. Crop Intelligence includes runtime versions and a user-triggered model rebuild using the included synthetic dataset.
- Rebuilt model artifacts write exact training runtime, dataset hash and hold-out row counts to `models/model_metadata.json`. The original retained legacy artifact's training runtime was not embedded; its known limitation remains documented.
- The theme uses local CSS with system-font fallbacks. Google Fonts are optional enhancements; the application remains usable if they cannot be fetched.


## ML model troubleshooting

Crop Intelligence now loads the model and runs a one-row prediction smoke test at startup. If it fails, the page shows the concrete exception, resolved artifact path and runtime versions instead of hiding the error. Confirm that you installed dependencies and started Streamlit with the same interpreter (`python -m pip ...` and `python -m streamlit run app.py`). If the artifact is incompatible with the local environment, use **Rebuild model for this Python environment** in Crop Intelligence. This retrains the pipeline from the bundled synthetic CSV, overwrites the local artifact and writes new runtime/data provenance to `models/model_metadata.json`. Retraining does not turn synthetic data into field validation.
