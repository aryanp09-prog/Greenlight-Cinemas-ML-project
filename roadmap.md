# 🎬 Greenlight Cinema — Project Roadmap

A data-driven film-synopsis generator: DuckDB analytics on real box-office data produces hard
constraints, which are injected into a multi-agent LLM loop (Writer → Critic → Refiner) that
generates a synopsis obeying them, iterating until critique score > 0.7 or 3 loops.

> **What kind of project is this?** A **data-analytics + agentic-LLM** system — *not* a
> supervised model-training project. The ML lifecycle maps cleanly onto steps 1–5 and 8–10,
> while steps 6–7 **transform**: instead of training a model, we *select* a pre-trained LLM and
> steer it with engineered constraints + an iterative critique loop. "Training" becomes
> "orchestration + prompt engineering + RAG (in-context learning)."

---

## Quick Status (glance)

| # | Phase | Status |
|---|---|---|
| 01 | Problem Definition | ✅ Done |
| 02 | Data Collection | ✅ Done |
| 03 | Data Cleaning & Preprocessing | 🟡 ~80% |
| 04 | Exploratory Data Analysis (EDA) | 🔜 Current |
| 05 | Feature Engineering & Selection | ⬜ |
| 06 | Model Selection | ⬜ |
| 07 | Model "Training" (agent orchestration) | ⬜ |
| 08 | Evaluation & Tuning | ⬜ |
| 09 | Deployment | ⬜ |
| 10 | Monitoring & Maintenance | ⬜ |

---

## Architecture (fixed)

