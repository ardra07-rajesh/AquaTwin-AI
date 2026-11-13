"""Plotly visualizations driven by calculated AquaTwin plans (not sensor streams)."""
from __future__ import annotations

import plotly.graph_objects as go


CROP_COLORS = {
    "Tomato": "#c65a43", "Lettuce": "#5e9f63", "Cucumber": "#4d8a55",
    "Rice": "#b6a65d", "Basil": "#4e9d80", "Strawberry": "#be6480",
    "Wheat": "#c5a45c", "Cotton": "#d6d0bd", "Maize": "#d6b34e",
    "Spinach": "#4a8a59", "Kale": "#437e50",
}
STATUS_COLORS = {"Critical": "#d66a55", "Shortage": "#d6a34a", "Covered": "#6f9d78"}


def zone_layout(count: int):
    """Stable 3-column zone footprint, suitable for the six-zone prototype."""
    positions = []
    for i in range(count):
        col = i % 3
        row = i // 3
        positions.append({"x": col * 11.5 + 1.0, "y": row * 10.5 + 1.0, "w": 9.4, "h": 7.8})
    return positions


def build_farm_figure(zones: list[dict], zone_rows: list[dict], selected_zone: str | None = None, available_water_l: float | None = None) -> go.Figure:
    """Create a rotatable 3D farm scene with plan-derived water-route overlays."""
    fig = go.Figure()
    positions = zone_layout(len(zones))
    row_by_zone = {str(r.get("Zone", r.get("zone", ""))): r for r in zone_rows}

    # Farm ground slab and boundary.
    fig.add_trace(go.Mesh3d(
        x=[0, 32.8, 32.8, 0], y=[0, 0, 20.0, 20.0], z=[0, 0, 0, 0],
        i=[0, 0], j=[1, 2], k=[2, 3], color="#d9d1b9", opacity=0.28,
        name="Farm ground", hoverinfo="skip", showscale=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[0, 32.8, 32.8, 0, 0], y=[0, 0, 20, 20, 0], z=[0.08]*5,
        mode="lines", line=dict(color="#9a9a79", width=5), name="Farm boundary", hoverinfo="skip",
    ))

    # Reservoir: cylindrical mesh at the head of the distribution network.
    import math
    theta = [2 * math.pi * i / 36 for i in range(37)]
    tank_x = [-4.0 + 1.65 * math.cos(t) for t in theta]
    tank_y = [9.6 + 1.65 * math.sin(t) for t in theta]
    side_i, side_j, side_k = [], [], []
    for ring_index in range(36):
        nxt = ring_index + 1
        side_i.extend([ring_index, ring_index])
        side_j.extend([nxt, 37+nxt])
        side_k.extend([37+nxt, 37+ring_index])
    fig.add_trace(go.Mesh3d(
        x=tank_x + tank_x, y=tank_y + tank_y,
        z=[0.15]*len(theta) + [3.1]*len(theta),
        i=side_i, j=side_j, k=side_k,
        color="#5f9fbd", opacity=0.70, name="Reservoir (planned supply)",
        hovertemplate="Reservoir<br>Available supply input: %{text}<extra></extra>",
        text=[f"{available_water_l:,.1f} L (manual supply input)" if available_water_l is not None else "manual supply input"] * (2 * len(theta)),
        showscale=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-4.0], y=[9.6], z=[3.35], mode="text",
        text=[f"RESERVOIR · {available_water_l:,.0f} L" if available_water_l is not None else "RESERVOIR"], textfont=dict(size=10, color="#174b64"), showlegend=False, hoverinfo="skip",
    ))

    # Pump symbol and main header.
    fig.add_trace(go.Scatter3d(
        x=[-1.0], y=[9.6], z=[0.7], mode="markers+text",
        marker=dict(size=12, color="#354b4b", symbol="square", line=dict(color="#ffffff", width=2)),
        text=["PUMP"], textposition="bottom center", textfont=dict(size=10, color="#334b45"),
        name="Pump", hovertemplate="Pump<br>Planning model node (not a connected controller)<extra></extra>",
    ))
    main_x = [-2.3, -1.0, 0.5, 10.0, 21.5, 32.0]
    main_y = [9.6] * len(main_x)
    fig.add_trace(go.Scatter3d(
        x=main_x, y=main_y, z=[0.45]*len(main_x), mode="lines",
        line=dict(color="#4b9cc5", width=7), name="Main supply pipeline",
        hovertemplate="Main line<br>Planned distribution route<extra></extra>",
    ))

    # Each zone bed, crop rows and branch line use the same allocation output.
    for idx, (zone, pos) in enumerate(zip(zones, positions)):
        code = str(zone.get("zone", f"Z{idx+1:02d}"))
        r = row_by_zone.get(code, {})
        demand = float(r.get("Demand (L)", r.get("demand_l", 0)) or 0)
        allocation = float(r.get("Allocation (L)", r.get("allocation_l", 0)) or 0)
        unmet = float(r.get("Unmet (L)", r.get("unmet_l", max(0, demand-allocation))) or 0)
        urgency = float(r.get("Urgency score", r.get("urgency", 1)) or 1)
        status = str(r.get("Status", "Covered"))
        planned_order = r.get("Irrigation order", idx + 1)
        crop = str(zone.get("crop", "Crop"))
        x0, y0, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
        is_selected = code == selected_zone
        edge_color = "#153f2b" if is_selected else STATUS_COLORS.get(status, "#6f9d78")
        bed_color = "#7d8c66" if zone.get("system") == "Soil" else "#809d9b"
        fig.add_trace(go.Mesh3d(
            x=[x0, x0+w, x0+w, x0], y=[y0, y0, y0+h, y0+h], z=[0.18]*4,
            i=[0, 0], j=[1, 2], k=[2, 3], color=bed_color,
            opacity=0.74, name=f"{code} bed", showscale=False,
            hovertemplate=(f"{code} · {crop}<br>Demand: {demand:.1f} L<br>Planned allocation: {allocation:.1f} L"
                           f"<br>Unmet: {unmet:.1f} L<br>Status: {status}<extra></extra>"),
        ))
        # Border emphasizes the selected zone without changing its underlying values.
        fig.add_trace(go.Scatter3d(
            x=[x0, x0+w, x0+w, x0, x0], y=[y0, y0, y0+h, y0+h, y0], z=[0.28]*5,
            mode="lines", line=dict(color=edge_color, width=8 if is_selected else 3),
            showlegend=False, hoverinfo="skip",
        ))

        plant_x, plant_y, plant_z, root_x, root_y, root_z = [], [], [], [], [], []
        for rr in range(4):
            for cc in range(5):
                px = x0 + 1.15 + cc * (w - 2.3) / 4
                py = y0 + 1.2 + rr * (h - 2.4) / 3
                height = 1.1 + (idx % 3) * 0.12
                plant_x.append(px); plant_y.append(py); plant_z.append(0.35 + height)
                root_x.extend([px, px, None]); root_y.extend([py, py, None]); root_z.extend([0.35, 0.35+height, None])
        fig.add_trace(go.Scatter3d(
            x=root_x, y=root_y, z=root_z, mode="lines",
            line=dict(color="#426c3e", width=2), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter3d(
            x=plant_x, y=plant_y, z=plant_z, mode="markers",
            marker=dict(size=5 if not is_selected else 7, color=CROP_COLORS.get(crop, "#639b5e"), symbol="circle", line=dict(color="#f5f5e8", width=0.6)),
            name=f"{code} · {crop}",
            hovertemplate=f"{code} · {crop}<br>Crop-row marker<br>Planned zone allocation: {allocation:.1f} L<extra></extra>",
        ))
        center_x, center_y = x0 + w/2, y0 + h/2
        fig.add_trace(go.Scatter3d(
            x=[center_x], y=[center_y], z=[2.25], mode="text",
            text=[f"{code} · {crop}<br>{allocation:,.0f} L planned"],
            textfont=dict(size=10 if not is_selected else 12, color="#1d3829"),
            showlegend=False, hovertemplate=f"{code}<br>Demand {demand:.1f} L<br>Allocated {allocation:.1f} L<br>Unmet {unmet:.1f} L<br>Urgency {urgency:.2f}<extra></extra>",
        ))

        # Branch pipe from main header to the centre of the zone.
        pipe_width = 2.0 + min(6.0, allocation / max(1.0, demand) * 5.0)
        branch_color = "#2384b7" if allocation > 0 else "#9aa7a0"
        fig.add_trace(go.Scatter3d(
            x=[center_x, center_x], y=[9.6, center_y], z=[0.45, 0.45], mode="lines",
            line=dict(color=branch_color, width=pipe_width, dash="solid" if allocation > 0 else "dot"),
            name=f"{code} planned branch", showlegend=False,
            hovertemplate=f"{code} branch<br>Planned allocation: {allocation:.1f} L<br>Demand: {demand:.1f} L<extra></extra>",
        ))
        if allocation > 0:
            fig.add_trace(go.Scatter3d(
                x=[center_x], y=[center_y], z=[0.58], mode="markers+text",
                marker=dict(size=6, color="#55b6d8", symbol="diamond"),
                text=[f"{planned_order}"], textposition="top center", textfont=dict(size=9, color="#155c7a"),
                showlegend=False, hovertemplate=f"Planned irrigation order: {planned_order}<br>{code}: {allocation:.1f} L<extra></extra>",
            ))

    fig.update_layout(
        height=640, margin=dict(l=0, r=0, t=12, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color="#29443a", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, x=0.01, bgcolor="rgba(255,255,255,0.62)"),
        scene=dict(
            xaxis=dict(visible=False, range=[-7, 34]),
            yaxis=dict(visible=False, range=[-1, 21]),
            zaxis=dict(visible=False, range=[0, 5.0]),
            aspectmode="manual", aspectratio=dict(x=1.75, y=1.0, z=0.38),
            camera=dict(eye=dict(x=1.55, y=1.55, z=1.18)),
            bgcolor="rgba(236,244,235,0.45)",
        ),
        title=dict(text="Farm twin · rotate and zoom to inspect zones", x=0.02, y=0.98, font=dict(size=15)),
    )
    return fig


def build_water_sankey(zones: list[dict], zone_rows: list[dict], available_water_l: float | None = None) -> go.Figure | None:
    """Water network Sankey. Values are calculated planned litres, not meter readings."""
    rows = {str(r.get("Zone", r.get("zone", ""))): r for r in zone_rows}
    selected = []
    total = 0.0
    for zone in zones:
        code = str(zone.get("zone", ""))
        row = rows.get(code, {})
        allocated = float(row.get("Allocation (L)", row.get("allocation_l", 0)) or 0)
        demand = float(row.get("Demand (L)", row.get("demand_l", 0)) or 0)
        if allocated > 1e-8:
            selected.append((code, str(zone.get("crop", "Crop")), allocated, demand))
            total += allocated
    if total <= 0:
        return None
    supply_label = f"{available_water_l:,.1f} L available" if available_water_l is not None else "supply input"
    labels = [f"Reservoir\n{supply_label}", f"Pump\n{total:,.1f} L scheduled"]
    labels.extend([f"{code} · {crop}\n{alloc:,.1f} L / {demand:,.1f} L demand" for code, crop, alloc, demand in selected])
    sources = [0] + [1] * len(selected)
    targets = [1] + [i + 2 for i in range(len(selected))]
    values = [total] + [item[2] for item in selected]
    colors = ["#65a9c3", "#4c7890"] + ["#73a47a" if a >= d - 1e-6 else "#d1a35b" for _, _, a, d in selected]
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=22, thickness=22, line=dict(color="rgba(44,72,57,.35)", width=1), label=labels, color=colors),
        link=dict(source=sources, target=targets, value=values,
                  color=["rgba(69,151,190,.42)"] + ["rgba(85,153,107,.38)" if a >= d - 1e-6 else "rgba(208,158,77,.45)" for _, _, a, d in selected]),
    ))
    fig.update_layout(height=420, margin=dict(l=15, r=15, t=15, b=15), paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12, color="#29443a"))
    return fig


