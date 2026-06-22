# 🎬 Greenlight Cinema

**A data-driven film-synopsis generator.** Real box-office data is mined into hard constraints, which steer a multi-agent LLM loop (Writer → Critic → Refiner) to produce a synopsis that obeys the data — complete with a **data-backed release window, budget verdict, and a cast tailored to the budget.**

> Type *"Generate a 250-word Sci-Fi synopsis for the best release window under a $100M budget"* → get a unique synopsis, the optimal release month, an ROI verdict on that budget, and the actors/directors who historically returned money in big-budget sci-fi.

It's not "an AI that writes movie pitches." It's an **analytics engine that greenlights films**, using an LLM as the writing tool — every creative choice is anchored to what the data says actually returns money.

---

## ✨ What makes it different

Most LLM apps generate text. This one **grounds generation in evidence**:

- **Release timing** comes from per-genre seasonal ROI, not vibes.
- **Budget advice** comes from real median ROI by budget band — and surfaces a genuine finding (below).
- **Cast suggestions** are the actors/directors who actually returned ROI *in that genre at that budget tier*.
- **The Critic is a deterministic, unit-tested validator**, not an LLM grading itself — so scores are reproducible.

---

## 📊 The headline data finding: the mid-budget valley

Analyzing **6,444 films with trustworthy budgets** (median ROI by genre × budget band) revealed that ROI is **not** "cheaper = better." It's a U-shape:

| Genre | <$1M | $1–10M | $10–40M | $40–100M | $100M+ |
|---|---|---|---|---|---|
| Sci-Fi | 4.00× | 1.53× | 1.46× | 1.58× | **2.61×** |
| Thriller | 3.33× | 2.33× | **1.50×** | 1.75× | 2.66× |
| Drama | 2.71× | 1.85× | **1.31×** | 1.86× | 2.33× |
| Action | 8.33×* | 2.12× | 1.57× | 1.81× | 2.67× |

**Two viable strategies — lean indie or full tentpole — and a money-losing mid-budget valley ($10–100M) to avoid.** Micro-budget wins the *ratio* (small samples / survivorship), the mid-range sags toward break-even, and $100M+ recovers because studios only greenlight blockbusters they're confident in. The app turns this into a live verdict banner per prompt.

\* *Action <$1M is a small-sample outlier (n=45).*

And the **budget-aware cast** reflects the same logic — e.g. Horror by tier:
- **lean** → Vincent Price, Jamie Lee Curtis · **mid** → Tobin Bell (*Saw*), Neve Campbell (*Scream*) · **big** → (none — horror rarely goes tentpole, so it falls back)

---

## 🏗️ Architecture

```
                 COLAB (GPU)                              LAPTOP
 ┌─────────────────────────────────────────┐      ┌────────────────────┐
 │  DuckDB analytics on 419K films          │      │  Streamlit UI       │
 │     ↓                                     │      │  (Oscar theme,      │
 │  constraints.json   ← the data→AI bridge  │      │   glassmorphism)    │
 │     ↓                                     │      │                     │
 │  LangGraph loop:                          │      │  text prompt ──┐    │
 │   Writer → Critic(validator) → Refiner    │      │                │    │
 │   (qwen2.5:7b via Ollama)                 │      │   ┌────────────┘    │
 │     ↓                                     │      │   ▼                 │
 │  FastAPI  /generate ───────── cloudflared │◀────▶│  POST /generate     │
 └─────────────────────────────────────────┘ tunnel└────────────────────┘
```

**Why split this way:** the dev laptop (i5 3rd-gen, 4 GB RAM) can't host Ollama or the ~900 MB dataset, so all compute runs on Colab's free GPU; only the lightweight Streamlit UI runs locally and calls the Colab backend over a tunnel.

---

## 🔬 How it works

### 1. Data → `constraints.json` (the bridge)
DuckDB queries over the cleaned dataset produce a single JSON contract the AI side consumes:

| Key | What it holds |
|---|---|
| `top_genres` | genres ranked by ROI |
| `seasonal_fit` / `seasonal_by_genre` | best release months overall and per genre |
| `director_trends` / `actor_trends` | top talent by ROI |
| `budget_insights` | median ROI by budget band, per genre |
| `cast_by_genre_budget` | top cast/directors per genre × budget tier |
| `audience_signal` | MovieLens rating → ROI relationship |

