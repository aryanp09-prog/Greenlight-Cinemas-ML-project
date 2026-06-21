"""
Build ui/faces.json : { actor/director name -> Wikipedia/Wikimedia photo URL }.
Runs on the laptop. No GPU, no API key, no VPN (Wikimedia isn't blocked in India).

    python ui/build_faces.py

    # optional — also ingest the real cast names from a constraints.json:
    python ui/build_faces.py path/to/constraints.json

Re-running is cheap: it keeps names already resolved and only fetches new/missing ones.
Uses Wikipedia's cache-friendly REST API; images come from upload.wikimedia.org (unblocked).
"""
import os
import sys
import json
import time
import requests

REST_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
REST_SEARCH = "https://en.wikipedia.org/w/rest.php/v1/search/page"
S = requests.Session()
S.headers.update({"User-Agent": "GreenlightCinema/1.0 "
                  "(https://github.com/aryanp09-prog/Greenlight-Cinemas-ML-project)"})

NAMES = {
    "Oscar Isaac", "Tessa Thompson", "John Boyega", "Sonoya Mizuno", "Denis Villeneuve", "Alex Garland",
    "Frances McDormand", "Mahershala Ali", "Florence Pugh", "Kathryn Bigelow",
    "Toni Collette", "Mia Goth", "Bill Skarsgård", "Essie Davis", "Ari Aster", "Jordan Peele",
    "Tiffany Haddish", "Nick Kroll", "Ayo Edebiri", "Sam Richardson", "Taika Waititi", "Greta Gerwig",
    "Dev Patel", "Gemma Chan", "Brian Cox", "Celine Song",
    "Charlize Theron", "Idris Elba", "Daniel Kaluuya", "Michelle Yeoh", "Chad Stahelski",
    "Anya Taylor-Joy", "Cynthia Erivo", "Pedro Pascal", "Guillermo del Toro",
    "Viola Davis", "Brian Tyree Henry", "André Holland", "Barry Jenkins", "Kenneth Lonergan",
    "Zendaya",
}


def _get(url, **kw):
    """GET with simple backoff on 429."""
    for attempt in range(4):
        r = S.get(url, timeout=15, **kw)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        return r
    return r


def _norm(u):
    return ("https:" + u) if u and u.startswith("//") else u


def _summary_thumb(title):
    r = _get(REST_SUMMARY + requests.utils.quote(title.replace(" ", "_"), safe="_"))
    if r.status_code == 404:
        return None
    r.raise_for_status()
    j = r.json()
    if j.get("type") == "disambiguation":
        return None
    src = (j.get("thumbnail") or {}).get("source") or (j.get("originalimage") or {}).get("source")
    return _norm(src)


def wiki_face(name):
    t = _summary_thumb(name)                     # 1) direct title
    if t:
        return t
    r = _get(REST_SEARCH, params={"q": f"{name} actor", "limit": 1})   # 2) search fallback
    if r.ok:
        pages = r.json().get("pages", [])
        if pages:
            thumb = (pages[0].get("thumbnail") or {}).get("url")
            if thumb:
                return _norm(thumb)
            return _summary_thumb(pages[0].get("key") or pages[0].get("title", ""))
    return None


def main():
    names = set(NAMES)
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):       # optional constraints.json
        c = json.load(open(sys.argv[1], encoding="utf-8"))
        for key, field in [("actor_trends", "actor"), ("director_trends", "director")]:
            for x in c.get(key, []):
                nm = (x.get(field) or x.get("name")) if isinstance(x, dict) else x
                if nm:
                    names.add(nm)
        # the live cast/directors come from cast_by_genre_budget — ingest those too
        for genre, tiers in c.get("cast_by_genre_budget", {}).items():
            for tier, slot in tiers.items():
                for who in ("actors", "directors"):
                    for p in slot.get(who, []):
                        nm = p.get("name") if isinstance(p, dict) else p
                        if nm:
                            names.add(nm)
        print(f"+ added real names from {sys.argv[1]}")

    out_path = os.path.join(os.path.dirname(__file__), "faces.json")
    faces = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}

    found = 0
    for nm in sorted(names):
        if faces.get(nm):                       # already resolved -> skip
            found += 1
            continue
        try:
            url = wiki_face(nm)
        except Exception as e:
            print("  !", nm, "->", e)
            url = None
        if url:
            faces[nm] = url
            found += 1
            print("  ok ", nm)
        else:
            print("  -- no photo:", nm)
        time.sleep(0.6)                         # be gentle on the API

    json.dump(faces, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nwrote {out_path}  ({found}/{len(names)} names have photos)")


if __name__ == "__main__":
    main()
