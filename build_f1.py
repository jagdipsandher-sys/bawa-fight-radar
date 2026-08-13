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


# Host nation per Grand Prix. Emoji rather than images so they survive any
# host, and keyed on the country adjective in the race name.
FLAGS = {
    "australian": "\U0001F1E6\U0001F1FA", "chinese": "\U0001F1E8\U0001F1F3",
    "japanese": "\U0001F1EF\U0001F1F5", "bahrain": "\U0001F1E7\U0001F1ED",
    "saudi arabian": "\U0001F1F8\U0001F1E6", "miami": "\U0001F1FA\U0001F1F8",
    "emilia romagna": "\U0001F1EE\U0001F1F9", "monaco": "\U0001F1F2\U0001F1E8",
    "spanish": "\U0001F1EA\U0001F1F8", "madrid": "\U0001F1EA\U0001F1F8",
    "canadian": "\U0001F1E8\U0001F1E6", "austrian": "\U0001F1E6\U0001F1F9",
    "british": "\U0001F1EC\U0001F1E7", "great britain": "\U0001F1EC\U0001F1E7",
    "hungarian": "\U0001F1ED\U0001F1FA", "belgian": "\U0001F1E7\U0001F1EA",
    "dutch": "\U0001F1F3\U0001F1F1", "italian": "\U0001F1EE\U0001F1F9",
    "azerbaijan": "\U0001F1E6\U0001F1FF", "singapore": "\U0001F1F8\U0001F1EC",
    "united states": "\U0001F1FA\U0001F1F8", "mexico city": "\U0001F1F2\U0001F1FD",
    "mexican": "\U0001F1F2\U0001F1FD", "sao paulo": "\U0001F1E7\U0001F1F7",
    "s\u00e3o paulo": "\U0001F1E7\U0001F1F7", "brazilian": "\U0001F1E7\U0001F1F7",
    "las vegas": "\U0001F1FA\U0001F1F8", "qatar": "\U0001F1F6\U0001F1E6",
    "abu dhabi": "\U0001F1E6\U0001F1EA", "malaysia": "\U0001F1F2\U0001F1FE",
    "portuguese": "\U0001F1F5\U0001F1F9", "french": "\U0001F1EB\U0001F1F7",
    "german": "\U0001F1E9\U0001F1EA", "korean": "\U0001F1F0\U0001F1F7",
}


def flag(r):
    """Flag of the host nation. A relocated race ('... in Malaysia') is hosted
    where it is actually run, not where the name says."""
    low = r["name"].lower()
    tail = re.search(r"\bin ([a-z\u00e0-\u00ff ]+)$", low)
    if tail:
        for key, f in FLAGS.items():
            if key in tail.group(1):
                return f
    for key in sorted(FLAGS, key=len, reverse=True):
        if key in low:
            return FLAGS[key]
    return ""


TWO_WORD_GP = ("Saudi Arabian", "United States", "Abu Dhabi", "Las Vegas",
               "Mexico City", "Emilia Romagna", "Sao Paulo", "S\u00e3o Paulo",
               "Great Britain", "Great Britain")


def gp_name(r):
    """Drop the title sponsor: 'Heineken Dutch Grand Prix' -> 'Dutch Grand Prix'.

    Country names are one word except for a known handful, so the sponsor is
    everything before that. Anything unexpected is left alone rather than
    mangled — a wordy name beats a wrong one.
    """
    name = r["name"]
    i = name.find("Grand Prix")
    if i <= 0:
        return name
    before, after = name[:i].strip(), name[i:].strip()
    for two in TWO_WORD_GP:
        if before.endswith(two):
            return f"{two} {after}"
    words = before.split()
    return f"{words[-1]} {after}" if words else name


def cid(r):
    return f"f1r{r['round']:02d}"


def ends(r):
    return (syd(r["race"]) + timedelta(hours=3)).isoformat()


def slot(r):
    """When a Sydney viewer actually has to be awake.

    Staying up late and setting a 3am alarm are very different asks, so they
    get different labels.
    """
    h = syd(r["race"]).hour
    if 6 <= h < 13:
        return "Morning here — the good ones", "good"
    if 13 <= h < 20:
        return "Afternoon or evening in Sydney — easy watching", "good"
    if 20 <= h < 24:
        return "Late night in Sydney, but you can stay up for it", "late"
    return "Small hours in Sydney — set an alarm or watch the replay", "brutal"


BADGE = {"good": '<span class="badge home">Good Time</span>',
         "late": '<span class="badge soon">Late Night</span>',
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
        <td><span class="flag" style="margin-right:6px">{flag(r)}</span><span class="ev">{esc(gp_name(r))}</span> {BADGE[band]}<br><span class="sub">{esc(verdict)}{' · qualifying ' + syd(quali).strftime('%a %-I:%M%p') if quali else ''}</span></td>
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
        <div class="big"><span style="font-size:2.2rem;vertical-align:middle">{flag(r)}</span> {esc(gp_name(r).replace(' Grand Prix', ''))} <em>GP</em></div>
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
    title:{json.dumps((flag(r) + " " if flag(r) else "") + f"Round {r['round']} · {gp_name(r)}")},
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

    # one hero only — the championship panel takes the left half of the grid
    heroes = [hero(upcoming[0], "Next Race Weekend")]

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
