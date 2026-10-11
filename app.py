"""
app.py  —  MoC Intelligence Platform  |  Run: streamlit run app.py
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from neo4j.exceptions import Neo4jError, ServiceUnavailable

st.set_page_config(
    page_title="MoC Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg-base:    #080c14;
  --bg-surface: #0d1220;
  --bg-card:    rgba(255,255,255,0.045);
  --bg-card-hv: rgba(255,255,255,0.075);
  --border:     rgba(255,255,255,0.10);
  --border-hv:  rgba(255,255,255,0.22);
  --accent:     #4f8ef7;
  --accent2:    #a78bfa;
  --ok:         #34d399;
  --warn:       #fbbf24;
  --danger:     #f87171;
  --text:       #e8eeff;
  --text-muted: rgba(232,238,255,0.55);
  --font:       'Inter', sans-serif;
  --mono:       'JetBrains Mono', monospace;
}

html, body, [class*="css"] { font-family: var(--font) !important; }

.stApp {
  background: var(--bg-base);
  background-image:
    radial-gradient(ellipse 80% 50% at 20% -10%, rgba(79,142,247,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 110%, rgba(167,139,250,0.10) 0%, transparent 60%);
}

.block-container { padding-top: 1rem !important; max-width: 1280px; padding-bottom: 2rem; }

/* ── Hero ── */
.hero {
  background: linear-gradient(135deg, rgba(79,142,247,0.15) 0%, rgba(167,139,250,0.08) 100%);
  border: 1px solid rgba(79,142,247,0.25);
  border-radius: 20px;
  padding: 20px 28px;
  margin-bottom: 1.2rem;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(79,142,247,0.06) 50%, transparent 100%);
  animation: shimmer 4s ease-in-out infinite;
}
@keyframes shimmer { 0%,100%{opacity:0} 50%{opacity:1} }
.hero-title { font-size: 1.5rem; font-weight: 700; color: var(--text); margin: 0 0 4px 0; letter-spacing: -0.3px; }
.hero-sub   { font-size: 0.85rem; color: var(--text-muted); margin: 0; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(79,142,247,0.15); border: 1px solid rgba(79,142,247,0.3);
  border-radius: 20px; padding: 3px 10px; font-size: 0.72rem; font-weight: 600;
  color: #93c5fd; margin-right: 6px; margin-top: 8px;
}

/* ── Cards ── */
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px 18px;
  transition: border-color .2s, background .2s;
}
.kpi-card:hover { border-color: var(--border-hv); background: var(--bg-card-hv); }
.kpi-label { font-size: 0.72rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .8px; margin-bottom: 6px; }
.kpi-value { font-size: 1.6rem; font-weight: 700; color: var(--text); line-height: 1; }
.kpi-sub   { font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }

.info-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 16px;
  margin: 6px 0;
}
.info-card-title { font-size: 0.78rem; font-weight: 600; color: var(--accent); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .6px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px; padding: 5px 6px;
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px;
  background: transparent;
  height: 38px;
  font-size: 0.84rem;
  font-weight: 500;
  color: var(--text-muted) !important;
  transition: all .15s;
}
.stTabs [aria-selected="true"] {
  background: rgba(79,142,247,0.18) !important;
  color: #93c5fd !important;
  border: 1px solid rgba(79,142,247,0.3) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stButton > button { width: 100%; }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: var(--font) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(79,142,247,0.15) !important;
}

/* ── Buttons ── */
.stButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  transition: all .15s !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #4f8ef7, #7c6af7) !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(79,142,247,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(79,142,247,0.45) !important;
}

/* ── Chat ── */
.stChatMessage {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  margin-bottom: 8px !important;
}

/* ── Status pills ── */
.pill-wrap { display: flex; flex-direction: column; gap: 8px; margin: 8px 0; }
.pill {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 12px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
}
.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-ok  { background: var(--ok);  box-shadow: 0 0 8px rgba(52,211,153,.7); }
.dot-bad { background: var(--danger); box-shadow: 0 0 8px rgba(248,113,113,.7); }
.pill-name { font-size: 0.8rem; font-weight: 600; color: var(--text); min-width: 54px; }
.pill-msg  { font-size: 0.73rem; color: var(--text-muted); }

/* ── Risk badge ── */
.risk-badge {
  display: inline-block; padding: 3px 10px; border-radius: 20px;
  font-size: 0.75rem; font-weight: 700; letter-spacing: .5px;
}
.risk-low      { background: rgba(52,211,153,.15);  color: #34d399; border: 1px solid rgba(52,211,153,.3); }
.risk-medium   { background: rgba(251,191,36,.15);  color: #fbbf24; border: 1px solid rgba(251,191,36,.3); }
.risk-high     { background: rgba(248,113,113,.15); color: #f87171; border: 1px solid rgba(248,113,113,.3); }
.risk-critical { background: rgba(239,68,68,.25);   color: #ef4444; border: 1px solid rgba(239,68,68,.4); }

/* ── Graph viz panel ── */
.graph-panel {
  background: rgba(13,18,32,0.8);
  border: 1px solid rgba(79,142,247,0.2);
  border-radius: 16px;
  padding: 4px;
}
.graph-legend {
  display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 12px;
  font-size: 0.72rem; color: var(--text-muted);
}
.legend-dot {
  width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px;
}

/* ── Timeline ── */
.timeline-item {
  display: flex; gap: 12px; padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.timeline-item:last-child { border-bottom: none; }
.timeline-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--accent); flex-shrink: 0; margin-top: 5px;
  box-shadow: 0 0 8px rgba(79,142,247,.6);
}
.timeline-content { flex: 1; }
.timeline-title { font-size: 0.83rem; font-weight: 600; color: var(--text); }
.timeline-meta  { font-size: 0.73rem; color: var(--text-muted); margin-top: 2px; }

/* ── Prompt chips ── */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px 0; }
.chip {
  background: rgba(79,142,247,0.1); border: 1px solid rgba(79,142,247,0.25);
  border-radius: 20px; padding: 5px 14px; font-size: 0.78rem; font-weight: 500;
  color: #93c5fd; cursor: pointer; transition: all .15s;
}
.chip:hover { background: rgba(79,142,247,0.2); border-color: rgba(79,142,247,0.5); }

/* ── Divider ── */
.section-divider {
  height: 1px; background: linear-gradient(90deg, transparent, var(--border), transparent);
  margin: 16px 0;
}

/* ── Mono text ── */
.mono { font-family: var(--mono) !important; font-size: 0.8rem; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────
RISK_SCORE_MAP = {"Low": 22, "Medium": 50, "High": 76, "Critical": 95}
CARD_H_SM = 155
CARD_H_MD = 210
CARD_H_LG = 230
CHANGE_TYPES = [
    "Mechanical", "Instrumentation", "Process Parameter",
    "Mechanical Maintenance", "Process & Instrumentation",
    "Mechanical Efficiency Improvement", "Procedural",
    "Mechanical Integrity Improvement", "Other",
]
ASSET_IDS = ["P-101","FV-103","R-201","C-203","SV-204","S-301","EX-403","P-502","ESD-SYS","CTL-205"]
ASSET_CATS = ["Pump","Control Valve","Reactor","Cyclone Separator","Flue gas expander",
              "Piping","Procedure","Fractionator","Compressor","Other"]

# Node colours for knowledge graph
NODE_COLORS = {
    "MoC":       "#4f8ef7",
    "Asset":     "#34d399",
    "Hazard":    "#f87171",
    "WorkOrder": "#fbbf24",
    "Personnel": "#a78bfa",
    "RiskAssessment": "#fb923c",
    "LessonsLearned": "#38bdf8",
    "HAZOP":     "#e879f9",
    "PSSR":      "#4ade80",
    "default":   "#94a3b8",
}

# ── Theme helpers ──────────────────────────────────────────────────────────
def _tc():
    return {"paper":"rgba(0,0,0,0)","plot_bg":"rgba(0,0,0,0)",
            "font":"#e8eeff","accent":"#4f8ef7","ok":"#34d399","warn":"#fbbf24","bad":"#f87171"}

def risk_badge_html(rating: str) -> str:
    cls = {"Low":"risk-low","Medium":"risk-medium","High":"risk-high","Critical":"risk-critical"}.get(rating,"risk-medium")
    return f'<span class="risk-badge {cls}">{rating}</span>'

# ── Plotly helpers ─────────────────────────────────────────────────────────
def plotly_risk_gauge(rating: str):
    c = _tc()
    val = RISK_SCORE_MAP.get(str(rating), 0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        title={"text": "Risk Score", "font": {"size": 13}},
        number={"suffix": "/100", "font": {"size": 22}},
        gauge={
            "axis": {"range": [0,100], "tickcolor": c["font"]},
            "bar": {"color": c["accent"], "thickness": 0.25},
            "bgcolor": "rgba(255,255,255,0.04)",
            "borderwidth": 0,
            "steps": [
                {"range":[0,35],  "color":"rgba(52,211,153,0.18)"},
                {"range":[35,70], "color":"rgba(251,191,36,0.18)"},
                {"range":[70,100],"color":"rgba(248,113,113,0.22)"},
            ],
            "threshold": {"line":{"color":c["bad"],"width":2},"thickness":0.75,"value":val},
        },
    ))
    fig.update_layout(height=CARD_H_LG, margin=dict(l=10,r=10,t=30,b=5),
                      paper_bgcolor=c["paper"], font={"color":c["font"],"family":"Inter"})
    return fig

def plotly_binary_card(label: str, value: str):
    c = _tc()
    is_yes = str(value).strip().lower() in {"yes","true","triggered","required"}
    color  = c["warn"] if is_yes else c["ok"]
    icon   = "⚠️" if is_yes else "✓"
    fig = go.Figure()
    fig.update_layout(
        margin=dict(l=8,r=8,t=14,b=8),
        paper_bgcolor="rgba(255,255,255,0.03)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        height=CARD_H_SM,
        shapes=[{"type":"rect","xref":"paper","yref":"paper",
                 "x0":0.03,"x1":0.97,"y0":0.08,"y1":0.92,
                 "line":{"color":color,"width":1.5},"fillcolor":"rgba(255,255,255,0.01)"}],
        font={"color":c["font"],"family":"Inter"},
        xaxis={"visible":False}, yaxis={"visible":False},
        annotations=[
            {"xref":"paper","yref":"paper","x":0.5,"y":0.88,
             "text":f"<b>{label}</b>","showarrow":False,"font":{"size":12,"color":c["font"]}},
            {"xref":"paper","yref":"paper","x":0.5,"y":0.48,
             "text":f"<b>{icon} {value}</b>","showarrow":False,"font":{"size":20,"color":color}},
        ],
    )
    return fig

def plotly_ci_bar(estimate: float, ci_low: float, ci_high: float, title: str):
    c = _tc()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[ci_low,ci_high],y=[title,title],mode="lines",
        line={"width":10,"color":"rgba(79,142,247,0.35)"},showlegend=False))
    fig.add_trace(go.Scatter(x=[estimate],y=[title],mode="markers+text",
        marker={"size":12,"color":c["accent"],"line":{"color":"white","width":1.5}},
        text=[f"{estimate:,.0f}"],textposition="top center",showlegend=False,
        textfont={"size":11,"color":c["font"]}))
    fig.update_layout(height=CARD_H_SM,margin=dict(l=8,r=8,t=28,b=8),
        xaxis={"showgrid":False,"zeroline":False},yaxis={"showgrid":False},
        paper_bgcolor=c["paper"],plot_bgcolor=c["plot_bg"],font={"color":c["font"],"family":"Inter"})
    return fig

# ── Knowledge Graph Visualisation ─────────────────────────────────────────
def build_graph_figure(context: dict, query_text: str = "") -> go.Figure:
    """Build an interactive Plotly network graph from RAG context."""
    import math, random

    nodes, edges = [], []
    node_ids = {}

    def add_node(nid: str, label: str, ntype: str, detail: str = ""):
        if nid not in node_ids:
            node_ids[nid] = len(nodes)
            nodes.append({"id": nid, "label": label, "type": ntype, "detail": detail})

    def add_edge(src: str, tgt: str, rel: str):
        if src in node_ids and tgt in node_ids:
            edges.append({"src": node_ids[src], "tgt": node_ids[tgt], "rel": rel})

    # Central query node
    add_node("QUERY", f"Query", "Query", query_text[:60])

    # MoC detail node
    d = context.get("moc_detail")
    if d:
        mid = d.get("moc_id","MoC")
        add_node(mid, mid, "MoC",
                 f"{d.get('title','')[:40]}\nRisk: {d.get('risk_category')} ({d.get('risk_score')})\n${d.get('actual_cost') or 0:,}")
        add_edge("QUERY", mid, "RETRIEVES")

        # Asset
        aid = d.get("asset_id","Asset")
        add_node(aid, aid, "Asset", d.get("asset_name",""))
        add_edge(mid, aid, "TARGETS")

        # Approver
        approver = d.get("final_approver_role","")
        if approver:
            add_node(f"P_{approver}", approver, "Personnel", "Approver")
            add_edge(mid, f"P_{approver}", "APPROVED_BY")

        # Hazards
        for i, hz in enumerate((d.get("hazards") or [])[:3]):
            hid = f"HZ_{i}"
            add_node(hid, f"Hazard {i+1}", "Hazard", str(hz)[:50])
            add_edge(mid, hid, "IDENTIFIES")

        # HAZOP/PSSR
        if d.get("hazop_outcome"):
            add_node("HAZOP", "HAZOP", "HAZOP", str(d.get("hazop_outcome",""))[:50])
            add_edge(mid, "HAZOP", "REQUIRES_HAZOP")
        if d.get("pssr_outcome"):
            add_node("PSSR", "PSSR", "PSSR", str(d.get("pssr_outcome",""))[:50])
            add_edge(mid, "PSSR", "REQUIRES_PSSR")

        # Lesson
        if d.get("lesson"):
            add_node("LL", "Lesson", "LessonsLearned", str(d.get("lesson",""))[:60])
            add_edge(mid, "LL", "CAPTURED_LESSON")

    # Work orders
    for wo in (context.get("work_orders") or [])[:3]:
        wid = wo.get("wo_id","WO")
        add_node(wid, wid, "WorkOrder",
                 f"{wo.get('title','')[:35]}\n{wo.get('actual_hrs')}h | ${wo.get('actual_cost') or 0:,}")
        if d:
            add_edge(d.get("moc_id","MoC"), wid, "GENERATES")

    # Impact chain
    for n in (context.get("impact_chain") or [])[:5]:
        nid = n.get("node_id","")
        if nid:
            add_node(nid, nid, "Asset", f"{n.get('node_name','')} ({n.get('hop_distance')} hop)")
            if d:
                add_edge(d.get("asset_id",""), nid, "IMPACTS")

    # Vector hits
    for h in (context.get("vector_hits") or [])[:3]:
        vid = h.get("moc_id","")
        if vid and vid not in node_ids:
            add_node(vid, vid, "MoC", f"sim={h.get('similarity',0):.2f}")
            add_edge("QUERY", vid, "SIMILAR")

    if not nodes:
        return None

    # Layout — radial from centre
    n = len(nodes)
    cx, cy = 0.5, 0.5
    positions = {}
    positions[0] = (cx, cy)  # QUERY at centre
    for i in range(1, n):
        angle = 2 * math.pi * (i - 1) / max(n - 1, 1)
        r = 0.28 + 0.12 * (i % 3)
        positions[i] = (cx + r * math.cos(angle), cy + r * math.sin(angle))

    # Edge traces
    edge_x, edge_y, edge_labels = [], [], []
    for e in edges:
        x0, y0 = positions.get(e["src"], (cx, cy))
        x1, y1 = positions.get(e["tgt"], (cx, cy))
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    fig = go.Figure()

    # Edges
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line={"width": 1.2, "color": "rgba(79,142,247,0.3)"},
        hoverinfo="none", showlegend=False,
    ))

    # Nodes grouped by type
    type_groups = {}
    for i, node in enumerate(nodes):
        t = node["type"]
        type_groups.setdefault(t, []).append(i)

    for ntype, idxs in type_groups.items():
        color = NODE_COLORS.get(ntype, NODE_COLORS["default"])
        xs = [positions[i][0] for i in idxs]
        ys = [positions[i][1] for i in idxs]
        labels = [nodes[i]["label"] for i in idxs]
        details = [f"<b>{nodes[i]['label']}</b><br><i>{ntype}</i><br>{nodes[i]['detail']}" for i in idxs]
        sizes = [22 if nodes[i]["id"] == "QUERY" else 16 if ntype == "MoC" else 13 for i in idxs]

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            marker={"size": sizes, "color": color,
                    "line": {"color": "rgba(255,255,255,0.3)", "width": 1.5},
                    "symbol": "circle"},
            text=labels,
            textposition="top center",
            textfont={"size": 9, "color": "#e8eeff", "family": "Inter"},
            hovertext=details,
            hoverinfo="text",
            name=ntype,
            showlegend=True,
        ))

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(13,18,32,0.0)",
        plot_bgcolor="rgba(13,18,32,0.0)",
        font={"color": "#e8eeff", "family": "Inter"},
        xaxis={"visible": False, "range": [0, 1]},
        yaxis={"visible": False, "range": [0, 1]},
        legend={
            "orientation": "h", "yanchor": "bottom", "y": -0.08,
            "xanchor": "center", "x": 0.5,
            "font": {"size": 10}, "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": "rgba(255,255,255,0.1)", "borderwidth": 1,
        },
        hoverlabel={"bgcolor": "#0d1220", "bordercolor": "rgba(79,142,247,0.4)",
                    "font": {"color": "#e8eeff", "size": 11, "family": "Inter"}},
    )
    return fig

# ── Singletons ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_smart_forms():
    from modules.smart_forms import SmartFormModule
    return SmartFormModule()

@st.cache_resource
def get_risk_engine():
    from modules.risk_engine import RiskEngine
    return RiskEngine()

@st.cache_resource
def get_cost_predictor():
    from modules.cost_predictor import CostPredictor
    return CostPredictor()

@st.cache_resource
def get_chatbot():
    from modules.nlp_chatbot import MoCChatbot
    return MoCChatbot()

@st.cache_data(ttl=30)
def get_connection_status(nonce: int = 0):
    status = {"neo4j": {"ok": False, "message": "Not checked"},
              "openai": {"ok": False, "message": "Not checked"}}
    try:
        from core.neo4j_client import Neo4jClient
        c = Neo4jClient(); c._run("RETURN 1"); c.close()
        status["neo4j"] = {"ok": True, "message": "Connected"}
    except Exception as e:
        status["neo4j"] = {"ok": False, "message": str(e)[:60]}
    try:
        from core.config import OPENAI_API_KEY, OPENAI_MODEL
        if not OPENAI_API_KEY:
            status["openai"] = {"ok": False, "message": "API key missing"}
        else:
            from openai import OpenAI
            OpenAI(api_key=OPENAI_API_KEY).models.retrieve(OPENAI_MODEL, timeout=8.0)
            status["openai"] = {"ok": True, "message": f"{OPENAI_MODEL}"}
    except Exception as e:
        status["openai"] = {"ok": False, "message": str(e)[:60]}
    return status

# ── Chat turn ──────────────────────────────────────────────────────────────
def run_chat_turn(user_input: str, asset_id=None):
    st.session_state["chat_messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Querying knowledge graph + vector memory…"):
            chatbot = get_chatbot()
            result  = chatbot.chat(user_input, asset_id=asset_id)
        st.write(result["response"])

        # Store graph context for visualisation
        raw_ctx = chatbot.pipeline.get_raw_context(
            user_input,
            asset_id=result.get("asset_id_used") if result.get("asset_id_used") != "none" else None,
            moc_id=result.get("moc_id_used") if result.get("moc_id_used") != "none" else None,
        )
        st.session_state["last_graph_context"] = raw_ctx
        st.session_state["last_query_text"]    = user_input

        with st.expander("🔍 Sources & Debug", expanded=False):
            st.caption(f"Intent: `{result['intent']}` | Asset: `{result['asset_id_used']}` | MoC: `{result.get('moc_id_used','none')}`")
            if result["vector_hits"]:
                st.markdown("**Vector matches:**")
                for h in result["vector_hits"][:3]:
                    st.markdown(f"- `{h['moc_id']}` sim={h['similarity']:.3f}")

    st.session_state["chat_messages"].append({"role": "assistant", "content": result["response"]})
    st.session_state["chat_last_intent"] = result.get("intent", "general")

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:12px 4px 8px 4px">
      <div style="font-size:1.1rem;font-weight:700;color:#e8eeff;letter-spacing:-.2px">⚡ MoC Platform</div>
      <div style="font-size:0.73rem;color:rgba(232,238,255,.5);margin-top:2px">FCC Unit · AI Decision Support</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:.72rem;font-weight:600;color:rgba(232,238,255,.5);text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">System Status</div>', unsafe_allow_html=True)

    if "conn_nonce" not in st.session_state:
        st.session_state["conn_nonce"] = 0
    if st.button("↺ Refresh", key="refresh_btn"):
        st.session_state["conn_nonce"] += 1

    conn = get_connection_status(st.session_state["conn_nonce"])
    for svc, info in conn.items():
        dot = "dot-ok" if info["ok"] else "dot-bad"
        st.markdown(f"""
        <div class="pill">
          <span class="dot {dot}"></span>
          <span class="pill-name">{svc.capitalize()}</span>
          <span class="pill-msg">{info['message']}</span>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:.72rem;font-weight:600;color:rgba(232,238,255,.5);text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Tech Stack</div>', unsafe_allow_html=True)
    for item in ["Neo4j Knowledge Graph","GPT-4o · LangChain","ChromaDB · OpenAI Embeddings","GradientBoosting ML"]:
        st.markdown(f'<div style="font-size:.8rem;color:rgba(232,238,255,.75);padding:3px 0">▸ {item}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:.72rem;font-weight:600;color:rgba(232,238,255,.5);text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Dataset</div>', unsafe_allow_html=True)
    for label, val in [("MoC Records","10"),("Assets","14+"),("Work Orders","21"),("Incidents","4")]:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,.06)">
          <span style="font-size:.78rem;color:rgba(232,238,255,.6)">{label}</span>
          <span style="font-size:.78rem;font-weight:600;color:#4f8ef7">{val}</span>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <div class="hero-title">MoC Intelligence Platform</div>
  <div class="hero-sub">Hybrid Neo4j + ChromaDB retrieval · GPT-4o reasoning · Engineering-grade decision support</div>
  <div style="margin-top:10px">
    <span class="hero-badge">⚡ Live Graph</span>
    <span class="hero-badge">🧠 RAG Pipeline</span>
    <span class="hero-badge">📊 ML Prediction</span>
    <span class="hero-badge">🔍 Vector Search</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📝  Smart Form", "⚠️  Risk & Impact", "💰  Cost Predictor", "💬  MoCBot"
])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Smart Guided Form
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div style="margin-bottom:16px">
      <div style="font-size:1.15rem;font-weight:700;color:#e8eeff">Smart Guided MoC Form</div>
      <div style="font-size:.8rem;color:rgba(232,238,255,.5);margin-top:3px">
        AI auto-prefills form fields using historical MoCs from the knowledge graph + semantic vector search.
      </div>
    </div>""", unsafe_allow_html=True)

    f_col1, f_col2 = st.columns([3, 2])
    with f_col1:
        fc1, fc2 = st.columns(2)
        with fc1:
            t1_ct  = st.selectbox("Change Type", CHANGE_TYPES, key="t1_ct")
        with fc2:
            t1_aid = st.selectbox("Asset ID", ASSET_IDS, key="t1_aid")
        t1_desc = st.text_area("Describe the proposed change", height=110,
            placeholder="e.g. Replace feed pump P-101 due to excessive vibration and bearing wear…")
        if st.button("🔍  Get AI Suggestions", type="primary", key="form_btn"):
            if t1_desc.strip():
                with st.spinner("Querying knowledge graph and generating suggestions…"):
                    m = get_smart_forms()
                    st.session_state["form_result"]  = m.get_prefill_suggestions(t1_ct, t1_aid, t1_desc)
                    st.session_state["form_similar"] = m.get_similar_mocs_summary(t1_ct, t1_aid, t1_desc)
            else:
                st.warning("Please enter a description first.")

    with f_col2:
        st.markdown("""
        <div class="info-card">
          <div class="info-card-title">How it works</div>
          <div style="font-size:.8rem;color:rgba(232,238,255,.7);line-height:1.6">
            <b>1.</b> Description is embedded via OpenAI and matched against 10 historical MoCs in ChromaDB.<br><br>
            <b>2.</b> Neo4j graph is traversed for same asset/change type — hazards, approvers, P&IDs retrieved.<br><br>
            <b>3.</b> GPT-4o synthesises both sources into structured form suggestions.
          </div>
        </div>""", unsafe_allow_html=True)

    if "form_result" in st.session_state:
        r = st.session_state["form_result"]
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
          <div style="font-size:1rem;font-weight:700;color:#e8eeff">AI Suggestions</div>
          {risk_badge_html(r.get('risk_level','Unknown'))}
        </div>""", unsafe_allow_html=True)

        gc1, gc2, gc3 = st.columns([1.2, 1, 1])
        with gc1:
            st.plotly_chart(plotly_risk_gauge(r.get("risk_level","Unknown")),
                            use_container_width=True, config={"displayModeBar":False}, key="f_gauge")
        with gc2:
            st.plotly_chart(plotly_binary_card("HAZOP Required", r.get("hazop_required","Unknown")),
                            use_container_width=True, config={"displayModeBar":False}, key="f_hazop")
        with gc3:
            st.plotly_chart(plotly_binary_card("PSSR Required", r.get("pssr_required","Unknown")),
                            use_container_width=True, config={"displayModeBar":False}, key="f_pssr")

        ra, rb = st.columns(2)
        with ra:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown('<div class="info-card-title">Recommended Approvers</div>', unsafe_allow_html=True)
            for a in r.get("approvers",[])[:5]:
                st.markdown(f'<div style="font-size:.82rem;color:#e8eeff;padding:2px 0">👤 {a}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="info-card" style="margin-top:8px">', unsafe_allow_html=True)
            st.markdown('<div class="info-card-title">Required Documents</div>', unsafe_allow_html=True)
            for d in r.get("documents",[])[:5]:
                st.markdown(f'<div style="font-size:.82rem;color:#e8eeff;padding:2px 0">📄 {d}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with rb:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown('<div class="info-card-title">P&ID Tags to Review</div>', unsafe_allow_html=True)
            for t in r.get("pid_tags",[])[:5]:
                st.markdown(f'<div style="font-size:.82rem;color:#e8eeff;padding:2px 0;font-family:var(--mono)">🔧 {t}</div>', unsafe_allow_html=True)
            if r.get("scope"):
                st.markdown(f'<div style="margin-top:8px;font-size:.8rem;color:rgba(232,238,255,.6)"><b>Scope:</b> {r["scope"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if r.get("justification"):
            st.markdown(f"""
            <div style="background:rgba(79,142,247,.08);border:1px solid rgba(79,142,247,.2);
                        border-radius:12px;padding:12px 16px;margin-top:8px;
                        font-size:.82rem;color:rgba(232,238,255,.85);line-height:1.6">
              💡 <b>AI Justification:</b> {r['justification']}
            </div>""", unsafe_allow_html=True)

        if st.session_state.get("form_similar"):
            with st.expander("📚  Similar Historical MoCs", expanded=False):
                for moc in st.session_state["form_similar"][:5]:
                    meta  = moc.get("metadata", {})
                    sim   = moc.get("similarity", 0)
                    title = meta.get("title", moc.get("title", moc.get("moc_id","?")))
                    desc  = meta.get("description", moc.get("description",""))
                    risk  = meta.get("risk_level", moc.get("risk_level","?"))
                    cost  = meta.get("cost", moc.get("cost","?"))
                    bar_w = int(sim * 100)
                    st.markdown(f"""
                    <div class="timeline-item">
                      <div class="timeline-dot"></div>
                      <div class="timeline-content">
                        <div class="timeline-title">{moc.get('moc_id','?')} — {title[:55]}</div>
                        <div class="timeline-meta">{desc[:100]}…</div>
                        <div style="display:flex;gap:12px;margin-top:5px;align-items:center">
                          {risk_badge_html(risk)}
                          <span style="font-size:.73rem;color:rgba(232,238,255,.5)">Cost: ${cost}</span>
                          <div style="flex:1;height:4px;background:rgba(255,255,255,.08);border-radius:2px">
                            <div style="width:{bar_w}%;height:100%;background:#4f8ef7;border-radius:2px"></div>
                          </div>
                          <span style="font-size:.72rem;color:#4f8ef7">{sim:.2f}</span>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Risk & Impact
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div style="margin-bottom:16px">
      <div style="font-size:1.15rem;font-weight:700;color:#e8eeff">Risk & Impact Assessment</div>
      <div style="font-size:.8rem;color:rgba(232,238,255,.5);margin-top:3px">
        Graph-traversal risk analysis — traces asset dependencies up to 3 hops across the FCC unit.
      </div>
    </div>""", unsafe_allow_html=True)

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        t2_ct  = st.selectbox("Change Type", CHANGE_TYPES, key="t2_ct")
    with r2c2:
        t2_aid = st.selectbox("Asset ID", ASSET_IDS, key="t2_aid")
    t2_desc = st.text_area("Describe the proposed change", key="risk_desc", height=90,
        placeholder="e.g. Upgrade catalyst slide valve SV-204 actuator to advanced feedback control…")

    if st.button("🔬  Analyse Risks", type="primary", key="risk_btn"):
        if t2_desc.strip():
            with st.spinner("Traversing knowledge graph and analysing risks…"):
                st.session_state["risk_result"] = get_risk_engine().analyse(t2_ct, t2_aid, t2_desc)
        else:
            st.warning("Please enter a description.")

    if "risk_result" in st.session_state:
        r = st.session_state["risk_result"]
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        rating = r.get("overall_rating","Unknown")

        # Top KPI row
        k1, k2, k3, k4 = st.columns(4)
        direct   = r.get("direct_assets",[])
        indirect = r.get("indirect_assets",[])
        with k1:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Overall Risk</div>
              <div>{risk_badge_html(rating)}</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Direct Assets</div>
              <div class="kpi-value" style="color:#34d399">{len(direct)}</div>
              <div class="kpi-sub">1 hop</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Indirect Assets</div>
              <div class="kpi-value" style="color:#fbbf24">{len(indirect)}</div>
              <div class="kpi-sub">2–3 hops</div>
            </div>""", unsafe_allow_html=True)
        with k4:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Hazards Found</div>
              <div class="kpi-value" style="color:#f87171">{len(r.get('hazards',[]))}</div>
              <div class="kpi-sub">from graph</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        left, right = st.columns([1, 1.1])
        with left:
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                st.plotly_chart(plotly_risk_gauge(rating), use_container_width=True,
                                config={"displayModeBar":False}, key="r_gauge")
            with gc2:
                st.plotly_chart(plotly_binary_card("HAZOP", r.get("hazop_triggered","?")),
                                use_container_width=True, config={"displayModeBar":False}, key="r_hazop")
            with gc3:
                st.plotly_chart(plotly_binary_card("PSSR", r.get("pssr_required","?")),
                                use_container_width=True, config={"displayModeBar":False}, key="r_pssr")

            if r.get("reasoning"):
                st.markdown(f"""
                <div style="background:rgba(79,142,247,.07);border:1px solid rgba(79,142,247,.18);
                            border-radius:12px;padding:11px 14px;font-size:.81rem;
                            color:rgba(232,238,255,.85);line-height:1.6;margin-top:4px">
                  🧠 {r['reasoning']}
                </div>""", unsafe_allow_html=True)

            st.markdown('<div class="info-card" style="margin-top:10px">', unsafe_allow_html=True)
            st.markdown('<div class="info-card-title">Top Risks</div>', unsafe_allow_html=True)
            for risk in r.get("risks",[]):
                sev = risk.get("severity","Medium")
                col = {"High":"#f87171","Critical":"#ef4444","Medium":"#fbbf24","Low":"#34d399"}.get(sev,"#94a3b8")
                st.markdown(f'<div style="font-size:.81rem;color:{col};padding:3px 0;border-bottom:1px solid rgba(255,255,255,.05)">● {risk.get("description","")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="info-card" style="margin-top:8px">', unsafe_allow_html=True)
            st.markdown('<div class="info-card-title">Mitigations</div>', unsafe_allow_html=True)
            for m in r.get("mitigations",[]):
                st.markdown(f'<div style="font-size:.81rem;color:rgba(232,238,255,.8);padding:3px 0">✅ {m}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            # Impact donut
            if direct or indirect:
                pie = go.Figure(go.Pie(
                    labels=["Direct (1 hop)","Indirect (2-3 hops)"],
                    values=[max(len(direct),1), max(len(indirect),1)],
                    hole=0.6,
                    marker={"colors":["#4f8ef7","#a78bfa"],
                            "line":{"color":"rgba(255,255,255,.1)","width":1}},
                    textinfo="label+percent",
                    textfont={"size":11,"color":"#e8eeff"},
                ))
                pie.update_layout(height=220, margin=dict(l=10,r=10,t=20,b=10),
                    paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    font={"color":"#e8eeff","family":"Inter"})
                st.plotly_chart(pie, use_container_width=True, config={"displayModeBar":False}, key="r_pie")

            # Asset impact list
            if direct:
                st.markdown('<div class="info-card">', unsafe_allow_html=True)
                st.markdown('<div class="info-card-title">Direct Impact (1 hop)</div>', unsafe_allow_html=True)
                for a in direct[:6]:
                    st.markdown(f'<div style="font-size:.8rem;color:#34d399;padding:2px 0">↳ <span class="mono">{a.get("node_id","")}</span> {a.get("node_name","")}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            if indirect:
                st.markdown('<div class="info-card" style="margin-top:8px">', unsafe_allow_html=True)
                st.markdown('<div class="info-card-title">Indirect Impact (2–3 hops)</div>', unsafe_allow_html=True)
                for a in indirect[:6]:
                    st.markdown(f'<div style="font-size:.8rem;color:#a78bfa;padding:2px 0">↳↳ <span class="mono">{a.get("node_id","")}</span> ({a.get("hop_distance","")} hops)</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Hazard severity bar
            if r.get("hazards"):
                sev_counts = {}
                for h in r["hazards"][:6]:
                    s = h.get("severity","?")
                    sev_counts[s] = sev_counts.get(s,0) + 1
                bar = go.Figure(go.Bar(
                    x=list(sev_counts.keys()), y=list(sev_counts.values()),
                    marker={"color":["#34d399","#fbbf24","#f87171","#ef4444"][:len(sev_counts)],
                            "line":{"color":"rgba(255,255,255,.1)","width":1}},
                    text=list(sev_counts.values()), textposition="outside",
                    textfont={"color":"#e8eeff","size":11},
                ))
                bar.update_layout(height=180, margin=dict(l=8,r=8,t=20,b=8),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font={"color":"#e8eeff","family":"Inter"},
                    xaxis={"title":"Severity","showgrid":False},
                    yaxis={"showgrid":False,"visible":False})
                st.plotly_chart(bar, use_container_width=True, config={"displayModeBar":False}, key="r_bar")

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Cost & Downtime Predictor
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div style="margin-bottom:16px">
      <div style="font-size:1.15rem;font-weight:700;color:#e8eeff">Cost & Downtime Prediction</div>
      <div style="font-size:.8rem;color:rgba(232,238,255,.5);margin-top:3px">
        ML model trained on historical MoC data, augmented with live knowledge graph features.
      </div>
    </div>""", unsafe_allow_html=True)

    cp1, cp2 = st.columns([3, 2])
    with cp1:
        cc1, cc2 = st.columns(2)
        with cc1:
            t3_ct   = st.selectbox("Change Type", CHANGE_TYPES, key="t3_ct")
            t3_aid  = st.selectbox("Asset ID", ASSET_IDS, key="t3_aid")
        with cc2:
            t3_acat = st.selectbox("Asset Category", ASSET_CATS, key="t3_acat")
            t3_rl   = st.selectbox("Risk Level", ["Low","Medium","High","Critical"])
        t3_desc = st.text_area("Change description", key="cost_desc", height=90,
            placeholder="e.g. Replace reflux pump P-502 due to bearing failure…")
        if st.button("📊  Predict Cost & Downtime", type="primary", key="cost_btn"):
            if t3_desc.strip():
                with st.spinner("Running ML model + graph feature extraction…"):
                    st.session_state["cost_result"] = get_cost_predictor().predict(
                        t3_ct, t3_aid, t3_acat, t3_rl, t3_desc)
            else:
                st.warning("Please enter a description.")

    with cp2:
        st.markdown("""
        <div class="info-card">
          <div class="info-card-title">Model Features</div>
          <div style="font-size:.8rem;color:rgba(232,238,255,.7);line-height:1.7">
            ▸ Change type encoding<br>
            ▸ Asset category encoding<br>
            ▸ Risk level encoding<br>
            ▸ Graph dependency count (Neo4j)<br>
            ▸ Associated hazard count (Neo4j)<br>
            ▸ Historical MoC count on asset
          </div>
        </div>""", unsafe_allow_html=True)

    if "cost_result" in st.session_state:
        r = st.session_state["cost_result"]
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # KPI cards
        ck1, ck2, ck3, ck4 = st.columns(4)
        with ck1:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Estimated Cost</div>
              <div class="kpi-value" style="color:#4f8ef7">${r['cost_estimate']:,.0f}</div>
              <div class="kpi-sub">${r['cost_ci'][0]:,.0f} – ${r['cost_ci'][1]:,.0f}</div>
            </div>""", unsafe_allow_html=True)
        with ck2:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Estimated Downtime</div>
              <div class="kpi-value" style="color:#a78bfa">{r['downtime_estimate']:.1f}h</div>
              <div class="kpi-sub">{r['downtime_ci'][0]:.1f} – {r['downtime_ci'][1]:.1f} hrs</div>
            </div>""", unsafe_allow_html=True)
        with ck3:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Graph Dependencies</div>
              <div class="kpi-value" style="color:#34d399">{r['features'].get('n_dependencies',0)}</div>
              <div class="kpi-sub">from Neo4j</div>
            </div>""", unsafe_allow_html=True)
        with ck4:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">Model</div>
              <div style="font-size:.78rem;color:#fbbf24;font-weight:600;margin-top:6px">{r['models_used']}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        cg1, cg2, cg3 = st.columns([1, 1, 1.1])
        with cg1:
            cost_fig = go.Figure(go.Indicator(
                mode="gauge+number", value=r["cost_estimate"],
                title={"text":"Estimated Cost","font":{"size":12}},
                number={"prefix":"$","valueformat":",.0f","font":{"size":20}},
                gauge={"axis":{"range":[0, max(r["cost_ci"][1]*1.1,1)]},
                       "bar":{"color":"#4f8ef7","thickness":0.25},
                       "bgcolor":"rgba(255,255,255,.04)","borderwidth":0,
                       "steps":[{"range":[0,r["cost_ci"][1]*1.1],"color":"rgba(79,142,247,.08)"}]},
            ))
            cost_fig.update_layout(height=CARD_H_MD, margin=dict(l=10,r=10,t=35,b=5),
                paper_bgcolor="rgba(0,0,0,0)", font={"color":"#e8eeff","family":"Inter"})
            st.plotly_chart(cost_fig, use_container_width=True, config={"displayModeBar":False}, key="c_gauge")
        with cg2:
            down_fig = go.Figure(go.Indicator(
                mode="gauge+number", value=r["downtime_estimate"],
                title={"text":"Downtime (hrs)","font":{"size":12}},
                number={"valueformat":".1f","font":{"size":20}},
                gauge={"axis":{"range":[0, max(r["downtime_ci"][1]*1.25,1)]},
                       "bar":{"color":"#a78bfa","thickness":0.25},
                       "bgcolor":"rgba(255,255,255,.04)","borderwidth":0},
            ))
            down_fig.update_layout(height=CARD_H_MD, margin=dict(l=10,r=10,t=35,b=5),
                paper_bgcolor="rgba(0,0,0,0)", font={"color":"#e8eeff","family":"Inter"})
            st.plotly_chart(down_fig, use_container_width=True, config={"displayModeBar":False}, key="d_gauge")
        with cg3:
            st.plotly_chart(plotly_ci_bar(r["cost_estimate"],r["cost_ci"][0],r["cost_ci"][1],"Cost ($)"),
                use_container_width=True, config={"displayModeBar":False}, key="c_ci")
            st.plotly_chart(plotly_ci_bar(r["downtime_estimate"],r["downtime_ci"][0],r["downtime_ci"][1],"Downtime (h)"),
                use_container_width=True, config={"displayModeBar":False}, key="d_ci")

        st.markdown('<div class="info-card" style="margin-top:8px">', unsafe_allow_html=True)
        st.markdown('<div class="info-card-title">AI Explanation</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:.83rem;color:rgba(232,238,255,.85);line-height:1.65">{r["explanation"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("🔬  Feature Vector", expanded=False):
            cols = st.columns(3)
            for i, (k, v) in enumerate(r["features"].items()):
                with cols[i % 3]:
                    st.markdown(f'<div style="font-size:.78rem;color:rgba(232,238,255,.6)">{k}</div>'
                                f'<div style="font-size:.9rem;font-weight:600;color:#4f8ef7;font-family:var(--mono)">{v}</div>',
                                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — MoCBot + Knowledge Graph Visualisation
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    # Init state
    for k, v in [("chat_messages",[{"role":"assistant",
        "content":"Welcome to MoCBot. I have direct access to the FCC Unit knowledge graph — "
                  "10 MoC records, 14+ assets, risk assessments, HAZOP/PSSR, work orders, and lessons learned. "
                  "Ask me anything specific."}]),
        ("chat_last_intent","general"),("chat_pending_input",""),
        ("last_graph_context",None),("last_query_text","")]:
        if k not in st.session_state:
            st.session_state[k] = v

    # Two-column layout: chat left, graph right
    chat_col, graph_col = st.columns([3, 2])

    with chat_col:
        st.markdown("""
        <div style="margin-bottom:12px">
          <div style="font-size:1.1rem;font-weight:700;color:#e8eeff">MoCBot</div>
          <div style="font-size:.78rem;color:rgba(232,238,255,.45)">
            Grounded answers from Neo4j + ChromaDB · No hallucination
          </div>
        </div>""", unsafe_allow_html=True)

        # Prompt chips
        st.markdown('<div style="font-size:.72rem;color:rgba(232,238,255,.45);margin-bottom:6px;text-transform:uppercase;letter-spacing:.6px">Quick prompts</div>', unsafe_allow_html=True)
        qc1, qc2, qc3, qc4 = st.columns(4)
        with qc1:
            if st.button("MoC-010 details", use_container_width=True, key="qp1"):
                st.session_state["chat_pending_input"] = "What changed in MoC-010 and what were the key lessons?"
        with qc2:
            if st.button("HAZOP list", use_container_width=True, key="qp2"):
                st.session_state["chat_pending_input"] = "Which MoCs required HAZOP?"
        with qc3:
            if st.button("SV-204 risks", use_container_width=True, key="qp3"):
                st.session_state["chat_pending_input"] = "What are the risks and mitigations for modifying SV-204?"
        with qc4:
            if st.button("All incidents", use_container_width=True, key="qp4"):
                st.session_state["chat_pending_input"] = "Which MoCs had incidents or near misses?"

        # Process pending
        pending = st.session_state.get("chat_pending_input","")
        if pending:
            st.session_state["chat_pending_input"] = ""
            run_chat_turn(pending, None)

        # Message history
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        for msg in st.session_state["chat_messages"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Clear + input
        ctrl = st.columns([5, 1])
        with ctrl[1]:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_btn"):
                st.session_state["chat_messages"] = []
                st.session_state["last_graph_context"] = None
                st.session_state["last_query_text"] = ""
                get_chatbot().reset_memory()
                st.rerun()

        with st.form("chat_form", clear_on_submit=True):
            fc = st.columns([5, 1])
            with fc[0]:
                user_input = st.text_input("Ask about MoC history, risks, HAZOP, approvals…",
                    key="chat_input", label_visibility="collapsed",
                    placeholder="e.g. What was the actual cost of MoC-005?")
            with fc[1]:
                send = st.form_submit_button("Send", use_container_width=True)
            if send and user_input.strip():
                run_chat_turn(user_input.strip(), None)
                st.rerun()

    # ── Knowledge Graph Panel ──────────────────────────────────────────────
    with graph_col:
        st.markdown("""
        <div style="margin-bottom:12px">
          <div style="font-size:1.1rem;font-weight:700;color:#e8eeff">Knowledge Graph</div>
          <div style="font-size:.78rem;color:rgba(232,238,255,.45)">
            Live visualisation of what the graph retrieved for your last query
          </div>
        </div>""", unsafe_allow_html=True)

        ctx  = st.session_state.get("last_graph_context")
        qtxt = st.session_state.get("last_query_text","")

        if ctx:
            fig = build_graph_figure(ctx, qtxt)
            if fig:
                st.markdown('<div class="graph-panel">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": True,
                                        "modeBarButtonsToRemove": ["lasso2d","select2d"],
                                        "displaylogo": False},
                                key="kg_viz")
                # Legend
                legend_html = '<div class="graph-legend">'
                for ntype, color in NODE_COLORS.items():
                    if ntype == "default": continue
                    legend_html += f'<span><span class="legend-dot" style="background:{color}"></span>{ntype}</span>'
                legend_html += '</div>'
                st.markdown(legend_html, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Context summary cards
                d = ctx.get("moc_detail")
                if d:
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="info-card">
                      <div class="info-card-title">Retrieved MoC</div>
                      <div style="font-size:.82rem;color:#e8eeff;font-weight:600">{d.get('moc_id')} — {d.get('title','')[:45]}</div>
                      <div style="font-size:.76rem;color:rgba(232,238,255,.55);margin-top:4px;line-height:1.5">
                        Asset: <span style="color:#34d399">{d.get('asset_id')}</span> ·
                        Risk: {risk_badge_html(d.get('risk_category','?'))} ·
                        Score: <span style="color:#f87171">{d.get('risk_score','?')}</span><br>
                        Cost: <span style="color:#4f8ef7">${d.get('actual_cost') or 0:,}</span> ·
                        Manhours: {d.get('actual_manhours','?')}h
                      </div>
                    </div>""", unsafe_allow_html=True)

                # Vector hits
                if ctx.get("vector_hits"):
                    st.markdown('<div class="info-card" style="margin-top:8px">', unsafe_allow_html=True)
                    st.markdown('<div class="info-card-title">Vector Similarity Matches</div>', unsafe_allow_html=True)
                    for h in ctx["vector_hits"][:4]:
                        sim = h.get("similarity", 0)
                        bar_w = int(sim * 100)
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,.05)">
                          <span style="font-size:.75rem;color:#4f8ef7;font-family:var(--mono);min-width:60px">{h.get('moc_id','')}</span>
                          <div style="flex:1;height:4px;background:rgba(255,255,255,.08);border-radius:2px">
                            <div style="width:{bar_w}%;height:100%;background:linear-gradient(90deg,#4f8ef7,#a78bfa);border-radius:2px"></div>
                          </div>
                          <span style="font-size:.72rem;color:rgba(232,238,255,.5)">{sim:.3f}</span>
                        </div>""", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                # Impact chain
                if ctx.get("impact_chain"):
                    st.markdown('<div class="info-card" style="margin-top:8px">', unsafe_allow_html=True)
                    st.markdown('<div class="info-card-title">Asset Impact Chain</div>', unsafe_allow_html=True)
                    for n in ctx["impact_chain"][:6]:
                        hop = n.get("hop_distance",1)
                        col = "#34d399" if hop == 1 else "#a78bfa"
                        st.markdown(f'<div style="font-size:.78rem;color:{col};padding:2px 0">{"↳"*hop} <span class="mono">{n.get("node_id","")}</span> {n.get("node_name","")}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:rgba(255,255,255,.03);border:1px dashed rgba(255,255,255,.1);
                            border-radius:14px;padding:40px 20px;text-align:center;color:rgba(232,238,255,.3);font-size:.85rem">
                  Graph data retrieved but no nodes to display.<br>Try a more specific query.
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(79,142,247,.04);border:1px dashed rgba(79,142,247,.2);
                        border-radius:16px;padding:50px 24px;text-align:center">
              <div style="font-size:2rem;margin-bottom:10px">🕸️</div>
              <div style="font-size:.9rem;font-weight:600;color:rgba(232,238,255,.6)">Knowledge Graph Visualisation</div>
              <div style="font-size:.78rem;color:rgba(232,238,255,.35);margin-top:6px;line-height:1.6">
                Send a message to MoCBot and the graph will<br>
                show exactly which nodes and relationships<br>
                were retrieved to answer your question.
              </div>
            </div>""", unsafe_allow_html=True)
