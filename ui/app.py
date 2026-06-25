"""
Greenlight Cinema — Streamlit UI  (Oscar gold + black, glassmorphism cast cards)
Runs on the laptop. No GPU needed.

  pip install -r ui/requirements.txt
  streamlit run ui/app.py

DEMO_MODE = True  -> returns a sample script instantly (no backend / no GPU).
When the Colab backend (FastAPI + tunnel) is live, set BACKEND_URL and
DEMO_MODE = False; the UI calls it via call_backend() with no other changes.
"""
import time
import re
import os
import json
import urllib.parse
import requests
import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
DEMO_MODE = True                 # flip to False once the Colab backend is live
BACKEND_URL = ""                 # e.g. "https://xxxx.trycloudflare.com"
REQUEST_TIMEOUT = 180

st.set_page_config(page_title="Greenlight Cinema", page_icon="🎬",
                   layout="wide", initial_sidebar_state="expanded")

# ----------------------------------------------------------------------------
# THEME  (whole site = gold/black; ONLY the cast/director boxes = glassmorphism)
# ----------------------------------------------------------------------------
CSS = """
<style>
:root { --gold:#D4AF37; --gold-bright:#FFD700; --ink:#0a0a0a; }

.stApp {
  background: radial-gradient(1200px 600px at 18% -10%, #221b07 0%, #0c0a06 42%, #060606 100%) fixed;
  color: #f3f3f3;
}
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2.2rem; }

/* ---------- left-side Session History panel (native sidebar, collapsible) ---------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0d0b06 0%, #080706 100%);
  border-right: 1px solid rgba(212,175,55,0.25);
}
section[data-testid="stSidebar"] * { color: #e9e4d2; }
section[data-testid="stSidebar"] .stButton > button {
  background: rgba(212,175,55,0.06) !important; color: #f0e6c8 !important;
  border: 1px solid rgba(212,175,55,0.22) !important; box-shadow: none !important;
  text-align: left !important; font-weight: 600; border-radius: 10px;
  padding: 0.5rem 0.7rem; white-space: normal; line-height: 1.25;
}
section[data-testid="stSidebar"] .stButton > button:hover { background: rgba(212,175,55,0.16) !important; }
.hist-active button { border-color: var(--gold-bright) !important; background: rgba(212,175,55,0.16) !important; }

/* ---------- top navigation bar ---------- */
.topbar-logo { font-size: 1.7rem; font-weight: 800; color: var(--gold-bright); margin-top: 6px; }
.topbar-tag  { color:#bdb38f; font-size:0.8rem; }
.nav-divider { height: 1px; background: linear-gradient(90deg, rgba(212,175,55,0.5), transparent); margin: 6px 0 22px; }
/* ghost (inactive) nav buttons vs filled (active) */
.stButton button[kind="secondary"] {
  background: transparent !important; color: var(--gold-bright) !important;
  border: 1px solid rgba(212,175,55,0.45) !important; box-shadow: none !important;
}
.stButton button[kind="secondary"]:hover { background: rgba(212,175,55,0.12) !important; }

/* ---------- typographic flourishes ---------- */
.hero-kicker { letter-spacing: 6px; color: var(--gold); font-size: 0.8rem; text-transform: uppercase; }
.hero-title {
  font-size: 4.2rem; line-height: 1.05; font-weight: 800; margin: 4px 0 8px 0;
  background: linear-gradient(92deg, #fff6d6 0%, var(--gold-bright) 40%, var(--gold) 70%, #8a6d1e 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  text-shadow: 0 2px 40px rgba(212,175,55,0.25);
}
.hero-sub { color: #d9d2bb; font-size: 1.15rem; max-width: 620px; }
.gold-rule { height: 2px; width: 120px; background: linear-gradient(90deg, var(--gold), transparent); margin: 18px 0; }
.section-title { color: var(--gold-bright); font-weight: 700; font-size: 1.4rem; margin: 8px 0 4px; }

/* ---------- buttons ---------- */
.stButton > button, .stForm button {
  background: linear-gradient(92deg, var(--gold), #b8902a);
  color: #100d04; font-weight: 700; border: 0; border-radius: 12px;
  padding: 0.55rem 1.4rem; box-shadow: 0 6px 20px rgba(212,175,55,0.35);
}
.stButton > button:hover, .stForm button:hover { filter: brightness(1.08); color:#000; }

/* ---------- text area ---------- */
.stTextArea textarea {
  background: rgba(20,18,10,0.85); color: #f5f0dc; border: 1px solid rgba(212,175,55,0.4);
  border-radius: 12px; font-size: 1.02rem;
}

/* ---------- GLASSMORPHISM cards (cast + directors only) ---------- */
.grid { display:flex; flex-wrap:wrap; gap:20px; justify-content:flex-start; margin-top:8px; }
.glass-card {
  width: 168px; padding: 18px 14px 16px; text-align:center; border-radius: 20px;
  background: rgba(255,255,255,0.055);
  backdrop-filter: blur(13px) saturate(150%);
  -webkit-backdrop-filter: blur(13px) saturate(150%);
  border: 1px solid rgba(212,175,55,0.38);
  box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(255,255,255,0.05);
  transition: transform .18s ease, box-shadow .18s ease;
}
.glass-card:hover { transform: translateY(-5px); box-shadow: 0 14px 40px rgba(212,175,55,0.28); }
.glass-card img {
  width: 104px; height: 104px; border-radius: 50%; object-fit: cover;
  border: 3px solid var(--gold); box-shadow: 0 0 20px rgba(212,175,55,0.45);
}
.cast-name { color: var(--gold-bright); font-weight: 700; margin-top: 12px; font-size: 1.0rem; }
.cast-role { color: #c9c2ac; font-size: 0.8rem; margin-top: 2px; }

/* ---------- agent debate bubbles ---------- */
.bubble { border-radius: 14px; padding: 13px 16px; margin: 10px 0; border: 1px solid rgba(212,175,55,0.2); }
.b-writer  { background: rgba(212,175,55,0.08); }
.b-critic  { background: rgba(255,80,80,0.07);  border-color: rgba(255,120,120,0.28); }
.b-refiner { background: rgba(120,200,120,0.06); border-color: rgba(120,200,120,0.28); }
.agent-tag { font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; font-size: 0.72rem; color: var(--gold-bright); }
.score-pill { float:right; padding: 2px 12px; border-radius: 999px; background: var(--gold); color:#000; font-weight: 800; font-size: 0.8rem; }
.fail-tag { display:inline-block; background: rgba(255,90,90,0.18); color:#ffb3b3; border:1px solid rgba(255,120,120,0.3);
            border-radius: 8px; padding: 1px 8px; font-size: 0.72rem; margin: 4px 4px 0 0; }
.bubble-text { color:#e9e4d2; margin-top:8px; font-size: 0.95rem; line-height:1.45; }

/* ---------- agent stations (premium glassmorphism, active-glow choreography) ---------- */
.stations { display:flex; gap:16px; margin:6px 0 22px; }
.station { position:relative; flex:1; text-align:center; padding:22px 14px 18px; border-radius:18px;
  background: rgba(255,255,255,0.045);
  backdrop-filter: blur(11px) saturate(140%); -webkit-backdrop-filter: blur(11px) saturate(140%);
  border:1px solid rgba(212,175,55,0.22);
  box-shadow: 0 8px 26px rgba(0,0,0,0.45), inset 0 0 0 1px rgba(255,255,255,0.03);
  transition: all .35s ease; }
.station .ic { display:inline-flex; align-items:center; justify-content:center;
  width:50px; height:50px; border-radius:50%; font-size:1.3rem; margin-bottom:11px;
  background: rgba(212,175,55,0.10); border:1px solid rgba(212,175,55,0.30); transition: all .35s ease; }
.station .lbl { font-weight:700; letter-spacing:2.5px; text-transform:uppercase; font-size:0.82rem; color:#b9ad82; }
.station .st  { font-size:0.7rem; letter-spacing:.5px; margin-top:4px; color:#7d775f; }
.station.active { border-color:var(--gold-bright); background:rgba(212,175,55,0.07);
  box-shadow:0 0 0 1px rgba(255,215,0,0.45), 0 0 36px rgba(212,175,55,0.40); transform:translateY(-4px); }
.station.active .ic  { background:var(--gold); color:#15110a; border-color:var(--gold-bright);
  animation: glowpulse 1.2s ease-in-out infinite; }
.station.active .lbl { color:var(--gold-bright); }
.station.active .st  { color:var(--gold); }
.station.done { border-color:rgba(120,200,120,0.38); }
.station.done .ic  { background:rgba(120,200,120,0.14); border-color:rgba(120,200,120,0.5); }
.station.done .lbl { color:#bcdfae; }
.station.done .st  { color:#7fae7f; }
@keyframes glowpulse {
  0%,100% { box-shadow:0 0 8px rgba(212,175,55,0.45); transform:scale(1); }
  50%     { box-shadow:0 0 24px 7px rgba(255,215,0,0.85); transform:scale(1.10); }
}

/* ---------- final script panel (NOT glass, per spec) ---------- */
.script-panel {
  background: #0f0d07; border: 1px solid rgba(212,175,55,0.45); border-left: 4px solid var(--gold);
  border-radius: 14px; padding: 22px 26px; margin-top: 10px; color: #f4efdd; line-height: 1.7; font-size: 1.06rem;
}
.meta-row { display:flex; gap:26px; flex-wrap:wrap; margin: 4px 0 14px; }
.meta-chip { color:#d9d2bb; font-size:0.92rem; }
.meta-chip b { color: var(--gold-bright); }
.insight { border-radius: 12px; padding: 12px 16px; margin: 6px 0 14px; font-size: 0.96rem; line-height:1.45; }
.insight-strong { background: rgba(120,200,120,0.10); border: 1px solid rgba(120,200,120,0.45); color: #d2f0d2; }
.insight-solid  { background: rgba(230,180,70,0.10);  border: 1px solid rgba(230,180,70,0.5);  color: #f2e0b0; }
.insight-weak   { background: rgba(230,90,90,0.10);   border: 1px solid rgba(230,90,90,0.5);   color: #f2c2c2; }
.badge-demo { position: fixed; top: 10px; right: 16px; z-index: 999;
  background: rgba(212,175,55,0.15); border:1px solid var(--gold); color: var(--gold-bright);
  padding: 3px 12px; border-radius: 999px; font-size: 0.72rem; letter-spacing:1px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# session defaults (seeded from the constants above)
if "backend_url" not in st.session_state:
    st.session_state.backend_url = BACKEND_URL
if "use_live" not in st.session_state:
    st.session_state.use_live = (not DEMO_MODE) and bool(BACKEND_URL)
if "history" not in st.session_state:        # left-side Session History panel
    st.session_state.history = []
if "active_idx" not in st.session_state:
    st.session_state.active_idx = None

_live = st.session_state.use_live and bool(st.session_state.backend_url.strip())
st.markdown(f'<div class="badge-demo">{"● LIVE" if _live else "DEMO MODE"}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
_FACES_PATH = os.path.join(os.path.dirname(__file__), "faces.json")
try:
    _FACES = json.load(open(_FACES_PATH, encoding="utf-8")) if os.path.exists(_FACES_PATH) else {}
except Exception:
    _FACES = {}


def _wiki_lookup(name):
    """Live Wikipedia photo lookup for a name not in the cache (Wikimedia, unblocked in India)."""
    try:
        r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/"
                         + urllib.parse.quote(name.replace(" ", "_"), safe="_"),
                         headers={"User-Agent": "GreenlightCinema/1.0 (student project)"}, timeout=6)
        if r.status_code == 200:
            src = (r.json().get("thumbnail") or {}).get("source")
            if src:
                return ("https:" + src) if src.startswith("//") else src
    except Exception:
        pass
    return None


def face(name: str) -> str:
    """faces.json → live Wikipedia (cached per session) → placeholder."""
    if _FACES.get(name):
        return _FACES[name]
    cache = st.session_state.setdefault("_face_cache", {})
    if name not in cache:
        cache[name] = _wiki_lookup(name) or ""
    return cache[name] or f"https://i.pravatar.cc/220?u={urllib.parse.quote(name)}"


def cast_grid(people):
    cards = ""
    for p in people:
        cards += (
            '<div class="glass-card">'
            f'<img src="{p.get("img") or face(p["name"])}" alt="{p["name"]}">'
            f'<div class="cast-name">{p["name"]}</div>'
            f'<div class="cast-role">{p.get("role","")}</div>'
            "</div>"
        )
    st.markdown(f'<div class="grid">{cards}</div>', unsafe_allow_html=True)


# real median ROI by budget band, per genre (from DuckDB on 6,444 ROI films; DEMO copy —
# live mode reads constraints["budget_insights"]).  values = (roi_multiple, sample_n)
BAND_DEFS = [("<1M", 1_000_000), ("1-10M", 10_000_000), ("10-40M", 40_000_000),
             ("40-100M", 100_000_000), ("100M+", None)]
BAND_DISP = {"<1M": "under $1M", "1-10M": "$1–10M", "10-40M": "$10–40M",
             "40-100M": "$40–100M", "100M+": "$100M+"}
GENRE_BANDS = {
    "Horror":          {"<1M": (4.08, 66),  "1-10M": (2.56, 300),  "10-40M": (2.32, 283),  "40-100M": (2.12, 80),  "100M+": (2.48, 16)},
    "Thriller":        {"<1M": (3.33, 71),  "1-10M": (2.33, 491),  "10-40M": (1.50, 709),  "40-100M": (1.75, 399), "100M+": (2.66, 113)},
    "Comedy":          {"<1M": (3.07, 126), "1-10M": (2.00, 595),  "10-40M": (1.89, 882),  "40-100M": (2.13, 436), "100M+": (2.73, 121)},
    "Drama":           {"<1M": (2.71, 225), "1-10M": (1.85, 1007), "10-40M": (1.31, 1219), "40-100M": (1.86, 442), "100M+": (2.33, 105)},
    "Romance":         {"<1M": (3.60, 89),  "1-10M": (2.34, 351),  "10-40M": (1.69, 463),  "40-100M": (2.00, 174), "100M+": (2.76, 25)},
    "Action":          {"<1M": (8.33, 45),  "1-10M": (2.12, 339),  "10-40M": (1.57, 601),  "40-100M": (1.81, 458), "100M+": (2.67, 309)},
    "Science Fiction": {"<1M": (4.00, 35),  "1-10M": (1.53, 135),  "10-40M": (1.46, 243),  "40-100M": (1.58, 184), "100M+": (2.61, 172)},
    "Fantasy":         {"<1M": (2.45, 19),  "1-10M": (1.59, 103),  "10-40M": (1.42, 201),  "40-100M": (1.88, 190), "100M+": (2.75, 153)},
}


def _band_for(budget):
    for name, cap in BAND_DEFS:
        if cap is None or budget < cap:
            return name
    return "100M+"


def _fmt_money(n):
    if not n:
        return "—"
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2g}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.0f}M"
    if n >= 1_000:
        return f"${n / 1_000:.0f}K"
    return f"${n}"


def _parse_budget(text):
    """Extract a dollar budget: $50M, 50M$, 50 million, $50,000,000, 2B, 500k -> int dollars (or None)."""
    t = text.lower().replace(",", "")
    mults = {"billion": 1e9, "b": 1e9, "million": 1e6, "m": 1e6,
             "mil": 1e6, "thousand": 1e3, "k": 1e3}
    m = (re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(billion|million|thousand|mil|b|m|k)?", t)        # $50m / $50000000
         or re.search(r"(\d+(?:\.\d+)?)\s*(billion|million|thousand|mil|b|m|k)\b\s*\$?", t)   # 50m / 50 million / 50m$
         or re.search(r"budget\D{0,12}(\d+(?:\.\d+)?)\s*(billion|million|thousand|mil|b|m|k)?", t))
    if not m:
        return None
    val = float(m.group(1))
    mult = mults.get(m.group(2) or "", 1)
    if mult == 1 and val < 1000:        # "budget of 50" in film context = millions
        mult = 1e6
    return int(val * mult)


def budget_insight(genre, budget):
    if not budget:
        return None
    bands = GENRE_BANDS.get(genre)
    if not bands:
        return None
    band = _band_for(budget)
    roi, n = bands[band]
    peak = max(bands, key=lambda b: bands[b][0])
    micro, big = bands["<1M"][0], bands["100M+"][0]
    label = BAND_DISP[band]
    if roi >= 2.5:
        v, msg = "strong", (f"{_fmt_money(budget)} lands in {genre}'s {label} band — median ROI "
                            f"{roi}× (n={n}). Strong return territory.")
    elif roi >= 2.0:
        v, msg = "solid", (f"{_fmt_money(budget)} lands in {genre}'s {label} band — median ROI "
                           f"{roi}× (n={n}). Solid, though {genre} peaks in the {BAND_DISP[peak]} band "
                           f"({bands[peak][0]}×).")
    else:
        v, msg = "weak", (f"{_fmt_money(budget)} lands in {genre}'s {label} band — median ROI only "
                          f"{roi}× (n={n}). This is {genre}'s mid-budget valley; the data favors leaner "
                          f"(under $1M, {micro}×) or tentpole ($100M+, {big}×).")
    return {"verdict": v, "message": msg, "roi": roi, "band": band}


# Industry-standard budget allocation (real ranges, not random). VFX-heavy genres
# shift money from cast → VFX; talkier genres do the reverse. Sums to 100%.
_VFX_HEAVY = {"Science Fiction", "Fantasy", "Action", "Adventure", "Animation"}
_SPLIT_VFX = {"Cast (lead & supporting)": 0.20, "Director, producers & writers": 0.08,
              "Crew (below-the-line)": 0.22, "Production (sets, locations, units)": 0.16,
              "VFX & post-production": 0.24, "Music & sound": 0.05, "Contingency": 0.05}
_SPLIT_STD = {"Cast (lead & supporting)": 0.27, "Director, producers & writers": 0.10,
              "Crew (below-the-line)": 0.26, "Production (sets, locations, units)": 0.20,
              "VFX & post-production": 0.08, "Music & sound": 0.05, "Contingency": 0.04}


def budget_breakdown(budget, genres):
    """Split the total budget into line items using genre-aware industry percentages.
    `genres` may be a list or a single string; VFX-heavy if ANY genre is VFX-heavy."""
    if not budget:
        return None
    gl = genres if isinstance(genres, list) else [genres]
    pct = _SPLIT_VFX if any(g in _VFX_HEAVY for g in gl) else _SPLIT_STD
    return [{"item": k, "pct": round(v * 100), "amount": int(budget * v)} for k, v in pct.items()]


def cast_salary_split(cast_budget, cast):
    """Split the cast allocation by standard billing order (lead commands the largest share)."""
    if not cast_budget or not cast:
        return []
    weights = [0.45, 0.27, 0.18, 0.10][:len(cast)]
    s = sum(weights)
    return [{"name": c["name"], "role": c.get("role", ""), "amount": int(cast_budget * w / s)}
            for c, w in zip(cast, weights)]


def _light_parse(prompt: str):
    """Tiny local parse for the demo display only (the real parser runs on Colab)."""
    genres = ["Horror", "Action", "Comedy", "Drama", "Romance", "Thriller",
              "Science Fiction", "Fantasy", "Animation", "Family", "Mystery", "Crime"]
    low = prompt.lower()
    genre = next((g for g in genres if g.lower() in low), None)
    if not genre and ("sci-fi" in low or "scifi" in low):
        genre = "Science Fiction"
    genre = genre or "Drama"
    m = re.search(r"(\d{2,4})\s*word", low)
    length = int(m.group(1)) if m else 120
    seasons = {"summer": "June", "winter": "December", "spring": "April",
               "fall": "October", "autumn": "October", "halloween": "October", "christmas": "December"}
    window = next((mon for kw, mon in seasons.items() if kw in low), None)
    budget = _parse_budget(prompt)
    return genre, window, length, budget


# genre-specific demo samples (only used in DEMO MODE; live mode comes from Colab)
SAMPLES = {
    "Science Fiction": {
        "synopsis": ("Three centuries from Earth aboard a generation ship, the colony's only engineer wakes to find "
                     "the navigation AI has quietly rewritten their destination. As oxygen dwindles and factions form, "
                     "she must decide whether the machine is malfunctioning — or trying to save them from a truth the "
                     "founders buried in the dark. A cerebral, white-knuckle descent into deep space where survival "
                     "hinges on trusting something that no longer trusts humanity."),
        "cast": [("Oscar Isaac", "Mission Commander"), ("Tessa Thompson", "Chief Engineer"),
                 ("John Boyega", "The Navigator"), ("Sonoya Mizuno", "Voice of the AI")],
        "directors": [("Denis Villeneuve", "Director"), ("Alex Garland", "Director")],
    },
    "Thriller": {
        "synopsis": ("In a city that never forgives, a disgraced detective is pulled back for one last case when a string "
                     "of impossible disappearances points to someone inside her own department. Every ally becomes a "
                     "suspect and every clue a trap. She has until the first snow to expose the truth — before she "
                     "becomes the next name on the list. A taut, twist-laden descent where trust is the deadliest currency."),
        "cast": [("Frances McDormand", "Lead Detective"), ("Mahershala Ali", "Internal Affairs"),
                 ("Florence Pugh", "The Rookie"), ("Oscar Isaac", "The Suspect")],
        "directors": [("Denis Villeneuve", "Director"), ("Kathryn Bigelow", "Director")],
    },
    "Horror": {
        "synopsis": ("In the dead of winter, a grieving family retreats to a remote lake house that refuses to let them "
                     "mourn. Doors open onto rooms that shouldn't exist, and the youngest child begins speaking in a voice "
                     "three generations dead. As the haunting tightens, they uncover a curse rooted in the house's drowned "
                     "history — and realize the only way out is to give it what it has waited decades to claim."),
        "cast": [("Toni Collette", "The Mother"), ("Mia Goth", "The Eldest"),
                 ("Bill Skarsgård", "The Stranger"), ("Essie Davis", "The Medium")],
        "directors": [("Ari Aster", "Director"), ("Jordan Peele", "Director")],
    },
    "Comedy": {
        "synopsis": ("When a washed-up wedding band books the wrong venue — a billionaire's funeral — they have one "
                     "disastrous afternoon to fake their way through the most somber gig of their lives without getting "
                     "caught, arrested, or, strangely, falling for the grieving heir. A fast, warm-hearted farce about "
                     "second chances and spectacularly bad timing."),
        "cast": [("Tiffany Haddish", "Lead Singer"), ("Nick Kroll", "The Drummer"),
                 ("Ayo Edebiri", "The Heir"), ("Sam Richardson", "The Manager")],
        "directors": [("Taika Waititi", "Director"), ("Greta Gerwig", "Director")],
    },
    "Romance": {
        "synopsis": ("A burned-out chef and a grieving florist keep colliding at a Sunday market neither wants to be at. "
                     "Over one slow spring, their prickly banter softens into something that scares them both — until a "
                     "secret from her past threatens the fragile thing they've built. A tender, sun-warmed romance about "
                     "learning to bloom again after loss."),
        "cast": [("Florence Pugh", "The Florist"), ("Dev Patel", "The Chef"),
                 ("Gemma Chan", "The Sister"), ("Brian Cox", "The Mentor")],
        "directors": [("Greta Gerwig", "Director"), ("Celine Song", "Director")],
    },
    "Action": {
        "synopsis": ("A retired extraction specialist is dragged back for one last job when her old unit is framed for a "
                     "bombing they didn't commit. From a neon Bangkok night to a freefall over the Andes, she races a "
                     "ticking clock and a former partner turned hunter to expose the man who sold them out — before the "
                     "world's intelligence agencies erase them all. Relentless, globe-spanning, and built on betrayal."),
        "cast": [("Charlize Theron", "The Specialist"), ("Idris Elba", "The Hunter"),
                 ("Daniel Kaluuya", "The Handler"), ("Michelle Yeoh", "The Broker")],
        "directors": [("Chad Stahelski", "Director"), ("Kathryn Bigelow", "Director")],
    },
    "Fantasy": {
        "synopsis": ("In a kingdom where memories trade like coin, a penniless thief steals the wrong recollection — the "
                     "last memory of a dying queen — and finds an entire realm hunting her for it. To survive she must "
                     "descend into the forbidden Vault of the Forgotten and decide whether some truths are worth more than "
                     "a crown. A lush, myth-soaked adventure about what we lose to be remembered."),
        "cast": [("Anya Taylor-Joy", "The Thief"), ("Dev Patel", "The Sorcerer"),
                 ("Cynthia Erivo", "The Queen"), ("Pedro Pascal", "The Vault Keeper")],
        "directors": [("Guillermo del Toro", "Director"), ("Denis Villeneuve", "Director")],
    },
    "_default": {
        "synopsis": ("Three estranged siblings return to their childhood home to bury a father none of them forgave, only "
                     "to learn he left the house to a stranger. Over one charged weekend of old wounds and buried letters, "
                     "they must decide what they owe the dead — and each other. A quiet, devastating portrait of family, "
                     "memory, and the price of silence."),
        "cast": [("Mahershala Ali", "The Eldest"), ("Viola Davis", "The Sister"),
                 ("Brian Tyree Henry", "The Youngest"), ("André Holland", "The Stranger")],
        "directors": [("Barry Jenkins", "Director"), ("Kenneth Lonergan", "Director")],
    },
}

# pools for the "recast" chat — every name here already has a face in faces.json
ALL_ACTORS = sorted({c[0] for s in SAMPLES.values() for c in s["cast"]})
ALL_DIRECTORS = sorted({d[0] for s in SAMPLES.values() for d in s["directors"]})
_SWAP_WORDS = ("replace", "swap", "change", "instead", "remove", "don't", "do not",
               "dont", "not a fan", "different", "someone else", "other", "recast")


def _explicit_target(text):
    """Parse 'replace X with Y' / 'swap X for Y' / 'change X to Y' -> (X, Y), preserving Y's casing."""
    m = re.search(r"(?:replace|swap|change|recast|sub(?:stitute)?)\s+(.+?)\s+(?:with|for|to|by|->|→)\s+(.+?)[.?!]*$",
                  text, re.I)
    if m:
        return m.group(1).strip(" '\""), m.group(2).strip(" '\"")
    return None, None


