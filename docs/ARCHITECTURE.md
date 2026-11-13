# AquaTwin AI v12 architecture

```text
Streamlit application (app.py) · hybrid forest/sage UI theme
  |-- Farm Dashboard
  |-- Farm Twin (Plotly 3D + Sankey + soil profile)
  |-- Crop Intelligence
  |-- Smart Irrigation Planner
  |-- Water Rescue
  |-- Smart Operations / Open-Meteo
  |-- Operations History
  +-- Cost & Performance

Agriculture services
  |-- agriculture/planner.py
  |     |-- zone input validation
  |     |-- crop/ML demand orchestration
  |     |-- selected-day rainfall credit
  |     +-- zone priority / allocation orchestration
  |-- agriculture/decision_engine.py
  |     |-- crop heuristic
  |     |-- allocation strategies
  |     |-- pump schedule
  |     +-- pump runtime / energy estimates
  +-- agriculture/farm_visualization.py
        |-- 3D farm geometry and plan overlays
        |-- Sankey planned distribution
        +-- conceptual estimated soil profile

UI layer
  |-- ui/styles.py (responsive premium-natural / command-centre theme)
  +-- ui/dashboard_figures.py (coverage gauge + plan-derived allocation treemap)

Persistence: SQLAlchemy + local SQLite (aquatwin.db)
  |-- farms / zones (legacy tables)
  |-- simulation_runs (plans and shortages)
  |-- configuration_snapshots
  |-- actual_irrigation_records
  +-- weather_records

Model assets and runtime diagnostics
  |-- legacy_water_model.joblib
  |-- metrics.json + model_metadata.json
  |-- ml/model_runtime.py (deserialize + prediction smoke test)
  +-- synthetic legacy dataset
```

The application directly calls local domain services; it does not expose a hardware API or command pump equipment. SQLite initialization is additive (`Base.metadata.create_all`) so existing v10 tables remain present while additional tables are created. This first release is intended for one local operator, not concurrent multi-user or safety-critical operation.


The active interface does not use stock farm photography. Farm and distribution visuals are Plotly figures generated from the configured zones and current calculated plan.
