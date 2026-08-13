#!/usr/bin/env python3
"""
Rebuilds the MotoGP tab.

ESPN does not carry MotoGP — every racing endpoint for it returns 403 — so this
uses the official motogp.com feed instead. That means a different shape to the
other builders, and field names that are not guaranteed, so everything is read
defensively: anything missing degrades to a gap, and a feed that has changed
shape entirely stops the build rather than writing a broken tab.

Race day is the last day of the event window, which is the Sunday of a normal
grand prix weekend.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from send_fights import SYD

PAGE = "index.html"
API = "https://api.motogp.pulselive.com/motogp/v1"
UA = {"User-Agent": "Mozilla/5.0 (compatible; bawa-radar/1.0)", "Accept": "application/json"}
WATCH = "https://www.foxsports.com.au/motorsport/motogp"
SRC = "https://www.motogp.com/en/calendar"

# ISO country code -> flag emoji, built from the code itself.
def iso_flag(code):
    code = (code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


NAME_FLAG = {
    "australia": "AU", "austria": "AT", "argentina": "AR", "catalunya": "ES", "spain": "ES",
    "france": "FR", "italy": "IT", "japan": "JP", "malaysia": "MY", "netherlands": "NL",
    "portugal": "PT", "qatar": "QA", "thailand": "TH", "united states": "US", "america": "US",
    "great britain": "GB", "united kingdom": "GB", "germany": "DE", "hungary": "HU",
    "czechia": "CZ", "czech republic": "CZ", "indonesia": "ID", "india": "IN", "brazil": "BR",
    "san marino": "SM", "aragon": "ES", "valencia": "ES", "emilia romagna": "IT",
}


def esc(t):
    return html.escape(str(t or ""), quote=True)


def syd(dt):
    return dt.astimezone(SYD)


def day(r, which="race"):
    """The event's own calendar day — never re-zoned when it came date-only."""
    d = r[which]
    return d if r["date_only"] else syd(d)


def text_of(v, *keys):
    """A field that is sometimes a string and sometimes an object."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in keys:
            if v.get(k):
                return str(v[k])
    return ""


def parse(d):
    """Returns (datetime, date_only).

    The feed sends plain calendar dates for the event window. Treating those as
    UTC midnight and converting to Sydney moves every Sunday race to Monday, so
    a date-only value is anchored to midday in SYDNEY and flagged, and the day
    is then printed exactly as the calendar says it.
    """
    if not d:
        return None, False
    raw = str(d)
    if "T" not in raw and len(raw) >= 10:
        try:
            y, m, dd = (int(x) for x in raw[:10].split("-"))
            return datetime(y, m, dd, 12, 0, tzinfo=SYD), True
        except ValueError:
            return None, False
    s2 = raw.replace("Z", "+00:00")
    for cut in (s2, s2[:19]):
        try:
            dt = datetime.fromisoformat(cut)
            return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)), False
        except ValueError:
            continue
    return None, False


def collect():
    year = datetime.now(timezone.utc).year
    try:
        req = urllib.request.Request(f"{API}/events?seasonYear={year}", headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            events = json.load(r)
    except Exception as e:
        sys.exit(f"MotoGP calendar fetch failed ({type(e).__name__}) — leaving the tab alone")

    if not isinstance(events, list) or not events:
        sys.exit("MotoGP feed returned nothing usable — leaving the tab alone")

    print(f"  feed returned {len(events)} entries; fields on the first: {sorted(events[0])[:14]}")

    now = datetime.now(timezone.utc)
    out, rnd = [], 0
    for ev in events:
        kind = str(ev.get("kind") or ev.get("type") or "").upper()
        if "TEST" in kind or ev.get("test") is True:
            continue                                    # pre-season tests are not rounds
        start, only_s = parse(ev.get("date_start") or ev.get("dateStart") or ev.get("date"))
        end, only_e = parse(ev.get("date_end") or ev.get("dateEnd"))
        if not end:
            end, only_e = start, only_s
        if not start:
            continue
        rnd += 1                                        # round number = order in the season
        country = text_of(ev.get("country"), "iso", "name", "code")
        flag = iso_flag(country) or iso_flag(NAME_FLAG.get(country.lower(), ""))
        name = (ev.get("sponsored_name") or ev.get("name")
                or ev.get("short_name") or f"Round {rnd}")
        if not flag:                                    # fall back to the name for the flag
            low = str(name).lower()
            for word, iso in NAME_FLAG.items():
                if word in low:
                    flag = iso_flag(iso)
                    break
        # Race day is the SUNDAY of the weekend, not the last day of the window:
        # several European rounds run an official test on the Monday, so the
        # feed's end date is a day late for them.
        race, only_r = end, only_e
        if start and end and end > start:
            span = (end.date() - start.date()).days
            for back in range(span + 1):
                cand = end - timedelta(days=back)
                if cand.weekday() == 6:
                    race, only_r = cand, only_e
                    break
        out.append({
            "round": rnd, "name": str(name), "flag": flag,
            "circuit": text_of(ev.get("circuit"), "name", "shortname"),
            "start": start, "race": race or end or start, "date_only": only_r,
            "done": (race or end or start) < now,
        })
    if not out:
        sys.exit("no MotoGP rounds found in the feed — leaving the tab alone")
    return out


SPONSORS = ("motul", "michelin", "red bull", "monster energy", "pertamina", "liqui moly",
            "gryfyn", "animoca", "bmw m", "qatar airways", "estrella galicia", "tissot",
            "motogp", "grande premio", "gran premio")


def clean_name(r):
    """Strip the title sponsor and tame the feed's block capitals."""
    n = re.sub(r"[\u00ae\u2122]", "", str(r["name"])).strip()
    low = n.lower()
    for sp in sorted(SPONSORS, key=len, reverse=True):
        if low.startswith(sp):
            n = n[len(sp):].strip()
            break
    if n.isupper():                      # the feed shouts; the page has its own caps
        n = " ".join(w.capitalize() for w in n.split())
        n = re.sub(r"\b(Of|And|The|De|Del|Du|Di|La|Le)\b",
                   lambda mm: mm.group(1).lower(), n)
    return n or str(r["name"])


