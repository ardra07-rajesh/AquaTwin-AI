"""High-level farm-zone demand, rainfall adjustment and water allocation service."""
from __future__ import annotations

import math
import pandas as pd

from agriculture.decision_engine import CROP_MM_DAY, STAGE_FACTOR, allocate, estimate_zone_demand

ML_CROPS = {"Rice", "Cotton", "Wheat", "Other"}


def validate_zone_records(records: list[dict]) -> list[dict]:
    """Validate editable zone settings before changing the active configuration."""
    cleaned = []
    seen = set()
    for i, raw in enumerate(records):
        z = dict(raw)
        code = str(z.get("zone", f"Z{i+1:02d}")).strip()
        if not code or code in seen:
            raise ValueError("Zone codes must be non-empty and unique.")
        seen.add(code)
        z["zone"] = code
        z["crop"] = str(z.get("crop", "Other"))
        z["system"] = str(z.get("system", "Soil"))
        z["stage"] = str(z.get("stage", "Vegetative"))
        if z["system"] not in {"Soil", "Hydroponic"}:
            raise ValueError(f"{code}: system must be Soil or Hydroponic.")
        for key, low, high in [
            ("area_m2", 0.01, 100000), ("plants", 1, 1000000), ("moisture", 0, 100),
            ("reservoir", 0, 1000000), ("capacity", 0.01, 1000000), ("temp", -10, 60),
            ("humidity", 0, 100), ("light", 0, 24), ("ph", 0, 14), ("ec", 0, 30),
        ]:
            try:
                value = float(z.get(key, 0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{code}: {key} must be numeric.") from exc
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{code}: {key} must be between {low} and {high}.")
            z[key] = int(value) if key == "plants" else value
        if z["reservoir"] > z["capacity"]:
            raise ValueError(f"{code}: reservoir level cannot exceed reservoir capacity.")
        if z["stage"] not in STAGE_FACTOR:
            raise ValueError(f"{code}: unsupported growth stage.")
        cleaned.append(z)
    if not cleaned:
        raise ValueError("At least one crop zone is required.")
    return cleaned


def calculate_plan(zones, available_water_l, efficiency, strategy, weather_adjustment=None, water_model=None):
    """Connect crop estimates, selected-date rainfall credit and allocation."""
    demands, climate, urgency = [], [], []
    base_demands, rainfall_credits = [], []
    zone_rows = []
    for z in zones:
        use_forecast_environment = bool(weather_adjustment and weather_adjustment.get("use_forecast_environment") and z["system"] == "Soil")
        demand_temperature = float(weather_adjustment.get("temperature_c")) if use_forecast_environment else float(z["temp"])
        demand_humidity = float(weather_adjustment.get("humidity_pct")) if use_forecast_environment else float(z["humidity"])
        base_demand, climate_mm = estimate_zone_demand(
            z["crop"], z["area_m2"], z["moisture"], demand_temperature, demand_humidity, z["light"],
            z["stage"], efficiency, z["system"], z["reservoir"], z["capacity"], z["plants"],
        )
        estimate_method = "Crop-profile heuristic"
        if water_model is not None and z["crop"] in ML_CROPS and z["system"] == "Soil":
            features = pd.DataFrame([{
                "crop": z["crop"], "soil_moisture_percent": z["moisture"],
                "temperature_c": demand_temperature, "humidity_percent": demand_humidity, "light_hours": z["light"],
            }])
            ml_mm = max(0.0, float(water_model.predict(features)[0]) * STAGE_FACTOR.get(z["stage"], 0.9))
            moisture_factor = max(0.10, min(1.50, (80-float(z["moisture"])) / 35))
            base_demand = round(ml_mm * float(z["area_m2"]) * moisture_factor / efficiency, 2)
            climate_mm = ml_mm
            estimate_method = "Bundled ML estimate (synthetic training data)"

        credit = 0.0
        if weather_adjustment and z["system"] == "Soil":
            gross_rain_l = float(weather_adjustment.get("rainfall_mm", 0)) * float(z["area_m2"])
            credit = min(base_demand, gross_rain_l * float(weather_adjustment.get("effective_fraction", 0.75)) * float(weather_adjustment.get("confidence", 0.0)))
        adjusted_demand = max(0.0, base_demand - credit)
        if z["system"] == "Soil":
            threshold = 35 if z["stage"] in {"Flowering", "Fruiting"} else 30
            urgency_score = 1 + max(0.0, (45-z["moisture"]) / 25) + (0.25 if z["stage"] in {"Flowering", "Fruiting"} else 0)
            is_critical = z["moisture"] < threshold
        else:
            reservoir_pct = 100 * z["reservoir"] / z["capacity"]
            urgency_score = 1 + max(0.0, (50-reservoir_pct) / 35) + (0.25 if z["stage"] in {"Flowering", "Fruiting"} else 0)
            is_critical = reservoir_pct < 30
        base_demands.append(base_demand)
        rainfall_credits.append(credit)
        demands.append(adjusted_demand)
        climate.append(climate_mm)
        urgency.append(urgency_score)
        zone_rows.append({
            "Zone": z["zone"], "Crop": z["crop"], "System": z["system"],
            "Growth stage": z["stage"], "Area (m²)": z["area_m2"],
            "Soil moisture (%)": z["moisture"] if z["system"] == "Soil" else None,
            "Reservoir (L)": z["reservoir"] if z["system"] == "Hydroponic" else None,
            "Base demand (L)": round(base_demand, 2), "Rain credit (L)": round(credit, 2),
            "Demand (L)": round(adjusted_demand, 2), "Urgency score": round(urgency_score, 2),
            "Status": "Critical" if is_critical else "Pending allocation",
            "Demand method": estimate_method,
            "Demand temperature (°C)": demand_temperature,
            "Demand humidity (%)": demand_humidity,
            "Climate-adjusted depth estimate (mm/day)": round(climate_mm, 2),
        })

    allocation = allocate(demands, float(available_water_l), urgency, strategy)
    for i, row in enumerate(zone_rows):
        row["Allocation (L)"] = round(allocation["allocation_l"][i], 2)
        row["Unmet (L)"] = round(allocation["unmet_l"][i], 2)
        if row["Status"] != "Critical":
            row["Status"] = "Shortage" if allocation["unmet_l"][i] > 0.5 else "Covered"
        row["Irrigation order"] = None
    order = sorted(range(len(zones)), key=lambda i: (urgency[i], allocation["allocation_l"][i]), reverse=True)
    for rank, i in enumerate(order, 1):
        zone_rows[i]["Irrigation order"] = rank
    allocation["zone_rows"] = zone_rows
    allocation["base_demands_l"] = base_demands
    allocation["rain_credits_l"] = rainfall_credits
    allocation["urgency"] = urgency
    allocation["climate_depth_mm"] = climate
    allocation["zone_order_indices"] = order
    allocation["demand_basis"] = "Rain-adjusted daily estimate" if weather_adjustment else "Daily crop-demand estimate"
    allocation["weather_adjustment"] = weather_adjustment
    return allocation
