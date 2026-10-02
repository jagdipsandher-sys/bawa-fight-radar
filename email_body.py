"""
The Friday email body.

Jack's brief: this goes to the boys, and to suppliers and close contacts, and
it is meant to fire people up for the weekend rather than read like a fixture
list. So it opens in his own voice, then gives a fast scan of what is actually
on across the whole radar, then gets out of the way.

Two hard rules, both from Jack's own writing style:
  * NO hyphens or dashes anywhere, subject line included. Restructure instead.
  * Contractions lose their apostrophes (Im, Ive, dont, Lets, its).
Keep both when editing this file. They are what make it read as him.

Nothing in here invents an event. Everything comes from weekend.lineup(),
which reads the live radar page, so a quiet weekend produces a short email
rather than a padded one.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

SYD = ZoneInfo("Australia/Sydney")
SITE = "https://jagdipsandher-sys.github.io/bawa-fight-radar/"
HD = "'Arial Narrow','Helvetica Neue Condensed',Arial,Helvetica,sans-serif"
BODY = "'Helvetica Neue',Helvetica,Arial,sans-serif"
RED = "#d20a0a"

# Tab id -> the anchor on the site, so every line can deep link to its tab
ANCHOR = {"fights": "fights", "bkfc": "bkfc", "panthers": "panthers",
          "united": "united", "f1": "f1", "motogp": "motogp", "wolves": "wolves",
          "pga": "pga", "tennis": "tennis"}


def subject(blocks, when=None):
    """A subject that says what is actually on, biggest thing first.

    No dashes. Australian events win, then the NRL, then whatever is left.
    """
    when = when or datetime.now(SYD)
    sat = when + __import__("datetime").timedelta(days=(5 - when.weekday()) % 7)
    bits = []
    for b in blocks:
        for e in b["events"]:
            if e.get("aus"):
                bits.append(e["name"])
                break
        if bits:
            break
    for b in blocks:
        lab = b["label"]
        if lab in ("NRL", "UFC") and len(bits) < 3:
            bits.append(b["events"][0]["name"])
    if not bits:
        return f"BAWA Radar: whats on this weekend, {sat:%d %b}"
    head = ", ".join(bits[:2])
    extra = f" and more" if len(blocks) > 2 else ""
    return f"Boys, big weekend: {head}{extra}"


def greeting(blocks, when=None):
    """Jack's own few lines at the top. Short, warm, no dashes."""
    when = when or datetime.now(SYD)
    aus = None
    for b in blocks:
        for e in b["events"]:
            if e.get("aus"):
                aus = e
                break
        if aus:
            break

    lines = ["Hey Boys,", "Hope youve all had a good week."]
    if aus:
        lines.append(f"Weve got one on home soil this weekend with {aus['name']}, "
                     f"so thats the one to get around.")
    else:
        lines.append("Decent one on the radar this weekend so lets get into it.")
    lines.append("Have a quick look through and let me know what youre watching.")
    return lines


def _row(label, e, tab):
    link = f"{SITE}#{ANCHOR.get(tab, '')}"
    flag = ('<span style="background:#00247d;color:#ffffff;font-size:9px;'
            'letter-spacing:2px;padding:2px 6px;font-weight:bold;">IN AUSTRALIA</span> '
            if e.get("aus") else "")
    sub = (f'<div style="font-size:12px;color:#6b6b6b;padding-top:3px;line-height:1.45;">'
           f'{e["sub"]}</div>' if e.get("sub") else "")
    return f"""
      <tr><td style="padding:12px 20px;border-bottom:1px solid #ececec;">
        <div style="font-size:10px;color:#6b6b6b;letter-spacing:2px;text-transform:uppercase;font-weight:bold;">
          <span style="background:#000000;color:#ffffff;padding:2px 7px;letter-spacing:2px;">{label}</span>
          &nbsp;{e['day']}</div>
        <div style="font-family:{HD};font-size:19px;font-weight:bold;color:#1b1b1b;text-transform:uppercase;padding:5px 0 2px;">
          {flag}<a href="{link}" style="color:#1b1b1b;text-decoration:none;">{e['name']}</a></div>
        {sub}
      </td></tr>"""