def cid(r):
    return f"mgp{r['round']:02d}"


def ends(r):
    d = r["race"] if r["date_only"] else syd(r["race"])
    return (d.replace(hour=23, minute=59) if r["date_only"] else d + timedelta(hours=6)).isoformat()


def slot(r):
    h = day(r).hour
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


def weekend(r):
    a, b = day(r, "start"), day(r, "race")
    return f"{a:%a %-d}–{b:%a %-d %b}" if a.date() != b.date() else f"{b:%a %-d %b}"


def row(r):
    verdict, band = slot(r)
    return f"""      <tr{' class="big"' if band == 'good' else ''} data-sport="motogp" data-ends="{ends(r)}" data-card="{cid(r)}">
        <td class="d">{day(r):%a %-d %b}<small>{weekend(r)}</small></td>
        <td><span class="sporttag m">R{r['round']}</span></td>
        <td><span class="flag" style="margin-right:6px">{r['flag']}</span><span class="ev">{esc(clean_name(r))}</span> {BADGE[band]}<br><span class="sub">{esc(verdict)}</span></td>
        <td>{esc(r['circuit'])}</td>
        <td><a class="mini buy" href="{WATCH}">Watch</a><button class="mini" onclick="openCard('{cid(r)}')">Details</button><button class="mini" onclick="addCal('{cid(r)}')">+ Cal</button></td>
      </tr>"""


def hero(r, label):
    verdict, band = slot(r)
    return f"""    <div class="card" data-slot="motogp" data-ends="{ends(r)}">
      <div class="sport">{esc(label)} &nbsp;<span class="badge fn">Round {r['round']}</span> {BADGE[band]} <span class="badge soon"><span class="cd" data-until="{day(r):%Y-%m-%d}"></span></span></div>
      <div class="crest dark">
        <div class="big"><span style="font-size:2.2rem;vertical-align:middle">{r['flag']}</span> {esc(clean_name(r).replace(' Grand Prix', ''))} <em>GP</em></div>
        <div class="lil">Round {r['round']} · {esc(r['circuit'] or 'circuit TBC')}</div>
      </div>
      <div class="inner">
        <div class="fight hd">{esc(clean_name(r))}
          <small>{esc(verdict)}</small>
        </div>
        <div class="when">Race day · <span class="t">{day(r):%a %-d %b}</span></div>
        <div class="meta">Weekend runs {weekend(r)}{' · ' + esc(r['circuit']) if r['circuit'] else ''}</div>
        <div class="btns">
          <a class="btn red" href="{WATCH}">Where To Watch</a>
          <button class="btn ghost" onclick="openCard('{cid(r)}')">Round Details</button>
          <button class="btn ghost" onclick="addCal('{cid(r)}')">+ Calendar</button>
        </div>
      </div>
    </div>"""


def card(r):
    verdict, _ = slot(r)
    start = r["race"].replace(hour=r["race"].hour, minute=0)
    end = start + timedelta(hours=3)
    b = ",".join(json.dumps(x) for x in [
        [clean_name(r), f"Round {r['round']}", 1],
        ["Race day", f"{day(r):%A %-d %B}"],
        ["Weekend", weekend(r)],
        ["Circuit", r["circuit"] or "TBC"],
        ["The verdict", verdict],
    ])
    return f"""  {cid(r)}: {{
    emoji:"\\U0001F3CD\\uFE0F",
    cal:{{s:"{start:%Y-%m-%dT%H:%M:%S}Z",e:"{end:%Y-%m-%dT%H:%M:%S}Z",loc:{json.dumps(r['circuit'] or 'TBC')}}},
    title:{json.dumps((r['flag'] + ' ' if r['flag'] else '') + f"Round {r['round']} · {clean_name(r)}")},
    when:{json.dumps(f"Race day {syd(r['race']):%a %-d %b} Sydney · weekend {weekend(r)}")},
    link:{json.dumps(SRC)},
    linkLabel:"Official MotoGP calendar \\u2197",
    secs:[{{h:"The Round",b:[{b}]}}],
    note:"Session-by-session times are not in this feed yet — the race day is right, the practice and qualifying times are not shown."
  }}"""


