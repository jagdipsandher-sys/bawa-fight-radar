#!/usr/bin/env python3
"""TEMPORARY probe — deleted after use.

Answers three things the sandbox can't reach the network to check:
  1. what time ESPN actually says this weekend's UFC card starts
  2. whether the feed carries fighter headshots we could use automatically
  3. whether the hand-typed photos.json URLs still resolve
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SYD = ZoneInfo("Australia/Sydney")
UA = {"User-Agent": "Mozilla/5.0 (compatible; bawa-radar/1.0)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


print("=" * 70)
print("1. THIS WEEKEND'S CARD — what ESPN actually says")
print("=" * 70)
d = get("https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
        "?dates=20260910-20260921")
for ev in d.get("events", []):
    when = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
    syd = when.astimezone(SYD)
    print(f"\n  {ev.get('name')}")
    print(f"    raw feed date : {ev['date']}")
    print(f"    Sydney        : {syd:%a %d %b %Y %-I:%M%p} {syd.tzname()} (UTC{syd:%z})")
    comps = ev.get("competitions") or []
    print(f"    competitions  : {len(comps)}")
    # main event is LAST in ESPN's running order
    if comps:
        main = comps[-1]
        names = []
        for c in main.get("competitors", []):
            a = c.get("athlete") or {}
            names.append(a.get("displayName") or a.get("shortName") or "?")
        print(f"    main event    : {' vs '.join(names)}")
        mwhen = main.get("date")
        if mwhen and mwhen != ev["date"]:
            ms = datetime.fromisoformat(mwhen.replace("Z", "+00:00")).astimezone(SYD)
            print(f"    main-event time: {ms:%a %d %b %-I:%M%p} {ms.tzname()}")

print()
print("=" * 70)
print("2. DOES THE FEED CARRY HEADSHOTS? (first card, first 2 fighters)")
print("=" * 70)
evs = d.get("events") or []
if evs:
    comps = evs[0].get("competitions") or []
    if comps:
        for c in (comps[-1].get("competitors") or [])[:2]:
            a = c.get("athlete") or {}
            print(f"\n  {a.get('displayName')}")
            print(f"    athlete keys: {sorted(a.keys())}")
            for k in ("headshot", "flag", "images", "logo"):
                if k in a:
                    print(f"    {k}: {json.dumps(a[k])[:220]}")
            aref = a.get("$ref") or a.get("ref")
            if aref:
                print(f"    $ref: {aref[:120]}")
                try:
                    detail = get(aref)
                    print(f"    detail headshot: {json.dumps(detail.get('headshot'))[:220]}")
                except Exception as e:
                    print(f"    detail fetch failed: {type(e).__name__}")

print()
print("=" * 70)
print("3. DO THE EXISTING photos.json URLS STILL WORK?")
print("=" * 70)
photos = json.load(open("photos.json"))
for k, url in photos.items():
    if k.startswith("_"):
        continue
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"  {r.status}  {k}")
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
        print(f"  {code}  {k}   <-- BROKEN")
