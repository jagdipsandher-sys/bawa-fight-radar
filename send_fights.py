#!/usr/bin/env python3
"""
BAWA Fight Radar — weekly fight email.

UFC/MMA:  pulled live from ESPN's public JSON API (no key needed).
Boxing:   read from boxing.json in this repo (no reliable free boxing API
          exists — update that file when big fights are announced).

Sends via Gmail SMTP (app password) to MAIL_TO. Refuses to send an empty
email. Writes .last_sent marker so the backup cron doesn't double-send.
"""
import json
import os
import ssl
import smtplib
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

SYD = ZoneInfo("Australia/Sydney")
DAYS_AHEAD = 9  # cover this weekend + the week ahead
MARKER = ".last_sent"

# Reliable rule-based AU watch info ONLY — anything else stays blank (never guess).
def au_watch(event_name: str) -> str:
    n = event_name.lower()
    if n.startswith("ufc ") and any(ch.isdigit() for ch in n.split(":")[0]):
        return "Main Event (Foxtel/Kayo PPV $59.95) — prelims Paramount+/10"
    if "ufc fight night" in n or "contender series" in n:
        return "Paramount+"
    return ""


def sydney(dt_utc: datetime) -> str:
    d = dt_utc.astimezone(SYD)
    return d.strftime("%a %d %b · %I:%M%p AEST").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def fetch_ufc(start: datetime, end: datetime):
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates="
        f"{start:%Y%m%d}-{end:%Y%m%d}"
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    events = []
    for ev in data.get("events", []):
        try:
            when = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        fights = []
        for comp in ev.get("competitions", [])[:6]:  # headline fights only
            names = [c.get("athlete", {}).get("displayName", "") for c in comp.get("competitors", [])]
            names = [n for n in names if n]
            if len(names) == 2:
                fights.append(f"{names[0]} vs {names[1]}")
        events.append({
            "sport": "UFC / MMA",
            "name": ev.get("name", "UFC event"),
            "when_utc": when,
            "fights": fights,
            "venue": "",
            "watch": au_watch(ev.get("name", "")),
        })
    return events


