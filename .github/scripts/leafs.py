"""Write the Toronto Maple Leafs' current record into README.md (between the LEAFS markers).

Runs daily from .github/workflows/leafs.yml. Uses the NHL's public API; standard library only.
"""
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TEAM = "TOR"
API = "https://api-web.nhle.com/v1"
README = Path(__file__).resolve().parents[2] / "README.md"
TORONTO = ZoneInfo("America/Toronto")
REGULAR_SEASON = 2


def fetch(path):
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "leafs-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def local_date(game):
    return datetime.fromisoformat(game["startTimeUTC"].replace("Z", "+00:00")).astimezone(TORONTO)


def last_result(game):
    home = game["homeTeam"]["abbrev"] == TEAM
    us, them = (game["homeTeam"], game["awayTeam"]) if home else (game["awayTeam"], game["homeTeam"])
    period = (game.get("gameOutcome") or {}).get("lastPeriodType", "REG")
    if us["score"] > them["score"]:
        result = "W"
    else:
        result = "OTL" if period in ("OT", "SO") else "L"
    suffix = f" ({period})" if period in ("OT", "SO") else ""
    where = "vs" if home else "@"
    return f"{result} {us['score']}-{them['score']}{suffix} {where} {them['abbrev']}"


def next_game(game):
    home = game["homeTeam"]["abbrev"] == TEAM
    opponent = game["awayTeam"]["abbrev"] if home else game["homeTeam"]["abbrev"]
    when = local_date(game)
    return f"{'vs' if home else '@'} {opponent}, {when:%b} {when.day} at {when:%-I:%M %p} ET"


def status_line():
    games = [g for g in fetch(f"club-schedule-season/{TEAM}/now")["games"] if g.get("gameType") == REGULAR_SEASON]
    played = [g for g in games if g.get("gameState") in ("OFF", "FINAL")]
    upcoming = [g for g in games if g.get("gameState") in ("FUT", "PRE", "LIVE", "CRIT")]

    if not played:
        if upcoming:
            return f"Leafs season opener: {next_game(upcoming[0])}. This is the year."
        return "Leafs are in the offseason. This is the year. (It's always the year.)"

    team = next(t for t in fetch("standings/now")["standings"] if t["teamAbbrev"]["default"] == TEAM)
    parts = [
        f"**{team['wins']}-{team['losses']}-{team['otLosses']}**",
        f"{team['points']} pts",
        f"{ordinal(team['divisionSequence'])} in the {team['divisionName']}",
        f"Last: {last_result(played[-1])}",
    ]
    if team.get("streakCount", 0) >= 3:
        parts.append(f"{team['streakCount']}-game {'win' if team['streakCode'] == 'W' else 'skid'}")
    if upcoming:
        parts.append(f"Next: {next_game(upcoming[0])}")
    return "Leafs right now: " + " · ".join(parts)


def main():
    readme = README.read_text()
    line = status_line()
    updated = re.sub(r"(<!-- LEAFS:START -->).*?(<!-- LEAFS:END -->)", lambda m: f"{m.group(1)}{line}{m.group(2)}",
                     readme, flags=re.S)
    if updated != readme:
        README.write_text(updated)
    print(line)


if __name__ == "__main__":
    main()
