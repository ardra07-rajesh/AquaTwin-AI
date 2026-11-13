import pytest

from agriculture.planner import calculate_plan, validate_zone_records


def zone(code="Z01", crop="Tomato", system="Soil", moisture=30, area=20, stage="Flowering"):
    return {
        "zone": code, "crop": crop, "system": system, "area_m2": area,
        "plants": 100, "moisture": moisture, "reservoir": 150,
        "capacity": 500, "stage": stage, "temp": 29, "humidity": 55,
        "light": 7, "ph": 6.0, "ec": 1.6,
    }


def test_planner_connects_zone_demand_allocation_and_sequence():
    zones = [zone("Z01", "Tomato", moisture=20), zone("Z02", "Lettuce", moisture=60)]
    plan = calculate_plan(zones, 100, 0.9, "Priority protection")
    assert plan["requested_l"] > 0
    assert sum(plan["allocation_l"]) == pytest.approx(100)
    assert sum(plan["unmet_l"]) == pytest.approx(plan["shortage_l"])
    assert sorted(r["Irrigation order"] for r in plan["zone_rows"]) == [1, 2]
    assert plan["zone_rows"][0]["Demand (L)"] > 0


def test_rainfall_credit_only_applies_to_soil_and_is_capped_at_demand():
    zones = [zone("Z01", "Tomato", "Soil"), zone("Z02", "Basil", "Hydroponic")]
    adjustment = {"rainfall_mm": 100, "confidence": 1.0, "effective_fraction": 1.0}
    plan = calculate_plan(zones, 10000, 0.9, "Priority protection", adjustment)
    assert plan["rain_credits_l"][0] == pytest.approx(plan["base_demands_l"][0])
    assert plan["rain_credits_l"][1] == 0
    assert plan["zone_rows"][0]["Demand (L)"] == 0
    assert plan["zone_rows"][1]["Demand (L)"] == plan["base_demands_l"][1]


def test_invalid_zone_configuration_is_rejected():
    with pytest.raises(ValueError, match="unique"):
        validate_zone_records([zone("Z01"), zone("Z01")])
    bad = zone()
    bad["reservoir"] = 501
    with pytest.raises(ValueError, match="cannot exceed"):
        validate_zone_records([bad])


def test_hydroponic_only_plan_can_be_allocated_without_soil_reading_credit():
    plan = calculate_plan([zone("H1", "Basil", "Hydroponic")], 100, 0.88, "Priority protection")
    assert plan["requested_l"] >= 0
    assert plan["zone_rows"][0]["System"] == "Hydroponic"
    assert plan["zone_rows"][0]["Rain credit (L)"] == 0
