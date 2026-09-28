#!/usr/bin/env python3
"""TEMPORARY probe — deleted after use.

Question: is there a machine-readable source for BKFC (bare knuckle), good
enough to build a self-maintaining tab on like every other tab here? Or would
it have to be hand-typed like boxing.json?
"""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; bawa-radar/1.0)"}


def get(url, headers=None, raw=False):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read()
        return r.status, (body if raw else json.loads(body))


print("=" * 72)
print("A. WHAT MMA LEAGUES DOES ESPN ACTUALLY EXPOSE?")
print("=" * 72)
try:
    st, d = get("https://site.api.espn.com/apis/site/v2/sports/mma")
    for s in d.get("sports", []):
        for lg in s.get("leagues", []):
            print(f"  {lg.get('slug'):<24} {lg.get('name')}")
except Exception as e:
    print("  failed:", type(e).__name__, e)

print()
print("=" * 72)
print("B. DOES ANY BARE-KNUCKLE LEAGUE CODE WORK ON THE SCOREBOARD?")
print("=" * 72)
for code in ["bkfc", "bareknuckle", "bare-knuckle", "bkb", "bkfc-mma"]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/mma/{code}/scoreboard?dates=20260920-20261130"
    try:
        st, d = get(url)
        print(f"  {code:<14} {st}  events={len(d.get('events', []))}")
    except Exception as e:
        print(f"  {code:<14} {getattr(e, 'code', type(e).__name__)}")

print()
print("=" * 72)
print("C. DOES THE UFC FEED HAPPEN TO CARRY BKFC EVENTS? (it should not)")
print("=" * 72)
try:
    st, d = get("https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
                "?dates=20260920-20261130")
    names = [e.get("name", "") for e in d.get("events", [])]
    print(f"  {len(names)} events returned:")
    for n in names:
        print("   ", n)
    print("  any bare-knuckle?", any("bkfc" in n.lower() or "knuckle" in n.lower() for n in names))
except Exception as e:
    print("  failed:", type(e).__name__, e)

print()
print("=" * 72)
print("D. DOES BKFC.COM EXPOSE ANYTHING MACHINE-READABLE?")
print("=" * 72)
for url in ["https://www.bkfc.com/events",
            "https://www.bkfc.com/api/events",
            "https://www.bkfc.com/wp-json/wp/v2/pages?per_page=1"]:
    try:
        st, body = get(url, headers=UA, raw=True)
        head = body[:120].decode("utf-8", "replace").replace("\n", " ")
        kind = "JSON" if body.lstrip()[:1] in (b"{", b"[") else "HTML/other"
        print(f"  {st}  {kind:<10} {url}")
        print(f"        {head[:100]}")
    except Exception as e:
        print(f"  {getattr(e, 'code', type(e).__name__)}  {url}")

print()
print("=" * 72)
print("E. WIKIPEDIA API AS A FALLBACK SCHEDULE SOURCE?")
print("=" * 72)
try:
    st, d = get("https://en.wikipedia.org/w/api.php?action=parse"
                "&page=2026_in_Bare_Knuckle_Fighting_Championship"
                "&prop=wikitext&section=1&format=json", headers=UA)
    txt = d["parse"]["wikitext"]["*"]
    print(f"  {st}  wikitext section pulled, {len(txt)} chars")
    print("  first 400 chars:")
    print("   ", txt[:400].replace("\n", "\n    "))
except Exception as e:
    print("  failed:", type(e).__name__, e)
