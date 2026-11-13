import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import textwrap
from ui.assets import GREENHOUSE_URI, LEAF_URI, LETTUCE_THUMB_URI, SIDEBAR_FOLIAGE_URI



def normalize_html_content(html_content):
    """Normalize HTML fragments so indentation cannot turn them into Markdown code blocks."""
    if not isinstance(html_content, str):
        raise TypeError("html_content must be a string")
    return textwrap.dedent(html_content).strip()

def render_html(html_content, unsafe_allow_html=True):
    """Render a custom HTML fragment with Streamlit's native HTML renderer when available.

    The keyword is retained for compatibility with the former st.markdown call sites.
    Older Streamlit releases fall back to Markdown's explicit HTML opt-in.
    """
    content = normalize_html_content(html_content)
    import streamlit as st
    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        return html_renderer(content)
    return st.markdown(content, unsafe_allow_html=unsafe_allow_html)


# Common chart layout helper
def get_clean_chart_layout(height=180, margin=None):
    if margin is None:
        margin = dict(l=8, r=8, t=28, b=12)
    return dict(
        height=height,
        margin=margin,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#334155", size=11),
        xaxis=dict(showgrid=True, gridcolor="rgba(226, 236, 242, 0.7)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(226, 236, 242, 0.7)", zeroline=False),
        hovermode="x unified",
    )

def render_top_header_html(date_str=None, temp_str="Demo telemetry", location_str="Location not configured", unread_alerts=0):
    if date_str is None:
        date_str = datetime.now().astimezone().strftime("%b %d, %Y  %I:%M %p")
    return f"""
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 22px; flex-wrap: wrap;">
      <!-- Search Input Container -->
      <div style="flex: 1; min-width: 260px; max-width: 480px; position: relative;">
        <div style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #94a3b8; pointer-events: none; display: flex; align-items: center;">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        </div>
        <input type="text" placeholder="Search farms, zones, crops, or features..." style="width: 100%; padding: 10px 14px 10px 42px; background: #ffffff; border: 1px solid #dbe6ec; border-radius: 24px; font-size: 0.84rem; color: #1e293b; outline: none; box-shadow: 0 2px 8px rgba(15,42,60,0.03);" />
      </div>

      <!-- Right Header Status Controls -->
      <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
        <!-- Demo telemetry badge -->
        <div style="display: flex; align-items: center; gap: 8px; background: #ffffff; border: 1px solid #e1ebf0; padding: 7px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; color: #1e293b; box-shadow: 0 2px 6px rgba(15,42,60,0.02);">
          <span style="color: #f59e0b; display: flex; align-items: center;">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path></svg>
          </span>
          <span>{temp_str}</span>
        </div>

        <!-- Location Badge -->
        <div style="display: flex; align-items: center; gap: 6px; background: #ffffff; border: 1px solid #e1ebf0; padding: 7px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; color: #475569; box-shadow: 0 2px 6px rgba(15,42,60,0.02);">
          <span style="color: #0ea5e9; display: flex; align-items: center;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path><circle cx="12" cy="10" r="3"></circle></svg>
          </span>
          <span>{location_str}</span>
        </div>

        <!-- Date & Time -->
        <div style="font-size: 0.82rem; font-weight: 600; color: #64748b; padding: 0 4px;">
          {date_str}
        </div>

        <!-- Notification Bell -->
        <div style="position: relative; width: 38px; height: 38px; border-radius: 50%; background: #ffffff; border: 1px solid #e1ebf0; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #475569; box-shadow: 0 2px 6px rgba(15,42,60,0.02);">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path></svg>
          <span style="position: absolute; top: -2px; right: -2px; background: #ef4444; color: white; font-size: 0.65rem; font-weight: 800; width: 17px; height: 17px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #ffffff;">{unread_alerts}</span>
        </div>

        <!-- Leaf Farm Status Icon -->
        <div style="width: 38px; height: 38px; border-radius: 50%; background: #ecfdf5; border: 1px solid #a7f3d0; display: flex; align-items: center; justify-content: center; color: #10b981;">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>
        </div>
      </div>
    </div>
    """