### 2. The multi-agent loop (LangGraph)
- **Writer** — drafts a synopsis from the genre, resolved release window, length, and budget scale.
- **Critic** — a **deterministic, unit-tested validator** `validate_synopsis(...) → {score, passed, failed, suggestions}`. Five weighted checks (length, genre signal, no placeholders, completeness, window consistency); valid only if `score ≥ 0.7` **and** no critical check fails.
- **Refiner** — re-prompts the Writer with the exact failed checks.
- **Loop** exits on `score > 0.7`, 3 iterations, or no improvement — tracking the best draft throughout.

### 3. Natural-language prompts
`parse_prompt(text)` uses the LLM to extract `{genre, window, length, budget}`, then **deterministic guardrails** clamp the genre to a known list, map seasons→months, and trust numeric values found in the text (so *"250 words"* and *"$50M"* are never confused). The extraction is fuzzy; the safety net is exact and tested.

### 4. Output
A unique synopsis + score history (the "agent debate"), the data-best release window, a **budget ROI verdict**, and a **budget-tailored cast & directors** — rendered in the UI with real actor photos.

---

## 🧪 Tested

The judge and parser are pure functions with unit tests (run on CPU, no GPU):

- **Critic validator** — 9/9 tests (good/empty/too-short/genre-mismatch/wrong-window/user-override…)
- **Prompt parser** — 15/15 tests (genre fallback, season mapping, length & budget extraction, no false positives)

Deterministic by design: the same synopsis always yields the same score.

```bash
pip install -r requirements-dev.txt
pytest                       # 24 passed in ~0.1s
```

The tested logic lives in `src/greenlight/` (`validator.py`, `parser.py`) — mirrored
from the Colab cells so the suite exercises the exact code that runs live.

---

## 🛠️ Tech stack

**Data:** DuckDB · Pandas · Kaggle (`rounakbanik/the-movies-dataset` + `asaniczka/tmdb-movies-dataset-2023` + IMDB ratings) — ~419K films, **6,444** in the trustworthy-ROI subset (`budget ≥ $100K`).
**AI:** Ollama (`qwen2.5:7b`, 4-bit) · LangGraph (Writer/Critic/Refiner) · JSON-mode prompting.
**Serving:** FastAPI · cloudflared tunnel (Colab) · Streamlit (laptop).
**Faces:** Wikipedia/Wikimedia REST API (cached to `ui/faces.json`).

---

## 📁 Repo structure

```
ui/
  app.py            # Streamlit UI (Oscar theme, glassmorphism cards, demo + live modes)
  build_faces.py    # one-time Wikipedia face ingest → faces.json
  faces.json        # cached name → photo-URL map (committed)
  requirements.txt
src/
  greenlight/
    validator.py    # deterministic Critic (mirrors Colab) — unit-tested
    parser.py       # prompt guardrails (genre/window/length/budget) — unit-tested
  data/ingest.py    # early data-cleaning helper (movies CSV → typed frame)
tests/              # pytest suite: 9 validator + 15 parser checks (CPU, no GPU)
pyproject.toml      # pytest config (pythonpath=src)
roadmap.md          # the 10-phase project plan
```

> The DuckDB database, the raw datasets, and `kaggle.json` live on Colab/Drive (gitignored). The Colab notebook holds the live backend cells (data build → constraints → agents → FastAPI → tunnel).

---

## ▶️ Running it

### Demo mode (laptop only — no GPU, no Colab)
The UI ships with a **demo mode** that returns curated sample results instantly, so the whole experience is browsable offline.

```bash
pip install -r ui/requirements.txt
streamlit run ui/app.py
```
Open `http://localhost:8501`. Try: *"Generate a 250-word Horror synopsis for the best release window under a $50M budget."*

*(Optional)* refresh the cast photos: `python ui/build_faces.py`

### Live mode (real generation — needs the Colab backend)
1. In Colab: run the setup → agent → data → FastAPI → cloudflared cells (GPU runtime).
2. Copy the printed `https://….trycloudflare.com` URL.
3. In the UI → **Create Project → ⚙️ Backend settings** → paste the URL → tick **Use live backend**.
4. Submit a prompt → real, unique synopsis + budget-tailored cast from the live agent loop.

---

## 📌 Notes
- Colab tunnel URLs are ephemeral (regenerate each session) — paste the fresh one into the UI's settings box; no code change needed.
- Built as a data-analytics + agentic-LLM project (see `roadmap.md` for the full 10-phase plan).
