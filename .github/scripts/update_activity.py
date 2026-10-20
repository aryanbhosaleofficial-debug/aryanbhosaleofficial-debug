"""Update the "latest activity" line in README.md from the owner's public GitHub events."""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

USER = os.environ["GH_USER"]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
TZ = ZoneInfo(os.environ.get("ACTIVITY_TZ", "UTC"))
README = os.environ.get("README_PATH", "README.md")
START, END = "<!-- ACTIVITY:START -->", "<!-- ACTIVITY:END -->"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-activity",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def latest_commit(events):
    for e in events:
        if e.get("type") != "PushEvent" or e.get("actor", {}).get("login", "").lower() != USER.lower():
            continue
        repo = e["repo"]["name"]
        when = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
        return repo, when
    return None


def render(found, now):
    if not found:
        return '<p align="center"><sub>No recent public commits yet</sub></p>'
    repo, when = found
    local, today = when.astimezone(TZ), now.astimezone(TZ)
    days = (today.date() - local.date()).days
    if days == 0:
        status = "🟢 <b>Active today</b>"
    elif days == 1:
        status = "🟡 <b>Last active yesterday</b>"
    else:
        status = f"⚪ <b>Last active {local.strftime('%b %-d, %Y')}</b>"
    repo_short = repo.split("/", 1)[1]
    link = f'<a href="https://github.com/{repo}">{html.escape(repo_short)}</a>'
    return f'<p align="center"><sub>{status} · latest commit in {link}</sub></p>'


def main():
    events_file = os.environ.get("EVENTS_FILE")
    events = json.load(open(events_file)) if events_file else api(f"/users/{USER}/events/public?per_page=100")
    block = render(latest_commit(events), datetime.now(timezone.utc))
    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        sys.exit("Activity markers not found in README")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), f"{START}\n{block}\n{END}", text, flags=re.S)
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README updated:", block)
    else:
        print("No change")


if __name__ == "__main__":
    main()