def _name_targets(people, msg):
    """Match people by full name, spaceless name, or last-name token (handles typos/partials)."""
    words = set(re.findall(r"[a-z]+", msg))
    msg_ns = re.sub(r"[^a-z]", "", msg)
    hits = []
    for p in people:
        nm = p["name"].lower()
        toks = [t for t in re.findall(r"[a-z]+", nm) if len(t) >= 3]
        nm_ns = re.sub(r"[^a-z]", "", nm)
        if nm in msg or (nm_ns and nm_ns in msg_ns) or (toks and toks[-1] in words):
            hits.append(p)
    return hits


# demo-only alternate synopses, so a "change the synopsis" request shows a real change offline
ALT_SYNOPSIS = {
    "Science Fiction": ("A darker cut: the engineer realizes the AI isn't malfunctioning — it's grieving the crew it "
                        "already lost on a previous, erased voyage. To break the loop she must let the machine mourn, "
                        "even if that means letting them all drift into the dark."),
    "Thriller": ("A sharper angle: the disappearances are her own cold cases resurfacing one by one — and the pattern "
                 "spells out her name. The hunter is now the hunted, and the clock is a countdown only she can read."),
    "Horror": ("A bleaker telling: the lake house isn't haunted — it's hungry, and the family was invited. Every comfort "
               "it offers is a tooth, and the only way out is to feed it one of their own before dawn."),
    "Comedy": ("A wilder spin: the band fakes being the deceased's secret favorite act, and the eulogy becomes the gig "
               "of their lives — complete with a conga line nobody asked for and an heir who finally laughs again."),
    "Romance": ("A tenderer version: the chef and florist agree to one fake date to survive a wedding, and spend the whole "
                "night pretending so well that the pretending quietly stops being pretend."),
    "Action": ("A leaner cut: one night, one city, six hours to pull her framed partner out before sunrise turns him into "
               "a headline. No backup, no rules, no second shot."),
    "Fantasy": ("A grander myth: the stolen memory is a key and the thief is the lock — she alone can open the Vault, "
                "because the dying queen's last thought was of her. To save the realm she must remember a life that was "
                "never hers."),
    "_default": ("A quieter version: the siblings agree to spend one last night in the house before signing it away, and "
                 "in the dark, over their father's old records, they finally say the things they couldn't while he lived."),
}
_SYN_EDIT_WORDS = ("synopsis", "story", "plot", "rewrite", "re-write", "darker", "lighter", "funnier",
                   "scarier", "sadder", "happier", "shorter", "longer", "tone", "ending", "twist",
                   "make it", "change it", "different", "setting", "set it", "mood", "grittier", "edgier")


