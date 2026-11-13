from html.parser import HTMLParser

from ui.components import (
    normalize_html_content,
    render_welcome_banner_html,
    render_top_header_html,
    render_sidebar_header_html,
    render_sidebar_ai_assistant_card,
    render_sidebar_profile_card,
    render_farm_statistics_html,
    render_weather_forecast_html,
)


class MarkupValidator(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
    def handle_startendtag(self, tag, attrs):
        self.tags.append(tag)


def test_normalize_html_removes_indentation_that_markdown_reads_as_code():
    html = normalize_html_content("\n    <div>\n      <span>Farm</span>\n    </div>\n    ")
    assert html.startswith("<div>")
    assert "```" not in html
    assert not html.startswith("    ")


def test_welcome_banner_contains_both_farm_summary_cards_and_svg():
    html = normalize_html_content(render_welcome_banner_html(total_area_m2=720, cultivation_mode="Hydroponic"))
    parser = MarkupValidator()
    parser.feed(html)
    assert "Total Farm Area" in html and "720 m²" in html
    assert "Cultivation Mode" in html and "Hydroponic" in html
    assert "<svg" in html and "<!--" in html
    assert "```" not in html
    assert "div" in parser.tags and "svg" in parser.tags


def test_all_component_html_helpers_return_parseable_markup():
    fragments = [
        render_top_header_html(), render_sidebar_header_html(),
        render_sidebar_ai_assistant_card(), render_sidebar_profile_card(),
        render_farm_statistics_html(zone_count=12, rack_count=4, plant_count=240),
        render_weather_forecast_html(),
    ]
    for fragment in fragments:
        normalized = normalize_html_content(fragment)
        parser = MarkupValidator()
        parser.feed(normalized)
        assert "<div" in normalized or "<svg" in normalized
        assert "```" not in normalized


def test_render_html_prefers_streamlit_native_html_renderer(monkeypatch):
    import sys
    from types import SimpleNamespace
    from ui.components import render_html

    calls = []
    fake_streamlit = SimpleNamespace(html=lambda content: calls.append(content) or "native-rendered")
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    result = render_html("\n    <div>Native HTML</div>\n")
    assert result == "native-rendered"
    assert calls == ["<div>Native HTML</div>"]


def test_render_html_uses_legacy_markdown_fallback_when_html_api_is_missing(monkeypatch):
    import sys
    from types import SimpleNamespace
    from ui.components import render_html

    calls = []
    fake_streamlit = SimpleNamespace(markdown=lambda content, unsafe_allow_html=False: calls.append((content, unsafe_allow_html)) or "markdown-rendered")
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    result = render_html("\n    <div>Fallback HTML</div>\n")
    assert result == "markdown-rendered"
    assert calls == [("<div>Fallback HTML</div>", True)]


def test_dashboard_uses_action_focused_modules_and_clear_simulation_notice():
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    for page in ["Farm Dashboard", "Crop Intelligence", "Smart Irrigation Planner", "Water Rescue", "Smart Operations", "Cost & Performance"]:
        assert page in app
    for removed_page in ["Farm Digital Twin", "Soil Intelligence", "Research Bench", "Farmer Copilot"]:
        assert removed_page not in app
    assert "no live sensor connection" in app
    assert "Open-Meteo forecast" in app
    assert "fetch_weather_forecast" in app
    assert "Pump runtime and energy calculator" in app
    assert "Measured pump flow" not in app
    assert "field-validated" in app


def test_active_dashboard_does_not_require_fake_farm_photography():
    from pathlib import Path
    from ui.assets import GREENHOUSE_URI, LEAF_URI, LETTUCE_THUMB_URI, SIDEBAR_FOLIAGE_URI

    root = Path(__file__).resolve().parents[1]
    assert not (root / "assets").exists()
    assert all(uri == "" for uri in [GREENHOUSE_URI, LEAF_URI, LETTUCE_THUMB_URI, SIDEBAR_FOLIAGE_URI])


def test_dashboard_uses_calculated_visualizations_and_not_bar_charts_everywhere():
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "build_farm_figure(zones, plan_rows" in app
    assert "build_allocation_treemap(plan_rows)" in app
    assert "render_zone_cards(plan_rows, zones)" in app
    assert "plotly.express as px" in app  # retained for weather/history series
    assert "px.bar(pdf" not in app
    assert "px.bar(plot" not in app
