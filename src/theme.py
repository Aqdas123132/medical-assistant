"""
theme.py - Look and feel: colours, animated Dr. Medi character, cards, banners.

Everything here returns HTML/CSS strings or draws with st.markdown, so the
rest of the app stays clean. No extra libraries are needed.
"""

from datetime import datetime
from html import escape

import streamlit as st

from src.config import DISCLAIMER_SHORT

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }

/* soft animated gradient behind the whole app */
.stApp {
    background: linear-gradient(135deg, #ffffff, #eef3ff, #ffffff, #e9f7ef);
    background-size: 400% 400%;
    animation: mgGradient 18s ease infinite;
}
@keyframes mgGradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ---------- hero ---------- */
.mg-hero {
    display: flex; align-items: center; gap: 24px;
    background: rgba(255,255,255,0.85);
    border-radius: 24px; padding: 20px 28px; margin-bottom: 16px;
    box-shadow: 0 8px 30px rgba(29, 78, 216, 0.15);
    animation: mgFadeUp 0.7s ease both;
}
.mg-hero h1 { margin: 0; font-size: 2rem; color: #1d4ed8; }
.mg-hero p.sub { margin: 4px 0 12px; color: #475569; }
.mg-bubble {
    position: relative; display: grid; align-items: center;
    background: #00897b; color: #ffffff; border-radius: 16px;
    padding: 12px 18px; font-size: 0.95rem; max-width: 520px;
}
.mg-bubble::before {
    content: ""; position: absolute; left: -10px; top: 16px;
    border: 8px solid transparent; border-right-color: #00897b; border-left: 0;
}
.mg-bubble span { grid-area: 1 / 1; opacity: 0; }
.mg-bubble .m1 { animation: mgMsg 12s infinite 0s; }
.mg-bubble .m2 { animation: mgMsg 12s infinite 4s; }
.mg-bubble .m3 { animation: mgMsg 12s infinite 8s; }
@keyframes mgMsg {
    0% { opacity: 0; transform: translateY(6px); }
    5%, 30% { opacity: 1; transform: translateY(0); }
    36%, 100% { opacity: 0; transform: translateY(-6px); }
}

/* ---------- character animations ---------- */
.mg-float { animation: mgFloat 3.2s ease-in-out infinite; }
@keyframes mgFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.mg-eye { transform-origin: center; animation: mgBlink 4s infinite; transform-box: fill-box; }
@keyframes mgBlink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.1); } }
.mg-arm { transform-origin: 0% 100%; transform-box: fill-box; animation: mgWave 2.4s ease-in-out infinite; }
@keyframes mgWave { 0%,100% { transform: rotate(0deg); } 50% { transform: rotate(-25deg); } }

/* ---------- cards ---------- */
.mg-card {
    background: rgba(255,255,255,0.9); border-radius: 18px;
    border-left: 4px solid #1d4ed8;
    padding: 14px 18px; margin-bottom: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    animation: mgFadeUp 0.6s ease both;
}
.mg-card:hover { transform: translateY(-4px); box-shadow: 0 10px 24px rgba(0,0,0,0.14); }
.mg-card h4 { margin: 0 0 2px; color: #1d4ed8; }
.mg-card p { margin: 0; color: #475569; font-size: 0.9rem; }

.mg-stat {
    text-align: center; background: rgba(255,255,255,0.92);
    border-radius: 20px; padding: 18px 10px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    transition: transform 0.2s ease; animation: mgFadeUp 0.6s ease both;
}
.mg-stat:hover { transform: scale(1.04); }
.mg-stat .value { font-size: 1.9rem; font-weight: 700; color: #1d4ed8; }
.mg-stat .label { color: #607d8b; font-size: 0.85rem; }

/* ---------- urgency banner ---------- */
.mg-urgency {
    color: white; text-align: center; border-radius: 18px;
    padding: 16px; margin: 10px 0 14px; font-size: 1.4rem; font-weight: 700;
    letter-spacing: 1px; animation: mgFadeUp 0.5s ease both;
}
.mg-urgency.EMERGENCY { animation: mgPulse 1.2s infinite; }
@keyframes mgPulse {
    0% { box-shadow: 0 0 0 0 rgba(198,40,40,0.6); }
    70% { box-shadow: 0 0 0 18px rgba(198,40,40,0); }
    100% { box-shadow: 0 0 0 0 rgba(198,40,40,0); }
}

@keyframes mgFadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }

/* ---------- Streamlit widgets ---------- */
div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
    border-radius: 14px; font-weight: 600; transition: transform 0.15s ease;
}
div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-2px) scale(1.02);
}
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.9); border-radius: 16px; padding: 10px 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.07);
}

