#!/usr/bin/env python3
"""
Rebuilds the Panthers tab of index.html from ESPN's NRL fixture feed, so the
draw maintains itself instead of being hand-typed once and left to rot.

The feed is queried a week at a time: a single-round query carries that round's
number at the top level, which is where the R24 / R25 tags come from. Anything
past round 27 is the finals series and is labelled as such.

Only the blocks between the BUILD:NRL- markers are touched. The season summary
card is left alone — the page computes its counters in the browser.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from send_fights import SYD

TEAM = "Panthers"
WEEKS_AHEAD = 14          # covers the run home plus the whole finals series
PAGE = "index.html"
FEED = "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/scoreboard?dates={}-{}"
TICKETS_HOME = "https://www.ticketmaster.com.au/penrith-panthers-tickets/artist/1297218"
TICKETS_AWAY = "https://premier.ticketek.com.au/shows/show.aspx?sh=NRLPREM26"
LAST_REGULAR_ROUND = 27


def esc(t):
    return html.escape(str(t or ""), quote=True)


def fetch_week(start):
    end = start + timedelta(days=6)
    url = FEED.format(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
    except Exception as e:                       # one bad week must not kill the build
        print(f"  week of {start:%d %b}: fetch failed ({type(e).__name__}) — skipped")
        return []

    rnd = (data.get("week") or {}).get("number")
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
        home_is_us = teams.get("home", "") == TEAM
        out.append({
            "when": when,
            "round": rnd,
            "home": home_is_us,
            "opponent": teams.get("away" if home_is_us else "home", "TBC"),
            "venue": (comp.get("venue") or {}).get("fullName", ""),
            "name": ev.get("name", ""),
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


def syd(dt):
    return dt.astimezone(SYD)


def tag(g):
    r = g["round"]
    if r and r <= LAST_REGULAR_ROUND:
        return f'<span class="sporttag n">R{r}</span>'
    return '<span class="sporttag f">Finals</span>'


def cid(g):
    return f"nrl{syd(g['when']):%m%d}"


def ends(g):
    return (syd(g["when"]) + timedelta(hours=2, minutes=10)).isoformat()


def kick(g):
    return syd(g["when"]).strftime("%-I:%M%p").lower()


def title(g):
    return f"Panthers v {g['opponent']}" if g["home"] else f"{g['opponent']} v Panthers"


def note(g):
    d = syd(g["when"])
    if g["home"] and d.weekday() == 6 and d.hour < 18:
        return "Sunday afternoon at home — daylight kick-off, done at a reasonable hour"
    if d.hour >= 19:
        return "Late finish — a school-night call for the young fella"
    if not g["home"]:
        return "Away game — one for the telly unless you fancy the trip"
    return "Home game at CommBank — ticket includes public transport on match day"


def row(g):
    home = g["home"]
    badge = '<span class="badge home">Home</span>' if home else '<span class="badge away">Away</span>'
    finals = not (g["round"] and g["round"] <= LAST_REGULAR_ROUND)
    extra = ' <span class="badge ppv">Finals</span>' if finals else ""
    url = TICKETS_HOME if home else TICKETS_AWAY
    label = "Buy · Ticketmaster" if home else "Tickets · Ticketek"
    return f"""      <tr{' class="big"' if home else ''} data-sport="nrl" data-ends="{ends(g)}" data-card="{cid(g)}">
        <td class="d">{syd(g['when']):%a %-d %b}<small>{kick(g)}</small></td>
        <td>{tag(g)}</td>
        <td><span class="ev">{esc(title(g))}</span> {badge}{extra}<br><span class="sub">{esc(note(g))}</span></td>
        <td>{esc(g['venue'])}</td>
        <td><a class="mini buy" href="{url}">{label}</a><button class="mini" onclick="openCard('{cid(g)}')">Details</button><button class="mini" onclick="addCal('{cid(g)}')">+ Cal</button></td>
      </tr>"""


def hero(g):
    home = g["home"]
    badge = '<span class="badge home">Home</span>' if home else '<span class="badge away">Away</span>'
    rnd = f"NRL Round {g['round']}" if g["round"] and g["round"] <= LAST_REGULAR_ROUND else "NRL Finals"
    url = TICKETS_HOME if home else TICKETS_AWAY
    return f"""    <div class="card" data-slot="nrl" data-ends="{ends(g)}">
      <div class="sport">{rnd} &nbsp;{badge} <span class="badge soon"><span class="cd" data-until="{syd(g['when']):%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big">Panthers <em>v</em> {esc(g['opponent'])}</div>
        <div class="lil">{esc(g['venue'])}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(title(g))}
          <small>{esc(note(g))}</small>
        </div>
        <div class="when">{syd(g['when']):%a %-d %b} · <span class="t">Kick-off {kick(g)} AEST</span></div>
        <div class="meta">{esc(g['venue'])}{' · gates usually open two hours before kick-off' if home else ''}</div>
        <ul class="mc">
          <li>{'Every pre-purchased ticket includes free travel on Sydney trains, buses, light rail and ferries on match day.' if home else 'Away from home — check the venue’s own ticketing before planning a trip.'}</li>
        </ul>
        <div class="btns">
          <a class="btn red" href="{url}">Tickets</a>
          <button class="btn ghost" onclick="openCard('{cid(g)}')">Match Details</button>
          <button class="btn ghost" onclick="addCal('{cid(g)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card(g):
    start = g["when"]
    end = start + timedelta(hours=2)
    rnd = f"Round {g['round']}" if g["round"] and g["round"] <= LAST_REGULAR_ROUND else "Finals"
    when = f"{syd(start):%a %-d %b} · Kick-off {kick(g)} AEST · {g['venue']}"
    bouts = [
        [title(g), f"{rnd} · {'home' if g['home'] else 'away'} game", 1],
        ["Venue", g["venue"] or "TBC"],
        ["Tickets", "Ticketmaster — Penrith sell all home games there" if g["home"]
                    else "Ticketek — the home club sells this one"],
    ]
    if g["home"]:
        bouts.append(["Getting there", "Ticket includes trains, buses, light rail and ferries on match day"])
    b = ",".join(json.dumps(x) for x in bouts)
    return f"""  {cid(g)}: {{
    emoji:"🐾",
    cal:{{s:"{start:%Y-%m-%dT%H:%M:%S}Z",e:"{end:%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(g['venue'] or 'TBC')}}},
    title:{json.dumps(rnd + ' · ' + title(g))},
    when:{json.dumps(when)},
    link:{json.dumps(TICKETS_HOME if g['home'] else TICKETS_AWAY)},
    secs:[{{h:"The Match",b:[{b}]}}],
    note:"Fixture pulled from the live NRL feed — kick-off times can move, finals venues are set after the last round."
  }}"""


