# BAWA Fight Radar — weekly fight email

Emails Jack, Garry and Jagpreet every **Friday 10am Sydney** with the week's
UFC and boxing, times converted to Sydney.

## Setup (one time, ~5 minutes)

1. Create a **private** repo on github.com and upload these files
   (keep the `.github/workflows/` folder structure exactly).
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GMAIL_APP_PASSWORD`
   - Value: your 16-character Google app password, **spaces removed**
3. Done. It runs itself every Friday.

## Test it now

Repo → **Actions** tab → "BAWA Fight Radar" → **Run workflow**.
An email should arrive within a minute or two. If it fails, the log tells you why —
the usual culprit is the app password (check the spaces are stripped).

## How it works

- `send_fights.py` pulls UFC/MMA events from ESPN's public feed (no key needed),
  reads boxing from `boxing.json`, converts everything to Sydney time, and emails
  via Gmail SMTP (port 465 SSL).
- Scheduled twice (10am + 11am Sydney) because GitHub sometimes skips scheduled
  runs; a `.last_sent` marker stops a double-send.
- It **refuses to send an empty email** — no fixtures, no email, run marked failed.
- AU broadcast info only appears when it's reliable (UFC PPV → Main Event $59.95,
  UFC Fight Night → Paramount+, or whatever is set in `boxing.json`). Blank means
  unconfirmed — deliberately never guessed.

## The radar page (`index.html`)

Nine tabs, all in the one file — same layout on each (hero cards, lookahead
table, slide-out detail panel, calendar buttons):

- **Fights** — UFC and boxing, as before.
- **Other Action** — monster trucks and motorsport around Sydney/NSW. The one
  that matters: **Monster Jam, Accor Stadium, Sat 10 Oct 2026, 6pm, from $34.**
- **Comedy** — confirmed headline stand-up shows in Sydney over the next four
  weeks, using official venue, promoter and ticket-seller details only.
- **Panthers** — Penrith's remaining 2026 fixtures with venues, kick-off times
  and where to buy.
- **Raiders** — Canberra's remaining NRL fixtures and finals path.
- **Man Utd** — Manchester United fixtures in Sydney time and the league table.
- **F1** and **MotoGP** — race weekends, Sydney session times and standings.
- **Wolves** — Minnesota Timberwolves fixtures in Sydney time and standings.

Tabs are linkable: `index.html#other`, `index.html#comedy`, `index.html#panthers`,
`index.html#raiders`, `index.html#united`, `index.html#f1`, `index.html#motogp`,
`index.html#wolves`.

### How each tab stays current

| Tab | Source | Refresh |
| --- | --- | --- |
| Fights | ESPN MMA feed + `boxing.json` | `build_radar.py`, daily — rolling 4 weeks |
| Panthers | ESPN NRL feed | `build_panthers.py`, daily — finals appear when published |
| Raiders | ESPN NRL feed | `build_raiders.py`, daily — finals appear when published |
| Man Utd | ESPN football feed | `build_united.py`, daily |
| F1 | ESPN motorsport feed | `build_f1.py`, daily |
| MotoGP | Official MotoGP feed | `build_motogp.py`, daily |
| Wolves | ESPN NBA feed | `build_wolves.py`, daily |
| Other Action | Human web search | Scheduled Claude session, Sun night 1am Sydney |
| Comedy | Official venue, promoter and ticket pages | Human web search; four-week Sydney lookahead |

The two builders rewrite only the blocks between the `BUILD:` markers in
`index.html` and commit when the output changes (`.github/workflows/radar.yml`).
**Never hand-edit inside those markers** — it gets overwritten next morning.

Monster trucks and motorsport have no feed worth trusting, so Other Action is
researched by a **weekly scheduled Claude session** (a Routine, 1am Monday
Sydney — i.e. Sunday night, off-peak) that searches for newly announced Sydney dates, updates that tab and
pushes. As a backstop, `check_stale.py` runs Mondays 8am
(`.github/workflows/upkeep.yml`) and emails only if that tab drops below three
events or its last one comes inside six weeks — so a silent failure still
surfaces. Set a `MAINTENANCE_TO` secret to keep that nag off the family list.