def standings():
    """Riders' championship, if the feed will give it up. Optional."""
    try:
        def get(u):
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
                return json.load(r)
        year = datetime.now(timezone.utc).year
        seasons = get(f"{API}/results/seasons")
        su = next((s["id"] for s in seasons if s.get("year") == year), None)
        cats = get(f"{API}/results/categories?seasonUuid={su}")
        mid = next((c["id"] for c in cats if "motogp" in str(c.get("name", "")).lower()), None)
        cl = get(f"{API}/results/standings?seasonUuid={su}&categoryUuid={mid}").get("classification", [])
    except Exception as e:
        print(f"  standings unavailable ({type(e).__name__}) — panel omitted")
        return None
    rows = []
    for r in cl:
        rider = r.get("rider") or {}
        rows.append({
            "pos": r.get("position") or len(rows) + 1,
            "name": (rider.get("full_name") or rider.get("name")
                     or " ".join(filter(None, [rider.get("first_name"), rider.get("last_name")]))),
            "pts": r.get("points"),
            "team": text_of(r.get("team"), "name"),
        })
    return [r for r in rows if r["name"]] or None


def ladder(rows, limit=None):
    body = ""
    for r in (rows[:limit] if limit else rows):
        cls = ' class="lead"' if str(r["pos"]) == "1" else ""
        body += (f'<tr{cls}><td class="pos">{esc(r["pos"])}</td>'
                 f'<td class="who">{esc(r["name"])}</td>'
                 f'<td class="pts">{esc(r["pts"] if r["pts"] is not None else "—")}</td></tr>')
    return ('<table class="ladder"><thead><tr><th></th><th>Rider</th>'
            f'<th class="pts">Pts</th></tr></thead><tbody>{body}</tbody></table>')


def splice(page, marker, block):
    pat = re.compile(rf"(<!--BUILD:{marker}-->|/\*BUILD:{marker}\*/).*?"
                     rf"(<!--/BUILD:{marker}-->|/\*/BUILD:{marker}\*/)", re.S)
    if not pat.search(page):
        sys.exit(f"marker {marker} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1)


def main():
    rounds = collect()
    upcoming = [r for r in rounds if not r["done"]]
    print(f"  {len(rounds)} rounds, {len(upcoming)} still to come")
    for r in upcoming[:5]:
        print(f"    R{r['round']:2d} {day(r):%a %d %b}  {r['flag']} {clean_name(r)}")
    if not upcoming:
        print("season finished — nothing to show")
        return

    riders = standings()
    if riders:
        print(f"  standings: {len(riders)} riders, leader {riders[0]['name']} on {riders[0]['pts']}")
        panel = f"""    <div class="card" data-slot="table">
      <div class="sport">MotoGP &nbsp;<span class="badge fn">Championship</span></div>
      <div class="inner" style="padding-top:14px">{ladder(riders, 8)}
        <div class="dr-note2" style="margin-top:12px">Riders' championship. Numbers from
        <a href="{SRC}" style="color:var(--grey)">motogp.com</a>.</div>
      </div>
    </div>"""
        full = ('<div class="meta" style="margin-bottom:8px">Riders\' championship — every rider</div>'
                + ladder(riders).replace('class="ladder"',
                  'class="ladder" style="border:1px solid var(--faint);padding:0 10px"')
                + f'<div class="dr-note2" style="margin-top:12px">Numbers from '
                  f'<a href="{SRC}" style="color:var(--grey)">the official MotoGP standings</a>.</div>')
    else:
        panel = """    <div class="card" data-slot="table">
      <div class="sport">MotoGP &nbsp;<span class="badge tbc">Standings</span></div>
      <div class="inner" style="padding-top:14px"><div class="fight hd">Not Available
        <small>The championship table isn't published in the feed this tab uses.</small></div></div>
    </div>"""
        full = ('<table><tbody><tr><td class="gone">Championship standings are not available '
                'from this feed.</td></tr></tbody></table>')

    page = open(PAGE).read()
    before = page
    page = splice(page, "MGP-TABLE", panel)
    page = splice(page, "MGP-HERO", hero(upcoming[0], "Next Race Weekend"))
    page = splice(page, "MGP-ROWS", "\n".join(row(r) for r in upcoming))
    page = splice(page, "MGP-CARDS", ",\n".join(card(r) for r in upcoming))
    page = splice(page, "MGP-FULL", full)
    if page == before:
        print("motogp tab already current")
        return
    open(PAGE, "w").write(page)
    print(f"rebuilt the MotoGP tab: {len(upcoming)} rounds ahead")


if __name__ == "__main__":
    main()
