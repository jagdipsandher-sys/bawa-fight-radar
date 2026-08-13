#!/usr/bin/env python3
"""
Rebuilds the Man Utd tab from ESPN's football feeds.

The point of this tab for an Australian is the CLOCK, not the fixture: a 3pm
Saturday kick-off at Old Trafford is midnight here. Everything is converted to
Sydney time and the awkward ones are called out.

ESPN's team-schedule endpoint returns nothing useful, so this walks the league
scoreboards a fortnight at a time and keeps the matches United are in. Cup
competitions are included on a best-effort basis — a competition that errors or
has no fixtures is skipped rather than failing the build.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from send_fights import SYD

TEAM = "Manchester United"
WEEKS_AHEAD = 16
PAGE = "index.html"
FEED = "https://site.api.espn.com/apis/site/v2/sports/soccer/{}/scoreboard?dates={}-{}"
COMPS = [
    ("eng.1", "Premier League", "PL"),
    ("eng.fa", "FA Cup", "FA"),
    ("eng.league_cup", "EFL Cup", "EFL"),
    ("uefa.champions", "Champions League", "UCL"),
    ("uefa.europa", "Europa League", "UEL"),
]
WATCH = "https://www.stan.com.au/sport"      # AU rights for the Premier League


def esc(t):
    return html.escape(str(t or ""), quote=True)


def syd(dt):
    return dt.astimezone(SYD)


def fetch(code, label, start):
    end = start + timedelta(days=13)
    url = FEED.format(code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
    except Exception as e:
        print(f"  {code} {start:%d %b}: skipped ({type(e).__name__})")
        return []
    out = []
    for ev in data.get("events", []):
        if TEAM not in ev.get("name", ""):
            continue
        comp = (ev.get("competitions") or [{}])[0]
        teams = {t.get("homeAway"): (t.get("team") or {}).get("displayName", "")
                 for t in comp.get("competitors", [])}
        try:
            when = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        home = teams.get("home", "") == TEAM
        out.append({
            "when": when, "comp": label,
            "home": home,
            "opponent": teams.get("away" if home else "home", "TBC"),
            "venue": (comp.get("venue") or {}).get("fullName", ""),
        })
    return out


def collect():
    now = datetime.now(timezone.utc)
    games, seen = [], set()
    for code, label, _ in COMPS:
        for w in range(0, WEEKS_AHEAD, 2):
            for g in fetch(code, label, now + timedelta(weeks=w)):
                key = g["when"].isoformat()
                if key not in seen and g["when"] > now:
                    seen.add(key)
                    games.append(g)
    games.sort(key=lambda g: g["when"])
    return games


def watchability(g):
    """The honest Australian verdict on the kick-off time."""
    d = syd(g["when"])
    day = d.strftime("%A")
    if 6 <= d.hour < 12:
        return f"{day} morning here — coffee and a replay-free watch", "good"
    if d.hour >= 22 or d.hour < 3:
        return f"Kicks off {d:%-I:%M%p} {day} Sydney time — a proper late one", "late"
    if 3 <= d.hour < 6:
        return f"{d:%-I:%M%p} {day} — alarm-clock territory", "brutal"
    return f"{day} {d:%-I:%M%p} Sydney — a civilised one for once", "good"


BADGE = {"good": '<span class="badge home">Good Time</span>',
         "late": '<span class="badge soon">Late Night</span>',
         "brutal": '<span class="badge ppv">Set An Alarm</span>'}


def cid(g):
    return f"utd{syd(g['when']):%m%d%H%M}"


def ends(g):
    return (syd(g["when"]) + timedelta(hours=2)).isoformat()


def title(g):
    return f"Man Utd v {g['opponent']}" if g["home"] else f"{g['opponent']} v Man Utd"


def row(g):
    verdict, band = watchability(g)
    ha = '<span class="badge home">Home</span>' if g["home"] else '<span class="badge away">Away</span>'
    return f"""      <tr{' class="big"' if band == 'good' else ''} data-sport="utd" data-ends="{ends(g)}" data-card="{cid(g)}">
        <td class="d">{syd(g['when']):%a %-d %b}<small>{syd(g['when']):%-I:%M%p} AEST</small></td>
        <td><span class="sporttag b">{esc(g['comp'][:3].upper())}</span></td>
        <td><span class="ev">{esc(title(g))}</span> {ha} {BADGE[band]}<br><span class="sub">{esc(verdict)} · {esc(g['comp'])}</span></td>
        <td>{esc(g['venue'])}</td>
        <td><a class="mini buy" href="{WATCH}">Watch · Stan Sport</a><button class="mini" onclick="openCard('{cid(g)}')">Details</button><button class="mini" onclick="addCal('{cid(g)}')">+ Cal</button></td>
      </tr>"""


def hero(g, label):
    verdict, band = watchability(g)
    ha = '<span class="badge home">Home</span>' if g["home"] else '<span class="badge away">Away</span>'
    return f"""    <div class="card" data-slot="utd" data-ends="{ends(g)}">
      <div class="sport">{esc(label)} &nbsp;{ha} {BADGE[band]} <span class="badge soon"><span class="cd" data-until="{syd(g['when']):%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big">{esc('Man Utd')} <em>v</em> {esc(g['opponent'])}</div>
        <div class="lil">{esc(g['comp'])} · {esc(g['venue'] or 'venue TBC')}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(title(g))}
          <small>{esc(verdict)}</small>
        </div>
        <div class="when">{syd(g['when']):%a %-d %b} · <span class="t">{syd(g['when']):%-I:%M%p} Sydney</span></div>
        <div class="meta">{esc(g['venue'])} · {esc(g['comp'])} · {syd(g['when']):%-I:%M%p %Z}</div>
        <div class="btns">
          <a class="btn red" href="{WATCH}">Watch · Stan Sport</a>
          <button class="btn ghost" onclick="openCard('{cid(g)}')">Match Details</button>
          <button class="btn ghost" onclick="addCal('{cid(g)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card(g):
    verdict, _ = watchability(g)
    start, end = g["when"], g["when"] + timedelta(hours=2)
    b = ",".join(json.dumps(x) for x in [
        [title(g), g["comp"] + (" · home" if g["home"] else " · away"), 1],
        ["Kick-off", f"{syd(start):%A %-d %B, %-I:%M%p} Sydney time"],
        ["Local kick-off", f"{start:%-I:%M%p} UK"],
        ["Ground", g["venue"] or "TBC"],
        ["The verdict", verdict],
    ])
    return f"""  {cid(g)}: {{
    emoji:"⚽",
    cal:{{s:"{start:%Y-%m-%dT%H:%M:%S}Z",e:"{end:%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(g['venue'] or 'TBC')}}},
    title:{json.dumps(title(g))},
    when:{json.dumps(f"{syd(start):%a %-d %b} · {syd(start):%-I:%M%p} Sydney · {g['comp']}")},
    link:{json.dumps(WATCH)},
    linkLabel:"Watch on Stan Sport ↗",
    secs:[{{h:"The Match",b:[{b}]}}],
    note:"Kick-off times move when games are picked for TV — this follows the live feed, so check back closer to the date."
  }}"""


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    games = collect()
    if not games:
        sys.exit("no Manchester United fixtures returned — leaving the tab alone")

    print(f"{len(games)} upcoming fixtures:")
    for g in games:
        print(f"  {syd(g['when']):%a %d %b %-I:%M%p} {'v' if g['home'] else 'away to'} "
              f"{g['opponent']} ({g['comp']})")

    heroes = [hero(games[0], "Next Match")]
    if len(games) > 1:
        heroes.append(hero(games[1], "And Then"))

    page = open(PAGE).read()
    before = page
    page = splice(page, "UTD-HERO", "\n".join(heroes))
    page = splice(page, "UTD-ROWS", "\n".join(row(g) for g in games))
    page = splice(page, "UTD-CARDS", ",\n".join(card(g) for g in games))
    if page == before:
        print("united tab already current")
        return
    open(PAGE, "w").write(page)
    print(f"rebuilt the Man Utd tab: {len(games)} fixtures")


if __name__ == "__main__":
    main()