def render_welcome_banner_html(user_name="Farm Operator", total_area_m2=480, cultivation_mode="Soil + Hydroponic", status_headline="Simulation Environment", status_sub="Illustrative data only"):
    return f"""
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 22px; flex-wrap: wrap;">
      <div>
        <div style="font-family: 'Manrope', sans-serif; font-size: 1.88rem; font-weight: 800; color: #0d2332; line-height: 1.2;">
          Good Morning, {user_name} 👋
        </div>
        <div style="font-size: 0.92rem; color: #577387; margin-top: 4px; font-weight: 500;">
          Here's what's happening with your farm today.
        </div>
      </div>

      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <!-- Farm Status Pill -->
        <div style="display: flex; align-items: center; gap: 10px; background: #eefcf3; border: 1px solid #b8f0ca; padding: 8px 16px; border-radius: 14px; box-shadow: 0 2px 8px rgba(34,197,94,0.06);">
          <div style="width: 28px; height: 28px; border-radius: 50%; background: #22c55e; display: flex; align-items: center; justify-content: center; color: white;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path></svg>
          </div>
          <div>
            <div style="font-size: 0.78rem; font-weight: 750; color: #166534; line-height: 1.1;">{status_headline}</div>
            <div style="font-size: 0.70rem; color: #15803d; font-weight: 500;">{status_sub} &rsaquo;</div>
          </div>
        </div>

        <!-- Total Farm Area -->
        <div style="display: flex; align-items: center; gap: 9px; background: #ffffff; border: 1px solid #e1ebf0; padding: 8px 14px; border-radius: 14px; box-shadow: 0 2px 6px rgba(15,42,60,0.03);">
          <div style="width: 28px; height: 28px; border-radius: 8px; background: #ecfdf5; display: flex; align-items: center; justify-content: center; color: #10b981;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
          </div>
          <div>
            <div style="font-size: 0.68rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.03em;">Total Farm Area</div>
            <div style="font-size: 0.95rem; font-weight: 800; color: #0f2434; font-family: 'Manrope', sans-serif;">{total_area_m2} m²</div>
          </div>
        </div>

        <!-- Cultivation Mode -->
        <div style="display: flex; align-items: center; gap: 9px; background: #ffffff; border: 1px solid #e1ebf0; padding: 8px 14px; border-radius: 14px; box-shadow: 0 2px 6px rgba(15,42,60,0.03);">
          <div style="width: 28px; height: 28px; border-radius: 8px; background: #ecfeff; display: flex; align-items: center; justify-content: center; color: #06b6d4;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
          </div>
          <div>
            <div style="font-size: 0.68rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.03em;">Cultivation Mode</div>
            <div style="font-size: 0.95rem; font-weight: 800; color: #0f2434; font-family: 'Manrope', sans-serif;">{cultivation_mode}</div>
          </div>
        </div>
      </div>
    </div>
    """

