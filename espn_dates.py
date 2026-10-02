"""
Month windows for ESPN scoreboard queries.

ESPN stopped accepting a date RANGE on several sports in late 2026: a
"?dates=20261002-20261008" now answers 400 Bad Request for rugby-league,
soccer and basketball, while mma and racing still accept it. Verified
against the live API on 2 Oct 2026:

    dates=A-B     400 on all three
    dates=A       200 but zero events unless something is on that exact day
    dates=YYYYMM  200, and returns the whole month

So the builders ask month by month instead. That is also fewer requests
than the old week by week walk.

One caveat worth knowing: a month query is capped at 100 events. For a
busy NBA month that truncates part way through, which is fine when you
only want the next few fixtures, and is why the builders still filter to
their own team rather than trusting the feed to be complete.
"""
from datetime import datetime, timedelta


def months_covering(start: datetime, weeks: int):
    """Every YYYYMM between start and start + weeks, in order, no repeats."""
    end = start + timedelta(weeks=weeks)
    out, seen = [], set()
    d = start
    while d <= end:
        key = d.strftime("%Y%m")
        if key not in seen:
            seen.add(key)
            out.append(key)
        # step a fortnight so a short month cannot be skipped
        d += timedelta(days=14)
    key = end.strftime("%Y%m")
    if key not in seen:
        out.append(key)
    return out
