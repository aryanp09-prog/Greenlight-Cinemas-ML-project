# 🎬 Greenlight Cinema — Project Roadmap

A data-driven film-synopsis generator: DuckDB analytics on real box-office data produces hard
constraints, which are injected into a multi-agent LLM loop (Writer → Critic → Refiner) that
generates a synopsis obeying them, iterating until critique score > 0.7 or 3 loops.

> **What kind of project is this?** A **data-analytics + agentic-LLM** system — *not* a
> supervised model-training project. So the ML lifecycle maps cleanly onto steps 1–5 and 8–10,
> while steps 6–7 **transform**: instead of training a model, we *select* a pre-trained LLM and
> steer it with engineered constraints + an iterative critique loop. "Training" becomes
> "orchestration + prompt engineering + RAG (in-context learning)."

---

## Phase Map (aligned to the ML Lifecycle)

| # | ML Lifecycle Step | What it means in this project | Status |
|---|---|---|---|
| 01 | **Problem Definition** | Bridge audience data ↔ AI creativity; data-grounded synopsis generation | ✅ Done |
| 02 | **Data Collection** | Rounak Banik `the-movies-dataset` via Kaggle API → Colab | ✅ Done |
| 03 | **Data Cleaning & Preprocessing** | `ingest.py` (coerce numerics, parse genres/dates, build ROI subset). Credits parsing pending | 🟡 ~80% |
| 04 | **Exploratory Data Analysis (EDA)** | DuckDB analytics: genre ROI, seasonal trends, director/actor impact, emerging talent | 🔜 **Current** |
| 05 | **Feature Engineering & Selection** | Turn insights into `constraints.json` (the data↔AI interface); embed scripts for RAG | ⬜ |
| 06 | **Model Selection** | Pick LLM (Qwen 7B vs 3B) + quantization; embedding model; LangGraph (select, don't train) | ⬜ |
| 07 | **Model "Training"** ⚠️ | No gradient training. In-context learning: build Writer→Critic→Refiner loop + RAG + prompts | ⬜ |
| 08 | **Model Evaluation & Tuning** | Constraint validator + critique score (0–1); tune 0.7 threshold, prompts, weights. Optional backtesting | ⬜ |
| 09 | **Model Deployment** | FastAPI backend + Streamlit UI + tunnel (Colab ↔ laptop) | ⬜ |
| 10 | **Model Monitoring & Maintenance** | Log agent state transitions / workflow trace; `/health`; graceful degradation | ⬜ |

---

## Architecture (fixed)

- **Author code in VS Code → push to GitHub → Colab pulls (`!git pull`) and runs it.**
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

## Next Steps (immediate → later)

1. **Finish Phase 3:** `src/data/credits.py` — load `credits.csv`, parse cast/crew, join on `id`, extract director (`crew` where `job=='Director'`) + top 3–5 cast.
2. **Phase 4 (EDA):** DuckDB SQL — top genres by ROI, ROI by release month (seasonal), director ROI, emerging actors.
3. **Phase 5:** assemble `constraints.json` `{top_genres, seasonal_fit, actor_trends, director_trends, budget_tier}`; build ChromaDB RAG over 100+ scripts.
4. **Phase 6–7:** Ollama on Colab + latency benchmark; LangGraph loop (state, exit at score>0.7 / 3 iters / no-progress).
5. **Phase 8:** constraint validator → validation report `{score, passed, failed, suggestions}`.
6. **Phase 9:** FastAPI (`/generate-synopsis`, `/status/{job_id}`, `/constraints`, `/health`) + Streamlit (analytics dashboard + generator).
7. **Phase 10:** logging/trace, graceful degradation (Ollama OOM, ChromaDB down, DuckDB timeout).
