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

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
DEMO_MODE = True                 # flip to False once the Colab backend is live
BACKEND_URL = ""                 # e.g. "https://xxxx.trycloudflare.com"
REQUEST_TIMEOUT = 180

st.set_page_config(page_title="Greenlight Cinema", page_icon="🎬",
                   layout="wide", initial_sidebar_state="collapsed")

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
section[data-testid="stSidebar"] { display: none; }
div[data-testid="collapsedControl"] { display: none; }
.block-container { padding-top: 2.2rem; }

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


def face(name: str) -> str:
    """Real TMDB profile photo if ingested (ui/faces.json), else a stable placeholder."""
    if _FACES.get(name):
        return _FACES[name]
    return f"https://i.pravatar.cc/220?u={urllib.parse.quote(name)}"


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


def chat_respond(result, message):
    """Deterministic recasting (works in demo, no GPU). Returns (reply, updated_result | None)."""
    msg = message.lower()
    rm_cast = _name_targets(result["cast"], msg)
    rm_dirs = _name_targets(result["directors"], msg)
    if (rm_cast or rm_dirs) and any(w in msg for w in _SWAP_WORDS):
        new = json.loads(json.dumps(result))
        retired = set(new.get("_retired", []))                       # never bring these back
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
            return ("Done — recast " + "; ".join(swapped) + ". Updated lineup below. 🎬"), new
        return ("I've cycled through the fresh demo faces for this genre — "
                "connect the live backend for the full talent pool."), None
    return ("I can recast the lineup — try *\"replace Dev Patel with someone else\"*. "
            "Rewriting the synopsis or changing tone needs the live backend (GPU)."), None


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