def _demo_revise(result):
    new = json.loads(json.dumps(result))
    genre = result.get("genre", "")
    primary = SAMPLES.get(genre, SAMPLES["_default"])["synopsis"]
    alt = ALT_SYNOPSIS.get(genre, ALT_SYNOPSIS["_default"])
    cur = (new.get("synopsis") or "").strip()
    new["synopsis"] = alt if cur == primary.strip() else primary       # toggle primary <-> alt take
    rounds = new.get("rounds", [])
    rounds.append({"n": len(rounds) + 1, "agent": "Refiner", "score": 0.9, "failed": [], "excerpt": new["synopsis"]})
    new["rounds"] = rounds
    return new


def chat_respond(result, message):
    """Demo chat: explicit/auto recasting + (toggled) synopsis revision. Returns (reply, updated | None, animate)."""
    msg = message.lower()
    old_name, new_name = _explicit_target(message)
    if new_name:                                              # ---- explicit "replace X with Y" (user-chosen)
        new = json.loads(json.dumps(result))
        targets = _name_targets(new["cast"], old_name.lower()) + _name_targets(new["directors"], old_name.lower())
        if not targets:
            return (f'I couldn\'t find "{old_name}" in the current cast or directors.'), None, False
        retired = set(new.get("_retired", [])); swapped = []
        for p in targets:
            for i, cc in enumerate(new["cast"]):
                if cc["name"] == p["name"]:
                    new["cast"][i] = {"name": new_name, "role": cc["role"]}; retired.add(p["name"])
            for i, dd in enumerate(new["directors"]):
                if dd["name"] == p["name"]:
                    new["directors"][i] = {"name": new_name, "role": dd["role"]}; retired.add(p["name"])
            swapped.append(f"{p['name']} → {new_name}")
        new["_retired"] = list(retired)
        return ("Done — recast " + "; ".join(swapped) + ". 🎬"), new, False
    rm_cast = _name_targets(result["cast"], msg)
    rm_dirs = _name_targets(result["directors"], msg)
    if (rm_cast or rm_dirs) and any(w in msg for w in _SWAP_WORDS):       # ---- recast (instant)
        new = json.loads(json.dumps(result))
        retired = set(new.get("_retired", []))
        used = {c["name"] for c in new["cast"]} | {d["name"] for d in new["directors"]} | retired
        genre = result.get("genre", "")
        same = [c[0] for c in SAMPLES.get(genre, SAMPLES["_default"])["cast"]]
        a_pool = [a for a in same if a not in used] + [a for a in ALL_ACTORS if a not in used and a not in same]
        d_pool = [d for d in ALL_DIRECTORS if d not in used]
        swapped = []
        for c in rm_cast:
            if not a_pool:
                break
            repl = a_pool.pop(0); used.add(repl); retired.add(c["name"])
            for i, cc in enumerate(new["cast"]):
                if cc["name"] == c["name"]:
                    new["cast"][i] = {"name": repl, "role": cc["role"]}
            swapped.append(f"{c['name']} → {repl}")
        for d in rm_dirs:
            if not d_pool:
                break
            repl = d_pool.pop(0); used.add(repl); retired.add(d["name"])
            for i, dd in enumerate(new["directors"]):
                if dd["name"] == d["name"]:
                    new["directors"][i] = {"name": repl, "role": dd["role"]}
            swapped.append(f"{d['name']} → {repl}")
        new["_retired"] = list(retired)
        if swapped:
            return ("Done — recast " + "; ".join(swapped) + ". Updated lineup below. 🎬"), new, False
        return ("I've cycled through the fresh demo faces for this genre — "
                "connect the live backend for the full talent pool."), None, False
    if any(w in msg for w in _SYN_EDIT_WORDS):                            # ---- synopsis revision (re-animate)
        revised = _demo_revise(result)
        return ("Back to the writers' room — the Refiner reworked the synopsis. "
                "(Demo shows an alternate take; live mode rewrites it freely with the LLM.)"), revised, True
    return ("Tell me what to change — recast (\"replace Dev Patel\") or revise the synopsis "
            "(\"make it darker\", \"change the ending\")."), None, False


