from agriculture.farm_visualization import build_farm_figure, build_soil_profile_figure, build_water_sankey

ZONES = [
    {"zone": "Z01", "crop": "Tomato", "system": "Soil", "area_m2": 20, "moisture": 32},
    {"zone": "Z02", "crop": "Lettuce", "system": "Soil", "area_m2": 15, "moisture": 50},
]
ROWS = [
    {"Zone": "Z01", "Crop": "Tomato", "Demand (L)": 120, "Allocation (L)": 90, "Unmet (L)": 30, "Urgency score": 2.1, "Status": "Shortage"},
    {"Zone": "Z02", "Crop": "Lettuce", "Demand (L)": 60, "Allocation (L)": 60, "Unmet (L)": 0, "Urgency score": 1.2, "Status": "Covered"},
]


def test_3d_farm_figure_contains_zone_scene_and_serializes():
    fig = build_farm_figure(ZONES, ROWS, "Z01")
    assert len(fig.data) > 10
    assert fig.layout.scene is not None
    assert "Z01" in fig.to_json()


def test_water_sankey_values_follow_zone_allocations():
    fig = build_water_sankey(ZONES, ROWS)
    assert fig is not None
    assert list(fig.data[0].link.value) == [150, 90, 60]


def test_water_sankey_is_absent_when_no_zone_is_allocated():
    empty = [{**row, "Allocation (L)": 0} for row in ROWS]
    assert build_water_sankey(ZONES, empty) is None


def test_soil_profile_labels_depth_values_as_estimates():
    fig, summary = build_soil_profile_figure(ZONES[0], 90, 0.9)
    assert len(fig.data) == 1
    assert summary["planned_net_irrigation_mm"] == 4.05
    assert len(summary["estimated_moisture_by_layer_pct"]) == 3


def test_dashboard_coverage_and_allocation_figures_use_calculated_values():
    from ui.dashboard_figures import build_allocation_treemap, build_coverage_gauge

    rows = [
        {"Zone": "Z01", "Crop": "Tomato", "Allocation (L)": 120.0, "Status": "Covered"},
        {"Zone": "Z02", "Crop": "Lettuce", "Allocation (L)": 35.0, "Status": "Shortage"},
        {"Zone": "Z03", "Crop": "Rice", "Allocation (L)": 0.0, "Status": "Critical"},
    ]
    tree = build_allocation_treemap(rows)
    assert tree is not None
    assert list(tree.data[0].values) == [120.0, 35.0]
    assert list(tree.data[0].labels) == ["Z01 · Tomato", "Z02 · Lettuce"]
    assert build_allocation_treemap([{"Allocation (L)": 0}]) is None

    gauge = build_coverage_gauge(72.5)
    assert gauge.data[0].value == 72.5
    assert build_coverage_gauge(140).data[0].value == 100
