# ============================================================
#  NATURAL-PROMPT PARSER (ported from the Colab notebook)
# ============================================================
# `parse_prompt` does fuzzy LLM extraction in Colab; the safety net — `_normalize`,
# `_match_genre`, `_parse_budget` — is pure, deterministic, and tested here. The
# extraction is fuzzy; the guardrails are exact (so "250 words" and "$50M" are
# never confused).
import json
import re

KNOWN_GENRES = ["Action","Adventure","Animation","Comedy","Crime","Documentary","Drama",
                "Family","Fantasy","History","Horror","Music","Mystery","Romance",
                "Science Fiction","Thriller","War","Western"]   # full TMDB list (keeps the Adventure fix)
SEASON_TO_MONTH = {"summer":"June","winter":"December","spring":"April","fall":"October",
                   "autumn":"October","holiday":"December","christmas":"December","halloween":"October"}
MONTHS = ["January","February","March","April","May","June","July","August",
          "September","October","November","December"]


def _match_genre(text):
    t = (text or "").lower()
    for g in KNOWN_GENRES:
        if g.lower() in t: return g
    if any(k in t for k in ("sci-fi","scifi","sci fi")): return "Science Fiction"
    if any(k in t for k in ("rom-com","romcom","rom com")): return "Romance"
    return None


def _match_genres(text):
    """All genres named in the text, in order ('horror comedy' -> [Horror, Comedy])."""
    t = (text or "").lower()
    found = [g for g in KNOWN_GENRES if g.lower() in t]
    if any(k in t for k in ("sci-fi", "scifi", "sci fi")) and "Science Fiction" not in found:
        found.append("Science Fiction")
    if any(k in t for k in ("rom-com", "romcom", "rom com")):
        for g in ("Romance", "Comedy"):
            if g not in found: found.append(g)
    return found


_INSP_TRIGGERS = ("take inspiration from", "inspiration from", "inspired by", "based on",
                  "in the style of", "combining the movies", "combining", "combine the movies",
                  "combine", "mix of", "fusion of", "cross between", "mashup of", "blend of",
                  "like the movies", "like the movie", "like the films", "like the film")
_INSP_PREFIX = re.compile(r"^(?:the\s+)?(?:movies?|films?)\s+", re.I)


def _inspirations_fallback(text):
    """Pull named movie titles after a trigger ('combine Matrix and Inception' -> [Matrix, Inception])."""
    low = (text or "").lower()
    for k in _INSP_TRIGGERS:
        i = low.find(k)
        if i != -1:
            tail = text[i + len(k):].strip(" :")
            tail = _INSP_PREFIX.sub("", tail)
            parts = re.split(r"\s*(?:,|&|\band\b|\bplus\b|\bwith\b)\s*", tail, flags=re.I)
            titles = [p.strip(" .\"'") for p in parts if p.strip()]
            titles = [t for t in titles if 1 <= len(t) <= 40]
            return titles[:3] or None
    return None


_PREMISE_TRIGGERS = ("where ", "about ", "in which ", "story of ", "involving ",
                     "featuring ", "following ", "centered on ", "centred on ",
                     "premise:", "plot:")


def _premise_fallback(text):
    """If the LLM didn't isolate the user's plot, grab the clause after a trigger
    word ('...$100M where two robots are made...' -> 'two robots are made...').
    Deterministic backstop so an obvious premise is never lost."""
    t = (text or "").strip()
    low = t.lower()
    best, bestpos = None, len(t) + 1
    for k in _PREMISE_TRIGGERS:
        i = low.find(k)
        if i != -1 and i < bestpos:
            bestpos, best = i, t[i + len(k):].strip(" .,:")
    return best or None