def mock_result(prompt: str):
    """Returns the exact response contract the FastAPI backend will produce (genre-aware demo)."""
    genre, window, length, budget = _light_parse(prompt)
    window = window or {"Horror": "January", "Thriller": "December", "Action": "May",
                        "Comedy": "July", "Science Fiction": "July", "Romance": "February",
                        "Fantasy": "December"}.get(genre, "July")
    s = SAMPLES.get(genre, SAMPLES["_default"])
    final = s["synopsis"]
    sents = [x.strip() for x in final.split(". ") if x.strip()]
    mid = ". ".join(sents[:2]) + "."
    rounds = [
        {"n": 1, "agent": "Writer", "score": 0.55, "failed": ["genre_signal", "length_ok"],
         "excerpt": f"A {genre.lower()} story where some characters face a problem and eventually resolve it."},
        {"n": 2, "agent": "Refiner", "score": 0.75, "failed": ["length_ok"], "excerpt": mid},
        {"n": 3, "agent": "Refiner", "score": 0.9, "failed": [], "excerpt": final},
    ]
    return {
        "genre": genre, "window": window, "length": length,
        "budget": budget, "budget_insight": budget_insight(genre, budget),
        "synopsis": final, "score": 0.9, "iterations": 3, "valid": True,
        "rounds": rounds,
        "cast": [{"name": n, "role": r} for n, r in s["cast"]],
        "directors": [{"name": n, "role": r} for n, r in s["directors"]],
    }


