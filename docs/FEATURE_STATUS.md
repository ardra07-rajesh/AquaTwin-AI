# AquaTwin AI v12 feature status

## Implemented in the application
- Retained multi-zone farm dashboard and daily zone-demand/allocation calculations.
- Crop-profile estimates and optional legacy ML estimate for the existing supported crop labels.
- Soil-moisture diagnostics, hydroponic reservoir/pH/EC checks.
- Priority-protection progressive filling and proportional sharing; demand caps and supply conservation are tested.
- Rotatable Plotly 3D farm view showing crop beds/rows, reservoir, pump, main pipeline, zone branches and allocation/urgency labels.
- Zone inspection panel with demand, allocation, unmet demand, urgency and order.
- Plan-derived Sankey water distribution visualization.
- Soil profile schematic clearly labelled as estimated from a surface input, not depth sensors.
- Weather forecast fetch for current conditions and seven daily records via Open-Meteo, forecast timestamp, caching, error handling and manual rainfall fallback.
- Selected-day effective-rainfall credit discounted by forecast probability and editable effective fraction, limited to soil zones and capped at demand.
- Irrigation schedule sorted by urgency; nominal pump runtime, energy, electricity cost, water-cost assumption and operating-window feasibility.
- Optional two-pump parallel flow/power comparison with a hydraulic-assumption warning.
- Water shortage scenarios at 10%, 20%, 30%, 50% and custom reductions; each recalculates allocations and visualizations.
- SQLite persistence for farm/zone configuration snapshots, plans, shortage scenarios, weather fetches and manually entered actual irrigation records.
- Historical planned-versus-actual comparison and CSV/JSON exports.
- Retained v10 ML bundle, model metrics and synthetic-data provenance disclosure; hold-out permutation feature importance is calculated for the synthetic dataset.
- ML load validation runs a one-row prediction and exposes the exact exception or compatibility warning. Crop Intelligence provides a user-triggered rebuild from the bundled synthetic CSV.
- Hybrid premium-natural/command-centre theme, dashboard zone cards, a demand-coverage gauge and allocation treemap; shortage/performance comparisons use dot plots instead of grouped bars.
- Unused legacy farm/leaf photography has been removed; the active UI contains no false photo, camera-feed or sensor imagery.

## Partially implemented / estimated
- Forecast is public weather-model output, not a local weather-station measurement.
- Rainfall effectiveness uses a simplified confidence × effective-fraction estimate; runoff, infiltration and crop-stage-specific rainfall response are not physically modelled.
- 3D farm dimensions/layout are illustrative schematic geometry; crop markers are visual representations of configured zones.
- Pipeline/Sankey values show planned allocations, not real flow.
- Soil depth distribution is an assumed visual gradient derived from one manually entered surface moisture input, not a depth-wise soil model.
- Pump runtime/energy/cost use operator-entered nominal flow and rated kW; no meter or pump curve is available.
- Historical actual-irrigation values are manual operator records, not automatically collected sensor records.
- ML hold-out scores and feature importance are derived from synthetic demonstration data only.

## Not implemented / hardware-dependent
- Physical soil-moisture, depth, rain-gauge, flow-meter, pH, EC or electricity-meter integration.
- Pump control, automated valve actuation, leak detection and pump fault diagnosis.
- Measured water savings, yield impact, crop quality improvement or independently verified operating-cost reductions.
- GIS boundary digitization and georeferenced zone editing.
- Field validation of crop coefficients, irrigation efficiency, soil/hydroponic rules or allocation priority weights.

Do not describe estimates as measurements, planned delivery as completed irrigation, or synthetic-model performance as field accuracy.