def finals_tail(games):
    """The finals draw is only published once the ladder locks, so the feed has
    nothing there yet. Keep the known end-of-season markers visible until real
    fixtures arrive to replace them."""
    if any(g["round"] and g["round"] > LAST_REGULAR_ROUND for g in games):
        return ""                                   # feed has the real finals now
    return """
      <tr data-sport="nrl" data-ends="2026-09-28T23:59:00+10:00">
        <td class="d">Mid-Sep<small>4-week series</small></td>
        <td><span class="sporttag f">Finals</span></td>
        <td><span class="ev">NRL Finals Series</span> <span class="badge tbc">Draw Set After Round 27</span><br><span class="sub">Top 4 get a qualifying final and a second life; 5th–8th are sudden death. Fixtures appear here automatically once the NRL publishes them</span></td>
        <td>TBC — Sydney venues likely</td>
        <td><a class="mini buy" href="https://www.nrl.com/draw/">NRL Draw</a></td>
      </tr>
      <tr class="big" data-sport="nrl" data-ends="2026-10-04T23:00:00+11:00">
        <td class="d">Sun 4 Oct<small>grand final</small></td>
        <td><span class="sporttag f">GF</span></td>
        <td><span class="ev">NRL Grand Final</span> <span class="badge ppv">Accor Stadium</span><br><span class="sub">The last Sunday of the season. Ballot and public sale open once the finalists are known</span></td>
        <td>Accor Stadium, Sydney Olympic Park</td>
        <td><a class="mini buy" href="https://www.accorstadium.com.au/events/n2026_nrl_nrlw_grand_finals">Grand Final Info</a></td>
      </tr>"""