- **Author code in VS Code → push to GitHub → Colab pulls (`git pull`) and runs it.**
- **Colab (free GPU) is the runtime** (laptop is i5 3rd-gen / 4GB RAM / 4GB disk — can't host Ollama or the ~900MB data).
- Backend (Ollama, DuckDB, ChromaDB, FastAPI + LangGraph) runs on Colab; only Streamlit UI runs on the laptop.
- Cleaned DuckDB + ChromaDB persist to Google Drive (Colab sessions are ephemeral — build once, reload).

## Data (locked in)

- **Source:** Kaggle `rounakbanik/the-movies-dataset` (45k movies, ~2017). Bundles movies + credits (cast/crew) + 26M MovieLens ratings + links, all aligned by TMDB `id`.
- **Key numbers:** 45,466 total movies; **5,381 with budget>0 AND revenue>0** (the ROI subset). Full set used for genre/seasonal counts.
- **Quirks:** genres/cast/crew are stringified Python dicts → `ast.literal_eval`. Ratings→revenue join: `ratings.movieId → links.movieId → links.tmdbId → movies.id = credits.id`.

## Repo

- github.com/aryanp09-prog/Greenlight-Cinemas-ML-project · commits as `aryanp09-prog <aryanp0901@gmail.com>`
- Datasets are gitignored (live on Colab/Drive). `src/data/ingest.py` done & working.

---

# Milestone Details

## Phase 01 — Problem Definition ✅
**Goal:** Define the problem precisely. Close the gap between *what we know about audience behavior* (data) and *what we ask the AI to create*.
**What we do:** Frame the system — analytics produces constraints; an agent loop generates a data-obeying synopsis.
**Output:** Problem statement + success criteria (synopsis must hit genre ROI, seasonal fit, talent; critique score > 0.7).

## Phase 02 — Data Collection ✅
**Goal:** Get real movie data into the runtime.
**What we do:** Pull `rounakbanik/the-movies-dataset` from Kaggle straight into Colab via the Kaggle API (`kaggle.json` stored on Drive).
**Tools:** Kaggle API, Colab, Google Drive.
**Output:** Raw CSVs in `/content/data` (movies_metadata, credits, ratings, links, keywords).

## Phase 03 — Data Cleaning & Preprocessing 🟡 (~80%)
**Goal:** Turn raw, messy CSVs into clean, queryable tables.
**What we do (done):** `src/data/ingest.py` — coerce budget/revenue/id to numeric, parse dates → year/month, parse stringified-dict genres → `genre_list`, build the ROI subset (`budget>0 & revenue>0` = 5,381 films).
**What's left:** `src/data/credits.py` — parse `credits.csv` cast/crew (also stringified dicts), extract **director** (crew where `job=='Director'`) + **top 3–5 cast**, join to movies on `id`. Then write everything to a **DuckDB file on Drive**.
**Tools:** Pandas, `ast`, DuckDB.
**Output:** Clean `movies`, `fin` (ROI subset), `credits` tables persisted in DuckDB.

## Phase 04 — Exploratory Data Analysis (EDA) 🔜 (Current)
**Goal:** Surface the business insights that will become AI constraints.
**What we do:** Write DuckDB SQL queries to find: **top genres by ROI** (revenue/budget), **seasonal trends** (avg ROI by `release_month`), **director ROI** (which directors return most per dollar), **emerging actors** (rising talent). Sanity-check against box-office reality.
**Tools:** DuckDB (SQL), Pandas, simple charts.
**Output:** A set of validated insight tables — the raw material for `constraints.json`.

## Phase 05 — Feature Engineering & Selection ⬜
**Goal:** Convert insights into machine-usable constraints + build the retrieval knowledge base.
**What we do:**
1. **`constraints.json`** — assemble the EDA insights into a structured contract: `{top_genres, seasonal_fit, actor_trends, director_trends, budget_tier}`. This is the interface between the data side and the AI side.
2. **ChromaDB RAG store** — collect 100+ historical film scripts/synopses, **chunk them** by scene/act, **embed** each chunk with a sentence-transformer, and store in **ChromaDB**. Implement retrieval: given a genre + plot snippet, return the **top-3 most similar** examples for the Writer agent to learn structure from (in-context, not training).
**Tools:** Python (build `constraints.json`), ChromaDB, sentence-transformers.
**Output:** `constraints.json` + a populated, queryable ChromaDB collection.

## Phase 06 — Model Selection ⬜
**Goal:** Choose the LLM and supporting models (we *select* pre-trained, we don't train).
**What we do:** Deploy **Ollama** on Colab's GPU; pull a quantized model (e.g. `qwen2.5:7b` 4-bit), and benchmark a smaller `qwen2.5:3b` for comparison. Measure latency (target: 300 tokens < 15s) and memory. Pick the embedding model for RAG. Decide LangGraph as the orchestrator.
**Tools:** Ollama, Qwen/Mistral GGUF (4-bit), LangGraph.
**Output:** A running local LLM + a latency/quality benchmark table (the "quantization tradeoff" writeup).

## Phase 07 — Model "Training" → Agent Orchestration ⬜ ⚠️
**Goal:** Build the multi-agent loop (no gradient training — this is in-context learning).
**What we do:** Implement a **LangGraph** workflow with shared state:
- **Writer Agent** — generates a 150-word synopsis from genre + `constraints.json` (+ top-3 RAG examples).
- **Critic Agent** — scores the synopsis 0–1 against constraints; returns failed constraints + suggestions. Score *must* depend on synopsis content.
- **Refiner Agent** — if score < 0.7, re-prompts the Writer with the failed constraints injected.
- **Exit conditions:** score > 0.7 **OR** 3 iterations **OR** no-improvement (cycle/graceful-failure handling).
**Tools:** LangGraph, Ollama, the validator (Phase 08), ChromaDB.
**Output:** A working agent loop that takes constraints → returns a refined synopsis + full state trace.

## Phase 08 — Evaluation & Tuning ⬜
**Goal:** Make sure the AI actually obeyed the data, and tune the loop.
**What we do:** Build the **constraint validator** as a pure, unit-tested function `(synopsis, constraints) → report`. Checks: correct genre mentioned, seasonal alignment, trending talent leveraged, narrative coherence. Outputs `{score, passed_constraints, failed_constraints, suggestions}`. Tune the 0.7 threshold, prompts, and constraint weights. *Optional: backtest against real box-office outcomes.*
**Tools:** Python, pytest.
**Output:** Validator module + validation report + (optional) backtest success rate.

## Phase 09 — Deployment ⬜
**Goal:** Expose the system through an API and a UI.
**What we do:**
- **FastAPI** (on Colab): `POST /generate-synopsis` (→ job_id), `GET /status/{job_id}`, `GET /constraints`, `GET /health`. Handle 5+ concurrent requests, queue overflow, rate limit (50 req/min/IP). Expose to laptop via a **cloudflared/ngrok tunnel**.
- **Streamlit** (on laptop): two tabs — **Analytics dashboard** (genre ROI, seasonal, actor charts) and **Generator** (form → call API → poll status → show synopsis + critique + validation report). Show live constraints on the form; clear error/retry if API unreachable.
**Tools:** FastAPI, Pydantic, Streamlit, cloudflared/ngrok.
**Output:** A running API + interactive frontend.

## Phase 10 — Monitoring & Maintenance ⬜
**Goal:** Make the system observable and resilient.
**What we do:** Log every agent decision (state transitions, LLM in/out, scores) → a live workflow trace. Implement **graceful degradation**: Ollama OOM → fall back to smaller model / cached response; ChromaDB down → skip RAG and continue; DuckDB timeout → return last-good constraints. No cascading crashes. `/health` reports component status.
**Tools:** Python logging, the FastAPI `/health` endpoint.
**Output:** Logging/trace + documented failure-handling behavior.

---

## Immediate Next Steps
1. **Finish Phase 03:** `src/data/credits.py` (parse cast/crew, join on `id`) → write to DuckDB on Drive.
2. **Phase 04:** DuckDB analytics queries (genre ROI, seasonal, director ROI, emerging actors).
3. **Phase 05:** assemble `constraints.json` + build the ChromaDB RAG store.