def build_soil_profile_figure(zone: dict, allocation_l: float, efficiency: float) -> tuple[go.Figure, dict]:
    """Create an estimated soil slice from one surface-moisture input.

    The depth gradient is an explicit illustrative assumption, not a physical
    infiltration model or depth sensor reading.
    """
    surface = float(zone.get("moisture", 0))
    area = max(0.01, float(zone.get("area_m2", 1)))
    planned_net_mm = float(allocation_l) / area * float(efficiency)
    depth_values = [surface, max(0.0, surface - 5.0), max(0.0, surface - 12.0)]
    layers = ["0–15 cm · topsoil", "15–30 cm · root zone", "30–45 cm · lower profile"]
    x_positions = list(range(0, 101, 10))
    z_values = [[max(0.0, min(100.0, value - abs(x-50)*0.025)) for x in x_positions] for value in depth_values]
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        x=x_positions, y=layers, z=z_values,
        colorscale=[[0, "#e7d9bd"], [0.35, "#b8c99e"], [0.7, "#5e9a70"], [1, "#286447"]],
        zmin=0, zmax=100, colorbar=dict(title="Moisture index (%)", thickness=12),
        hovertemplate="Position in zone: %{x}%<br>%{y}<br>Estimated moisture index: %{z:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        height=290, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Schematic position across zone", yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#d9d0b8",
        font=dict(color="#29443a", size=10),
    )
    summary = {
        "planned_net_irrigation_mm": planned_net_mm,
        "estimated_moisture_by_layer_pct": depth_values,
        "root_zone_deficit_index_pct_points": max(0.0, 75.0-surface),
        "surface_moisture_margin_to_action_threshold_pct_points": surface - 35.0,
        "assumed_profile_depth_cm": 45,
    }
    return fig, summary
