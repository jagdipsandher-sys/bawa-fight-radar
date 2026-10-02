#!/usr/bin/env python3
"""
Reads the radar page and works out what is actually on this weekend, across
every tab rather than just the fights.

send_fights.py used to email the UFC/boxing list only. Jack wants the Friday
email to fire the boys up for the whole weekend, so it needs to see the NRL,
the bare knuckle, the Sydney stuff and the series too. index.html is the one
place that already knows all of it, so this parses the page rather than
re-fetching ten feeds.

Nothing here invents content. If a tab has nothing on this weekend it returns
nothing for that tab, and the email simply leaves the section out.
"""
import html as html_mod
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SYD = ZoneInfo("Australia/Sydney")
PAGE = "index.html"

# Tab id -> (label used in the email, how many entries are worth showing)
WANTED = [
    ("bkfc",     "Bare Knuckle", 2),
    ("fights",   "UFC",          2),
    ("panthers", "NRL",          1),
    ("united",   "Man Utd",      1),
    ("f1",       "F1",           1),
    ("motogp",   "MotoGP",       1),
    ("wolves",   "NBA",          1),
    ("pga",      "Golf",         1),
    ("tennis",   "Tennis",       1),
]


def _txt(s):
    """Tag soup to plain text, entities decoded, and no dashes.

    Jack's one unbreakable writing rule is no hyphens or dashes anywhere, and
    this text goes straight into an email under his name. Site copy uses them
    freely ("Reacher - Season 4", "Thu night-Mon morning"), so they are
    normalised here rather than in six places downstream.
    """
    t = html_mod.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
    t = re.sub(r"\s*\u2013\s*", " to ", t)      # en dash joins a range
    t = re.sub(r"\s*\u2014\s*", " \u00b7 ", t)   # em dash separates a clause
    return re.sub(r"\s{2,}", " ", t).strip()


def panes(page):
    return dict(re.findall(
        r'<div class="pane[^"]*" id="pane-([a-z0-9]+)">(.*?)</div><!-- /pane-\1 -->',
        page, re.S))


def rows_between(body, start, finish):
    """Event rows whose finish time falls in the window, in order."""
    out = []
    for ends, inner in re.findall(r"<tr[^>]*data-ends=\"([^\"]+)\"[^>]*>(.*?)</tr>", body, re.S):
        try:
            when = datetime.fromisoformat(ends)
        except ValueError:
            continue
        if not (start <= when <= finish):
            continue
        ev = re.search(r'class="ev">(.*?)</span>', inner, re.S)
        day = re.search(r'class="d">(.*?)</td>', inner, re.S)
        sub = re.search(r'class="sub">(.*?)</span>', inner, re.S)
        # the date cell is "Sun 4 Oct<small>from 7am</small>" — without a
        # separator those run together as "Sun 4 Octfrom 7am"
        day_txt = ""
        if day:
            day_txt = _txt(re.sub(r"<small>", " \u00b7 ", day.group(1)))
        out.append({
            "when": when,
            "name": _txt(ev.group(1)) if ev else "",
            "day": day_txt,
            "sub": _txt(sub.group(1)) if sub else "",
            "aus": "badge aus" in inner,
        })
    out.sort(key=lambda r: r["when"])
    return out


def lineup(now=None, days=3, page_path=PAGE):
    """What is on between now and the end of the weekend, tab by tab."""
    now = now or datetime.now(SYD)
    # from this morning (so a Friday night event still counts) to end of Sunday
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    finish = (start + timedelta(days=days)).replace(hour=23, minute=59)
    page = open(page_path).read()
    p = panes(page)

    found = []
    for tab, label, limit in WANTED:
        if tab not in p:
            continue
        hits = rows_between(p[tab], start, finish)
        if hits:
            found.append({"tab": tab, "label": label, "events": hits[:limit]})
    return found


def watchlist(page_path=PAGE, limit=3):
    """A couple of series off the Series tab, for the 'have you watched this' line."""
    page = open(page_path).read()
    p = panes(page)
    body = p.get("series", "")
    names = [_txt(n) for n in re.findall(r'class="ev">(.*?)</span>', body, re.S)]
    return [n for n in names if n][:limit]


def sydney_bits(page_path=PAGE, limit=3):
    """What is on around Sydney, for the non fight crowd on the list."""
    page = open(page_path).read()
    p = panes(page)
    body = p.get("sydney", "")
    names = [_txt(n) for n in re.findall(r'class="ev">(.*?)</span>', body, re.S)]
    return [n for n in names if n][:limit]


if __name__ == "__main__":
    now = datetime.now(SYD)
    print(f"Weekend lineup as at {now:%a %d %b %-I:%M%p}\n")
    for block in lineup(now):
        print(f"{block['label']}:")
        for e in block["events"]:
            star = "  (IN AUSTRALIA)" if e["aus"] else ""
            print(f"   {e['day']:<22} {e['name']}{star}")
            if e["sub"]:
                print(f"      {e['sub'][:80]}")
        print()
    print("Series:", watchlist())
    print("Sydney:", sydney_bits())