def load_boxing(start: datetime, end: datetime):
    try:
        with open("boxing.json") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return []
    events = []
    for ev in raw:
        try:
            when = datetime.fromisoformat(ev["date_utc"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if not (start <= when <= end):
            continue
        events.append({
            "sport": "Boxing · " + ev.get("promotion", ""),
            "name": ev.get("name", ""),
            "when_utc": when,
            "fights": ev.get("fights", []),
            "venue": ev.get("venue", ""),
            "watch": ev.get("watch_au", ""),  # blank = unconfirmed, never guess
        })
    return events


SITE_URL = "https://jagdipsandher-sys.github.io/bawa-fight-radar/"

# Condensed-caps stack: closest email-safe match to the site's Barlow Condensed.
HD = "'Arial Narrow','Helvetica Neue Condensed',Arial,Helvetica,sans-serif"


def build_html(events):
    # EMAIL HTML RULES: tables + inline styles only, no JS, single column.
    # The email is the door-knock; the button opens the full site.
    rows = []
    for ev in events:
        fights = "<br>".join(ev["fights"][:5]) or "Card TBA"
        watch = ev["watch"] or "AU broadcaster TBC"
        venue = f" · {ev['venue']}" if ev["venue"] else ""
        is_ufc = ev["sport"].startswith("UFC")
        tag_bg = "#000000" if is_ufc else "#00247d"
        tag = "UFC" if is_ufc else "BOX"
        rows.append(f"""
        <tr><td style="padding:14px 20px;border-bottom:1px solid #ececec;">
          <div style="font-size:10px;color:#6b6b6b;letter-spacing:3px;text-transform:uppercase;font-weight:bold;">
            <span style="background:{tag_bg};color:#ffffff;padding:2px 7px;letter-spacing:2px;">{tag}</span>
            &nbsp;{ev['sport']}{venue}</div>
          <div style="font-family:{HD};font-size:22px;font-weight:bold;color:#1b1b1b;text-transform:uppercase;padding:6px 0 2px;">{ev['name']}</div>
          <div style="font-family:{HD};font-size:15px;color:#d20a0a;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">{sydney(ev['when_utc'])} (Sydney)</div>
          <div style="font-size:13px;color:#333333;padding-top:6px;line-height:1.5;">{fights}</div>
          <div style="font-size:12px;color:#6b6b6b;padding-top:5px;">Watch: <b>{watch}</b></div>
        </td></tr>""")
    button = f"""
      <tr><td align="center" style="padding:22px 20px 8px;">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td align="center" bgcolor="#d20a0a" style="background:#d20a0a;">
            <a href="{SITE_URL}" target="_blank"
               style="display:inline-block;padding:14px 34px;font-family:{HD};font-size:17px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#ffffff;text-decoration:none;">
              View The Fight Radar &#8594;</a>
          </td>
        </tr></table>
        <div style="font-size:11px;color:#999999;padding-top:8px;">Full cards · fighter photos · add-to-calendar · opens in your browser</div>
      </td></tr>"""
    return f"""<!DOCTYPE html><html><body style="margin:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;max-width:600px;width:100%;">
      <tr><td style="background:#000000;padding:16px 20px;">
        <span style="font-family:{HD};color:#d20a0a;font-size:26px;font-weight:bold;letter-spacing:1px;">BAWA</span>
        <span style="font-family:{HD};color:#ffffff;font-size:26px;font-weight:bold;letter-spacing:1px;"> FIGHT RADAR</span>
      </td></tr>
      <tr><td style="background:#d20a0a;height:4px;font-size:0;line-height:4px;">&nbsp;</td></tr>
      {button}
      <tr><td style="padding:4px 20px 10px;">
        <div style="font-family:{HD};font-size:14px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#1b1b1b;border-bottom:2px solid #000000;padding-bottom:6px;">
          <span style="color:#d20a0a;">&#9646;</span> This Week's Fights</div>
      </td></tr>
      {''.join(rows)}
      <tr><td align="center" style="padding:18px 20px;">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td align="center" bgcolor="#d20a0a" style="background:#d20a0a;">
            <a href="{SITE_URL}" target="_blank"
               style="display:inline-block;padding:12px 28px;font-family:{HD};font-size:15px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#ffffff;text-decoration:none;">
              View The Fight Radar &#8594;</a>
          </td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:12px 20px 16px;font-size:11px;color:#999999;border-top:1px solid #ececec;">
        All times Sydney. UFC data auto-pulled from ESPN; boxing curated. Broadcast details firm up closer to fight week.
      </td></tr>
    </table></td></tr></table></body></html>"""


def send(subject, html):
    user = os.environ.get("GMAIL_USER", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = [a.strip() for a in os.environ.get("MAIL_TO", "").replace(";", ",").split(",") if a.strip()]
    if not (user and pw and to):
        print("missing GMAIL_USER / GMAIL_APP_PASSWORD / MAIL_TO")
        sys.exit(1)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(to)
    msg.set_content("Please view this in an HTML capable email client.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"sent to {len(to)} recipient(s)")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    # dedupe: the backup cron must not double-send
    if os.path.exists(MARKER) and open(MARKER).read().strip() == today:
        print("already sent today — skipping")
        return

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=DAYS_AHEAD)
    events = fetch_ufc(now, end) + load_boxing(now, end)
    events.sort(key=lambda e: e["when_utc"])

    # NEVER send an empty/broken email — a wrong email is worse than no email.
    if not events:
        print("no fixtures found — refusing to send")
        sys.exit(1)

    syd_sat = (now.astimezone(SYD) + timedelta(days=1)).strftime("%d %b")
    send(f"BAWA Fight Radar — weekend of {syd_sat}", build_html(events))
    with open(MARKER, "w") as f:
        f.write(today)


if __name__ == "__main__":
    main()