/* ---------- royal blue widgets (replace Streamlit's default red) ---------- */
span[data-baseweb="tag"] { background-color: #1d4ed8 !important; color: #ffffff !important; }
span[data-baseweb="tag"] span { color: #ffffff !important; }
div[data-testid="stSlider"] [role="slider"] { background-color: #1d4ed8 !important; }
div[data-testid="stSlider"] [data-testid="stThumbValue"] { color: #1d4ed8 !important; }
/* slider track: turn Streamlit's default red fill blue */
div[data-testid="stSlider"] [data-baseweb="slider"] div[style*="255, 75, 75"] { background: #1d4ed8 !important; }
button[kind="primary"], div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
    background-color: #1d4ed8 !important; border-color: #1d4ed8 !important; color: #ffffff !important;
}
button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"]:hover {
    background-color: #1e40af !important; border-color: #1e40af !important;
}
button[role="tab"][aria-selected="true"] { color: #1d4ed8 !important; }
div[data-baseweb="tab-highlight"] { background-color: #1d4ed8 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { border-color: #1d4ed8 !important; }
a { color: #1d4ed8; }

/* ---------- inputs ---------- */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
    background-color: #f7f9ff !important;
    border: 1.5px solid #a9bff0 !important;
    border-radius: 10px !important;
}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea { background-color: transparent !important; }

/* ================= always-readable light look (even if Streamlit is in dark mode) ================= */
:root { color-scheme: light; }

/* SOLID header so Deploy and the 3 dots stay visible while scrolling */
[data-testid="stHeader"] {
    background: #ffffff !important;
    border-bottom: 1px solid #dbe5fb;
    z-index: 999990 !important;
}
[data-testid="stHeader"] *, [data-testid="stToolbar"] * { color: #1e3a8a !important; }

[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #dbe5fb; }
/* keep "Model configuration" clear of the bottom notice bar */
[data-testid="stSidebar"] > div:first-child { padding-bottom: 100px; }
[data-testid="stSidebarContent"] { padding-bottom: 100px; }
.block-container { padding-bottom: 90px !important; }
[data-testid="stBottom"] { padding-bottom: 46px !important; }

h1, h2, h3, h4 { color: #1e3a8a !important; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-testid="stWidgetLabel"] p, label { color: #0b1b3a !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #475569 !important; }
.mg-hero h1, .mg-card h4, .mg-stat .value { color: #1d4ed8 !important; }
.mg-hero p.sub { color: #475569 !important; }
.mg-bubble, .mg-bubble span { color: #ffffff !important; }
.mg-urgency { color: #ffffff !important; }

/* text typed inside fields + dropdown lists */
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] *, div[data-baseweb="select"] input {
    color: #0b1b3a !important; -webkit-text-fill-color: #0b1b3a !important;
}
input::placeholder, textarea::placeholder { color: #94a3b8 !important; -webkit-text-fill-color: #94a3b8 !important; }
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li, div[data-baseweb="menu"] {
    background-color: #ffffff !important; color: #0b1b3a !important;
}
div[data-baseweb="popover"] li *, div[data-baseweb="menu"] * { color: #0b1b3a !important; }
div[data-baseweb="popover"] li:hover { background-color: #eaf0ff !important; }
span[data-baseweb="tag"], span[data-baseweb="tag"] * { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }

/* ================= form fields ================= */
/* thin blue bar in front of every label */
[data-testid="stWidgetLabel"] p { position: relative; padding-left: 12px; font-weight: 600; font-size: 0.92rem; }
[data-testid="stWidgetLabel"] p::before {
    content: ""; position: absolute; left: 0; top: 12%; height: 76%; width: 4px; border-radius: 4px;
    background: linear-gradient(180deg, #1d4ed8, #00897b);
}

/* section headings inside the form */
.mg-section {
    margin: 16px 0 8px; padding-bottom: 6px; font-weight: 700; font-size: 0.85rem;
    letter-spacing: 0.8px; text-transform: uppercase; color: #1e3a8a !important;
    border-bottom: 2px solid #dbe5fb;
}

/* fields lift on hover and glow when you click into them */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
    transition: border-color .2s ease, box-shadow .25s ease, transform .2s ease;
}
div[data-baseweb="input"]:hover, div[data-baseweb="textarea"]:hover, div[data-baseweb="select"] > div:hover {
    border-color: #1d4ed8 !important; transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(29, 78, 216, 0.15);
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="select"] > div:focus-within {
    border-color: #1d4ed8 !important; animation: mgGlow 2s ease-in-out infinite;
}
@keyframes mgGlow {
    0%, 100% { box-shadow: 0 0 0 4px rgba(29,78,216,0.18), 0 8px 22px rgba(29,78,216,0.18); }
    50%      { box-shadow: 0 0 0 6px rgba(0,137,123,0.20), 0 8px 22px rgba(0,137,123,0.18); }
}

/* form card */
div[data-testid="stForm"] {
    background: rgba(255,255,255,0.92); border: 1px solid #dbe5fb; border-radius: 20px;
    padding: 22px 26px; box-shadow: 0 10px 30px rgba(29,78,216,0.08); animation: mgFadeUp .6s ease both;
}

/* symptom chips pop in, slider knob grows when touched */
@keyframes mgPop { 0% { transform: scale(.5); opacity: 0; } 70% { transform: scale(1.08); } 100% { transform: scale(1); opacity: 1; } }
span[data-baseweb="tag"] { animation: mgPop .3s ease both; border-radius: 999px !important; }
div[data-testid="stSlider"] [role="slider"] { transition: transform .15s ease, box-shadow .15s ease; }
div[data-testid="stSlider"] [role="slider"]:hover, div[data-testid="stSlider"] [role="slider"]:focus {
    transform: scale(1.3); box-shadow: 0 0 0 8px rgba(29,78,216,0.18) !important;
}

/* the main button: flowing blue-green gradient */
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(90deg, #1d4ed8, #00897b, #1d4ed8) !important; background-size: 200% 100% !important;
    border: none !important; color: #ffffff !important; font-size: 1.05rem; padding: 0.55rem 1.6rem;
    box-shadow: 0 8px 20px rgba(29,78,216,0.3); animation: mgShift 4s linear infinite;
}
div[data-testid="stFormSubmitButton"] > button * { color: #ffffff !important; }
@keyframes mgShift { to { background-position: 200% 0; } }

/* ================= side note + moving disclaimer bar ================= */
.mg-side-note {
    background: #fff7ed; border-left: 4px solid #f97316; border-radius: 10px;
    padding: 8px 12px; font-size: 0.78rem; line-height: 1.4; margin: 6px 0 4px;
}
.mg-side-note, .mg-side-note * { color: #7c2d12 !important; }

.mg-ticker {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 999991; height: 38px;
    display: flex; align-items: center; overflow: hidden;
    background: linear-gradient(90deg, #1d4ed8, #1e40af); box-shadow: 0 -4px 16px rgba(29,78,216,0.25);
}
.mg-ticker .badge {
    flex: none; height: 100%; display: flex; align-items: center; padding: 0 14px;
    background: #e53935; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.5px; z-index: 2;
}
.mg-ticker .track { flex: 1; overflow: hidden; white-space: nowrap; }
.mg-ticker .move { display: inline-block; padding-left: 100%; font-size: 0.85rem; animation: mgTicker 45s linear infinite; }
.mg-ticker:hover .move { animation-play-state: paused; }
.mg-ticker, .mg-ticker * { color: #ffffff !important; }
@keyframes mgTicker { from { transform: translateX(0); } to { transform: translateX(-100%); } }

/* ===== same field styling for newer Streamlit versions (no data-baseweb) ===== */
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"], [data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] div[data-rac] > div[role="group"], [data-testid="stMultiSelect"] div[data-rac] > div[role="group"] {
    background-color: #f7f9ff !important; border: 1.5px solid #a9bff0 !important; border-radius: 10px !important;
    transition: border-color .2s ease, box-shadow .25s ease, transform .2s ease;
}
[data-testid="stTextInputRootElement"]:hover, [data-testid="stTextAreaRootElement"]:hover, [data-testid="stNumberInputContainer"]:hover,
[data-testid="stSelectbox"] div[data-rac] > div[role="group"]:hover, [data-testid="stMultiSelect"] div[data-rac] > div[role="group"]:hover {
    border-color: #1d4ed8 !important; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(29, 78, 216, 0.15);
}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stSelectbox"] div[data-rac] > div[role="group"]:focus-within,
[data-testid="stMultiSelect"] div[data-rac] > div[role="group"]:focus-within {
    border-color: #1d4ed8 !important; animation: mgGlow 2s ease-in-out infinite;
}
[data-testid="stTextInputField"], [data-testid="stTextAreaRootElement"] textarea,
[data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input {
    background: transparent !important; color: #0b1b3a !important; -webkit-text-fill-color: #0b1b3a !important;
}
span[data-tag] {
    background: #1d4ed8 !important; border-radius: 999px !important; animation: mgPop .3s ease both;
}
span[data-tag], span[data-tag] * { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
[role="listbox"], [role="listbox"] [role="option"] { background: #ffffff !important; color: #0b1b3a !important; }
[role="listbox"] [role="option"] * { color: #0b1b3a !important; }
[role="listbox"] [role="option"]:hover, [role="listbox"] [role="option"][data-focused="true"] { background: #eaf0ff !important; }
</style>
"""


def apply_theme():
    """Call once at the top of main()."""
    st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Dr. Medi - a small SVG doctor that blinks, waves and floats
# --------------------------------------------------------------------------
def character_svg(size: int = 120) -> str:
    return f"""
<svg class="mg-float" width="{size}" height="{size}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <path d="M25 118 Q25 80 60 80 Q95 80 95 118 Z" fill="#ffffff" stroke="#b2dfdb" stroke-width="2"/>
  <path d="M60 80 L50 118 M60 80 L70 118" stroke="#b2dfdb" stroke-width="2" fill="none"/>
  <path d="M44 84 Q40 104 56 104" stroke="#455a64" stroke-width="3" fill="none"/>
  <circle cx="58" cy="104" r="4" fill="#00897b"/>
  <g class="mg-arm"><rect x="92" y="62" width="9" height="30" rx="4.5" fill="#ffe0b2" transform="rotate(25 96 92)"/></g>
  <circle cx="60" cy="48" r="26" fill="#ffe0b2"/>
  <path d="M34 44 Q36 20 60 20 Q84 20 86 44 Q74 32 60 34 Q46 32 34 44 Z" fill="#4e342e"/>
  <circle cx="60" cy="25" r="6" fill="#b2ebf2" stroke="#00897b" stroke-width="2"/>
  <ellipse class="mg-eye" cx="50" cy="50" rx="3.5" ry="4.5" fill="#263238"/>
  <ellipse class="mg-eye" cx="70" cy="50" rx="3.5" ry="4.5" fill="#263238"/>
  <circle cx="43" cy="58" r="4" fill="#ffab91" opacity="0.6"/>
  <circle cx="77" cy="58" r="4" fill="#ffab91" opacity="0.6"/>
  <path d="M51 61 Q60 70 69 61" stroke="#6d4c41" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <rect x="72" y="92" width="14" height="14" rx="3" fill="#e53935"/>
  <path d="M79 95 V103 M75 99 H83" stroke="white" stroke-width="2.5"/>
</svg>
"""


def hero(title: str, subtitle: str, messages: list, size: int = 130):
    """Big header card: character on the left, rotating speech bubble on the right."""
    messages = (list(messages) + ["", "", ""])[:3]
    bubble = (
        f'<span class="m1">{escape(messages[0])}</span>'
        f'<span class="m2">{escape(messages[1])}</span>'
        f'<span class="m3">{escape(messages[2])}</span>'
    )
    st.markdown(
        f"""
<div class="mg-hero">
  <div>{character_svg(size)}</div>
  <div>
    <h1>{escape(title)}</h1>
    <p class="sub">{escape(subtitle)}</p>
    <div class="mg-bubble">{bubble}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def greeting(full_name: str) -> str:
    """'Good morning, Aqdas!' based on the time of day."""
    hour = datetime.now().hour
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    first = (full_name or "").split(" ")[0] or "there"
    return f"Good {part}, {first}!"


# --------------------------------------------------------------------------
# Small HTML builders (use with st.markdown(..., unsafe_allow_html=True))
# The icon argument is kept so old calls still work, but it is no longer shown.
# --------------------------------------------------------------------------
def info_card(icon: str, title: str, text: str) -> str:
    return (
        f'<div class="mg-card"><h4>{escape(title)}</h4><p>{escape(text)}</p></div>'
    )


def stat_card(icon: str, value, label: str) -> str:
    return (
        f'<div class="mg-stat"><div class="value">{escape(str(value))}</div>'
        f'<div class="label">{escape(label)}</div></div>'
    )


def urgency_banner(level: str, color: str) -> str:
    return (
        f'<div class="mg-urgency {escape(level)}" style="background:{escape(color)}">'
        f'Urgency level: {escape(level)}</div>'
    )


# --------------------------------------------------------------------------
# Disclaimers: a small calm note in the sidebar + a moving bar at the very bottom
# --------------------------------------------------------------------------
def sidebar_disclaimer():
    """Short, soft disclaimer for the sidebar (the full text scrolls at the bottom)."""
    st.markdown(
        '<div class="mg-side-note"><b>Educational AI only</b><br>'
        "Not a doctor or an emergency service. In an emergency, call your local emergency number.</div>",
        unsafe_allow_html=True,
    )


def disclaimer_ticker():
    """Fixed bar at the bottom of every page; the text travels from right to left."""
    text = escape(DISCLAIMER_SHORT)
    st.markdown(
        '<div class="mg-ticker"><div class="badge">NOTICE</div>'
        f'<div class="track"><span class="move">{text} &nbsp;&nbsp;•&nbsp;&nbsp; {text}</span></div></div>',
        unsafe_allow_html=True,
    )