def create_sparkline_fig(y_series, color="#22c55e", fill_rgba="rgba(34, 197, 94, 0.12)", height=38):
    fig = go.Figure(
        go.Scatter(
            y=y_series,
            mode="lines",
            line=dict(color=color, width=2.4, shape="spline"),
            fill="tozeroy",
            fillcolor=fill_rgba,
            hoverinfo="skip"
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=2, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False
    )
    return fig

def render_plant_health_gauge_svg(score_pct=96):
    # Circular SVG gauge with clean emerald stroke
    radius = 38
    circ = 2 * 3.14159 * radius
    stroke_offset = circ * (1 - score_pct / 100.0)
    return f"""
    <div style="position: relative; width: 92px; height: 92px; display: flex; align-items: center; justify-content: center;">
      <svg width="92" height="92" viewBox="0 0 92 92" style="transform: rotate(-90deg);">
        <circle cx="46" cy="46" r="{radius}" fill="none" stroke="#e2ece7" stroke-width="8"></circle>
        <circle cx="46" cy="46" r="{radius}" fill="none" stroke="#22c55e" stroke-width="8" stroke-linecap="round" stroke-dasharray="{circ}" stroke-dashoffset="{stroke_offset}"></circle>
      </svg>
      <div style="position: absolute; text-align: center;">
        <div style="font-family: 'Manrope', sans-serif; font-size: 1.25rem; font-weight: 800; color: #0f2331; line-height: 1;">{score_pct}%</div>
      </div>
    </div>
    """
def create_3d_farm_digital_twin_fig(farm):
    """
    Renders an interactive 3D digital twin greenhouse model using configured demo-zone values.
    """
    xs, ys, zs, texts, colors = [], [], [], [], []
    
    # 2 rows of 12 racks, 2 tiers each (48 rack stations)
    for i, z in enumerate(farm.zones):
        # Place zone racks
        row = 1 if i < 6 else 2
        col = (i % 6) * 2 + 1
        for sub in [0, 1]:
            rack_num = (i * 2) + sub + 1
            x = col + sub
            y = row * 3.5
            z_pos = z.tier * 1.8
            xs.append(x)
            ys.append(y)
            zs.append(z_pos)
            
            status_color = "#22c55e" if z.status == "Optimal" else "#f59e0b" if z.status == "Warning" else "#ef4444"
            colors.append(status_color)
            
            info = f"<b>Rack #{rack_num:02d} ({z.zone_id})</b><br>" \
                   f"Crop: {z.crop}<br>" \
                   f"System: {z.method.title()}<br>" \
                   f"Tier: {z.tier}<br>" \
                   f"Plants: {z.plants // 2}<br>" \
                   f"Status: {z.status}"
            if z.method == "soil":
                info += f"<br>Moisture: {z.moisture_pct:.0f}%"
            else:
                info += f"<br>Reservoir: {z.reservoir_l:.0f} L"
            texts.append(info)
            
    fig = go.Figure()
    
    # Ground greenhouse footprint grid
    fig.add_trace(go.Scatter3d(
        x=[0, 14, 14, 0, 0],
        y=[0, 0, 10, 10, 0],
        z=[0, 0, 0, 0, 0],
        mode="lines",
        line=dict(color="#94a3b8", width=3),
        name="Footprint (480 m²)",
        hoverinfo="skip"
    ))
    
    # Structural Rack Columns
    for x, y in zip(xs, ys):
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[y, y], z=[0, 4.0],
            mode="lines",
            line=dict(color="#cbd5e1", width=2),
            hoverinfo="skip",
            showlegend=False
        ))
        
    # Active Plant Racks (Markers)
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="markers",
        marker=dict(
            size=11,
            color=colors,
            symbol="diamond",
            opacity=0.92,
            line=dict(color="#ffffff", width=1.5)
        ),
        text=texts,
        hoverinfo="text",
        name="Active Racks"
    ))
    
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(title="Greenhouse Length (m)", showgrid=True, gridcolor="#e2e8f0", backgroundcolor="rgba(240,249,255,0.4)"),
            yaxis=dict(title="Aisle Width (m)", showgrid=True, gridcolor="#e2e8f0", backgroundcolor="rgba(240,249,255,0.4)"),
            zaxis=dict(title="Tier Height (m)", showgrid=True, gridcolor="#e2e8f0", backgroundcolor="rgba(240,249,255,0.4)"),
            camera=dict(eye=dict(x=1.45, y=-1.6, z=1.35))
        ),
        legend=dict(orientation="h", y=1.05, x=0)
    )
    return fig

