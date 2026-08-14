#!/usr/bin/env python3
"""
Rebuilds the Wolves (Minnesota Timberwolves) tab from ESPN's NBA feed.

Same idea as the Man Utd tab — the point is the CLOCK. NBA tip-offs are US
evening times, which land anywhere from a Sydney lunchtime to a Sydney
sunrise depending on which US time zone the game is in, so everything is
converted to Sydney and the awkward ones are called out.

Only one competition exists here (no cups to juggle like the football tab),
so this queries a week at a time like the Panthers/Raiders builders rather
than the fortnightly multi-competition walk build_united.py does. The NBA
season doesn't start until mid-October, so in the off-season this correctly
returns nothing until the schedule is out — see finals_tail-less handling
in main().
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from send_fights import SYD

TEAM = "Timberwolves"
WEEKS_AHEAD = 16          # off-season now; this needs to reach the October tip-off
PAGE = "index.html"
FEED = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}-{}"
WATCH = "https://kayosports.com.au/"      # AU NBA rights holder


def esc(t):
    return html.escape(str(t or ""), quote=True)


def syd(dt):
    return dt.astimezone(SYD)


def fetch_week(start):
    end = start + timedelta(days=6)
    url = FEED.format(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
    except Exception as e:
        print(f"  week of {start:%d %b}: fetch failed ({type(e).__name__}) — skipped")
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
        logos = {t_.get("homeAway"): ((t_.get("team") or {}).get("logo")
                 or (((t_.get("team") or {}).get("logos") or [{}])[0] or {}).get("href") or "")
                 for t_ in comp.get("competitors", [])}
        home = teams.get("home", "") == TEAM
        out.append({
            "when": when,
            "home": home,
            "opponent": teams.get("away" if home else "home", "TBC"),
            "venue": (comp.get("venue") or {}).get("fullName", ""),
            "logo": logos.get("away" if home else "home", ""),
            "mylogo": logos.get("home" if home else "away", ""),
        })
    return out


def collect():
    now = datetime.now(timezone.utc)
    games, seen = [], set()
    for w in range(WEEKS_AHEAD):
        for g in fetch_week(now + timedelta(weeks=w)):
            key = g["when"].isoformat()
            if key not in seen and g["when"] > now:
                seen.add(key)
                games.append(g)
    games.sort(key=lambda g: g["when"])
    return games


def watchability(g):
    """The honest Australian verdict on the tip-off time."""
    d = syd(g["when"])
    day = d.strftime("%A")
    if 6 <= d.hour < 12:
        return f"{day} morning here — coffee and a replay-free watch", "good"
    if d.hour >= 22 or d.hour < 3:
        return f"Tips off {d:%-I:%M%p} {day} Sydney time — a proper late one", "late"
    if 3 <= d.hour < 6:
        return f"{d:%-I:%M%p} {day} — alarm-clock territory", "brutal"
    return f"{day} {d:%-I:%M%p} Sydney — a civilised one for once", "good"


BADGE = {"good": '<span class="badge home">Good Time</span>',
         "late": '<span class="badge soon">Late Night</span>',
         "brutal": '<span class="badge ppv">Set An Alarm</span>'}


def cid(g):
    return f"wlv{syd(g['when']):%m%d%H%M}"


def ends(g):
    return (syd(g["when"]) + timedelta(hours=3)).isoformat()


def crest(url, name, size=""):
    """Team crest with an initials fallback."""
    if not url:
        return ""
    ini = "".join(w[0] for w in str(name).split()[:2]).upper()
    style = f' style="{size}"' if size else ""
    return f'<img class="crest-ico"{style} src="{esc(url)}" alt="" onerror="imgFail(this,\'{ini}\')">'


def title(g):
    return f"Wolves v {g['opponent']}" if g["home"] else f"{g['opponent']} v Wolves"


def row(g):
    verdict, band = watchability(g)
    ha = '<span class="badge home">Home</span>' if g["home"] else '<span class="badge away">Away</span>'
    return f"""      <tr{' class="big"' if band == 'good' else ''} data-sport="wlv" data-ends="{ends(g)}" data-card="{cid(g)}">
        <td class="d">{syd(g['when']):%a %-d %b}<small>{syd(g['when']):%-I:%M%p} AEST</small></td>
        <td><span class="sporttag b">NBA</span></td>
        <td>{crest(g['logo'], g['opponent'])}<span class="ev">{esc(title(g))}</span> {ha} {BADGE[band]}<br><span class="sub">{esc(verdict)}</span></td>
        <td>{esc(g['venue'])}</td>
        <td><a class="mini buy" href="{WATCH}">Watch · Kayo Sports</a><button class="mini" onclick="openCard('{cid(g)}')">Details</button><button class="mini" onclick="addCal('{cid(g)}')">+ Cal</button></td>
      </tr>"""


def hero(g):
    verdict, band = watchability(g)
    ha = '<span class="badge home">Home</span>' if g["home"] else '<span class="badge away">Away</span>'
    return f"""    <div class="card" data-slot="wlv" data-ends="{ends(g)}">
      <div class="sport">Next Game &nbsp;{ha} {BADGE[band]} <span class="badge soon"><span class="cd" data-until="{syd(g['when']):%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big">{crest(g['mylogo'] if g['home'] else g['logo'], 'x', 'width:34px;height:34px;vertical-align:middle;margin-right:8px')}{esc(g['opponent'] if not g['home'] else 'Wolves')} <em>v</em> {esc('Wolves' if not g['home'] else g['opponent'])}{crest(g['logo'] if g['home'] else g['mylogo'], 'x', 'width:34px;height:34px;vertical-align:middle;margin-left:8px')}</div>
        <div class="lil">{esc(g['venue'] or 'venue TBC')}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(title(g))}
          <small>{esc(verdict)}</small>
        </div>
        <div class="when">{syd(g['when']):%a %-d %b} · <span class="t">{syd(g['when']):%-I:%M%p} Sydney</span></div>
        <div class="meta">{esc(g['venue'])} · {syd(g['when']):%-I:%M%p %Z}</div>
        <div class="btns">
          <a class="btn red" href="{WATCH}">Watch · Kayo Sports</a>
          <button class="btn ghost" onclick="openCard('{cid(g)}')">Game Details</button>
          <button class="btn ghost" onclick="addCal('{cid(g)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card(g):
    verdict, _ = watchability(g)
    start, end = g["when"], g["when"] + timedelta(hours=3)
    b = ",".join(json.dumps(x) for x in [
        [title(g), "home game" if g["home"] else "away game", 1],
        ["Tip-off", f"{syd(start):%A %-d %B, %-I:%M%p} Sydney time"],
        ["Arena", g["venue"] or "TBC"],
        ["The verdict", verdict],
    ])
    return f"""  {cid(g)}: {{
    emoji:"🏀",
    cal:{{s:"{start:%Y-%m-%dT%H:%M:%S}Z",e:"{end:%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(g['venue'] or 'TBC')}}},
    title:{json.dumps(title(g))},
    when:{json.dumps(f"{syd(start):%a %-d %b} · {syd(start):%-I:%M%p} Sydney")},
    link:{json.dumps(WATCH)},
    linkLabel:"Watch on Kayo Sports ↗",
    secs:[{{h:"The Game",b:[{b}]}}],
    note:"Tip-off times move for national TV picks — this follows the live NBA schedule feed, so check back closer to the date."
  }}"""


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    games = collect()
    if not games:
        print("no Timberwolves fixtures returned (off-season, or schedule not out yet) — leaving the tab as it is")
        return

    print(f"{len(games)} upcoming Timberwolves fixtures:")
    for g in games:
        print(f"  {syd(g['when']):%a %d %b %-I:%M%p} {'v' if g['home'] else 'away to'} {g['opponent']}")

    page = open(PAGE).read()
    before = page
    page = splice(page, "WOLVES-HERO", hero(games[0]))
    page = splice(page, "WOLVES-ROWS", "\n".join(row(g) for g in games))
    page = splice(page, "WOLVES-CARDS", ",\n".join(card(g) for g in games))
    if page == before:
        print("wolves tab already current")
        return
    open(PAGE, "w").write(page)
    print(f"rebuilt the Wolves tab: {len(games)} fixtures")


if __name__ == "__main__":
    main()
