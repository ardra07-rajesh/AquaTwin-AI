"""Transparent irrigation calculations for AquaTwin.

All water quantities are daily planning estimates unless a function explicitly
states otherwise. The functions do not represent sensor measurements or pump
control commands.
"""
from __future__ import annotations

import math

CROP_MM_DAY = {
    "Lettuce": 4.0, "Tomato": 4.5, "Spinach": 3.5, "Basil": 3.2,
    "Cucumber": 5.0, "Strawberry": 4.0, "Kale": 3.8,
    "Rice": 5.5, "Cotton": 5.0, "Wheat": 4.0, "Maize": 5.0,
    "Other": 4.0,
}
STAGE_FACTOR = {"Seedling": 0.65, "Vegetative": 0.90, "Flowering": 1.15, "Fruiting": 1.20, "Maturity": 0.80}


def _finite_non_negative(value: float, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be a finite non-negative number.")
    return number


def estimate_zone_demand(crop, area_m2, soil_moisture_pct, temperature_c, humidity_pct,
                         light_hours, growth_stage="Vegetative", efficiency=0.88,
                         method="Soil", reservoir_l=0.0, reservoir_capacity_l=500.0,
                         plants=100):
    """Return daily top-up litres and climate-adjusted depth (mm/day).

    Soil: base crop depth × stage × climate × moisture deficit × area / efficiency.
    Hydroponic: a simplified reservoir deficit heuristic in L/plant/day.
    This is an explainable planning estimate, not a field-validated prescription.
    """
    area_m2 = float(area_m2)
    efficiency = float(efficiency)
    moisture = float(soil_moisture_pct)
    temperature = float(temperature_c)
    humidity = float(humidity_pct)
    light = float(light_hours)
    if not math.isfinite(area_m2) or area_m2 <= 0:
        raise ValueError("Area must be positive.")
    if not 0 < efficiency <= 1:
        raise ValueError("Irrigation efficiency must be in (0, 1].")
    if not 0 <= moisture <= 100 or not 0 <= humidity <= 100:
        raise ValueError("Soil moisture and humidity must be between 0 and 100%.")
    if not -10 <= temperature <= 60 or not 0 <= light <= 24:
        raise ValueError("Temperature or light hours are outside supported input bounds.")

    base_mm = CROP_MM_DAY.get(str(crop), CROP_MM_DAY["Other"]) * STAGE_FACTOR.get(str(growth_stage), 0.90)
    temp_factor = max(0.75, min(1.35, 1 + (temperature - 25) * 0.012))
    humidity_factor = max(0.75, min(1.20, 1 + (60 - humidity) * 0.004))
    light_factor = max(0.80, min(1.20, 0.90 + light * 0.025))
    climate_mm = base_mm * temp_factor * humidity_factor * light_factor

    if str(method).lower() == "hydroponic":
        capacity = float(reservoir_capacity_l)
        level = float(reservoir_l)
        plants = int(plants)
        if capacity <= 0 or not math.isfinite(capacity):
            raise ValueError("Hydroponic reservoir capacity must be positive.")
        if level < 0 or not math.isfinite(level) or plants < 0:
            raise ValueError("Reservoir level and plant count must be non-negative.")
        deficit = max(0.0, min(1.0, (capacity - min(level, capacity)) / capacity))
        return round(min(plants * 0.35, max(0.0, plants * 0.35 * deficit)), 2), climate_mm

    moisture_factor = max(0.10, min(1.50, (80 - moisture) / 35))
    return round(climate_mm * area_m2 * moisture_factor / efficiency, 2), climate_mm


def allocate(demands, available_l, priorities, strategy="Priority protection"):
    """Allocate supply by weighted progressive filling or proportional sharing."""
    demands = [_finite_non_negative(x, "Demand") for x in demands]
    available_l = _finite_non_negative(available_l, "Available water")
    priorities = [_finite_non_negative(x, "Priority") for x in priorities]
    if len(priorities) != len(demands):
        raise ValueError("Priority count must match demand count.")
    if strategy not in {"Priority protection", "Proportional sharing"}:
        raise ValueError("Unknown allocation strategy.")
    total = sum(demands)
    if total <= available_l:
        allocations = list(demands)
    elif total == 0 or available_l == 0:
        allocations = [0.0] * len(demands)
    elif strategy == "Proportional sharing":
        allocations = [d * available_l / total for d in demands]
    else:
        # Weighted max-min progressive fill: each zone is capped at its own demand.
        allocations = [0.0] * len(demands)
        active = set(range(len(demands)))
        remaining = float(available_l)
        weights = [max(0.1, p) for p in priorities]
        while active and remaining > 1e-9:
            weight_sum = sum(weights[i] for i in active)
            proposed = {i: remaining * weights[i] / weight_sum for i in active}
            capped = [i for i in active if allocations[i] + proposed[i] >= demands[i] - 1e-12]
            if not capped:
                for i, amount in proposed.items():
                    allocations[i] += amount
                remaining = 0.0
            else:
                for i in capped:
                    amount = max(0.0, demands[i] - allocations[i])
                    allocations[i] += amount
                    remaining -= amount
                    active.remove(i)
    unmet = [max(0.0, d - a) for d, a in zip(demands, allocations)]
    allocated = sum(allocations)
    return {
        "allocation_l": allocations,
        "unmet_l": unmet,
        "requested_l": total,
        "allocated_l": allocated,
        "shortage_l": max(0.0, total - allocated),
        "feasible": total <= available_l + 1e-8,
        "unused_supply_l": max(0.0, available_l - allocated),
    }


def build_schedule(zones, allocations, flow_l_min, pump_power_kw, electricity_rate, water_rate):
    """Build a serial schedule with nominal-flow runtime and rated-power energy."""
    flow_l_min = float(flow_l_min)
    pump_power_kw = _finite_non_negative(pump_power_kw, "Pump rated power")
    electricity_rate = _finite_non_negative(electricity_rate, "Electricity tariff")
    water_rate = _finite_non_negative(water_rate, "Water tariff")
    if not math.isfinite(flow_l_min) or flow_l_min <= 0:
        raise ValueError("Pump flow rate must be greater than zero.")
    if len(zones) != len(allocations):
        raise ValueError("Zone count must match allocation count.")
    rows = []
    elapsed = 0.0
    for z, litres in zip(zones, allocations):
        litres = _finite_non_negative(litres, "Allocated water")
        minutes = litres / flow_l_min
        kwh = minutes / 60 * pump_power_kw
        water_cost = litres / 1000 * water_rate
        electricity_cost = kwh * electricity_rate
        rows.append({
            "Zone": z["zone"], "Crop": z["crop"], "Water (L)": round(litres, 1),
            "Start (min)": round(elapsed, 1), "Duration (min)": round(minutes, 1),
            "Energy (kWh)": kwh, "Electricity cost (₹)": round(electricity_cost, 2),
            "Water cost (₹)": round(water_cost, 2),
            "Estimated cost (₹)": round(water_cost + electricity_cost, 2),
        })
        elapsed += minutes
    return rows


def pump_summary(total_water_l: float, flow_l_min: float, rated_power_kw: float, tariff_per_kwh: float, available_hours: float) -> dict:
    """Return transparent pump planning estimates for a single operating point."""
    water = _finite_non_negative(total_water_l, "Total water")
    flow = float(flow_l_min)
    power = _finite_non_negative(rated_power_kw, "Rated power")
    tariff = _finite_non_negative(tariff_per_kwh, "Electricity tariff")
    hours = _finite_non_negative(available_hours, "Available hours")
    if not math.isfinite(flow) or flow <= 0:
        raise ValueError("Pump flow rate must be greater than zero.")
    runtime_min = water / flow
    runtime_h = runtime_min / 60
    energy_kwh = power * runtime_h
    return {
        "water_l": water,
        "runtime_min": runtime_min,
        "runtime_h": runtime_h,
        "energy_kwh": energy_kwh,
        "electricity_cost": energy_kwh * tariff,
        "water_per_operating_hour_l": flow * 60,
        "available_hours": hours,
        "fits_window": runtime_h <= hours + 1e-9,
        "overrun_min": max(0.0, runtime_min - hours * 60),
    }