def create_water_flow_sankey_fig():
    """
    Renders the exact Water Flow & Resource Allocation Sankey diagram from the reference image:
    Reservoir (2,400 L) + Makeup Water (320 L) -> Zones 1-5 -> Plant Uptake (62%), Drainage (16%), Evaporation (8%), Losses (14%)
    """
    labels = [
        "Reservoir<br>2,400 L",      # 0
        "Makeup Water<br>320 L",     # 1
        "Zone 1<br>10%",             # 2
        "Zone 2<br>20%",             # 3
        "Zone 3<br>25%",             # 4
        "Zone 4<br>30%",             # 5
        "Zone 5<br>15%",             # 6
        "Plant Uptake<br>62%",       # 7
        "Drainage<br>16%",           # 8
        "Evaporation<br>8%",         # 9
        "Losses<br>14%"              # 10
    ]
    
    sources = [
        0, 0, 0, 0, 0,
        1, 1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, 4, 4, 4,
        5, 5, 5, 5,
        6, 6, 6, 6
    ]
    targets = [
        2, 3, 4, 5, 6,
        2, 3, 4, 5, 6,
        7, 8, 9, 10,
        7, 8, 9, 10,
        7, 8, 9, 10,
        7, 8, 9, 10,
        7, 8, 9, 10
    ]
    values = [
        240, 480, 600, 720, 360,
        32, 64, 80, 96, 48,
        272*0.62, 272*0.16, 272*0.08, 272*0.14,
        544*0.62, 544*0.16, 544*0.08, 544*0.14,
        680*0.62, 680*0.16, 680*0.08, 680*0.14,
        816*0.62, 816*0.16, 816*0.08, 816*0.14,
        408*0.62, 408*0.16, 408*0.08, 408*0.14,
    ]
    
    node_colors = [
        "#0ea5e9", "#06b6d4",
        "#10b981", "#22c55e", "#3b82f6", "#8b5cf6", "#f59e0b",
        "#22c55e", "#0ea5e9", "#f59e0b", "#ef4444"
    ]
    
    link_colors = ["rgba(14, 165, 233, 0.25)"] * 10 + ["rgba(34, 197, 94, 0.22)"] * 20

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=16,
            thickness=16,
            line=dict(color="rgba(255,255,255,0.7)", width=1),
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors
        )
    )])
    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", size=10, color="#1e293b")
    )
    return fig

def create_crop_growth_curve_fig(crop_name="Lettuce"):
    """
    Renders the Crop Growth Progress curve matching the screenshot:
    Area chart from May 14 to May 26 with Today marker and green gradient.
    """
    dates = ["May 14", "May 17", "May 20", "May 23", "May 26"]
    
    if crop_name == "Lettuce":
        progress_vals = [22, 38, 54, 69, 78]
    elif crop_name == "Tomato":
        progress_vals = [18, 32, 46, 62, 71]
    elif crop_name == "Basil":
        progress_vals = [28, 44, 60, 74, 85]
    else:
        progress_vals = [20, 35, 50, 65, 75]
        
    fig = go.Figure()
    
    # Filled area
    fig.add_trace(go.Scatter(
        x=dates,
        y=progress_vals,
        mode="lines+markers",
        line=dict(color="#22c55e", width=3, shape="spline"),
        marker=dict(size=6, color="#16a34a"),
        fill="tozeroy",
        fillcolor="rgba(34, 197, 94, 0.16)",
        name="Growth Index",
        hoverinfo="x+y"
    ))
    
    # "Today" point pin
    fig.add_annotation(
        x="May 26",
        y=progress_vals[-1],
        text="Today",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.5,
        arrowcolor="#16a34a",
        ax=0,
        ay=-24,
        font=dict(family="DM Sans", size=10, color="#16a34a", weight=700),
        bgcolor="#f0fdf4",
        bordercolor="#bbf7d0",
        borderwidth=1,
        borderpad=3
    )
    
    fig.update_layout(
        height=145,
        margin=dict(l=8, r=18, t=28, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, linecolor="#e2e8f0"),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor="rgba(226, 232, 240, 0.6)", visible=False),
        showlegend=False
    )
    return fig
def render_sidebar_header_html():
    return f"""
    <div style="padding: 10px 4px 18px;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #10b981, #22c55e); display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 14px rgba(34, 197, 94, 0.4);">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>
        </div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.32rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">
            AquaTwin <span style="color: #4ade80;">AI</span>
          </div>
          <div style="font-size: 0.68rem; letter-spacing: 0.05em; color: #94a3b8; font-weight: 500;">
            Smart Farming. Sustainable Future.
          </div>
        </div>
      </div>
    </div>
    """