# The hand-written season card has "Finals Explained" and "+ GF Calendar"
# buttons. Their cards live in this generated block, so they must be emitted
# every run or those buttons quietly do nothing.
STATIC_CARDS = """  panFinals: {
    emoji:"🏆",
    title:"NRL Finals — How It Works",
    when:"Four weeks from mid-September · Grand Final Sun 4 Oct, Accor Stadium",
    link:"https://www.nrl.com/draw/",
    linkLabel:"NRL Draw & Finals ↗",
    secs:[
      {h:"The Format",b:[
        ["Week 1 — Qualifying Finals","1st v 4th and 2nd v 3rd. Winners go straight to a Preliminary Final; losers get a second life.",1],
        ["Week 1 — Elimination Finals","5th v 8th and 6th v 7th. Lose and you're out."],
        ["Week 2 — Semi Finals","Qualifying losers v Elimination winners. Sudden death."],
        ["Week 3 — Preliminary Finals","Winners go to the Grand Final."],
        ["Week 4 — Grand Final","Sun 4 Oct, Accor Stadium",1]
      ]},
      {h:"What It Means For Penrith",b:[
        ["A top-four finish means a second chance","Lose a qualifying final and you still get another week",1],
        ["Fixtures appear on this tab automatically","They are pulled from the NRL feed as soon as the draw is published"],
        ["Tickets go on sale within days of each draw","Worth watching nrl.com the Monday after the last round"]
      ]}
    ],
    note:"Nothing about the finals is bookable until the ladder locks in."
  },
  panGF: {
    emoji:"🏆",
    cal:{s:"2026-10-04T08:30:00Z",e:"2026-10-04T10:30:00Z",loc:"Accor Stadium, Sydney Olympic Park"},
    title:"NRL Grand Final 2026",
    when:"Sun 4 Oct · Accor Stadium, Sydney Olympic Park · kick-off TBC",
    link:"https://www.accorstadium.com.au/events/n2026_nrl_nrlw_grand_finals",
    linkLabel:"Accor Stadium — Grand Final ↗",
    secs:[
      {h:"The Day",b:[
        ["NRL and NRLW Grand Finals","Both played at Accor Stadium on the same day",1],
        ["Kick-off time not yet confirmed","Traditionally early evening — the calendar entry uses 7:30pm as a placeholder"]
      ]},
      {h:"Tickets",b:[
        ["Members' ballots first","Club members of the qualifying teams get first access"],
        ["General sale after the Preliminary Finals","Only once the two finalists are known"],
        ["Accor Stadium is on the Olympic Park line","Same station as Monster Jam"]
      ]}
    ],
    note:"Placeholder entry — the date is confirmed, kick-off and pricing are not."
  }"""


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    games = collect()
    if not games:
        sys.exit("no Panthers fixtures returned — leaving the tab as it is")

    print(f"found {len(games)} upcoming Panthers fixtures:")
    for g in games:
        print(f"  R{g['round']} {syd(g['when']):%a %d %b %-I:%M%p} "
              f"{'v' if g['home'] else 'away to'} {g['opponent']} @ {g['venue']}")

    page = open(PAGE).read()
    before = page
    page = splice(page, "NRL-HERO", hero(games[0]))
    page = splice(page, "NRL-ROWS", "\n".join(row(g) for g in games) + finals_tail(games))
    page = splice(page, "NRL-CARDS", ",\n".join([card(g) for g in games] + [STATIC_CARDS]))

    if page == before:
        print("panthers tab already current")
        return
    with open(PAGE, "w") as f:
        f.write(page)
    print(f"rebuilt the Panthers tab: {len(games)} fixtures")


if __name__ == "__main__":
    main()
