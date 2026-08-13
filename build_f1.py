#!/usr/bin/env python3
"""
Rebuilds the F1 tab from ESPN's racing calendar.

Built for someone who doesn't get to watch live: every round, the round number,
and what time the race actually starts in Sydney — because that is the thing you
can't work out from a European schedule without a calculator.

ESPN gives each Grand Prix as one event with its sessions underneath. It does not
label which session is which, so the race is taken as the last session of the
weekend, which is true for every round including sprints.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from send_fights import SYD

PAGE = "index.html"
FEED = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates={}"
WATCH = "https://www.kayosports.com.au/"


def esc(t):
    return html.escape(str(t or ""), quote=True)


def syd(dt):
    return dt.astimezone(SYD)


def parse(d):
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def collect():
    year = datetime.now(timezone.utc).year
    try:
        with urllib.request.urlopen(FEED.format(year), timeout=30) as r:
            data = json.load(r)
    except Exception as e:
        sys.exit(f"F1 calendar fetch failed ({type(e).__name__}) — leaving the tab alone")

    now = datetime.now(timezone.utc)
    rounds = []
    for i, ev in enumerate(data.get("events", []), start=1):
        status = ((ev.get("status") or {}).get("type") or {}).get("name", "")
        sessions = [s for s in (parse(c.get("date")) for c in ev.get("competitions", [])) if s]
        sessions.sort()
        race = sessions[-1] if sessions else parse(ev.get("endDate")) or parse(ev.get("date"))
        if not race:
            continue
        rounds.append({
            "round": i, "name": ev.get("name", "Grand Prix"),
            "short": ev.get("shortName", ""), "race": race,
            "sessions": sessions, "status": status,
            "done": race < now or status in ("STATUS_FINAL", "STATUS_CANCELED"),
            "canceled": status == "STATUS_CANCELED",
        })
    return rounds


def gp_name(r):
    """Strip the sponsor off the front — 'Heineken Dutch Grand Prix' -> 'Dutch Grand Prix'."""
    return re.sub(r"^(.*?)\b(\w+ Grand Prix)$", r"\2", r["name"]).strip() or r["name"]


def cid(r):
    return f"f1r{r['round']:02d}"


def ends(r):
    return (syd(r["race"]) + timedelta(hours=3)).isoformat()


def slot(r):
    """When a Sydney viewer actually has to be awake."""
    d = syd(r["race"])
    if 6 <= d.hour < 13:
        return "Sunday morning here — the good ones", "good"
    if d.hour >= 22 or d.hour < 4:
        return "Middle of the night in Sydney", "brutal"
    if 13 <= d.hour < 20:
        return "Afternoon or evening in Sydney — easy watching", "good"
    return "Early hours here", "late"


BADGE = {"good": '<span class="badge home">Good Time</span>',
         "late": '<span class="badge soon">Early Start</span>',
         "brutal": '<span class="badge ppv">Set An Alarm</span>'}


def session_list(r):
    """Practice/qualifying/race, labelled by position in the weekend."""
    names = ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"]
    n = len(r["sessions"])
    labels = names[-n:] if n <= len(names) else ["Session"] * (n - 5) + names
    return list(zip(labels, r["sessions"]))


def row(r):
    verdict, band = slot(r)
    sess = session_list(r)
    quali = next((t for lab, t in sess if lab == "Qualifying"), None)
    return f"""      <tr{' class="big"' if band == 'good' else ''} data-sport="f1" data-ends="{ends(r)}" data-card="{cid(r)}">
        <td class="d">{syd(r['race']):%a %-d %b}<small>race {syd(r['race']):%-I:%M%p}</small></td>
        <td><span class="sporttag m">R{r['round']}</span></td>
        <td><span class="ev">{esc(gp_name(r))}</span> {BADGE[band]}<br><span class="sub">{esc(verdict)}{' · qualifying ' + syd(quali).strftime('%a %-I:%M%p') if quali else ''}</span></td>
        <td>Round {r['round']}</td>
        <td><a class="mini buy" href="{WATCH}">Watch · Kayo</a><button class="mini" onclick="openCard('{cid(r)}')">Sessions</button><button class="mini" onclick="addCal('{cid(r)}')">+ Cal</button></td>
      </tr>"""


def hero(r, label):
    verdict, band = slot(r)
    sess = session_list(r)
    lis = "".join(f"<li><b>{lab}</b> — {syd(t):%a %-d %b, %-I:%M%p}</li>" for lab, t in sess)
    return f"""    <div class="card" data-slot="f1" data-ends="{ends(r)}">
      <div class="sport">{esc(label)} &nbsp;<span class="badge fn">Round {r['round']}</span> {BADGE[band]} <span class="badge soon"><span class="cd" data-until="{syd(r['race']):%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big">{esc(gp_name(r).replace(' Grand Prix', ''))} <em>GP</em></div>
        <div class="lil">Round {r['round']} · Race {syd(r['race']):%a %-d %b}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(gp_name(r))}
          <small>{esc(verdict)} — all times below are Sydney</small>
        </div>
        <div class="when">Race · <span class="t">{syd(r['race']):%a %-d %b, %-I:%M%p} AEST</span></div>
        <div class="meta">Full weekend, converted from the circuit's local time</div>
        <ul class="mc">{lis}</ul>
        <div class="btns">
          <a class="btn red" href="{WATCH}">Watch · Kayo</a>
          <button class="btn ghost" onclick="openCard('{cid(r)}')">All Sessions</button>
          <button class="btn ghost" onclick="addCal('{cid(r)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card(r):
    verdict, _ = slot(r)
    start = r["race"]
    end = start + timedelta(hours=2)
    b = ",".join(json.dumps([lab, f"{syd(t):%a %-d %b, %-I:%M%p} Sydney", 1 if lab == "Race" else 0])
                 for lab, t in session_list(r))
    return f"""  {cid(r)}: {{
    emoji:"🏎️",
    cal:{{s:"{start:%Y-%m-%dT%H:%M:%S}Z",e:"{end:%Y-%m-%dT%H:%M:%S}Z",loc:"Watch on Kayo"}},
    title:{json.dumps(f"Round {r['round']} · {gp_name(r)}")},
    when:{json.dumps(f"Race {syd(start):%a %-d %b, %-I:%M%p} Sydney")},
    link:{json.dumps(WATCH)},
    linkLabel:"Watch on Kayo ↗",
    secs:[{{h:"The Weekend, In Sydney Time",b:[{b}]}}],
    note:{json.dumps(verdict + ". Session times occasionally shift; this follows the live calendar.")}
  }}"""


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    rounds = collect()
    upcoming = [r for r in rounds if not r["done"]]
    if not upcoming:
        print(f"season finished — {len(rounds)} rounds ran, nothing left to show")
        return

    print(f"{len(rounds)} rounds in the calendar, {len(upcoming)} still to come:")
    for r in upcoming[:6]:
        print(f"  R{r['round']:2d} {syd(r['race']):%a %d %b %-I:%M%p}  {gp_name(r)}")

    heroes = [hero(upcoming[0], "Next Race Weekend")]
    if len(upcoming) > 1:
        heroes.append(hero(upcoming[1], "The Round After"))

    page = open(PAGE).read()
    before = page
    page = splice(page, "F1-HERO", "\n".join(heroes))
    page = splice(page, "F1-ROWS", "\n".join(row(r) for r in upcoming))
    page = splice(page, "F1-CARDS", ",\n".join(card(r) for r in upcoming))
    if page == before:
        print("f1 tab already current")
        return
    open(PAGE, "w").write(page)
    print(f"rebuilt the F1 tab: {len(upcoming)} rounds ahead")


if __name__ == "__main__":
    main()