def call_backend(prompt: str):
    url = st.session_state.get("backend_url", "").strip()
    live = st.session_state.get("use_live", False)
    if live and url:
        r = requests.post(f"{url}/generate", json={"prompt": prompt}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    time.sleep(0.4)
    return mock_result(prompt)


def chat_backend(message: str, result: dict):
    """Live-mode chat → Colab /chat (LLM synopsis edits + budget-aware recast). Returns (reply, updated)."""
    url = st.session_state.get("backend_url", "").strip()
    r = requests.post(f"{url}/chat", json={"message": message, "state": result}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    return d.get("reply", ""), d.get("result")


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
    """Move a gold glow Writer→Critic→Refiner→Critic per iteration, then settle green."""
    seq = ["Writer", "Critic"]
    for _ in range(max(0, int(iterations) - 1)):
        seq += ["Refiner", "Critic"]
    ph = st.empty()
    for active in seq:
        ph.markdown(_stations_html(active=active), unsafe_allow_html=True)
        time.sleep(0.8)
    ph.markdown(_stations_html(done_all=True), unsafe_allow_html=True)


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
    st.markdown('<div class="section-title">🌟 Talent the data loves</div>', unsafe_allow_html=True)
    cast_grid([
        {"name": "Denis Villeneuve", "role": "Director"},
        {"name": "Greta Gerwig", "role": "Director"},
        {"name": "Florence Pugh", "role": "Actor"},
        {"name": "Mahershala Ali", "role": "Actor"},
        {"name": "Zendaya", "role": "Actor"},
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
        with st.spinner("Writer drafting · Critic scoring · Refiner polishing…"):
            try:
                result = call_backend(prompt)
            except Exception as e:
                st.error(f"Backend error: {e}\n\nCheck the URL and that the Colab cells are running. Showing a demo result instead.")
                result = mock_result(prompt)
        st.session_state.result = result
        st.session_state.chat = []
        st.session_state.animate = True
    elif submitted:
        st.warning("Give the writers something to work with — type a pitch first.")

    result = st.session_state.get("result")
    if not result:
        return

    # ---- the agents' debate ----
    st.markdown('<div class="section-title">🗣️ Writers\' room debate</div>', unsafe_allow_html=True)
    if st.session_state.pop("animate", False):
        _agent_choreography(result.get("iterations", 3))     # glow travels Writer→Critic→Refiner
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
    st.markdown(
        f'<div class="meta-row">'
        f'<span class="meta-chip">Genre: <b>{result["genre"]}</b></span>'
        f'<span class="meta-chip">Best window: <b>{result["window"]}</b></span>'
        f'<span class="meta-chip">Length: <b>~{result["length"]} words</b></span>'
        f'{budget_chip}'
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
        if _live:                                    # live: backend handles recast + free-form edits
            with st.spinner("The writers' room is revising…"):
                try:
                    reply, updated = chat_backend(user_msg, st.session_state.result)
                except Exception as e:
                    reply, updated = f"Backend error: {e}", None
        else:                                        # demo: deterministic recast only
            reply, updated = chat_respond(st.session_state.result, user_msg)
        if updated:
            st.session_state.result = updated
        st.session_state.chat.append({"role": "assistant", "content": reply})
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

    # ---- the valley chart ----
    st.markdown('<div class="section-title">📉 The Mid-Budget Valley</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="meta-chip">Median ROI by budget band. Notice the dip in the middle — '
        'big enough to be expensive, not big enough to be an event. ROI recovers only at tentpole scale.</div>',
        unsafe_allow_html=True,
    )
    genres = st.multiselect("Genres to compare", list(GENRE_BANDS.keys()),
                            default=["Science Fiction", "Thriller", "Drama", "Action"])
    if genres:
        long = [{"Budget band": band_x[i], "Median ROI": GENRE_BANDS[g][k][0], "Genre": g}
                for g in genres for i, k in enumerate(band_keys)]
        chart = (alt.Chart(pd.DataFrame(long))
                 .mark_line(point=True, strokeWidth=3)
                 .encode(
                     x=alt.X("Budget band:N", sort=band_x, title="Budget band"),
                     y=alt.Y("Median ROI:Q", title="Median ROI (×)"),
                     color=alt.Color("Genre:N", legend=alt.Legend(title="Genre")),
                     tooltip=["Genre", "Budget band", "Median ROI"])
                 .properties(height=360))
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Pick at least one genre to see its ROI curve.")

    # ---- per-genre band breakdown ----
    st.write("")
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

    # ---- peak vs valley summary ----
    st.write("")
    st.markdown('<div class="section-title">🏆 Peak vs. valley, every genre</div>', unsafe_allow_html=True)
    disp = dict(zip(band_keys, band_x))
    cells = ""
    for gn in GENRE_BANDS:
        b = GENRE_BANDS[gn]
        peak = max(band_keys, key=lambda k: b[k][0])
        valley = min(band_keys, key=lambda k: b[k][0])
        cells += (f'<tr>'
                  f'<td style="padding:6px 16px;color:#f0e0b0;">{gn}</td>'
                  f'<td style="padding:6px 16px;color:#9fe09f;">{disp[peak]} ({b[peak][0]}×)</td>'
                  f'<td style="padding:6px 16px;color:#f0a0a0;">{disp[valley]} ({b[valley][0]}×)</td>'
                  f'</tr>')
    st.markdown(
        '<table style="border-collapse:collapse;">'
        '<tr><th style="text-align:left;padding:6px 16px;color:#D4AF37;">Genre</th>'
        '<th style="text-align:left;padding:6px 16px;color:#D4AF37;">Best band</th>'
        '<th style="text-align:left;padding:6px 16px;color:#D4AF37;">Worst band</th></tr>'
        f'{cells}</table>',
        unsafe_allow_html=True,
    )
    st.caption("Source: median revenue/budget over films with budget ≥ $100K, joined to genre. "
               "The generator's budget verdict reads these same numbers live.")


# ----------------------------------------------------------------------------
# NAV
# ----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"

# ---- top navigation bar ----
logo_col, nav_home, nav_create, nav_insights = st.columns([5, 1.0, 1.5, 1.2])
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
