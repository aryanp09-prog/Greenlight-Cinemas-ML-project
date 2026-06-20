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
import urllib.parse
import requests
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

/* ---------- final script panel (NOT glass, per spec) ---------- */
.script-panel {
  background: #0f0d07; border: 1px solid rgba(212,175,55,0.45); border-left: 4px solid var(--gold);
  border-radius: 14px; padding: 22px 26px; margin-top: 10px; color: #f4efdd; line-height: 1.7; font-size: 1.06rem;
}
.meta-row { display:flex; gap:26px; flex-wrap:wrap; margin: 4px 0 14px; }
.meta-chip { color:#d9d2bb; font-size:0.92rem; }
.meta-chip b { color: var(--gold-bright); }
.badge-demo { position: fixed; top: 10px; right: 16px; z-index: 999;
  background: rgba(212,175,55,0.15); border:1px solid var(--gold); color: var(--gold-bright);
  padding: 3px 12px; border-radius: 999px; font-size: 0.72rem; letter-spacing:1px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
if DEMO_MODE:
    st.markdown('<div class="badge-demo">DEMO MODE</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def face(name: str) -> str:
    """Placeholder real-face photo (stable per name). Swap to TMDB profile URL later."""
    seed = urllib.parse.quote(name)
    return f"https://i.pravatar.cc/220?u={seed}"


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
    return genre, window, length


def mock_result(prompt: str):
    """Returns the exact response contract the FastAPI backend will produce."""
    genre, window, length = _light_parse(prompt)
    window = window or {"Horror": "January", "Thriller": "December",
                        "Action": "May", "Comedy": "July"}.get(genre, "July")
    final = (
        f"In a city that never forgives, a disgraced detective is pulled back for one last case "
        f"when a string of impossible disappearances points to someone inside her own department. "
        f"As {genre.lower()} tension tightens, every ally becomes a suspect and every clue a trap. "
        f"She has until the first snow to expose the truth — before she becomes the next name on the list. "
        f"A taut, twist-laden descent where trust is the deadliest currency."
    )
    rounds = [
        {"n": 1, "agent": "Writer",
         "score": 0.55, "failed": ["genre_signal", "length_ok"],
         "excerpt": "A detective investigates some disappearances in a quiet town and slowly finds out the truth."},
        {"n": 2, "agent": "Refiner",
         "score": 0.75, "failed": ["length_ok"],
         "excerpt": "A disgraced detective returns for a final case as impossible disappearances point inside her department..."},
        {"n": 3, "agent": "Refiner",
         "score": 0.9, "failed": [],
         "excerpt": final},
    ]
    return {
        "genre": genre, "window": window, "length": length,
        "synopsis": final, "score": 0.9, "iterations": 3, "valid": True,
        "rounds": rounds,
        "cast": [
            {"name": "Frances McDormand", "role": "Lead Detective"},
            {"name": "Mahershala Ali", "role": "Internal Affairs"},
            {"name": "Florence Pugh", "role": "The Rookie"},
            {"name": "Oscar Isaac", "role": "The Suspect"},
        ],
        "directors": [
            {"name": "Denis Villeneuve", "role": "Director"},
            {"name": "Kathryn Bigelow", "role": "Director"},
        ],
    }


def call_backend(prompt: str):
    if DEMO_MODE or not BACKEND_URL:
        time.sleep(0.4)
        return mock_result(prompt)
    r = requests.post(f"{BACKEND_URL}/generate", json={"prompt": prompt}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------------------------
# PAGES
# ----------------------------------------------------------------------------
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

    with st.form("create"):
        prompt = st.text_area(
            "Your pitch",
            placeholder="Generate a 250-word synopsis for a Thriller for the best release window…",
            height=130,
        )
        submitted = st.form_submit_button("🎬  Action!  Send to the writers' room")

    if not submitted:
        return
    if not prompt.strip():
        st.warning("Give the writers something to work with — type a pitch first.")
        return

    # ---- the agents "argue" ----
    st.markdown('<div class="section-title">🗣️ The writers\' room is in session…</div>', unsafe_allow_html=True)
    with st.spinner("Writer drafting · Critic scoring · Refiner polishing…"):
        result = call_backend(prompt)

    debate = st.container()
    for rnd in result["rounds"]:
        css = {"Writer": "b-writer", "Critic": "b-critic", "Refiner": "b-refiner"}.get(rnd["agent"], "b-writer")
        fails = "".join(f'<span class="fail-tag">✗ {f}</span>' for f in rnd["failed"]) or \
                '<span class="fail-tag" style="background:rgba(120,200,120,.18);color:#bdf0bd;border-color:rgba(120,200,120,.4)">✓ all checks pass</span>'
        debate.markdown(
            f'<div class="bubble {css}">'
            f'<span class="agent-tag">{rnd["agent"]} · round {rnd["n"]}</span>'
            f'<span class="score-pill">score {rnd["score"]:.2f}</span>'
            f'<div class="bubble-text">{rnd["excerpt"]}</div>'
            f'<div>{fails}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.7)

    # ---- final script ----
    st.markdown('<div class="section-title">🏆 Final Synopsis</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="meta-row">'
        f'<span class="meta-chip">Genre: <b>{result["genre"]}</b></span>'
        f'<span class="meta-chip">Best window: <b>{result["window"]}</b></span>'
        f'<span class="meta-chip">Length: <b>~{result["length"]} words</b></span>'
        f'<span class="meta-chip">Critic score: <b>{result["score"]:.2f}</b></span>'
        f'<span class="meta-chip">Iterations: <b>{result["iterations"]}</b></span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="script-panel">{result["synopsis"]}</div>', unsafe_allow_html=True)

    # ---- suggested cast + directors (glassmorphism) ----
    st.write("")
    st.markdown('<div class="section-title">🎭 Suggested Cast</div>', unsafe_allow_html=True)
    cast_grid(result["cast"])
    st.write("")
    st.markdown('<div class="section-title">🎬 Suggested Directors</div>', unsafe_allow_html=True)
    cast_grid(result["directors"])


# ----------------------------------------------------------------------------
# NAV
# ----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"

# ---- top navigation bar ----
logo_col, nav_home, nav_create = st.columns([6, 1.1, 1.6])
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
st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)

if st.session_state.page == "Home":
    page_home()
else:
    page_create()