def build(blocks, series=None, sydney=None, owner="", when=None):
    when = when or datetime.now(SYD)
    rows = "".join(_row(b["label"], e, b["tab"]) for b in blocks for e in b["events"])

    hello = "".join(
        f'<div style="font-size:15px;color:#1b1b1b;line-height:1.6;padding-bottom:10px;">{l}</div>'
        for l in greeting(blocks, when))

    extras = ""
    if series:
        picks = ", ".join(series[:3])
        extras += f"""
      <tr><td style="padding:12px 20px;border-bottom:1px solid #ececec;">
        <div style="font-size:10px;color:#6b6b6b;letter-spacing:2px;text-transform:uppercase;font-weight:bold;">
          <span style="background:#555555;color:#ffffff;padding:2px 7px;letter-spacing:2px;">ON THE BOX</span></div>
        <div style="font-size:14px;color:#1b1b1b;padding-top:6px;line-height:1.5;">
          Anyone watching {picks}? Full list is on the
          <a href="{SITE}#series" style="color:{RED};font-weight:bold;">Series tab</a>.</div>
      </td></tr>"""
    if sydney:
        out = ", ".join(sydney[:3])
        extras += f"""
      <tr><td style="padding:12px 20px;border-bottom:1px solid #ececec;">
        <div style="font-size:10px;color:#6b6b6b;letter-spacing:2px;text-transform:uppercase;font-weight:bold;">
          <span style="background:#555555;color:#ffffff;padding:2px 7px;letter-spacing:2px;">AROUND SYDNEY</span></div>
        <div style="font-size:14px;color:#1b1b1b;padding-top:6px;line-height:1.5;">
          {out}. More on the
          <a href="{SITE}#sydney" style="color:{RED};font-weight:bold;">Whats On Sydney tab</a>.</div>
      </td></tr>"""

    foot = ""
    if owner:
        foot = (f'<div style="padding-top:10px;">You are on this because you asked Jack to be. '
                f'To come off it, <a href="mailto:{owner}?subject=Unsubscribe%20from%20BAWA%20Radar" '
                f'style="color:#6b6b6b;">reply with unsubscribe</a> and youre off before the next one. '
                f'Sent by Jack Sandher, Sydney.</div>')

    return f"""<!DOCTYPE html><html><body style="margin:0;background:#f4f4f4;font-family:{BODY};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;max-width:600px;width:100%;">

      <tr><td style="background:#000000;padding:16px 20px;">
        <span style="font-family:{HD};color:{RED};font-size:26px;font-weight:bold;letter-spacing:1px;">BAWA</span>
        <span style="font-family:{HD};color:#ffffff;font-size:26px;font-weight:bold;letter-spacing:1px;"> FIGHT RADAR</span>
        <div style="font-size:10px;color:#9a9a9a;letter-spacing:3px;text-transform:uppercase;font-weight:bold;padding-top:4px;">
          Weekend of {when:%d %b %Y} &nbsp;&middot;&nbsp; Sydney time</div>
      </td></tr>
      <tr><td style="background:{RED};height:4px;line-height:4px;font-size:0;">&nbsp;</td></tr>

      <tr><td style="padding:20px 20px 6px;">{hello}</td></tr>

      <tr><td style="padding:6px 20px 4px;">
        <div style="font-family:{HD};font-size:13px;font-weight:bold;letter-spacing:3px;text-transform:uppercase;color:{RED};">
          Whats On This Weekend</div>
      </td></tr>
      {rows}
      {extras}

      <tr><td align="center" style="padding:22px 20px 8px;">
        <a href="{SITE}" style="background:{RED};color:#ffffff;font-family:{HD};font-size:17px;font-weight:bold;
           letter-spacing:2px;text-transform:uppercase;padding:14px 30px;text-decoration:none;display:inline-block;">
          Open The Radar</a>
      </td></tr>
      <tr><td align="center" style="padding:0 20px 20px;">
        <div style="font-size:12px;color:#6b6b6b;">Times, cards and broadcasters are on the site and stay current all week.</div>
      </td></tr>

      <tr><td style="background:#fafafa;padding:14px 20px;border-top:1px solid #ececec;">
        <div style="font-size:11px;color:#9a9a9a;line-height:1.6;">
          All times Sydney. Fight cards move, so check the radar before you commit to a 7am alarm.{foot}</div>
      </td></tr>

    </table></td></tr></table></body></html>"""
