"""Hybrid premium-natural and agricultural command-centre theme for AquaTwin AI."""


def get_app_css() -> str:
    return r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root {
  --aqua-forest:#173b2b; --aqua-forest-2:#214b37; --aqua-leaf:#477b58;
  --aqua-sage:#e8efe6; --aqua-paper:#f5f6f1; --aqua-surface:#ffffff;
  --aqua-ink:#20382b; --aqua-muted:#738176; --aqua-border:#dfe6dc;
  --aqua-water:#5e9db5; --aqua-amber:#bd8b48;
}
html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif!important;color:var(--aqua-ink);}
.stApp {background:var(--aqua-paper)!important;}
.block-container {max-width:1680px!important;padding-top:1.35rem!important;padding-bottom:3rem!important;}
[data-testid="stHeader"] {background:rgba(245,246,241,.92)!important;backdrop-filter:blur(12px);}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#173b2b 0%,#102d21 100%)!important;border-right:1px solid rgba(255,255,255,.08);}
[data-testid="stSidebar"] * {color:#e7efe7!important;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color:#b9cbbb!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {gap:5px!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:9px 12px!important;border-radius:11px!important;border:1px solid transparent!important;color:#c2d2c5!important;font-weight:600!important;transition:all .16s ease;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:rgba(255,255,255,.07)!important;border-color:rgba(255,255,255,.08)!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#315b42!important;border:1px solid rgba(205,232,207,.24)!important;color:#fff!important;box-shadow:inset 3px 0 #a8c9a6;}
[data-testid="stSidebar"] [data-testid="stRadio"] label>div:first-child {display:none!important;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.13)!important;}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea {background:#244a36!important;color:white!important;border-color:#42654f!important;}
h1,h2,h3,h4 {font-family:'Manrope',sans-serif!important;color:var(--aqua-forest)!important;letter-spacing:-.035em!important;}
h1 {font-size:2rem!important;font-weight:800!important;} h2 {font-size:1.38rem!important;font-weight:760!important;} h3 {font-size:1.08rem!important;font-weight:730!important;}
p,li {line-height:1.55;}
.aqua-hero {position:relative;overflow:hidden;display:flex;align-items:flex-end;justify-content:space-between;gap:22px;background:linear-gradient(112deg,#153a2a 0%,#214b36 72%,#315c43 100%);padding:27px 30px;border-radius:21px;color:#fff;margin:3px 0 22px;box-shadow:0 12px 28px rgba(24,59,42,.12);}
.aqua-hero:after {content:"";position:absolute;width:310px;height:310px;right:-105px;top:-170px;border:1px solid rgba(224,241,222,.14);border-radius:50%;box-shadow:0 0 0 28px rgba(224,241,222,.035),0 0 0 62px rgba(224,241,222,.025);pointer-events:none;}
.aqua-hero-copy {position:relative;z-index:1;max-width:860px;}
.aqua-hero h1 {color:#fff!important;font-size:2rem!important;margin:.25rem 0 .45rem!important;line-height:1.15!important;}
.aqua-hero p {color:#d3e3d4!important;margin:0!important;font-size:.95rem;}
.aqua-kicker {font-size:.69rem;letter-spacing:.16em;text-transform:uppercase;color:#b5d0b4;font-weight:800;}
.aqua-hero-tag {position:relative;z-index:1;white-space:nowrap;border:1px solid rgba(231,244,231,.23);background:rgba(255,255,255,.08);padding:8px 12px;border-radius:999px;color:#e8f1e7;font-size:.74rem;font-weight:650;}
[data-testid="stMetric"] {background:#fff;border:1px solid var(--aqua-border);border-radius:16px;padding:15px 17px;box-shadow:0 4px 14px rgba(32,56,43,.035);min-height:108px;}
[data-testid="stMetricLabel"] {color:var(--aqua-muted)!important;font-size:.79rem!important;font-weight:650!important;}
[data-testid="stMetricValue"] {color:var(--aqua-forest)!important;font-family:'Manrope',sans-serif;font-weight:800!important;letter-spacing:-.03em;}
[data-testid="stMetricDelta"] {font-size:.74rem!important;}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button {border-radius:11px!important;border:1px solid #d2ddd0!important;min-height:2.55rem;font-weight:700!important;color:#294a36!important;background:#fff!important;transition:all .16s ease!important;}
.stButton>button:hover,.stDownloadButton>button:hover {border-color:#8eaf92!important;transform:translateY(-1px);box-shadow:0 5px 14px rgba(32,56,43,.08)!important;}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"] {background:#285d40!important;border-color:#285d40!important;color:#fff!important;}
[data-testid="stDataFrame"],[data-testid="stTable"] {border:1px solid var(--aqua-border);border-radius:13px;overflow:hidden;}
[data-testid="stPlotlyChart"] {background:rgba(255,255,255,.72);border:1px solid var(--aqua-border);border-radius:16px;padding:8px 8px 0;}
[data-testid="stAlert"] {border-radius:13px!important;}
[data-testid="stExpander"] {background:rgba(255,255,255,.65);border:1px solid var(--aqua-border);border-radius:13px;}
[data-testid="stTabs"] button {font-weight:700!important;}
.aqua-section-label {font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;color:#718173;font-weight:800;margin:.25rem 0 .55rem;}
.aqua-zone-card {background:#fff;border:1px solid var(--aqua-border);border-radius:16px;padding:15px 16px 14px;box-shadow:0 3px 12px rgba(27,56,38,.035);min-height:155px;margin-bottom:10px;}
.aqua-zone-top {display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;}
.aqua-zone-title {font-family:'Manrope',sans-serif;font-weight:800;color:#1a3e2b;font-size:1rem;}
.aqua-zone-crop {font-size:.78rem;color:#738176;margin-top:2px;}
.aqua-zone-status {font-size:.68rem;font-weight:800;border-radius:999px;padding:4px 8px;white-space:nowrap;}
.aqua-zone-status.critical {background:#f8e8e5;color:#a64e42;}.aqua-zone-status.shortage {background:#f7efdf;color:#986b2f;}.aqua-zone-status.covered {background:#e7f1e7;color:#39734b;}
.aqua-progress {height:7px;background:#edf1ea;border-radius:999px;overflow:hidden;margin:10px 0 7px;}
.aqua-progress span {display:block;height:100%;border-radius:999px;}
.aqua-zone-foot {display:flex;justify-content:space-between;gap:8px;color:#748176;font-size:.72rem;}
.aqua-note {background:#edf3ec;border:1px solid #dce8da;border-radius:13px;padding:13px 15px;color:#405a47;font-size:.86rem;line-height:1.5;}
.aqua-error {background:#fbefed;border:1px solid #efd4cf;border-radius:12px;padding:13px 15px;color:#8e423b;font-size:.84rem;overflow-wrap:anywhere;}
small,.stCaption {color:#778379!important;}
@media(max-width:800px){.block-container{padding-left:1rem!important;padding-right:1rem!important}.aqua-hero{padding:22px;display:block}.aqua-hero-tag{display:inline-block;margin-top:14px}.aqua-hero h1{font-size:1.55rem!important;}}
</style>
"""
