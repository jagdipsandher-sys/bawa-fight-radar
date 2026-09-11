#!/usr/bin/env python3
"""TEMPORARY probe #2 — deleted after use.

Question: can fighter headshots be sourced automatically, so photos.json
stops running dry every time the card rolls over?

Dumps the full raw shape of one bout (looking for athlete IDs), then tests
every plausible ESPN headshot URL pattern for a real 200.
"""
import json
import urllib.request

BASE = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates=20260910-20260921"


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def status(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.headers.get("Content-Type", ""), r.headers.get("Content-Length", "?")
    except Exception as e:
        return getattr(e, "code", type(e).__name__), "", ""


d = get(BASE)
ev = d["events"][0]
comp = ev["competitions"][-1]          # main event

print("=" * 72)
print("A. FULL RAW COMPETITOR OBJECT (main event, fighter 1)")
print("=" * 72)
print(json.dumps(comp["competitors"][0], indent=2)[:2500])

print()
print("=" * 72)
print("B. COMPETITION-LEVEL KEYS (is there an id / link to follow?)")
print("=" * 72)
print("competition keys:", sorted(comp.keys()))
print("event keys      :", sorted(ev.keys()))
for k in ("id", "uid", "links"):
    if k in comp:
        print(f"  comp.{k}: {json.dumps(comp[k])[:400]}")

print()
print("=" * 72)
print("C. CAN WE GET AN ATHLETE ID FROM THE SUMMARY ENDPOINT?")
print("=" * 72)
try:
    summ = get(f"https://site.api.espn.com/apis/site/v2/sports/mma/ufc/summary?event={ev['id']}")
    print("summary keys:", sorted(summ.keys()))
    txt = json.dumps(summ)
    print("mentions 'headshot'? ", "headshot" in txt.lower())
    # find any athlete blocks with ids
    found = 0
    def walk(node, path=""):
        global found
        if found >= 3:
            return
        if isinstance(node, dict):
            if "athlete" in node and isinstance(node["athlete"], dict):
                a = node["athlete"]
                if a.get("id") or a.get("headshot"):
                    print(f"\n  at {path}.athlete:")
                    print(f"    keys: {sorted(a.keys())}")
                    print(f"    id: {a.get('id')}  name: {a.get('displayName')}")
                    if a.get("headshot"):
                        print(f"    headshot: {json.dumps(a['headshot'])[:250]}")
                    found += 1
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node[:6]):
                walk(v, f"{path}[{i}]")
    walk(summ)
except Exception as e:
    print("summary fetch failed:", type(e).__name__, e)

print()
print("=" * 72)
print("D. DO ESPN HEADSHOT URL PATTERNS ACTUALLY RESOLVE?")
print("=" * 72)
# Jon Jones is a well-known MMA athlete id on ESPN — a control test for the
# URL pattern itself, independent of whether this weekend's fighters have one.
for label, url in [
    ("mma pattern (control, Jon Jones 2335639)",
     "https://a.espncdn.com/i/headshots/mma/players/full/2335639.png"),
    ("combined-ufc pattern",
     "https://a.espncdn.com/i/headshots/ufc/players/full/2335639.png"),
]:
    print(f"  {status(url)}  {label}")
