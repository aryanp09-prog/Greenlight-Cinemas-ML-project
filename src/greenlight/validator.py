# ============================================================
#  PHASE 8 — DETERMINISTIC, TESTED CRITIC (validator)
# ============================================================
# Ported verbatim from the Colab notebook so the repo tests exercise the exact
# logic that runs live. The Critic is NOT an LLM grading itself: it is this pure
# function, so the same synopsis always yields the same score.
import re

GENRE_LEXICON = {
    "horror":     {"horror","terror","fear","haunt","nightmare","dread","evil","demon","ghost","blood","dark","death","sinister","supernatural","scream","monster","curse","possessed","killer","shadow","grim"},
    "action":     {"action","explosive","fight","chase","battle","mission","weapon","danger","combat","hero","escape","showdown","relentless","adrenaline","pursuit","gun","war","strike","ruthless"},
    "comedy":     {"comedy","hilarious","laugh","funny","witty","absurd","misadventure","awkward","chaos","prank","goofy","humor","quirky","mishap"},
    "drama":      {"drama","emotional","struggle","grief","family","loss","redemption","heart","journey","conflict","betrayal","sacrifice","truth","haunted"},
    "romance":    {"romance","love","heart","passion","relationship","longing","desire","affair","wedding","soulmate","tender","fall"},
    "thriller":   {"thriller","suspense","tension","danger","secret","conspiracy","hunt","twist","deadly","betrayal","race","mystery","stalk"},
    "science fiction": {"future","space","alien","technology","robot","dystopia","time","galaxy","cyber","experiment","planet","artificial"},
    "scifi":      {"future","space","alien","technology","robot","dystopia","time","galaxy","cyber","experiment","planet","artificial"},
    "fantasy":    {"magic","kingdom","dragon","quest","myth","sorcerer","realm","enchanted","prophecy","legend","wizard","spell"},
    "animation":  {"adventure","friendship","colorful","family","journey","wonder","heart","magical","young","discover"},
    "family":     {"family","friendship","heartwarming","adventure","together","young","wholesome","journey","home","love"},
    "mystery":    {"mystery","clue","detective","secret","murder","investigate","puzzle","hidden","truth","suspect","unravel"},
    "crime":      {"crime","heist","gang","detective","murder","police","criminal","robbery","underworld","justice","mob"},
}
CRITICAL = {"genre_signal", "window_consistent", "no_placeholder"}


def _genre_terms(genre):
    g = (genre or "").strip().lower()
    terms = set(GENRE_LEXICON.get(g, set()))
    terms.add(g)                       # the genre word itself always counts
    return terms


def _month_match(target_window, best):
    tw = (target_window or "").lower()
    return any(m.strip().lower()[:3] in tw for m in best)   # "Jan" matches "January", "Jun" matches "June"


def validate_synopsis(synopsis, genre, target_window, constraints, user_window=None, target_len=80):
    """Pure, deterministic. (synopsis, plan) -> {score, passed, failed, suggestions, valid}."""
    s = (synopsis or "").strip()
    words = re.findall(r"[A-Za-z']+", s)
    n = len(words); low = s.lower()
    checks = []   # (name, passed, weight, suggestion)

    # 1. length (band scales with requested length; default 80 -> 40-120)
    lo, hi = round(target_len * 0.5), round(target_len * 1.5)
    checks.append(("length_ok", lo <= n <= hi, 0.20,
        f"Synopsis is {n} words; aim for ~{target_len} ({lo}-{hi})."))
    checks.append(("length_ok", 40 <= n <= 120, 0.20,
        f"Synopsis is {n} words; aim for 40-120 (logline to short paragraph)."))

    # 2. genre signal
    terms = _genre_terms(genre)
    hits = sorted({w for w in (x.lower() for x in words) if w in terms})
    checks.append(("genre_signal", len(hits) > 0, 0.25,
        f"Add {genre}-appropriate language (e.g. {', '.join(list(terms)[:5])})."))

    # 3. no placeholders / leaked formatting / meta-text
    bad = ["todo","lorem","[insert","{","}","```","as an ai","i cannot","here is","synopsis:","note:"]
    checks.append(("no_placeholder", not any(b in low for b in bad), 0.15,
        "Remove placeholders, JSON/markdown artifacts, or meta-text like 'Here is the synopsis'."))

    # 4. complete (terminal punctuation + at least 2 sentences)
    sentences = [x for x in re.split(r"[.!?]+", s) if x.strip()]
    checks.append(("complete", s.endswith((".","!","?")) and len(sentences) >= 2, 0.15,
        "End with terminal punctuation and write at least two full sentences (no truncation)."))

    # 5. window consistency (is the release plan aligned with the data?)
    best = constraints.get("seasonal_by_genre", {}).get(genre) \
           or constraints.get("seasonal_fit", {}).get("best_months_named", [])
    if user_window:
        window_ok = bool(target_window and target_window.strip())
        win_sug = "User override given; ensure target_window reflects the user's requested timing."
    else:
        window_ok = _month_match(target_window, best)
        win_sug = f"Release window should match the data-best months for {genre}: {', '.join(best)}."
    checks.append(("window_consistent", window_ok, 0.25, win_sug))

    passed      = [c[0] for c in checks if c[1]]
    failed      = [c[0] for c in checks if not c[1]]
    suggestions = [c[3] for c in checks if not c[1]]
    score       = round(sum(c[2] for c in checks if c[1]), 3)
    critical_failed = [f for f in failed if f in CRITICAL]
    valid = score >= 0.7 and not critical_failed

    return {"score": score, "passed": passed, "failed": failed,
            "suggestions": suggestions, "n_words": n, "genre_hits": hits,
            "critical_failed": critical_failed, "valid": valid}
