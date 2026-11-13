"""Data-bound dashboard visualizations for the AquaTwin command centre."""
from __future__ import annotations

import plotly.graph_objects as go


STATUS_COLORS = {
    "Critical": "#b85c4d",
    "Shortage": "#bd8b48",
    "Covered": "#4c8a5d",
}


def build_allocation_treemap(zone_rows: list[dict]) -> go.Figure | None:
    """Treemap sized by calculated planned litres for zones receiving water."""
    included = [row for row in zone_rows if float(row.get("Allocation (L)", 0) or 0) > 0]
    if not included:
        return None
    fig = go.Figure(go.Treemap(
        labels=[f'{row["Zone"]} · {row["Crop"]}' for row in included],
        parents=["Allocated water"] * len(included),
        values=[float(row["Allocation (L)"]) for row in included],
        marker=dict(
            colors=[STATUS_COLORS.get(row.get("Status"), "#4c8a5d") for row in included],
            line=dict(color="#f5f6f1", width=3),
        ),
        texttemplate="%{label}<br>%{value:.1f} L",
        hovertemplate="%{label}<br>Planned allocation: %{value:.1f} L<extra></extra>",
        branchvalues="total",
    ))
    fig.update_layout(
        height=280, margin=dict(l=2, r=2, t=8, b=2),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#294434", size=12),
    )
    return fig


def build_coverage_gauge(coverage_pct: float) -> go.Figure:
    """Gauge of allocated demand coverage from the active irrigation plan."""
    value = max(0.0, min(100.0, float(coverage_pct)))
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": "%", "font": {"size": 38, "color": "#173b2b", "family": "Manrope"}},
        title={"text": "of estimated demand allocated", "font": {"size": 13, "color": "#718176"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#dfe6dc"},
            "bar": {"color": "#4c8a5d", "thickness": .25},
            "bgcolor": "#edf1ea", "borderwidth": 0,
            "steps": [
                {"range": [0, 50], "color": "#f5e8e3"},
                {"range": [50, 80], "color": "#f3eedf"},
                {"range": [80, 100], "color": "#e5eee3"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=18, r=18, t=42, b=8), paper_bgcolor="rgba(0,0,0,0)")
    return fig
