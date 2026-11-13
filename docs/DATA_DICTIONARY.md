# Data dictionary

All timestamps should be ISO 8601. Record the source as `synthetic`, `public_dataset`, `manual` or `sensor`.

| Field | Unit | Meaning |
|---|---|---|
| temperature_c | deg C | Air temperature |
| humidity_pct | % | Relative humidity |
| moisture_pct | % | Volumetric water content where measured |
| eto_mm_day | mm/day | Reference evapotranspiration |
| kc | dimensionless | Crop coefficient |
| reservoir_l | L | Hydroponic reservoir volume |
| ec_ms_cm | mS/cm | Electrical conductivity |
| ph | pH | Nutrient solution acidity |
| water_l | L | Water volume |

Never mix field capacity, volumetric moisture percentage and reservoir volume as if they were the same state variable.
