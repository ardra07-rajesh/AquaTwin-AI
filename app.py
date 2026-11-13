"""AquaTwin AI v12 — premium hybrid interface for farm water decision support."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import html

import sklearn
import plotly.graph_objects as go

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="AquaTwin AI v12 | Smart Agriculture", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

from agriculture.decision_engine import CROP_MM_DAY, STAGE_FACTOR, allocate, build_schedule, pump_summary
from ml.model_runtime import load_model_artifact
from ui.styles import get_app_css
from ui.dashboard_figures import build_allocation_treemap, build_coverage_gauge
from agriculture.planner import calculate_plan, validate_zone_records
from agriculture.farm_visualization import (
    build_farm_figure, build_soil_profile_figure, build_water_sankey,
)
from database.db import (
    init_db, list_actual_irrigation, list_runs, list_weather_records,
    load_latest_configuration, save_actual_irrigation, save_configuration,
    save_run, save_weather,
)

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "legacy_water_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
MODEL_METADATA_PATH = ROOT / "models" / "model_metadata.json"
ML_CROPS = {"Rice", "Cotton", "Wheat", "Other"}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather_forecast(latitude: float, longitude: float):
    """Fetch current conditions and a seven-day forecast from Open-Meteo.

    Current and forecast values are weather-model/API data, not on-farm sensor
    observations. The caller stores the successful fetch timestamp separately.
    """
    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
        "forecast_days": 7,
        "timezone": "auto",
    })
    url = "https://api.open-meteo.com/v1/forecast?" + params
    request = Request(url, headers={"User-Agent": "AquaTwin-AI/12.0"})
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(payload.get("reason", "Open-Meteo returned an API error."))
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        raise RuntimeError("The weather API returned no daily forecast rows.")

    def values(key):
        data = daily.get(key)
        return data if isinstance(data, list) and len(data) == len(dates) else [None] * len(dates)

    frame = pd.DataFrame({
        "Date": dates,
        "Mean temperature (°C)": values("temperature_2m_mean"),
        "Max temperature (°C)": values("temperature_2m_max"),
        "Min temperature (°C)": values("temperature_2m_min"),
        "Mean humidity (%)": values("relative_humidity_2m_mean"),
        "Forecast rainfall (mm)": values("precipitation_sum"),
        "Rain probability (%)": values("precipitation_probability_max"),
        "Max wind speed (km/h)": values("wind_speed_10m_max"),
    })
    current = payload.get("current") or {}
    fetched_at = datetime.now(timezone.utc).isoformat()
    return frame, payload.get("timezone", "Local timezone"), current, fetched_at


DEFAULT_ZONES = [
    {"zone": "Z01", "crop": "Tomato", "system": "Soil", "area_m2": 40.0, "plants": 160, "moisture": 34.0, "reservoir": 380.0, "capacity": 500.0, "stage": "Flowering", "temp": 29.0, "humidity": 55.0, "light": 7.0, "ph": 6.0, "ec": 1.6},
    {"zone": "Z02", "crop": "Lettuce", "system": "Soil", "area_m2": 30.0, "plants": 180, "moisture": 58.0, "reservoir": 360.0, "capacity": 500.0, "stage": "Vegetative", "temp": 27.0, "humidity": 62.0, "light": 6.0, "ph": 6.1, "ec": 1.5},
    {"zone": "Z03", "crop": "Cucumber", "system": "Soil", "area_m2": 35.0, "plants": 100, "moisture": 27.0, "reservoir": 420.0, "capacity": 500.0, "stage": "Fruiting", "temp": 31.0, "humidity": 48.0, "light": 8.0, "ph": 6.0, "ec": 1.8},
    {"zone": "Z04", "crop": "Rice", "system": "Soil", "area_m2": 25.0, "plants": 150, "moisture": 66.0, "reservoir": 370.0, "capacity": 500.0, "stage": "Vegetative", "temp": 26.0, "humidity": 65.0, "light": 5.0, "ph": 6.0, "ec": 1.4},
    {"zone": "Z05", "crop": "Basil", "system": "Hydroponic", "area_m2": 20.0, "plants": 120, "moisture": 60.0, "reservoir": 145.0, "capacity": 500.0, "stage": "Vegetative", "temp": 28.0, "humidity": 58.0, "light": 7.0, "ph": 5.2, "ec": 2.8},
    {"zone": "Z06", "crop": "Strawberry", "system": "Hydroponic", "area_m2": 20.0, "plants": 100, "moisture": 60.0, "reservoir": 310.0, "capacity": 500.0, "stage": "Fruiting", "temp": 27.0, "humidity": 60.0, "light": 6.0, "ph": 6.2, "ec": 1.7},
]


@st.cache_resource(show_spinner=False)
def load_water_model():
    """Load and smoke-test the bundled model; return its exact diagnostic."""
    return load_model_artifact(MODEL_PATH)


@st.cache_data(show_spinner=False)
def load_model_metrics():
    if METRICS_PATH.exists():
        try:
            return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


@st.cache_data(show_spinner=False)
def load_model_metadata():
    if MODEL_METADATA_PATH.exists():
        try:
            return json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


@st.cache_data(ttl=3600, show_spinner=False)
def synthetic_feature_importance():
    """Permutation importance on the documented synthetic hold-out split."""
    dataset_path = ROOT / "data" / "raw" / "legacy_irrigation_dataset.csv"
    if not dataset_path.exists():
        return pd.DataFrame(columns=["Feature", "Permutation importance (MAE increase)"])
    from sklearn.inspection import permutation_importance
    from sklearn.model_selection import train_test_split
    frame = pd.read_csv(dataset_path)
    target = "water_need_mm"
    x = frame.drop(columns=[target])
    y = frame[target]
    _, x_test, _, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    model, _diagnostic = load_water_model()
    if model is None:
        return pd.DataFrame(columns=["Feature", "Permutation importance (MAE increase)"])
    result = permutation_importance(model, x_test, y_test, n_repeats=5, random_state=42, scoring="neg_mean_absolute_error")
    return pd.DataFrame({
        "Feature": x.columns,
        "Permutation importance (MAE increase)": result.importances_mean,
    }).sort_values("Permutation importance (MAE increase)", ascending=False)


# Initialize persistent tables and restore the last saved farm/zone configuration.
init_db()
saved_configuration = load_latest_configuration("farm_configuration") or {}
st.markdown(get_app_css(), unsafe_allow_html=True)

if "zones" not in st.session_state:
    st.session_state.zones = saved_configuration.get("zones", DEFAULT_ZONES)
if "farm_name" not in st.session_state:
    st.session_state.farm_name = saved_configuration.get("farm_name", "AquaTwin Demonstration Farm")
if "farm_location" not in st.session_state:
    st.session_state.farm_location = saved_configuration.get("farm_location", "Not specified")
if "available_water" not in st.session_state:
    st.session_state.available_water = float(saved_configuration.get("available_water_l", 650.0))
if "efficiency_pct" not in st.session_state:
    st.session_state.efficiency_pct = int(saved_configuration.get("efficiency_pct", 88))
for state_key, config_key, default_value in [
    ("pump_flow", "pump_flow_l_min", 48.0), ("pump_kw", "pump_rated_power_kw", 0.75),
    ("electricity_tariff", "electricity_tariff_per_kwh", 8.0),
    ("water_rate", "water_tariff_per_1000_l", 20.0), ("pumping_hours", "available_pumping_hours", 8.0),
]:
    if state_key not in st.session_state:
        st.session_state[state_key] = float(saved_configuration.get(config_key, default_value))
if "weather_adjustment" not in st.session_state:
    st.session_state.weather_adjustment = None
if "weather_forecast" not in st.session_state:
    st.session_state.weather_forecast = None
if "last_saved_plan_id" not in st.session_state:
    st.session_state.last_saved_plan_id = None

WATER_MODEL, MODEL_LOAD_DIAGNOSTIC = load_water_model()

with st.sidebar:
    st.markdown("## 🌱 AquaTwin AI")
    st.caption("Farm water intelligence · v12")
    page = st.radio(
        "Workspace",
        ["Farm Dashboard", "Farm Twin", "Crop Intelligence", "Smart Irrigation Planner", "Water Rescue", "Smart Operations", "Operations History", "Cost & Performance"],
        label_visibility="collapsed",
    )
    st.divider()
    st.subheader("Farm profile")
    farm_name = st.text_input("Farm name", key="farm_name")
    farm_location = st.text_input("Farm location", key="farm_location")
    st.subheader("Daily water supply")
    water = st.number_input("Available water today (L)", min_value=0.0, max_value=10_000_000.0, step=50.0, key="available_water")
    efficiency = st.slider("Irrigation efficiency (%)", 40, 100, key="efficiency_pct") / 100.0
    strategy_options = ["Priority protection", "Proportional sharing"]
    saved_strategy = saved_configuration.get("strategy", "Priority protection")
    strategy = st.selectbox("Allocation strategy", strategy_options, index=strategy_options.index(saved_strategy) if saved_strategy in strategy_options else 0)
    if st.session_state.weather_adjustment:
        adjustment = st.session_state.weather_adjustment
        st.info(f"Weather credit active · {adjustment.get('label', 'selected rainfall')}")
        if st.button("Remove weather adjustment"):
            st.session_state.weather_adjustment = None
            st.rerun()
    st.divider()
    st.caption("Input provenance: farm readings and pump specifications are manual; crop demand is estimated; weather is an external forecast; no live sensor or pump-control connection is configured.")
    st.divider()
    if WATER_MODEL is not None:
        st.success("Crop ML model · loaded and smoke-tested")
        if MODEL_LOAD_DIAGNOSTIC:
            st.warning("Model compatibility notice is available in Crop Intelligence.")
    else:
        st.warning("Crop ML model unavailable · profile estimator active")

zones = validate_zone_records(st.session_state.zones)
plan = calculate_plan(zones, water, efficiency, strategy, st.session_state.weather_adjustment, WATER_MODEL)
plan_rows = plan["zone_rows"]
pdf = pd.DataFrame(plan_rows)
coverage_pct = 100 * plan["allocated_l"] / plan["requested_l"] if plan["requested_l"] else 100.0


def render_hero(kicker: str, title: str, subtitle: str, tag: str = "PLANNING WORKSPACE"):
    safe = [html.escape(str(x)) for x in (kicker, title, subtitle, tag)]
    st.markdown(
        '<section class="aqua-hero"><div class="aqua-hero-copy">'
        f'<div class="aqua-kicker">{safe[0]}</div><h1>{safe[1]}</h1><p>{safe[2]}</p>'
        f'</div><div class="aqua-hero-tag">{safe[3]}</div></section>',
        unsafe_allow_html=True,
    )


def render_zone_cards(zone_rows, zone_records):
    """Compact zone inspection cards populated only from current plan inputs/outputs."""
    source = {z["zone"]: z for z in zone_records}
    cols = st.columns(3)
    for index, row in enumerate(zone_rows):
        zone = source.get(row["Zone"], {})
        demand = max(0.0, float(row.get("Demand (L)", 0) or 0))
        allocated = max(0.0, float(row.get("Allocation (L)", 0) or 0))
        coverage = min(100.0, 100.0 * allocated / demand) if demand else 100.0
        status = str(row.get("Status", "Pending"))
        status_class = "critical" if status == "Critical" else "shortage" if status == "Shortage" else "covered"
        bar_color = "#b85c4d" if status_class == "critical" else "#bd8b48" if status_class == "shortage" else "#4c8a5d"
        detail = (f"Moisture {float(zone.get('moisture', 0)):.0f}%" if zone.get("system") == "Soil"
                  else f"Reservoir {float(zone.get('reservoir', 0)):.0f}/{float(zone.get('capacity', 0)):.0f} L")
        with cols[index % 3]:
            st.markdown(
                '<div class="aqua-zone-card">'
                '<div class="aqua-zone-top"><div>'
                f'<div class="aqua-zone-title">{html.escape(str(row["Zone"]))}</div>'
                f'<div class="aqua-zone-crop">{html.escape(str(row["Crop"]))} · {html.escape(str(row["Growth stage"]))}</div>'
                f'</div><span class="aqua-zone-status {status_class}">{html.escape(status)}</span></div>'
                f'<div class="aqua-zone-foot"><span>Allocated</span><b>{allocated:,.1f} / {demand:,.1f} L</b></div>'
                f'<div class="aqua-progress"><span style="width:{coverage:.1f}%;background:{bar_color};"></span></div>'
                f'<div class="aqua-zone-foot"><span>{html.escape(detail)}</span><span>Priority #{html.escape(str(row.get("Irrigation order", "—")))}</span></div>'
                '</div>', unsafe_allow_html=True,
            )


def save_current_plan(label: str = "Planned irrigation") -> int:
    pump_flow = float(st.session_state.get("pump_flow", 48.0))
    pump_kw = float(st.session_state.get("pump_kw", 0.75))
    tariff = float(st.session_state.get("electricity_tariff", 8.0))
    hours = float(st.session_state.get("pumping_hours", 8.0))
    order = plan["zone_order_indices"]
    sorted_zones = [{"zone": zones[i]["zone"], "crop": zones[i]["crop"]} for i in order]
    sorted_allocations = [plan["allocation_l"][i] for i in order]
    schedule = build_schedule(sorted_zones, sorted_allocations, pump_flow, pump_kw, tariff, 0.0)
    pump = pump_summary(plan["allocated_l"], pump_flow, pump_kw, tariff, hours)
    outputs = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "mode": "planned estimate from manual farm inputs",
        "available_water_l": float(water), "requested_l": float(plan["requested_l"]),
        "allocated_l": float(plan["allocated_l"]), "shortage_l": float(plan["shortage_l"]),
        "demand_coverage_pct": float(coverage_pct), "strategy": strategy,
        "demand_basis": plan["demand_basis"], "weather_adjustment": plan["weather_adjustment"],
        "zones": zones, "zone_rows": plan_rows, "schedule": schedule, "pump_summary": pump,
        "limitations": [
            "Soil moisture and reservoir readings are manual inputs, not sensor measurements.",
            "Crop demand and effective-rainfall credit are estimates and need local calibration.",
            "Pump runtime and energy use nominal rated specifications, not measured electrical or flow data.",
            "A saved plan records a plan only; it is not proof that irrigation occurred.",
        ],
    }
    inputs = {
        "farm_name": farm_name, "farm_location": farm_location, "available_water_l": float(water),
        "efficiency": float(efficiency), "efficiency_pct": round(float(efficiency)*100),
        "strategy": strategy, "zones": zones,
        "pump_flow_l_min": pump_flow, "pump_rated_power_kw": pump_kw,
        "electricity_tariff_per_kwh": tariff, "water_tariff_per_1000_l": water_rate,
        "available_pumping_hours": hours, "weather_adjustment": plan["weather_adjustment"],
    }
    save_configuration("farm_configuration", {
        "farm_name": farm_name, "farm_location": farm_location,
        "available_water_l": float(water), "efficiency_pct": round(float(efficiency)*100),
        "strategy": strategy, "zones": zones,
        "pump_flow_l_min": pump_flow, "pump_rated_power_kw": pump_kw,
        "electricity_tariff_per_kwh": tariff, "water_tariff_per_1000_l": water_rate,
        "available_pumping_hours": hours,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }, farm_name, farm_location)
    record_id = save_run(label, inputs, outputs, farm_name, farm_location)
    st.session_state.last_saved_plan_id = record_id
    return record_id


def render_zone_status():
    status_order = {"Critical": 0, "Shortage": 1, "Covered": 2}
    frame = pdf.copy()
    frame["_order"] = frame["Status"].map(status_order)
    frame = frame.sort_values(["_order", "Urgency score"], ascending=[True, False]).drop(columns="_order")
    st.dataframe(frame[["Zone", "Crop", "System", "Demand (L)", "Allocation (L)", "Unmet (L)", "Urgency score", "Status"]], use_container_width=True, hide_index=True)


if page == "Farm Dashboard":
    total_area = sum(float(z["area_m2"]) for z in zones)
    render_hero(
        "FARM OPERATIONS CENTER",
        "A clear view of the water decision.",
        f"{farm_name} · {len(zones)} configured zones · {total_area:,.1f} m² total area · {strategy}",
        "CALCULATED PLAN · NOT LIVE TELEMETRY",
    )
    k = st.columns(4)
    k[0].metric("Available water", f"{water:,.0f} L", help="Operator-entered daily supply.")
    k[1].metric("Estimated demand", f"{plan['requested_l']:,.1f} L", help="Calculated from crop profiles or the bundled ML model, where available.")
    k[2].metric("Planned allocation", f"{plan['allocated_l']:,.1f} L", help="Calculated distribution, not measured delivery.")
    k[3].metric("Unmet demand", f"{plan['shortage_l']:,.1f} L", delta=f"{coverage_pct:.1f}% demand covered", delta_color="normal")

    st.markdown('<div class="aqua-section-label">Farm model · based on configured zones and calculated allocation</div>', unsafe_allow_html=True)
    twin_col, allocation_col = st.columns([1.55, 1], gap="large")
    with twin_col:
        st.plotly_chart(
            build_farm_figure(zones, plan_rows, selected_zone=None, available_water_l=water),
            use_container_width=True, config={"scrollZoom": True, "displaylogo": False},
        )
        st.caption("Schematic farm geometry. Zone labels, status and allocation values are taken from the current farm configuration and planning calculation; the footprint is not a surveyed GIS boundary.")
    with allocation_col:
        st.subheader("Water demand coverage")
        gauge = build_coverage_gauge(coverage_pct)
        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
        st.subheader("Where allocated water goes")
        allocation_tree = build_allocation_treemap(plan_rows)
        if allocation_tree is not None:
            st.plotly_chart(allocation_tree, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No water is allocated under the current supply and demand inputs.")

    st.markdown('<div class="aqua-section-label">Zone condition and allocation</div>', unsafe_allow_html=True)
    st.subheader("Inspect the zones")
    st.caption("Status combines manually entered soil moisture or reservoir level with estimated demand and calculated allocation. These are not sensor readings.")
    render_zone_cards(plan_rows, zones)

    attention = pdf[pdf["Status"].isin(["Critical", "Shortage"])].sort_values("Urgency score", ascending=False)
    with st.expander("Decision notes and items requiring attention", expanded=not attention.empty):
        if attention.empty:
            st.success("No unmet planned demand under the current inputs. Confirm the field readings before applying water.")
        else:
            for _, row in attention.iterrows():
                st.warning(f"{row['Zone']} · {row['Crop']} — {row['Status']}. Estimated demand {row['Demand (L)']:.1f} L; planned allocation {row['Allocation (L)']:.1f} L; unmet {row['Unmet (L)']:.1f} L.")
        st.markdown("<div class='aqua-note'><b>How this decision is produced</b><br>Crop demand comes from the crop-profile estimator or the bundled ML model for supported crops when it passes its load and prediction check. Priority protection weights moisture/reservoir deficit and growth stage; proportional sharing distributes supply in proportion to estimated demand. No automatic irrigation or physical water delivery is claimed.</div>", unsafe_allow_html=True)

    if st.button("Save this calculated plan to farm history", type="primary"):
        try:
            record_id = save_current_plan("Planned irrigation")
            st.success(f"Plan #{record_id} saved. It records planned allocations, not evidence of irrigation completed.")
        except Exception as exc:
            st.error(f"The plan could not be saved: {exc}")
    st.caption("All water quantities are planning estimates from current inputs. No yield increase, water saving, or physical delivery is inferred from this calculation.")


elif page == "Farm Twin":
    render_hero("INTERACTIVE FARM MODEL", "Inspect zones and trace the planned water route.", "Rotatable 3D scene · calculated allocations · conceptual soil profile · no connected field hardware")
    selected_zone = st.selectbox("Inspect a crop zone", [z["zone"] for z in zones])
    flow_metrics = st.columns(5)
    flow_metrics[0].metric("Available supply", f"{water:,.1f} L")
    flow_metrics[1].metric("Estimated crop demand", f"{plan['requested_l']:,.1f} L")
    flow_metrics[2].metric("Planned allocation", f"{plan['allocated_l']:,.1f} L")
    flow_metrics[3].metric("Unmet demand", f"{plan['shortage_l']:,.1f} L")
    flow_metrics[4].metric("Assumed irrigation efficiency", f"{efficiency*100:.0f}%")
    st.caption("The farm footprint and crop-row markers are schematic, not a surveyed GIS boundary or a plant-by-plant inventory. Zone allocations and sequence labels are taken from the active calculation.")
    st.plotly_chart(build_farm_figure(zones, plan_rows, selected_zone, water), use_container_width=True, config={"scrollZoom": True, "displaylogo": False})
    selected = next(z for z in zones if z["zone"] == selected_zone)
    selected_row = next(r for r in plan_rows if r["Zone"] == selected_zone)
    m = st.columns(4)
    m[0].metric("Crop and stage", f"{selected['crop']} · {selected['stage']}")
    m[1].metric("Estimated demand", f"{selected_row['Demand (L)']:,.1f} L")
    m[2].metric("Planned allocation", f"{selected_row['Allocation (L)']:,.1f} L")
    m[3].metric("Unmet demand", f"{selected_row['Unmet (L)']:,.1f} L")
    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Water distribution network")
        st.caption("The Sankey uses the same allocated-litre values as the irrigation planner. Links represent a planned distribution, not measured flow.")
        sankey = build_water_sankey(zones, plan_rows, water)
        if sankey is None:
            st.info("No water is allocated under the current inputs, so there is no planned distribution path to display.")
        else:
            st.plotly_chart(sankey, use_container_width=True)
    with right:
        st.subheader("Selected zone inspection")
        st.markdown(f"**{selected['zone']} · {selected['crop']}**\nSystem: {selected['system']} · Area: {selected['area_m2']:.1f} m² · Plants: {selected['plants']}\nCalculated urgency score: {selected_row['Urgency score']:.2f}\nPlanned order: {selected_row['Irrigation order']} · Status: {selected_row['Status']}")
        if selected["system"] == "Soil":
            st.write(f"Manual surface moisture input: **{selected['moisture']:.1f}%**")
            fig, soil_summary = build_soil_profile_figure(selected, selected_row["Allocation (L)"], efficiency)
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Planned net water input", f"{soil_summary['planned_net_irrigation_mm']:.2f} mm")
            st.write(f"Estimated deficit index to 75% reference: {soil_summary['root_zone_deficit_index_pct_points']:.1f} percentage points · surface-moisture margin to 35% alert threshold: {soil_summary['surface_moisture_margin_to_action_threshold_pct_points']:+.1f} points · illustrative profile depth: {soil_summary['assumed_profile_depth_cm']} cm.")
            st.caption("Depth layers are a schematic estimated gradient from one manually entered surface moisture value. There are no depth probes; infiltration, root-zone storage and true water availability are not measured.")
        else:
            reservoir_pct = 100 * selected["reservoir"] / selected["capacity"]
            st.metric("Manual reservoir level", f"{selected['reservoir']:.1f} / {selected['capacity']:.1f} L", delta=f"{reservoir_pct:.1f}% full")
            st.write(f"pH input: {selected['ph']:.1f} · EC input: {selected['ec']:.2f} mS/cm")
            st.caption("Hydroponic demand is a reservoir-deficit top-up heuristic; pH/EC are operator inputs, not live probe readings.")
    st.subheader("Planned irrigation sequence")
    sequence = pdf.sort_values("Irrigation order")[["Irrigation order", "Zone", "Crop", "Demand (L)", "Allocation (L)", "Unmet (L)", "Status"]]
    st.dataframe(sequence, use_container_width=True, hide_index=True)
    st.info("The blue pipeline and zone markers visualize calculated allocations. They do not prove water has moved; no flow meters, actuated valves, or pump controller are connected.")


elif page == "Crop Intelligence":
    render_hero("CROP AND SOIL DECISION SUPPORT", "Estimate crop demand and identify stress signals.", "Crop profile or bundled ML estimate · manual soil and climate inputs · local calibration required")
    st.caption("Soil-zone demand uses crop type, growth stage, area, entered moisture, temperature, humidity, light and irrigation efficiency. Hydroponic zones use a separate reservoir top-up heuristic.")
    crop_columns = ["Zone", "Crop", "Growth stage", "System", "Base demand (L)", "Rain credit (L)", "Demand (L)", "Climate-adjusted depth estimate (mm/day)", "Demand method"]
    st.dataframe(pdf[crop_columns], use_container_width=True, hide_index=True)
    st.subheader("Crop stress diagnostics")
    for z, r in zip(zones, plan_rows):
        if z["system"] == "Soil":
            threshold = 35 if z["stage"] in {"Flowering", "Fruiting"} else 30
            if z["moisture"] < threshold:
                st.error(f"{z['zone']} · {z['crop']}: entered soil moisture {z['moisture']:.1f}% is below the prototype action threshold ({threshold}%). Urgency is increased.")
            elif z["moisture"] > 80:
                st.warning(f"{z['zone']} · {z['crop']}: entered soil moisture is high. Check drainage and the root zone before applying irrigation.")
            else:
                st.success(f"{z['zone']} · {z['crop']}: entered surface moisture is within the prototype operating band. Current unmet estimate: {r['Unmet (L)']:.1f} L.")
        else:
            pct = 100*z["reservoir"]/z["capacity"]
            if pct < 35:
                st.error(f"{z['zone']} · {z['crop']}: entered reservoir is {pct:.1f}% full. Check level, pH and EC before topping up.")
            elif pct > 90:
                st.warning(f"{z['zone']} · {z['crop']}: reservoir is near capacity. Check return flow and overflow risk.")
            else:
                st.success(f"{z['zone']} · {z['crop']}: reservoir level is {pct:.1f}% of capacity.")
            if not 5.5 <= z["ph"] <= 6.5:
                st.warning(f"{z['zone']}: entered pH {z['ph']:.1f} is outside the prototype reference band 5.5–6.5.")
            if not 1.2 <= z["ec"] <= 2.4:
                st.warning(f"{z['zone']}: entered EC {z['ec']:.2f} mS/cm is outside the prototype reference band 1.2–2.4.")
    st.subheader("ML model provenance and evaluation")
    metrics = load_model_metrics()
    if WATER_MODEL is None:
        st.error("The bundled ML model did not pass its load and prediction check. Crop-profile estimation remains active; ML predictions are not being used.")
        st.markdown(f'<div class="aqua-error"><b>Exact loading diagnostic</b><br>{html.escape(MODEL_LOAD_DIAGNOSTIC or "No diagnostic was returned.")}</div>', unsafe_allow_html=True)
        st.caption(f"Expected artifact: {MODEL_PATH} · Exists: {MODEL_PATH.is_file()} · Runtime Python: {html.escape(__import__('sys').version.split()[0])} · scikit-learn: {sklearn.__version__} · joblib: {joblib.__version__}")
        if st.button("Rebuild model for this Python environment", type="primary", help="Retrains the bundled pipeline from the included synthetic CSV and replaces the local model artifact."):
            try:
                from ml.train import train as train_bundled_model
                with st.spinner("Training the bundled model using the included synthetic dataset…"):
                    train_bundled_model()
                load_water_model.clear()
                load_model_metrics.clear()
                load_model_metadata.clear()
                synthetic_feature_importance.clear()
                st.success("Model retrained and saved. Reloading the application to verify it.")
                st.rerun()
            except Exception as exc:
                st.error(f"Model rebuild failed: {type(exc).__name__}: {exc}")
    else:
        st.success("Bundled ML model loaded and passed a one-row prediction smoke test.")
        model_type = type(WATER_MODEL.named_steps.get("model", WATER_MODEL)).__name__ if hasattr(WATER_MODEL, "named_steps") else type(WATER_MODEL).__name__
        st.markdown(f"""**Bundled model:** `{MODEL_PATH.name}` · {model_type}