def _parse_budget(text):
    """$50M, 50M$, 50 million, $50,000,000, 2B, 500k -> int dollars (or None)."""
    t = (text or "").lower().replace(",", "")
    mults = {"billion":1e9,"b":1e9,"million":1e6,"m":1e6,"mil":1e6,"thousand":1e3,"k":1e3}
    m = (re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(billion|million|thousand|mil|b|m|k)?", t)
         or re.search(r"(\d+(?:\.\d+)?)\s*(billion|million|thousand|mil|b|m|k)\b\s*\$?", t)
         or re.search(r"budget\D{0,12}(\d+(?:\.\d+)?)\s*(billion|million|thousand|mil|b|m|k)?", t))
    if not m: return None
    val = float(m.group(1)); mult = mults.get(m.group(2) or "", 1)
    if mult == 1 and val < 1000: mult = 1e6          # "budget of 50" = millions
    return int(val * mult)


def _normalize(data, text):                          # deterministic guardrails — TESTABLE
    genre = data.get("genre")
    if genre not in KNOWN_GENRES:
        genre = _match_genre(text) or "Drama"
    # multi-genre: LLM list + deterministic scan (dedup, keep order); primary genre = first
    genres = [g for g in (data.get("genres") or []) if g in KNOWN_GENRES]
    for g in _match_genres(text):
        if g not in genres: genres.append(g)
    if not genres:
        genres = [genre]
    genre = genres[0]
    window = data.get("window")
    if isinstance(window, str):
        w = window.strip().lower()
        if w in ("", "null", "none", "best", "any", "data-driven"): window = None
        elif w in SEASON_TO_MONTH: window = SEASON_TO_MONTH[w]
        else: window = next((mo for mo in MONTHS if mo.lower()[:3] in w), None)
    else:
        window = None
    length = data.get("length")
    lm = re.search(r"(\d{2,4})\s*word", (text or "").lower())
    if lm: length = int(lm.group(1))
    if not isinstance(length, int) or not (30 <= length <= 600): length = 80
    budget = _parse_budget(text)                     # number in text wins
    premise = data.get("premise")                    # the user's specific plot, if any
    if isinstance(premise, str):
        premise = premise.strip()
        if premise.lower() in ("", "null", "none", "n/a"): premise = None
    else:
        premise = None
    if not premise:
        premise = _premise_fallback(text)
    inspirations = data.get("inspirations")              # named movies to take inspiration from / fuse
    if isinstance(inspirations, list):
        inspirations = [str(x).strip(" .\"'") for x in inspirations if str(x).strip()]
    else:
        inspirations = []
    if not inspirations:
        inspirations = _inspirations_fallback(text) or []
    return {"genre": genre, "genres": genres, "window": window, "length": length,
            "budget": budget, "premise": premise, "inspirations": inspirations}


def parse_prompt(text, call_llm=None):
    """LLM extraction + deterministic guardrails.

    In Colab a `call_llm` callable is provided by the runtime. Off-Colab (e.g. on
    the laptop), pass your own callable or leave it None to skip extraction and
    rely entirely on the deterministic guardrails over the raw text.
    """
    schema = ('{"genre":"<primary genre>","genres":["<all genres named>"],'
              '"window":"<month/season, or null>","length":<int or null>,'
              '"budget":<int dollars or null>,'
              '"premise":"<the specific plot/characters the user describes, or null>",'
              '"inspirations":["<movie titles to take inspiration from / combine, or empty>"]}')
    prompt = (f"Extract fields from this film request. Reply ONLY JSON: {schema}\n"
              f"Allowed genres: {', '.join(KNOWN_GENRES)}.\n"
              f"If they say 'best release window' or give no timing, window=null.\n"
              f"Put any specific story the user describes (characters, what happens) into premise; "
              f"if they only name a genre with no plot, premise=null.\n"
              f"List EVERY genre they name in genres (e.g. 'horror comedy' -> both). "
              f"Put ONLY movies the user EXPLICITLY names (as inspiration or to combine) into inspirations "
              f"(e.g. 'combine Matrix and Inception' -> [\"The Matrix\",\"Inception\"]); if they name no "
              f"movie, inspirations=[]. Do NOT infer or guess movies from the plot.\n"
              f"Request: {text}")
    data = {}
    if call_llm is not None:
        try: data = json.loads(call_llm(prompt, max_tokens=120, fmt="json"))
        except Exception: data = {}
    return _normalize(data, text)