def render_sidebar_ai_assistant_card():
    return f"""
    <div style="margin: 18px 0 12px; background: linear-gradient(135deg, rgba(16, 75, 85, 0.55), rgba(7, 36, 46, 0.7)); border: 1px solid rgba(46, 175, 125, 0.35); border-radius: 14px; padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 16px rgba(0,0,0,0.15);">
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="width: 32px; height: 32px; border-radius: 50%; background: #22c55e; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 0 12px rgba(34, 197, 94, 0.45);">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
        </div>
        <div>
          <div style="font-size: 0.78rem; font-weight: 750; color: #ffffff; line-height: 1.1;">Need Help?</div>
          <div style="font-size: 0.68rem; color: #86efac; font-weight: 500;">Rule-based farm helper</div>
        </div>
      </div>
      <div style="color: #e2e8f0; font-size: 1.1rem; font-weight: 700; cursor: pointer;">
        &rarr;
      </div>
    </div>
    """

def render_sidebar_profile_card(name="Farm Operator", role="Demo User"):
    return f"""
    <div style="margin-top: 14px; padding: 10px 4px 4px; display: flex; align-items: center; justify-content: space-between;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="width: 36px; height: 36px; border-radius: 50%; background: #133a4a; border: 1px solid rgba(52, 211, 153, 0.4); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.82rem; color: #34d399;">
          AR
        </div>
        <div>
          <div style="font-size: 0.82rem; font-weight: 750; color: #ffffff; line-height: 1.1;">{name}</div>
          <div style="font-size: 0.68rem; color: #94a3b8; font-weight: 500;">{role}</div>
        </div>
      </div>
      <div style="color: #94a3b8; cursor: pointer;">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
      </div>
    </div>
    """

def render_farm_statistics_html(zone_count=12, rack_count=24, plant_count=5760):
    return f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 10px; display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.35rem; color: #0284c7;">🏢</div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; color: #0f172a; line-height: 1;">{zone_count}</div>
          <div style="font-size: 0.70rem; color: #64748b; font-weight: 600;">Zones</div>
        </div>
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 10px; display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.35rem; color: #16a34a;">🪜</div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; color: #0f172a; line-height: 1;">{rack_count}</div>
          <div style="font-size: 0.70rem; color: #64748b; font-weight: 600;">Racks</div>
        </div>
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 10px; display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.35rem; color: #0d9488;">🔌</div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; color: #0f172a; line-height: 1;">0</div>
          <div style="font-size: 0.70rem; color: #64748b; font-weight: 600;">Connected devices</div>
        </div>
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 10px; display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.35rem; color: #8b5cf6;">📡</div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; color: #0f172a; line-height: 1;">0</div>
          <div style="font-size: 0.70rem; color: #64748b; font-weight: 600;">Connected sensors</div>
        </div>
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 10px; display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.35rem; color: #10b981;">🧠</div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; color: #0f172a; line-height: 1;">{plant_count:,}</div>
          <div style="font-size: 0.70rem; color: #64748b; font-weight: 600;">Plants</div>
        </div>
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 10px; display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.35rem; color: #0ea5e9;">⏱️</div>
        <div>
          <div style="font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; color: #0f172a; line-height: 1;">Demo</div>
          <div style="font-size: 0.70rem; color: #64748b; font-weight: 600;">Simulation mode</div>
        </div>
      </div>
    </div>
    """

def render_weather_forecast_html():
    return """
    <div style="padding: 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;">
      <div style="font-size: 0.9rem; font-weight: 800; color: #0f2434; margin-bottom: 6px;">
        Live weather service not connected
      </div>
      <div style="font-size: 0.76rem; color: #64748b; line-height: 1.5;">
        Weather-driven irrigation adjustments are disabled. Connect a trusted weather API and configure the farm location before using forecast data.
      </div>
      <div style="margin-top: 10px; display: inline-block; padding: 5px 9px; border-radius: 8px; background: #e0f2fe; color: #075985; font-size: 0.7rem; font-weight: 700;">
        SIMULATION ONLY
      </div>
    </div>
    """