The page also prunes itself in the browser: every event carries a `data-ends`
timestamp, past events are dropped on load, and a hero card whose event has
finished is rebuilt from the next one up.

Anything not yet published (kick-off times, finals venues, future dates) carries
a **TBC** badge rather than a guess — same rule as the email.

Supporting data files: `photos.json` (surname → headshot, missing ones fall back
to initials), `aussies.json` (surnames that earn a flag and an Aussie/NZ badge).

## The mailing list

Recipients are the `MAIL_TO` secret (the original three) **plus** anyone marked
`active` in `subscribers.json`. Everyone is BCC'd, so no recipient ever sees
another's address.

**Adding a friend.** They ask via the "Add Me To The List" button on the page,
which opens an email to Jack. Add an entry to `subscribers.json` recording who
asked and how:

```json
{ "email": "mate@example.com", "name": "Mate", "active": true,
  "consent": { "source": "asked by email 14 Aug", "date": "2026-08-14" } }
```

**Removing.** Set `"active": false` — don't delete the entry, so an unsubscribe
can't be undone by a later edit. `verify_page.py` rejects an active subscriber
with no recorded consent, a malformed address, or a duplicate.

**Why the referral button doesn't sign anyone up.** Australia's Spam Act needs
consent from the person themselves; a mate can't consent on their behalf. So
"Send It To A Mate" just forwards them the page, and they ask for themselves.
Every email carries sender identification, a one-click unsubscribe, and a
`List-Unsubscribe` header.

**Ceiling.** A Gmail app password does roughly 500 recipients a day. The sender
refuses to run past 400 and tells you to move to a mailing provider. Twenty
friends is nowhere near it.

## Feedback

Three buttons at the bottom of every tab open a pre-filled email tagged
`[BAWA FEEDBACK]`. `collect_feedback.py` reads that mailbox over IMAP every
Monday 7am (`.github/workflows/feedback.yml`), appends anything new to
`feedback/log.md`, and emails a digest. It says nothing when nobody wrote in.

The address printed on the buttons comes from a `FEEDBACK_TO` secret, falling
back to `GMAIL_USER` when it isn't set. Two secrets, two jobs:

| Secret | What it is | Where it shows |
| --- | --- | --- |
| `GMAIL_USER` | the account SMTP and IMAP log into | the From: on the Friday email |
| `FEEDBACK_TO` | the address printed on the public page | the feedback buttons |

`FEEDBACK_TO` can be a plus-alias of the same account (`you+bawa@gmail.com`) —
mail still arrives in the same inbox, so `collect_feedback.py` still finds it,
and you can filter or bin the alias later if it ever attracts spam. Gmail will
not accept an alias as a *login*, so `GMAIL_USER` has to stay a real account.

To keep your name off the page entirely, make a separate free Gmail, set it to
forward to your main inbox, and put it in both secrets with its own app
password.

`feedback/log.md` records the request and a **first name only** — the repo is
public, so no addresses, surnames or personal details go in it. Read the
"asked for repeatedly" counts before deciding what to build; one person wanting
cricket is a note, four people wanting it is the next tab.

## Updating boxing

No reliable free boxing API exists, so `boxing.json` is the source of truth.
Edit it on github.com (pencil icon) when fights are announced — or ask Claude
each week for the current list. Each entry:

```json
{
  "name": "Fighter A vs Fighter B",
  "promotion": "Matchroom",
  "date_utc": "2026-08-29T21:00:00Z",
  "venue": "O2 Arena, London",
  "fights": ["Main event (title)", "Co-feature"],
  "watch_au": "DAZN"
}
```

`date_utc` is the main-event start in UTC (Sydney is UTC+10 winter, +11 summer).
Leave `watch_au` as `""` if the Australian broadcaster isn't confirmed.