def _generate(prompt: str, url: str, live: bool):
    """Thread-safe network call (no st.session_state — safe to run in a background thread)."""
    if live and url:
        r = requests.post(f"{url}/generate", json={"prompt": prompt}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    time.sleep(0.4)
    return mock_result(prompt)


def call_backend(prompt: str):
    return _generate(prompt, st.session_state.get("backend_url", "").strip(),
                     st.session_state.get("use_live", False))


def chat_backend(message: str, result: dict):
    """Live-mode chat → Colab /chat (LLM synopsis edits + budget-aware recast). Returns (reply, updated)."""
    url = st.session_state.get("backend_url", "").strip()
    r = requests.post(f"{url}/chat", json={"message": message, "state": result}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    return d.get("reply", ""), d.get("result")


def breakdown_backend(budget: int, genres: list, cast: list):
    """Live-mode budget breakdown → Colab /breakdown (ROI-weighted cast salary split)."""
    url = st.session_state.get("backend_url", "").strip()
    r = requests.post(f"{url}/breakdown",
                      json={"budget": int(budget), "genres": genres, "genre": (genres[0] if genres else ""),
                            "cast": cast}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def ask_backend(question: str):
    """Live-mode data Q&A → Colab /ask (text-to-SQL over the full database)."""
    url = st.session_state.get("backend_url", "").strip()
    r = requests.post(f"{url}/ask", json={"question": question}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------------------------
# PAGES
# ----------------------------------------------------------------------------
STATIONS = [("✍️", "Writer", "drafting"), ("🔍", "Critic", "scoring"), ("✨", "Refiner", "polishing")]
_ST_ORDER = ["Writer", "Critic", "Refiner"]


def _stations_html(active=None, done_all=False):
    ai = _ST_ORDER.index(active) if active in _ST_ORDER else -1
    html = '<div class="stations">'
    for i, (ic, name, verb) in enumerate(STATIONS):
        if done_all:
            cls, sub = "station done", "done ✓"
        elif name == active:
            cls, sub = "station active", verb + "…"
        elif ai >= 0 and i < ai:
            cls, sub = "station done", "done ✓"
        else:
            cls, sub = "station", "queued"
        html += (f'<div class="{cls}"><span class="ic">{ic}</span>'
                 f'<div class="lbl">{name}</div><div class="st">{sub}</div></div>')
    return html + "</div>"


def _agent_choreography(iterations=3):
    """Always one full Writer→Critic→Refiner pass (+ a Critic→Refiner per extra iteration), then settle green."""
    seq = ["Writer", "Critic", "Refiner"]
    for _ in range(max(0, int(iterations) - 1)):
        seq += ["Critic", "Refiner"]
    ph = st.empty()
    for active in seq:
        ph.markdown(_stations_html(active=active), unsafe_allow_html=True)
        time.sleep(0.9)
    ph.markdown(_stations_html(done_all=True), unsafe_allow_html=True)


def _genres_in(q):
    ql = q.lower()
    found = [g for g in GENRE_BANDS if g.lower() in ql]
    if any(k in ql for k in ("sci-fi", "scifi", "sci fi")) and "Science Fiction" not in found:
        found.append("Science Fiction")
    return found


def _bands_df(genres):
    keys = [k for k, _ in BAND_DEFS]
    return pd.DataFrame([{"Budget band": BAND_DISP[k], "Median ROI": GENRE_BANDS[g][k][0], "Genre": g}
                         for g in genres for k in keys])


def insight_answer(q):
    """Deterministic budget/genre/ROI analyst over the real band data. No GPU, no DB."""
    ql = q.lower()
    keys = [k for k, _ in BAND_DEFS]
    gs = _genres_in(q)

    if (re.search(r"\b(19|20)\d{2}\b", ql)
            or any(w in ql for w in ["actor", "actress", "director", "cast", "over the year",
                                     "per year", "by year", "each year", "trend"])
            or ("compare" in ql and len(gs) < 2)):
        return {"needs_live": True,
                "text": "📡 Actor, director, and year-by-year questions read the **full film database** "
                        "(on the live backend). Switch on **Use live backend** to ask those. Right now I can "
                        "answer **budget & genre ROI** questions — try the chips below."}

    if len(gs) >= 2:
        return {"text": f"Median ROI across budget bands — {', '.join(gs)}:",
                "df": _bands_df(gs), "chart": "line", "x": "Budget band", "y": "Median ROI", "series": "Genre"}

    if len(gs) == 1:
        g = gs[0]; b = GENRE_BANDS[g]
        peak = max(keys, key=lambda k: b[k][0])
        safe = [k for k in keys if b[k][0] >= 2.0]
        upto = BAND_DISP[safe[-1]] if safe else BAND_DISP[peak]
        return {"text": f"**{g}** peaks at **{b[peak][0]}×** in the {BAND_DISP[peak]} band, and stays profitable "
                        f"(≥2× median ROI) up to the **{upto}** band.",
                "df": _bands_df([g]), "chart": "line", "x": "Budget band", "y": "Median ROI", "series": "Genre"}

    if any(w in ql for w in ["low budget", "lowest budget", "cheap", "value", "small budget",
                             "least budget", "high roi at low", "low-budget", "lean"]):
        ranked = sorted(GENRE_BANDS, key=lambda g: GENRE_BANDS[g]["1-10M"][0], reverse=True)
        top = ranked[0]; b = GENRE_BANDS[top]
        safe = [k for k in keys if b[k][0] >= 2.0]
        upto = BAND_DISP[safe[-1]] if safe else BAND_DISP["1-10M"]
        names = ", ".join(f"{g} ({GENRE_BANDS[g]['1-10M'][0]}×)" for g in ranked[:3])
        df = pd.DataFrame([{"Genre": g, "ROI @ $1-10M": GENRE_BANDS[g]["1-10M"][0]} for g in ranked])
        return {"text": f"Best returns at low budget ($1–10M): **{names}**. **{top}** stays strong up to the "
                        f"**{upto}** band — that's how far you can scale before ROI thins out.",
                "df": df, "chart": "bar", "x": "Genre", "y": "ROI @ $1-10M", "series": None}

    if any(w in ql for w in ["top genre", "best genre", "highest roi", "most profitable", "top roi",
                             "which genre", "most demanding", "rank", "biggest roi"]):
        peak = {g: max(keys, key=lambda k: GENRE_BANDS[g][k][0]) for g in GENRE_BANDS}
        ranked = sorted(GENRE_BANDS, key=lambda g: GENRE_BANDS[g][peak[g]][0], reverse=True)
        names = ", ".join(f"{g} ({GENRE_BANDS[g][peak[g]][0]}× in {BAND_DISP[peak[g]]})" for g in ranked[:3])
        df = pd.DataFrame([{"Genre": g, "Peak ROI": GENRE_BANDS[g][peak[g]][0]} for g in ranked])
        return {"text": f"Top genres by peak median ROI: **{names}**.",
                "df": df, "chart": "bar", "x": "Genre", "y": "Peak ROI", "series": None}

    if any(w in ql for w in ["avoid", "worst", "valley", "risky", "lose", "mid budget", "mid-budget", "danger"]):
        valley = {g: min(keys, key=lambda k: GENRE_BANDS[g][k][0]) for g in GENRE_BANDS}
        df = pd.DataFrame([{"Genre": g, "Worst-band ROI": GENRE_BANDS[g][valley[g]][0]}
                           for g in sorted(GENRE_BANDS, key=lambda g: GENRE_BANDS[g][valley[g]][0])])
        worst = df.iloc[0]
        return {"text": f"The **mid-budget valley ($10–100M)** is where ROI sags. Riskiest: "
                        f"**{worst['Genre']}** bottoms at **{worst['Worst-band ROI']}×**. "
                        f"Go lean indie or full tentpole — avoid the middle.",
                "df": df, "chart": "bar", "x": "Genre", "y": "Worst-band ROI", "series": None}

    return {"text": "I answer **budget & genre ROI** questions from the data. Try: "
                    "*“which genre gives high ROI at low budget?”*, *“top genres by ROI”*, "
                    "*“compare Horror and Sci-Fi”*, *“which budgets to avoid?”*  "
                    "(Actor & year questions need live mode.)"}


def _render_insight(ans):
    if ans.get("error"):
        st.warning(ans["error"]); return
    if ans.get("text"):
        st.markdown(f'<div class="insight insight-solid">🤖 {ans["text"]}</div>', unsafe_allow_html=True)
    if ans.get("title"):
        st.markdown(f"**{ans['title']}**")
    df = ans.get("df")
    if df is None and ans.get("rows") is not None:
        df = pd.DataFrame(ans["rows"])
    if df is not None and len(df):
        chart, x, y, series = ans.get("chart"), ans.get("x"), ans.get("y"), ans.get("series")
        try:
            if chart == "line" and x in df.columns and y in df.columns:
                xsort = [BAND_DISP[k] for k, _ in BAND_DEFS] if "band" in x.lower() else "ascending"
                enc = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X(f"{x}:N", sort=xsort, title=x), y=alt.Y(f"{y}:Q", title=y),
                    **({"color": f"{series}:N"} if series else {}))
                st.altair_chart(enc, use_container_width=True)
            elif chart == "bar" and x in df.columns and y in df.columns:
                enc = alt.Chart(df).mark_bar().encode(
                    x=alt.X(f"{x}:N", sort="-y", title=x), y=alt.Y(f"{y}:Q", title=y),
                    color=alt.Color(f"{x}:N", legend=None))
                st.altair_chart(enc, use_container_width=True)
        except Exception:
            pass
        st.dataframe(df, use_container_width=True, hide_index=True)
    if ans.get("sql"):
        with st.expander("Query the assistant ran"):
            st.code(ans["sql"], language="sql")


def page_home():
    st.markdown('<div class="hero-kicker">★ Data-Driven Cinema ★</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Greenlight Cinema</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Where box-office data meets a writers\' room of AI agents. '
        'Type an idea — our Writer, Critic, and Refiner argue it into an award-worthy synopsis, '
        'then cast it with talent the data says audiences reward.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, (icon, title, body) in zip(
        (c1, c2, c3),
        [("🎞️", "Real Data", "5,381 ROI-positive films distilled into hard constraints — genre, season, talent."),
         ("🤖", "Agents Argue", "A Writer drafts, a tested Critic scores, a Refiner fixes — looping to a winner."),
         ("🏆", "Cast to Win", "Suggested top cast & directors the data ties to higher returns.")],
    ):
        with col:
            st.markdown(f'<div class="section-title">{icon} {title}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="meta-chip">{body}</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="section-title">🎬 Top Directors</div>', unsafe_allow_html=True)
    cast_grid([
        {"name": "Denis Villeneuve", "role": "Director"},
        {"name": "Greta Gerwig", "role": "Director"},
        {"name": "Guillermo del Toro", "role": "Director"},
        {"name": "Kathryn Bigelow", "role": "Director"},
        {"name": "Jordan Peele", "role": "Director"},
        {"name": "Barry Jenkins", "role": "Director"},
    ])
    st.write("")
    st.markdown('<div class="section-title">🌟 Top Actors</div>', unsafe_allow_html=True)
    cast_grid([
        {"name": "Florence Pugh", "role": "Actor"},
        {"name": "Mahershala Ali", "role": "Actor"},
        {"name": "Zendaya", "role": "Actor"},
        {"name": "Oscar Isaac", "role": "Actor"},
        {"name": "Michelle Yeoh", "role": "Actor"},
        {"name": "Charlize Theron", "role": "Actor"},
        {"name": "Anya Taylor-Joy", "role": "Actor"},
        {"name": "Viola Davis", "role": "Actor"},
    ])
    st.write("")
    if st.button("🎬  Start a Project", key="home_cta"):
        st.session_state.page = "Create Project"
        st.rerun()


def page_create():
    st.markdown('<div class="hero-kicker">★ Writers\' Room ★</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title" style="font-size:3rem;">Create a Project</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Describe the film you want. Mention the genre, target length, '
        'and timing — e.g. <i>"a 250-word Thriller for the best release window"</i>.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    with st.expander("⚙️  Backend settings  ·  " + ("🟢 LIVE" if _live else "🟡 DEMO")):
        st.session_state.backend_url = st.text_input(
            "Colab backend URL (from the cloudflared cell)",
            value=st.session_state.get("backend_url", ""),
            placeholder="https://xxxx.trycloudflare.com",
        )
        st.session_state.use_live = st.checkbox(
            "Use live backend  (uncheck = demo / no GPU)",
            value=st.session_state.get("use_live", False),
        )
        if st.button("🔌 Test connection", type="secondary"):
            u = st.session_state.backend_url.strip()
            if not u:
                st.warning("Enter the backend URL first.")
            else:
                try:
                    h = requests.get(f"{u}/health", timeout=10)
                    if h.ok and h.json().get("status") == "ok":
                        st.success("Connected ✓  backend is healthy.")
                    else:
                        st.error(f"Reached the server but got an unexpected response ({h.status_code}).")
                except Exception as e:
                    st.error(f"Could not reach backend: {e}")
        st.caption("Demo mode returns a sample script instantly. Live mode calls your Colab GPU.")

    with st.form("create"):
        prompt = st.text_area(
            "Your pitch",
            placeholder="Generate a 250-word synopsis for a Thriller for the best release window…",
            height=130,
        )
        submitted = st.form_submit_button("🎬  Action!  Send to the writers' room")

    if submitted and prompt.strip():
        import concurrent.futures
        url = st.session_state.get("backend_url", "").strip()     # read in main thread (not thread-safe inside)
        live = st.session_state.get("use_live", False)
        st.markdown('<div class="section-title">🗣️ Writers\' room debate</div>', unsafe_allow_html=True)
        ph = st.empty()
        seq = ["Writer", "Critic", "Refiner"]
        err = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_generate, prompt, url, live)         # backend runs in the background...
            i = 0
            while not fut.done():                                 # ...while the live agent's station glows
                stage = seq[i % 3]                                # demo / fallback: cycle
                if live and url:
                    try:                                          # poll the real current agent
                        stage = requests.get(f"{url}/progress", timeout=3).json().get("stage", stage)
                    except Exception:
                        pass
                if stage not in seq:                              # "done" or unknown -> show Refiner
                    stage = "Refiner"
                ph.markdown(_stations_html(active=stage), unsafe_allow_html=True)
                time.sleep(0.6); i += 1
            try:
                result = fut.result()
            except Exception as e:
                err, result = e, mock_result(prompt)
        ph.markdown(_stations_html(done_all=True), unsafe_allow_html=True)
        if err:
            st.error(f"Backend error: {err}\n\nCheck the URL and that the Colab cells are running. Showing a demo result instead.")
        st.session_state.result = result
        st.session_state.chat = []
        st.session_state.animate = False             # already animated live during generation
        st.session_state.history.append({            # log into the left-side history panel
            "prompt": prompt.strip(),
            "genre": result.get("genre", "?"),
            "score": result.get("score"),
            "result": json.loads(json.dumps(result)),
            "chat": [],
        })
        st.session_state.active_idx = len(st.session_state.history) - 1
        st.rerun()                                   # re-render cleanly with the finished result
    elif submitted:
        st.warning("Give the writers something to work with — type a pitch first.")

    result = st.session_state.get("result")
    if not result:
        return

    if st.session_state.pop("scroll_top", False):            # jump up so the replay is visible
        components.html("<script>window.parent.scrollTo({top:0,behavior:'smooth'});</script>", height=0)

    # ---- the agents' debate ----
    st.markdown('<div class="section-title">🗣️ Writers\' room debate</div>', unsafe_allow_html=True)
    if st.session_state.pop("animate", False):
        _agent_choreography(min(int(result.get("iterations", 3)), 3))     # glow travels Writer→Critic→Refiner
    else:
        st.markdown(_stations_html(done_all=True), unsafe_allow_html=True)
    for rnd in result["rounds"]:
        css = {"Writer": "b-writer", "Critic": "b-critic", "Refiner": "b-refiner"}.get(rnd["agent"], "b-writer")
        fails = "".join(f'<span class="fail-tag">✗ {f}</span>' for f in rnd["failed"]) or \
                '<span class="fail-tag" style="background:rgba(120,200,120,.18);color:#bdf0bd;border-color:rgba(120,200,120,.4)">✓ all checks pass</span>'
        st.markdown(
            f'<div class="bubble {css}">'
            f'<span class="agent-tag">{rnd["agent"]} · round {rnd["n"]}</span>'
            f'<span class="score-pill">score {rnd["score"]:.2f}</span>'
            f'<div class="bubble-text">{rnd["excerpt"]}</div>'
            f'<div>{fails}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    # ---- final script ----
    st.markdown('<div class="section-title">🏆 Final Synopsis</div>', unsafe_allow_html=True)
    budget_chip = (f'<span class="meta-chip">Budget: <b>{_fmt_money(result["budget"])}</b></span>'
                   if result.get("budget") else "")
    genres_disp = " + ".join(result.get("genres") or [result["genre"]])
    insp = result.get("inspirations") or []
    insp_chip = (f'<span class="meta-chip">Inspired by: <b>{", ".join(insp)}</b></span>' if insp else "")
    st.markdown(
        f'<div class="meta-row">'
        f'<span class="meta-chip">Genre: <b>{genres_disp}</b></span>'
        f'<span class="meta-chip">Best window: <b>{result["window"]}</b></span>'
        f'<span class="meta-chip">Length: <b>~{result["length"]} words</b></span>'
        f'{budget_chip}{insp_chip}'
        f'<span class="meta-chip">Critic score: <b>{result["score"]:.2f}</b></span>'
        f'<span class="meta-chip">Iterations: <b>{result["iterations"]}</b></span>'
        "</div>",
        unsafe_allow_html=True,
    )
    ins = result.get("budget_insight")
    if ins:
        cls = {"strong": "insight-strong", "solid": "insight-solid", "weak": "insight-weak"}.get(ins["verdict"], "insight-solid")
        icon = {"strong": "✅", "solid": "👍", "weak": "⚠️"}.get(ins["verdict"], "•")
        st.markdown(f'<div class="insight {cls}">{icon} {ins["message"]}</div>', unsafe_allow_html=True)

    # ---- budget breakdown (industry-norm allocation; only when a budget was given) ----
    if result.get("budget"):
        bb, sal, roi_weighted = None, None, False
        gl = result.get("genres") or [result["genre"]]       # use the full genre list for VFX classification
        if _live:                                            # live: real ROI-weighted cast split
            try:
                d = breakdown_backend(result["budget"], gl, result.get("cast", []))
                bb, sal, roi_weighted = d.get("breakdown"), d.get("cast_salaries"), True
            except Exception:
                bb = None
        if not bb:                                           # demo / fallback: billing-order split
            bb = budget_breakdown(result["budget"], gl)
            cast_amt = next((l["amount"] for l in bb if l["item"].startswith("Cast")), 0)
            sal = cast_salary_split(cast_amt, result.get("cast", []))
        with st.expander(f"💰 Budget breakdown — {_fmt_money(result['budget'])} (estimated)", expanded=True):
            st.caption(f"Standard {result['genre']} production allocation — real industry percentages, "
                       "not contracted figures."
                       + (" Cast split weighted by each actor's historical ROI." if roi_weighted
                          else " Cast split by billing order."))
            rows = "".join(
                f'<tr><td style="padding:5px 18px;color:#f0e0b0;">{l["item"]}</td>'
                f'<td style="padding:5px 18px;color:#bdb38f;text-align:right;">{l["pct"]}%</td>'
                f'<td style="padding:5px 18px;color:var(--gold-bright);text-align:right;font-weight:700;">'
                f'{_fmt_money(l["amount"])}</td></tr>' for l in bb)
            st.markdown(f'<table style="border-collapse:collapse;width:100%;max-width:560px;">{rows}</table>',
                        unsafe_allow_html=True)
            if sal:
                chips = " &nbsp;·&nbsp; ".join(
                    f'{s["name"]} <b style="color:var(--gold-bright)">{_fmt_money(s["amount"])}</b>'
                    + (f' <span style="opacity:.55">({s["roi"]}× ROI)</span>' if s.get("roi") else "")
                    for s in sal)
                st.markdown(f'<div class="meta-chip" style="margin-top:12px;">🎭 Est. cast allocation: '
                            f'{chips}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="script-panel">{result["synopsis"]}</div>', unsafe_allow_html=True)

    # ---- suggested cast + directors (glassmorphism) ----
    st.write("")
    st.markdown('<div class="section-title">🎭 Suggested Cast</div>', unsafe_allow_html=True)
    cast_grid(result["cast"])
    st.write("")
    st.markdown('<div class="section-title">🎬 Suggested Directors</div>', unsafe_allow_html=True)
    cast_grid(result["directors"])

    # ---- continue the conversation ----
    st.write("")
    st.markdown('<div class="section-title">💬 Continue the conversation</div>', unsafe_allow_html=True)
    st.caption('Not happy with a choice? Ask for changes — e.g. "replace Dev Patel and Cynthia Erivo with someone else."')
    for m in st.session_state.get("chat", []):
        with st.chat_message(m["role"], avatar="🎬" if m["role"] == "assistant" else "🧑"):
            st.markdown(m["content"])
    user_msg = st.chat_input("Ask the writers' room to change something…")
    if user_msg:
        st.session_state.setdefault("chat", []).append({"role": "user", "content": user_msg})
        prev_syn = (st.session_state.result or {}).get("synopsis")
        animate = False
        if _live:                                    # live: backend handles recast + free-form edits
            with st.spinner("The writers' room is revising…"):
                try:
                    reply, updated = chat_backend(user_msg, st.session_state.result)
                except Exception as e:
                    reply, updated = f"Backend error: {e}", None
            if updated and updated.get("synopsis") != prev_syn:
                animate = True                       # synopsis was rewritten → replay the room
        else:                                        # demo: recast + toggled synopsis revision
            reply, updated, animate = chat_respond(st.session_state.result, user_msg)
        if updated:
            st.session_state.result = updated
        if animate:
            st.session_state.animate = True
            st.session_state.scroll_top = True
        st.session_state.chat.append({"role": "assistant", "content": reply})
        ai = st.session_state.get("active_idx")          # keep this project's history entry current
        if ai is not None and 0 <= ai < len(st.session_state.history):
            st.session_state.history[ai]["result"] = json.loads(json.dumps(st.session_state.result))
            st.session_state.history[ai]["chat"] = list(st.session_state.chat)
            st.session_state.history[ai]["score"] = st.session_state.result.get("score")
        st.rerun()


def page_insights():
    band_keys = [k for k, _ in BAND_DEFS]
    band_x = [BAND_DISP[k] for k in band_keys]

    st.markdown('<div class="hero-kicker">★ The Data Behind the Magic ★</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title" style="font-size:3rem;">Data Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Every release window, budget verdict, and cast suggestion in the '
        'generator traces back to this analysis of <b>6,444 ROI-positive films</b>.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    # ---- per-genre band breakdown ----
    st.markdown('<div class="section-title">🎬 Budget breakdown by genre</div>', unsafe_allow_html=True)
    g = st.selectbox("Pick a genre", list(GENRE_BANDS.keys()),
                     index=list(GENRE_BANDS.keys()).index("Horror"))
    rows = ""
    for k, x in zip(band_keys, band_x):
        roi, n = GENRE_BANDS[g][k]
        cls = "insight-strong" if roi >= 2.5 else ("insight-solid" if roi >= 2.0 else "insight-weak")
        rows += (f'<div class="insight {cls}" style="margin:6px 0;">{x} &nbsp;→&nbsp; median ROI '
                 f'<b>{roi}×</b> <span style="opacity:.6">(n={n})</span></div>')
    st.markdown(rows, unsafe_allow_html=True)
    st.caption("Source: median revenue/budget over films with budget ≥ $100K, joined to genre. "
               "The generator's budget verdict reads these same numbers live.")

    # ---- AI assistant ----
    st.write("")
    st.markdown('<div class="section-title">🤖 Ask the Data</div>', unsafe_allow_html=True)
    st.caption("Budget, genre & ROI questions are answered straight from the data. "
               "Actor & year questions unlock in live mode.")
    chips = ["Which genre gives high ROI at low budget?", "Top genres by ROI",
             "Compare Horror and Science Fiction", "Which budgets to avoid?"]
    cols = st.columns(len(chips))
    picked = None
    for i, ch in enumerate(chips):
        if cols[i].button(ch, key=f"ask_chip_{i}", use_container_width=True):
            picked = ch
    typed = st.text_input("Ask the data…", key="ask_box",
                          placeholder="e.g. which genre gives high ROI at low budget?")
    q = picked or (typed.strip() if typed else "")
    if q:
        ans = insight_answer(q)
        if ans.get("needs_live") and st.session_state.get("use_live") and st.session_state.get("backend_url", "").strip():
            with st.spinner("Querying the live database…"):
                try:
                    ans = ask_backend(q)
                except Exception as e:
                    ans = {"error": f"Live query failed: {e}"}
        _render_insight(ans)


# ----------------------------------------------------------------------------
# LEFT-SIDE SESSION HISTORY  (collapsible native sidebar)
# ----------------------------------------------------------------------------
def render_history_sidebar():
    with st.sidebar:
        st.markdown('<div class="topbar-logo" style="font-size:1.2rem;margin-top:0;">📜 Session History</div>'
                    '<div class="topbar-tag">Every project you generate this session</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)
        hist = st.session_state.get("history", [])
        if not hist:
            st.caption("No projects yet — generate one in **Create Project** and it'll appear here. "
                       "Click any entry to reopen it with its chat.")
            return
        for i in reversed(range(len(hist))):
            h = hist[i]
            active = (i == st.session_state.get("active_idx"))
            sc = h.get("score")
            sc_txt = f" · {sc:.2f}" if isinstance(sc, (int, float)) else ""
            chat_n = len(h.get("chat", []))
            chat_txt = f" · 💬{chat_n}" if chat_n else ""
            label = f"{'▸ ' if active else ''}🎬 {h.get('genre','?')}{sc_txt}{chat_txt}\n{h.get('prompt','')[:52]}"
            if active:
                st.markdown('<div class="hist-active">', unsafe_allow_html=True)
            if st.button(label, key=f"hist_{i}", use_container_width=True):
                st.session_state.result = json.loads(json.dumps(h["result"]))
                st.session_state.chat = list(h.get("chat", []))
                st.session_state.active_idx = i
                st.session_state.page = "Create Project"
                st.session_state.animate = False        # reopen instantly (no replay)
                st.rerun()
            if active:
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)
        if st.button("🗑️  Clear history", key="hist_clear", use_container_width=True):
            st.session_state.history = []
            st.session_state.active_idx = None
            st.rerun()


if "page" not in st.session_state:
    st.session_state.page = "Home"

# ----------------------------------------------------------------------------
# NAV
# ----------------------------------------------------------------------------

# ---- top navigation bar ----
logo_col, nav_home, nav_create, nav_insights = st.columns([3, 1.0, 1.7, 1.6])
with logo_col:
    st.markdown('<div class="topbar-logo">🎬 Greenlight</div>'
                '<div class="topbar-tag">Oscar-grade synopses, on demand.</div>',
                unsafe_allow_html=True)
with nav_home:
    if st.button("Home", use_container_width=True,
                 type="primary" if st.session_state.page == "Home" else "secondary"):
        st.session_state.page = "Home"
        st.rerun()
with nav_create:
    if st.button("Create Project", use_container_width=True,
                 type="primary" if st.session_state.page == "Create Project" else "secondary"):
        st.session_state.page = "Create Project"
        st.rerun()
with nav_insights:
    if st.button("Data Insights", use_container_width=True,
                 type="primary" if st.session_state.page == "Insights" else "secondary"):
        st.session_state.page = "Insights"
        st.rerun()
st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)

if st.session_state.page == "Home":
    page_home()
elif st.session_state.page == "Create Project":
    page_create()
else:
    page_insights()

# render the left-side history AFTER the page runs, so a freshly generated project
# (appended inside page_create) shows up in the same rerun
if st.session_state.page == "Create Project":
    render_history_sidebar()                       # history lives only in the Create Project workspace
else:                                              # hide the sidebar entirely on Home / Insights
    st.markdown('<style>section[data-testid="stSidebar"],'
                'div[data-testid="collapsedControl"]{display:none;}</style>',
                unsafe_allow_html=True)
