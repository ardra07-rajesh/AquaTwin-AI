# AquaTwin AI methodology and data boundaries

## Soil-zone demand

The crop-profile estimator starts with a configured daily crop depth (mm/day), multiplies by growth-stage and bounded temperature, humidity and light factors, applies a soil-moisture adjustment and divides by irrigation efficiency. Since 1 mm over 1 m² equals 1 litre, the resulting depth is converted to litres using cultivated area.

The legacy ML path is retained for Rice, Cotton, Wheat and Other soil zones. It estimates a water-need depth from crop, soil moisture, temperature, humidity and light, then applies the existing growth-stage/moisture/efficiency conversions. The bundled dataset and its hold-out scores are synthetic.

## Hydroponic top-up

Hydroponic demand is a simplified reservoir-deficit heuristic based on plant count and fraction of reservoir capacity missing. It is not a nutrient-chemistry or crop-specific evapotranspiration model.

## Rainfall credit

For a selected forecast day or explicitly entered manual expectation, gross rainfall-equivalent litres are estimated as precipitation (mm) × soil area (m²). The result is multiplied by operator-set effective-rainfall fraction and probability/confidence, limited to the base zone demand, and subtracted from soil-zone demand only. Hydroponic reservoir calculations receive no rainfall credit. No historical observed rain is added to this estimate.

## Allocation

- Priority protection uses weighted progressive filling. Weights are a transparent urgency heuristic based on soil moisture or reservoir deficit and reproductive stage; they require local calibration.
- Proportional sharing allocates supply in proportion to each zone's estimated demand.
- Both methods cap allocations at zone demand and total available supply.

## Pump and cost

Runtime (minutes) = planned allocated litres / entered nominal flow (L/min). Energy (kWh) = entered pump rated power (kW) × runtime (hours). Electricity cost is estimated energy × tariff. Water cost is optional and uses the entered price per 1,000 L. A parallel-pump comparison assumes additive flow and rated power only where the actual hydraulic setup permits parallel operation.

## Soil profile view

The UI creates three estimated moisture-index layers by subtracting fixed offsets from the entered surface moisture. This is an illustration for inspection only. The app does not estimate true infiltration dynamics, root-zone storage, field capacity or wilting point from those inputs.

## Data provenance

Farm readings and pump specifications are manual. Weather API values are forecasts/current model output. Crop demand, rainfall credit, allocation and pump outputs are estimates. Irrigation plans are planned actions. Actual irrigation records are separately entered by an operator. Synthetic ML files remain labelled as synthetic.
