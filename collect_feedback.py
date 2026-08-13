#!/usr/bin/env python3
"""
Collates the feedback people send from the buttons on the radar page.

The buttons email the radar's own Gmail account with "[BAWA FEEDBACK]" in the
subject. This reads that mailbox over IMAP with the app password already in the
repo secrets, appends anything new to feedback/log.md, and emails Jack a digest.
Scheduled sessions can't reach Gmail in this org, which is why this runs as a
plain script in Actions instead.

Nothing personal goes in the log — the repo is public, so it records the request
and a first name, never an address.
"""
import email
import email.utils
import imaplib
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from send_fights import SYD, send

LOG = "feedback/log.md"
TAG = "[BAWA FEEDBACK]"
DAYS = 8


def body_of(msg):
    """Plain text of a message, however it was sent."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(errors="replace")
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(errors="replace")
    except Exception:
        return str(msg.get_payload())


def first_name(addr_header):
    """A first name only — never the address. The repo is public."""
    name, addr = email.utils.parseaddr(addr_header or "")
    if name:
        return re.split(r"[\s,]+", name.strip())[0][:20]
    local = addr.split("@")[0] if addr else ""
    return re.split(r"[._\-0-9]+", local)[0][:20].title() or "Anonymous"


def clean(text):
    """Trim quoted replies, signatures and blank template lines."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">") or s.startswith("--") or s.lower().startswith("sent from"):
            break
        if s and not s.endswith(":"):        # drop untouched template prompts
            out.append(s)
    return " / ".join(out)[:400]


def fetch():
    user = os.environ.get("GMAIL_USER", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not (user and pw):
        print("missing GMAIL_USER / GMAIL_APP_PASSWORD")
        sys.exit(1)

    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    items = []
    with imaplib.IMAP4_SSL("imap.gmail.com") as M:
        M.login(user, pw)
        M.select("INBOX")
        typ, data = M.search(None, f'(SINCE {since} SUBJECT "{TAG}")')
        if typ != "OK":
            return items
        for num in data[0].split():
            typ, raw = M.fetch(num, "(RFC822)")
            if typ != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
            when = email.utils.parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
            items.append({
                "kind": subject.replace(TAG, "").strip(" :-") or "General",
                "who": first_name(msg.get("From")),
                "what": clean(body_of(msg)) or "(no detail given)",
                "when": (when or datetime.now(timezone.utc)).astimezone(SYD),
                "id": msg.get("Message-ID", subject)[:120],
            })
    return items


def main():
    items = fetch()
    if not items:
        print("no new feedback this week")
        return

    old = open(LOG).read() if os.path.exists(LOG) else "# Feedback log\n"
    fresh = [i for i in items if i["id"] not in old]
    if not fresh:
        print(f"{len(items)} feedback email(s) found, all already logged")
        return

    today = datetime.now(timezone.utc).astimezone(SYD)
    block = [f"\n## Week to {today:%a %d %b %Y}\n"]
    for i in sorted(fresh, key=lambda x: x["when"]):
        block.append(f"- **{i['kind']}** — {i['what']}  \n"
                     f"  _{i['who']}, {i['when']:%d %b}_ <!-- {i['id']} -->\n")
    block.append("\n_Status: unreviewed._\n")

    head, _, rest = old.partition("---\n")
    open(LOG, "w").write(head + "---\n" + "".join(block) + rest)
    print(f"logged {len(fresh)} new item(s)")

    lines = "".join(f"<li><b>{i['kind']}</b> — {i['what']} <i>({i['who']})</i></li>" for i in fresh)
    send(f"BAWA Radar — {len(fresh)} piece(s) of feedback this week",
         f"""<html><body style="font-family:Arial,Helvetica,sans-serif;color:#1b1b1b">
         <p style="font-family:'Arial Narrow',Arial;font-size:22px;font-weight:bold;text-transform:uppercase">
           <span style="color:#d20a0a">BAWA</span> Radar · Feedback</p>
         <p>{len(fresh)} new this week:</p><ul>{lines}</ul>
         <p>All of it is in <code>feedback/log.md</code> in the repo, oldest at the bottom.
            Recurring asks are the ones worth building — check the log for anything
            that has now come up more than once.</p>
         </body></html>""")


if __name__ == "__main__":
    main()
