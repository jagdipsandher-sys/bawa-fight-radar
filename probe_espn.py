#!/usr/bin/env python3
"""TEMPORARY — does the month fix actually produce fixtures? Deleted after."""
import build_panthers, build_raiders, build_united, build_wolves

for mod, label in [(build_panthers, "PANTHERS"), (build_raiders, "RAIDERS"),
                   (build_united, "MAN UTD"), (build_wolves, "WOLVES")]:
    print("=" * 60)
    print(label)
    print("=" * 60)
    try:
        games = mod.collect()
        print(f"  {len(games)} upcoming fixtures")
        for g in games[:6]:
            when = mod.syd(g["when"])
            name = g.get("opponent") or g.get("name", "")
            print(f"    {when:%a %d %b %-I:%M%p}  {name}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
    print()
