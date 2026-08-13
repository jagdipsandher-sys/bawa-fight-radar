#!/usr/bin/env python3
"""Throwaway: is there a trustworthy standings feed for the Premier League and F1?"""
import json, urllib.request

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

CANDS = {
 "PL standings (site v2)":   "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings",
 "PL standings (web v2)":    "https://site.web.api.espn.com/apis/v2/sports/soccer/eng.1/standings?season=2026",
 "F1 standings (site v2)":   "https://site.api.espn.com/apis/v2/sports/racing/f1/standings",
 "F1 standings (web v2)":    "https://site.web.api.espn.com/apis/v2/sports/racing/f1/standings?season=2026",
}
for label, url in CANDS.items():
    print("\n" + "=" * 70, f"\n{label}\n{url}")
    try:
        d = get(url)
    except Exception as e:
        print("  FAILED:", type(e).__name__, e); continue
    print("  keys:", list(d)[:12])
    groups = d.get("children") or ([d.get("standings")] if d.get("standings") else [])
    print("  children:", len(d.get("children") or []))
    for g in (d.get("children") or [d])[:3]:
        st = g.get("standings") or {}
        entries = st.get("entries") or []
        print(f"   group: {g.get('name') or d.get('name')} | entries: {len(entries)}")
        for e in entries[:6]:
            team = (e.get("team") or {}).get("displayName") or e.get("athlete", {}).get("displayName") or e.get("note")
            stats = {s.get("name") or s.get("abbreviation"): s.get("displayValue") for s in e.get("stats", [])}
            keep = {k: v for k, v in stats.items() if k in
                    ("rank","points","gamesPlayed","wins","losses","ties","pointDifferential","overall")}
            print(f"     - {team}: {keep or list(stats)[:8]}")