**Supported ML crop labels:** Rice, Cotton, Wheat and Other (soil zones only)

**Training data provenance:** `data/raw/legacy_irrigation_dataset.csv`, synthetic demonstration data.

**Model version:** legacy v10 bundle; no independent field validation is available.""")
        if MODEL_LOAD_DIAGNOSTIC:
            st.warning(f"The model loaded and passed prediction, but emitted a compatibility warning: {MODEL_LOAD_DIAGNOSTIC}")
        st.caption(f"Runtime versions: Python {__import__('sys').version.split()[0]} · scikit-learn {sklearn.__version__} · joblib {joblib.__version__}")
        metadata = load_model_metadata()
        with st.expander("Model artifact metadata and compatibility details"):
            if metadata:
                st.json(metadata)
            else:
                st.info("No model metadata file is present. The original legacy artifact did not record its training environment.")
            st.write(f"Resolved model path: `{MODEL_PATH}`")
            st.write(f"Model file size: {MODEL_PATH.stat().st_size:,} bytes" if MODEL_PATH.is_file() else "Model file is missing.")
        if metrics.get("models"):
            st.dataframe(pd.DataFrame(metrics["models"]).T.rename_axis("Model").reset_index(), use_container_width=True, hide_index=True)
        importance = synthetic_feature_importance()
        if not importance.empty:
            st.subheader("Permutation feature importance")
            st.caption("An increase in synthetic hold-out MAE when a feature is permuted. This is a diagnostic of fit to generated data, not proof of real-world causal importance.")
            imp = importance.sort_values("Permutation importance (MAE increase)", ascending=True)
            fig = go.Figure()
            for _, r in imp.iterrows():
                fig.add_trace(go.Scatter(
                    x=[0, r["Permutation importance (MAE increase)"]], y=[r["Feature"], r["Feature"]],
                    mode="lines", line=dict(color="#d8e2d6", width=3), showlegend=False, hoverinfo="skip",
                ))
            fig.add_trace(go.Scatter(
                x=imp["Permutation importance (MAE increase)"], y=imp["Feature"], mode="markers",
                marker=dict(size=12, color="#477b58", line=dict(color="#ffffff", width=1.5)),
                hovertemplate="%{y}<br>MAE increase: %{x:.4f}<extra></extra>", name="Importance",
            ))
            fig.update_layout(height=300, margin=dict(l=8, r=12, t=10, b=8), showlegend=False,
                              xaxis_title="Synthetic hold-out MAE increase", yaxis_title="",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#405647"), xaxis=dict(gridcolor="#e8eee5", zeroline=False),
                              yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)
    if metrics.get("warning"):
        st.info(metrics["warning"])
    st.caption("Crop-profile calculations remain the fallback when the model is unavailable or a crop is not supported. Synthetic training and hold-out metrics do not establish prediction accuracy on a real farm. Crop coefficients and stress thresholds require agronomic calibration.")


elif page == "Smart Irrigation Planner":
    render_hero("IRRIGATION DECISION ENGINE", "Build a plan that fits the available supply and pump window.", "Transparent crop demand · urgency-ranked sequence · nominal pump and electricity estimates")
    st.subheader("1 · Crop-zone configuration")
    editor_frame = pd.DataFrame(zones)[["zone", "crop", "system", "area_m2", "plants", "moisture", "reservoir", "capacity", "stage", "temp", "humidity", "light", "ph", "ec"]]
    edited = st.data_editor(
        editor_frame, use_container_width=True, hide_index=True, num_rows="fixed",
        disabled=["zone"], key="zone_editor",
        column_config={
            "crop": st.column_config.SelectboxColumn(options=list(CROP_MM_DAY), required=True),
            "system": st.column_config.SelectboxColumn(options=["Soil", "Hydroponic"], required=True),
            "stage": st.column_config.SelectboxColumn(options=list(STAGE_FACTOR), required=True),
            "area_m2": st.column_config.NumberColumn(min_value=0.01, max_value=100000, step=1.0),
            "plants": st.column_config.NumberColumn(min_value=1, max_value=1000000, step=1),
            "moisture": st.column_config.NumberColumn(min_value=0, max_value=100, step=1.0),
            "reservoir": st.column_config.NumberColumn(min_value=0, max_value=1000000, step=1.0),
            "capacity": st.column_config.NumberColumn(min_value=0.01, max_value=1000000, step=1.0),
            "temp": st.column_config.NumberColumn(min_value=-10, max_value=60, step=0.5),
            "humidity": st.column_config.NumberColumn(min_value=0, max_value=100, step=1.0),
            "light": st.column_config.NumberColumn(min_value=0, max_value=24, step=0.5),
            "ph": st.column_config.NumberColumn(min_value=0, max_value=14, step=0.1),
            "ec": st.column_config.NumberColumn(min_value=0, max_value=30, step=0.1),
        },
    )
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Apply and save zone readings", type="primary"):
            try:
                st.session_state.zones = validate_zone_records(edited.to_dict("records"))
                save_configuration("farm_configuration", {
                    "farm_name": farm_name, "farm_location": farm_location,
                    "available_water_l": float(water), "efficiency_pct": round(float(efficiency)*100),
                    "strategy": strategy, "zones": st.session_state.zones,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }, farm_name, farm_location)
                st.success("Zone configuration saved locally and will be restored after restart.")
                st.rerun()
            except Exception as exc:
                st.error(f"Zone readings were not applied: {exc}")
    with c2:
        st.caption("Values in this editor are operator-entered inputs. Applying changes validates them and stores a new configuration snapshot; prior plan history is not overwritten.")

    st.subheader("2 · Pump and energy settings")
    pump_cols = st.columns(4)
    pump_flow = pump_cols[0].number_input("Pump 1 flow (L/min)", 1.0, 5000.0, 48.0, step=1.0, key="pump_flow")
    pump_kw = pump_cols[1].number_input("Pump 1 rated power (kW)", 0.05, 500.0, 0.75, step=0.05, key="pump_kw")
    tariff = pump_cols[2].number_input("Electricity tariff (₹/kWh)", 0.0, 10000.0, 8.0, step=0.5, key="electricity_tariff")
    hours = pump_cols[3].number_input("Available pumping hours", 0.1, 24.0, 8.0, step=0.5, key="pumping_hours")
    water_rate = st.number_input("Water tariff (₹ per 1,000 L; optional)", 0.0, 100000.0, 20.0, step=5.0, key="water_rate")
    add_second_pump = st.checkbox("Compare an optional second pump in parallel")
    second_flow = second_kw = 0.0
    if add_second_pump:
        p2a, p2b, p2c = st.columns(3)
        second_flow = p2a.number_input("Pump 2 flow (L/min)", 1.0, 5000.0, 36.0, step=1.0, key="pump2_flow")
        second_kw = p2b.number_input("Pump 2 rated power (kW)", 0.05, 500.0, 0.55, step=0.05, key="pump2_kw")
        p2c.caption("Parallel totals assume both pumps can operate together at their entered nominal flow. Confirm the hydraulic arrangement and pump curves before use.")

    pump1 = pump_summary(plan["allocated_l"], pump_flow, pump_kw, tariff, hours)
    pump_rows = [{"Configuration": "Pump 1 only", "Combined flow (L/min)": pump_flow, "Rated power (kW)": pump_kw,
                  "Runtime (min)": pump1["runtime_min"], "Energy (kWh)": pump1["energy_kwh"], "Electricity cost (₹)": pump1["electricity_cost"], "Fits window": pump1["fits_window"]}]
    if add_second_pump:
        parallel = pump_summary(plan["allocated_l"], pump_flow + second_flow, pump_kw + second_kw, tariff, hours)
        pump_rows.append({"Configuration": "Pump 1 + Pump 2 parallel", "Combined flow (L/min)": pump_flow + second_flow, "Rated power (kW)": pump_kw + second_kw,
                          "Runtime (min)": parallel["runtime_min"], "Energy (kWh)": parallel["energy_kwh"], "Electricity cost (₹)": parallel["electricity_cost"], "Fits window": parallel["fits_window"]})
    st.dataframe(pd.DataFrame(pump_rows).round(2), use_container_width=True, hide_index=True)
    if not pump1["fits_window"]:
        st.error(f"Pump 1 estimate exceeds the available operating window by {pump1['overrun_min']:.1f} minutes.")
    else:
        st.success(f"Pump 1 nominal-flow estimate fits the {hours:.1f}-hour operating window.")
    st.caption("Energy = rated kW × estimated runtime. This is an estimate, not measured electrical consumption or measured pump delivery. Head, pressure, pipe losses and pump curves can change actual performance.")

    st.subheader("3 · Priority-ranked irrigation sequence")
    order = plan["zone_order_indices"]
    ordered_zones = [{"zone": zones[i]["zone"], "crop": zones[i]["crop"]} for i in order]
    ordered_allocations = [plan["allocation_l"][i] for i in order]
    schedule = pd.DataFrame(build_schedule(ordered_zones, ordered_allocations, pump_flow, pump_kw, tariff, water_rate))
    schedule.insert(0, "Sequence", range(1, len(schedule)+1))
    st.dataframe(schedule, use_container_width=True, hide_index=True)
    st.write(f"**Estimated water + electricity cost:** ₹{schedule['Estimated cost (₹)'].sum():,.2f} (water tariff is an editable assumption).")
    total_runtime = float(schedule["Duration (min)"].sum())
    st.write(f"**Total planned runtime:** {total_runtime:.1f} minutes · **Unmet estimated demand:** {plan['shortage_l']:.1f} L · **Selected allocation strategy:** {strategy}")
    with st.expander("Why this plan was generated"):
        st.markdown("- Crop demand starts from a crop-specific daily depth and growth-stage factor.\n- Soil zones adjust for the entered temperature, humidity, light and moisture; hydroponic zones use reservoir deficit.\n- If an active rainfall adjustment exists, only the selected date's forecast or manual expected rainfall is credited to soil zones, discounted by effective-rainfall fraction and confidence.\n- Priority protection uses a weighted progressive allocation based on moisture/reservoir deficit and reproductive stage. Proportional sharing distributes supply in proportion to each zone's estimated demand.\n- Pump runtime is allocated litres divided by operator-entered nominal flow. Electricity is estimated from rated power and runtime.")
    if st.button("Generate and save irrigation plan", type="primary"):
        try:
            record_id = save_current_plan("Weather-adjusted irrigation plan" if plan["weather_adjustment"] else "Planned irrigation")
            st.success(f"Plan #{record_id} saved to SQLite. The plan remains marked as planned until a user enters actual irrigation records.")
        except Exception as exc:
            st.error(f"Plan could not be saved: {exc}")


elif page == "Water Rescue":
    render_hero("WATER SHORTAGE RESPONSE", "Rebalance when supply drops.", "Every scenario reruns the same zone-demand and allocation engine; compare the effect zone by zone.")
    preset = st.selectbox("Shortage scenario", ["10% reduction", "20% reduction", "30% reduction", "50% reduction", "Custom reduction"])
    if preset == "Custom reduction":
        reduction = st.slider("Custom supply reduction (%)", 0, 90, 30, 5)
    else:
        reduction = int(preset.split("%")[0])
    scenario_supply = water * (1 - reduction/100)
    scenario = calculate_plan(zones, scenario_supply, efficiency, strategy, st.session_state.weather_adjustment, WATER_MODEL)
    m = st.columns(4)
    m[0].metric("Original supply", f"{water:,.1f} L")
    m[1].metric("Scenario supply", f"{scenario_supply:,.1f} L", delta=f"-{reduction}%")
    m[2].metric("Original unmet", f"{plan['shortage_l']:,.1f} L")
    m[3].metric("Scenario unmet", f"{scenario['shortage_l']:,.1f} L", delta=f"{scenario['shortage_l']-plan['shortage_l']:+,.1f} L", delta_color="inverse")
    comp = pd.DataFrame({
        "Zone": [z["zone"] for z in zones], "Crop": [z["crop"] for z in zones],
        "Demand (L)": [r["Demand (L)"] for r in plan_rows],
        "Original allocation (L)": [round(x, 2) for x in plan["allocation_l"]],
        "Scenario allocation (L)": [round(x, 2) for x in scenario["allocation_l"]],
        "Scenario unmet (L)": [round(x, 2) for x in scenario["unmet_l"]],
        "Scenario order": [r["Irrigation order"] for r in scenario["zone_rows"]],
    })
    st.subheader("Zone-by-zone response")
    st.dataframe(comp, use_container_width=True, hide_index=True)
    st.subheader("Allocation change by zone")
    change_fig = go.Figure()
    for _, row in comp.iterrows():
        change_fig.add_trace(go.Scatter(
            x=[row["Original allocation (L)"], row["Scenario allocation (L)"]],
            y=[row["Zone"], row["Zone"]], mode="lines+markers",
            line=dict(color="#b7c6b3", width=2), marker=dict(size=[10, 10], color=["#477b58", "#bd8b48"], line=dict(color="white", width=1)),
            showlegend=False, hovertemplate=f'{row["Zone"]}<br>%{{x:.1f}} L<extra></extra>',
        ))
    change_fig.update_layout(height=max(300, 58*len(comp)), margin=dict(l=10,r=12,t=8,b=8),
                             xaxis_title="Planned allocation (L)", yaxis_title="",
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font=dict(color="#405647"), xaxis=dict(gridcolor="#e8eee5",zeroline=False),
                             yaxis=dict(showgrid=False, autorange="reversed"))
    st.plotly_chart(change_fig, use_container_width=True)
    st.subheader("Revised water route")
    st.plotly_chart(build_farm_figure(zones, scenario["zone_rows"], available_water_l=scenario_supply), use_container_width=True)
    sankey = build_water_sankey(zones, scenario["zone_rows"], scenario_supply)
    if sankey is not None:
        st.plotly_chart(sankey, use_container_width=True)
    st.write(f"**Scenario allocation:** {scenario['allocated_l']:,.1f} L · **Unmet demand:** {scenario['shortage_l']:,.1f} L · **Demand coverage:** {100*scenario['allocated_l']/scenario['requested_l'] if scenario['requested_l'] else 100:.1f}%")
    if scenario["shortage_l"] > 0:
        worst = max(zip(zones, scenario["unmet_l"]), key=lambda item: item[1])
        st.warning(f"Largest unmet requirement is in {worst[0]['zone']} · {worst[0]['crop']}: {worst[1]:.1f} L. Priority weighting determines who receives a larger share; verify crop vulnerability and local agronomic needs.")
    if st.button("Save this shortage scenario"):
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(), "mode": "shortage scenario estimate",
            "reduction_pct": reduction, "available_water_l": scenario_supply,
            "requested_l": scenario["requested_l"], "allocated_l": scenario["allocated_l"],
            "shortage_l": scenario["shortage_l"], "strategy": strategy,
            "zones": zones, "zone_rows": scenario["zone_rows"],
            "limitations": ["Scenario is a calculated plan, not a field delivery record.", "Inputs and crop demand estimates require local validation."],
        }
        try:
            record_id = save_run(f"Water shortage {reduction}%", {"reduction_pct": reduction, "base_supply_l": water, "strategy": strategy, "zones": zones}, output, farm_name, farm_location)
            st.success(f"Shortage scenario #{record_id} saved as a separate history record.")
        except Exception as exc:
            st.error(f"Scenario could not be saved: {exc}")
    st.caption("Water Rescue compares scenarios using the exact same demand estimate and allocation functions used by the planner. No water saving is claimed without a measured baseline and outcome.")


elif page == "Smart Operations":
    render_hero("WEATHER AND FIELD OPERATIONS", "Use forecast evidence carefully.", "Open-Meteo forecast · effective-rainfall estimate · manual fallback · nominal pump energy calculation")
    st.subheader("1 · Seven-day Open-Meteo forecast")
    st.caption("Regional weather-model output from the farm coordinates. Forecast rain is not recorded rainfall and is not guaranteed to occur at the field.")
    loc1, loc2 = st.columns(2)
    latitude = loc1.number_input("Farm latitude (example default: Bengaluru)", min_value=-90.0, max_value=90.0, value=12.9716, step=0.0001, format="%.4f")
    longitude = loc2.number_input("Farm longitude (example default: Bengaluru)", min_value=-180.0, max_value=180.0, value=77.5946, step=0.0001, format="%.4f")
    st.caption("The prefilled coordinates are an example only. Replace both values with the actual farm coordinates before fetching weather; the farm profile text field does not geocode an address.")
    if st.button("Fetch current conditions and 7-day forecast", type="primary"):
        try:
            forecast_df, timezone_name, current, fetched_at = fetch_weather_forecast(latitude, longitude)
            st.session_state.weather_forecast = forecast_df
            st.session_state.weather_timezone = timezone_name
            st.session_state.weather_current = current
            st.session_state.weather_fetched_at = fetched_at
            st.session_state.weather_location = (latitude, longitude)
            payload = {"current": current, "daily": forecast_df.where(pd.notna(forecast_df), None).to_dict("records")}
            weather_id = save_weather(latitude, longitude, timezone_name, payload, farm_name, farm_location)
            st.success(f"Forecast fetched and saved as weather record #{weather_id}.")
        except Exception as exc:
            st.error(f"Weather service unavailable: {exc}. The manual rainfall fallback remains available.")
    forecast_df = st.session_state.weather_forecast
    if forecast_df is not None:
        timezone_name = st.session_state.get("weather_timezone", "Local timezone")
        current = st.session_state.get("weather_current", {})
        fetched_at = st.session_state.get("weather_fetched_at", "timestamp unavailable")
        stored_location = st.session_state.get("weather_location", (latitude, longitude))
        st.caption(f"Last successful update: {fetched_at} · Forecast timezone: {timezone_name} · Coordinates used: {stored_location[0]:.4f}, {stored_location[1]:.4f}")
        if abs(latitude-stored_location[0]) > 1e-6 or abs(longitude-stored_location[1]) > 1e-6:
            st.warning("The coordinate inputs have changed since this forecast was fetched. Fetch again to refresh the forecast for the new location.")
        if current:
            current_cols = st.columns(4)
            current_cols[0].metric("Current temperature", f"{current.get('temperature_2m', '—')} °C")
            current_cols[1].metric("Current humidity", f"{current.get('relative_humidity_2m', '—')}%")
            current_cols[2].metric("Current precipitation", f"{current.get('precipitation', '—')} mm")
            current_cols[3].metric("Current wind speed", f"{current.get('wind_speed_10m', '—')} km/h")
            st.caption("Current values are API/model context, not readings from an on-farm weather station.")
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)
        weather_chart = px.bar(forecast_df, x="Date", y="Forecast rainfall (mm)", color="Rain probability (%)", color_continuous_scale="Greens")
        weather_chart.update_layout(height=330, margin=dict(l=5, r=5, t=10, b=5))
        st.plotly_chart(weather_chart, use_container_width=True)
    else:
        st.info("No successful forecast is loaded in this session. Fetch it or use a manual expected-rainfall estimate below.")

    st.subheader("2 · Rainfall assumption for the next irrigation plan")
    manual_mode = st.checkbox("Use a manual rainfall estimate instead of the API forecast", value=forecast_df is None)
    if manual_mode:
        rainfall_mm = st.number_input("Expected rainfall (mm)", 0.0, 300.0, 0.0, 0.5)
        confidence_pct = st.slider("Confidence in this manual estimate (%)", 0, 100, 70, 5)
        selected_date = "Manual estimate"
        source_label = "Manual expected rainfall estimate"
    elif forecast_df is not None:
        selected_date = st.selectbox("Select forecast date for the plan", forecast_df["Date"].tolist())
        selected_forecast = forecast_df.loc[forecast_df["Date"] == selected_date].iloc[0]
        rainfall_value = selected_forecast["Forecast rainfall (mm)"]
        rainfall_mm = 0.0 if pd.isna(rainfall_value) else float(rainfall_value)
        probability = selected_forecast["Rain probability (%)"]
        confidence_pct = 0 if pd.isna(probability) else int(probability)
        temp_value = selected_forecast["Mean temperature (°C)"]
        humidity_value = selected_forecast["Mean humidity (%)"]
        forecast_temp = None if pd.isna(temp_value) else float(temp_value)
        forecast_humidity = None if pd.isna(humidity_value) else float(humidity_value)
        source_label = "Open-Meteo forecast"
        st.info(f"Selected forecast: {rainfall_mm:.1f} mm precipitation · {confidence_pct}% maximum daily precipitation probability · mean temperature {forecast_temp if forecast_temp is not None else 'unavailable'} °C · mean humidity {forecast_humidity if forecast_humidity is not None else 'unavailable'}%. This is forecast data, not guaranteed or measured at the field.")
    else:
        rainfall_mm = 0.0
        confidence_pct = 0
        selected_date = "No forecast"
        source_label = "Unavailable"
        forecast_temp = forecast_humidity = None
    use_forecast_environment = False
    if not manual_mode and forecast_df is not None and forecast_temp is not None and forecast_humidity is not None:
        use_forecast_environment = st.checkbox("Use selected forecast mean temperature and humidity in soil-zone demand", value=False)
    effective_pct = st.slider("Estimated effective rainfall fraction (%)", 0, 100, 75, 5)
    st.caption("Effective rainfall fraction is an operator-set planning assumption. Rainfall credit is calculated only for soil zones, only for this selected date, and is limited so adjusted demand cannot become negative. Forecast probability discounts the forecast amount; this is a simplified estimate, not a soil-water balance measurement.")
    preview_credits = []
    for zone_index, zone in enumerate(zones):
        gross = rainfall_mm * zone["area_m2"] if zone["system"] == "Soil" else 0.0
        base_demand = plan["base_demands_l"][zone_index]
        credit = min(base_demand, gross * effective_pct/100 * confidence_pct/100)
        preview_credits.append({"Zone": zone["zone"], "Crop": zone["crop"], "System": zone["system"], "Base demand (L)": base_demand, "Estimated rainfall credit (L)": credit})
    st.dataframe(pd.DataFrame(preview_credits).round(2), use_container_width=True, hide_index=True)
    if st.button("Apply this rainfall assumption to the next irrigation plan", type="primary"):
        st.session_state.weather_adjustment = {
            "rainfall_mm": float(rainfall_mm), "confidence": float(confidence_pct)/100,
            "effective_fraction": float(effective_pct)/100,
            "source": source_label, "date": selected_date,
            "use_forecast_environment": bool(use_forecast_environment),
            "temperature_c": forecast_temp if use_forecast_environment else None,
            "humidity_pct": forecast_humidity if use_forecast_environment else None,
            "label": f"{source_label} · {selected_date} · {rainfall_mm:.1f} mm",
            "fetched_at": st.session_state.get("weather_fetched_at") if not manual_mode else None,
        }
        if manual_mode:
            save_configuration("manual_weather_estimate", st.session_state.weather_adjustment, farm_name, farm_location)
        st.success("Rainfall assumption applied. Crop demand, allocations and the Farm Twin will use the adjusted plan until you remove it.")
        st.rerun()

    st.subheader("3 · Pump runtime and energy calculator")
    ec = st.columns(4)
    op_flow = ec[0].number_input("Nominal pump flow (L/min)", 1.0, 5000.0, 48.0, key="ops_flow")
    op_kw = ec[1].number_input("Pump rated power (kW)", 0.05, 500.0, 0.75, key="ops_kw")
    op_tariff = ec[2].number_input("Electricity tariff (₹/kWh)", 0.0, 10000.0, 8.0, key="ops_tariff")
    op_hours = ec[3].number_input("Available pumping hours", 0.1, 24.0, 8.0, key="ops_hours")
    ops_summary = pump_summary(plan["allocated_l"], op_flow, op_kw, op_tariff, op_hours)
    m = st.columns(4)
    m[0].metric("Water to deliver", f"{ops_summary['water_l']:,.1f} L")
    m[1].metric("Estimated runtime", f"{ops_summary['runtime_min']:.1f} min")
    m[2].metric("Estimated energy", f"{ops_summary['energy_kwh']:.2f} kWh")
    m[3].metric("Estimated electricity cost", f"₹{ops_summary['electricity_cost']:.2f}")
    if ops_summary["fits_window"]:
        st.success(f"The nominal-flow estimate fits within {op_hours:.1f} available pumping hours.")
    else:
        st.error(f"The estimate exceeds the pumping window by {ops_summary['overrun_min']:.1f} minutes.")
    st.caption("Pump specifications are operator-entered. AquaTwin estimates delivery time and energy; it does not monitor actual flow, meter electricity, detect leaks, or command a pump.")


elif page == "Operations History":
    render_hero("OPERATIONAL RECORDS", "Keep plans separate from field outcomes.", "SQLite persistence · configuration snapshots · manual actual-irrigation entries · weather fetch logs")
    runs = list_runs()
    actual_records = list_actual_irrigation()
    if not runs:
        st.info("No irrigation plans or shortage scenarios have been saved yet. Generate one from Smart Irrigation Planner or Water Rescue.")
    else:
        run_frame = pd.DataFrame([{"Plan ID": r["id"], "Scenario": r["scenario"], "Created": r["created_at"], "Demand (L)": r["outputs"].get("requested_l", r["outputs"].get("demand_l", 0)), "Allocated (L)": r["outputs"].get("allocated_l", 0), "Unmet (L)": r["outputs"].get("shortage_l", r["outputs"].get("unmet_l", 0))} for r in runs])
        st.subheader("Saved plans and scenarios")
        st.dataframe(run_frame, use_container_width=True, hide_index=True)
        export_a, export_b = st.columns(2)
        export_a.download_button("Export plan history CSV", run_frame.to_csv(index=False).encode("utf-8-sig"), "aquatwin_plan_history.csv", "text/csv")
        export_b.download_button("Export plan history JSON", json.dumps(runs, indent=2, default=str).encode("utf-8"), "aquatwin_plan_history.json", "application/json")
        valid_runs = [r for r in runs if r["outputs"].get("zone_rows")]
        if valid_runs:
            run_lookup = {r["id"]: r for r in valid_runs}
            selected_plan_id = st.selectbox("Select a saved plan to record field delivery", list(run_lookup), format_func=lambda rid: f"Plan #{rid} · {run_lookup[rid]['scenario']} · {run_lookup[rid]['created_at'][:19]}")
            chosen_plan = run_lookup[selected_plan_id]
            plan_zone_codes = [r["Zone"] for r in chosen_plan["outputs"]["zone_rows"]]
            with st.form("actual_irrigation_form"):
                actual_zone = st.selectbox("Zone irrigated", plan_zone_codes)
                actual_water = st.number_input("Actual water delivered (L)", min_value=0.0, max_value=10000000.0, value=0.0, step=10.0)
                actual_runtime = st.number_input("Actual pump runtime (minutes, optional)", min_value=0.0, max_value=100000.0, value=0.0, step=1.0)
                actual_notes = st.text_area("Field notes", placeholder="Operator-entered observations, delivery method, meter reading reference…")
                submitted = st.form_submit_button("Save actual irrigation record", type="primary")
            if submitted:
                try:
                    record_id = save_actual_irrigation(actual_zone, actual_water, selected_plan_id, actual_runtime if actual_runtime > 0 else None, actual_notes, farm_name, farm_location)
                    st.success(f"Actual irrigation entry #{record_id} saved. The selected plan remains unchanged.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Actual record could not be saved: {exc}")
    st.subheader("Actual irrigation records")
    if actual_records:
        actual_frame = pd.DataFrame(actual_records).rename(columns={"plan_id": "Plan ID", "zone": "Zone", "actual_water_l": "Actual water (L)", "runtime_min": "Actual runtime (min)", "recorded_at": "Recorded at", "notes": "Notes", "source": "Source"})
        st.dataframe(actual_frame, use_container_width=True, hide_index=True)
        st.download_button("Export actual irrigation CSV", actual_frame.to_csv(index=False).encode("utf-8-sig"), "aquatwin_actual_irrigation.csv", "text/csv")
        st.download_button("Export actual irrigation JSON", json.dumps(actual_records, indent=2, default=str).encode("utf-8"), "aquatwin_actual_irrigation.json", "application/json")
    else:
        st.info("No actual delivery has been entered. A generated plan does not automatically become a completed operation.")
    st.subheader("Weather update history")
    weather_records = list_weather_records()
    if weather_records:
        weather_frame = pd.DataFrame([{ "Record ID": r["id"], "Source": r["source"], "Fetched at": r["fetched_at"], "Latitude": r["latitude"], "Longitude": r["longitude"], "Timezone": r["timezone"] } for r in weather_records])
        st.dataframe(weather_frame, use_container_width=True, hide_index=True)
        weather_a, weather_b = st.columns(2)
        weather_a.download_button("Export weather log CSV", weather_frame.to_csv(index=False).encode("utf-8-sig"), "aquatwin_weather_history.csv", "text/csv")
        weather_b.download_button("Export weather records JSON", json.dumps(weather_records, indent=2, default=str).encode("utf-8"), "aquatwin_weather_history.json", "application/json")
    else:
        st.caption("No successful Open-Meteo forecast fetch is stored yet.")
    st.caption("All historical entries are append-only. Configuration snapshots and plan records are not silently overwritten; actual-irrigation rows are manual operator records.")


elif page == "Cost & Performance":
    render_hero("FARM PERFORMANCE", "Evaluate demand, distribution and operating effort.", "Metrics are calculated from the active plan and saved records; no unverified savings or yield claims")
    c = st.columns(4)
    c[0].metric("Estimated demand", f"{plan['requested_l']:,.1f} L")
    c[1].metric("Planned allocation", f"{plan['allocated_l']:,.1f} L")
    c[2].metric("Unmet estimate", f"{plan['shortage_l']:,.1f} L")
    c[3].metric("Demand covered", f"{coverage_pct:.1f}%")
    st.subheader("Demand and allocation by zone")
    st.caption("Each line spans planned allocation to estimated demand. The gap is unmet demand for that zone.")
    perf = go.Figure()
    for _, row in pdf.iterrows():
        perf.add_trace(go.Scatter(
            x=[row["Allocation (L)"], row["Demand (L)"]], y=[row["Zone"], row["Zone"]],
            mode="lines+markers", line=dict(color="#c5d1c1", width=3),
            marker=dict(size=[11, 11], color=["#477b58", "#bd8b48"], line=dict(color="white", width=1)),
            showlegend=False, hovertemplate=f'{row["Zone"]} · {row["Crop"]}<br>%{{x:.1f}} L<extra></extra>',
        ))
    perf.update_layout(height=max(300, 55*len(pdf)), margin=dict(l=10,r=12,t=8,b=8),
                       xaxis_title="Water quantity (L)", yaxis_title="",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       font=dict(color="#405647"), xaxis=dict(gridcolor="#e8eee5",zeroline=False),
                       yaxis=dict(showgrid=False,autorange="reversed"))
    st.plotly_chart(perf, use_container_width=True)
    st.subheader("Allocation strategy comparison")
    alternate_name = "Proportional sharing" if strategy == "Priority protection" else "Priority protection"
    alt = allocate([r["Demand (L)"] for r in plan_rows], water, plan["urgency"], alternate_name)
    compare = pd.DataFrame({
        "Zone": [z["zone"] for z in zones], "Crop": [z["crop"] for z in zones],
        "Selected allocation (L)": np.round(plan["allocation_l"], 2),
        "Alternative allocation (L)": np.round(alt["allocation_l"], 2),
        "Selected unmet (L)": np.round(plan["unmet_l"], 2),
        "Alternative unmet (L)": np.round(alt["unmet_l"], 2),
    })
    st.dataframe(compare, use_container_width=True, hide_index=True)
    st.caption("The strategy comparison is a what-if calculation. Neither strategy is universally optimal; validate the priority weights against the farm's agronomic objectives.")

    records = list_runs()
    if records:
        hist = pd.DataFrame([{"Plan ID": r["id"], "Created": r["created_at"], "Scenario": r["scenario"], "Demand (L)": r["outputs"].get("requested_l", r["outputs"].get("demand_l", 0)), "Allocated (L)": r["outputs"].get("allocated_l", 0), "Unmet (L)": r["outputs"].get("shortage_l", r["outputs"].get("unmet_l", 0))} for r in records])
        st.subheader("Saved plan history")
        st.dataframe(hist, use_container_width=True, hide_index=True)
        time_chart = px.line(hist.sort_values("Created"), x="Created", y=["Demand (L)", "Allocated (L)", "Unmet (L)"], markers=True)
        st.plotly_chart(time_chart, use_container_width=True)
    else:
        st.info("Save plans over time to build a historical comparison. This screen does not generate historical values artificially.")

    actual_records = list_actual_irrigation()
    st.subheader("Planned versus manually recorded irrigation")
    if actual_records:
        plan_map = {r["id"]: r for r in records}
        actual_rows = []
        for actual in actual_records:
            plan_rec = plan_map.get(actual["plan_id"])
            planned = None
            if plan_rec:
                match = next((z for z in plan_rec["outputs"].get("zone_rows", []) if z.get("Zone") == actual["zone"]), None)
                planned = match.get("Allocation (L)") if match else None
            actual_rows.append({"Plan ID": actual["plan_id"], "Zone": actual["zone"], "Planned (L)": planned, "Actual (L)": actual["actual_water_l"], "Difference (L)": None if planned is None else actual["actual_water_l"]-planned, "Recorded": actual["recorded_at"]})
        actual_compare = pd.DataFrame(actual_rows)
        st.dataframe(actual_compare, use_container_width=True, hide_index=True)
    else:
        st.info("No manual field-delivery records exist yet. Planned allocations remain separate from actual irrigation.")

    current_export = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "farm_name": farm_name, "farm_location": farm_location,
        "data_mode": "manual inputs + estimated demand + calculated planned allocation",
        "available_water_l": float(water), "strategy": strategy, "demand_basis": plan["demand_basis"],
        "requested_l": float(plan["requested_l"]), "allocated_l": float(plan["allocated_l"]),
        "shortage_l": float(plan["shortage_l"]), "zone_rows": plan_rows,
        "limitations": ["No connected farm sensors, flow meters or pump controller.", "Weather forecasts are not recorded rainfall.", "Demand methods are estimates, not field validated.", "Plans are not actual irrigation records."],
    }
    x1, x2 = st.columns(2)
    with x1:
        st.download_button("Export current plan (CSV)", pdf.to_csv(index=False).encode("utf-8-sig"), "aquatwin_current_plan.csv", "text/csv")
    with x2:
        st.download_button("Export current report (JSON)", json.dumps(current_export, indent=2, default=str).encode("utf-8"), "aquatwin_current_report.json", "application/json")
    if records:
        all_export = [{"id": r["id"], "scenario": r["scenario"], "created_at": r["created_at"], "inputs": r["inputs"], "outputs": r["outputs"]} for r in records]
        hist_a, hist_b = st.columns(2)
        hist_a.download_button("Export complete plan history (CSV)", hist.to_csv(index=False).encode("utf-8-sig"), "aquatwin_plan_history.csv", "text/csv")
        hist_b.download_button("Export complete plan history (JSON)", json.dumps(all_export, indent=2, default=str).encode("utf-8"), "aquatwin_plan_history.json", "application/json")


st.divider()
st.caption("AquaTwin AI v12 · Streamlit decision-support prototype · Open-Meteo forecast is external model data · farm readings and pump specifications are manual · soil profile layers are estimated schematics · planned distribution is not measured flow · no live sensor connection or automatic irrigation control · demand estimates are not field-validated")
