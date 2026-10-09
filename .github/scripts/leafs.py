"""Draw the Toronto Maple Leafs' current season as an SVG card (assets/leafs-card.svg) for the profile README.

Runs daily from .github/workflows/leafs.yml. Uses the NHL's public API; standard library only.
"""
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

TEAM = "TOR"
API = "https://api-web.nhle.com/v1"
CARD = Path(__file__).resolve().parents[2] / "assets" / "leafs-card.svg"
TORONTO = ZoneInfo("America/Toronto")
REGULAR_SEASON = 2

BLUE, DEEP, WHITE, MUTED = "#00205B", "#001640", "#FFFFFF", "#A9B8D6"
RESULT_COLORS = {"W": "#3FB37F", "L": "#E5484D", "OTL": "#F2A93B"}


def fetch(path):
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "leafs-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def local_time(game):
    return datetime.fromisoformat(game["startTimeUTC"].replace("Z", "+00:00")).astimezone(TORONTO)


def result(game):
    """('W' | 'L' | 'OTL', '5-4 OT vs NSH') from the Leafs' side."""
    home = game["homeTeam"]["abbrev"] == TEAM
    us, them = (game["homeTeam"], game["awayTeam"]) if home else (game["awayTeam"], game["homeTeam"])
    period = (game.get("gameOutcome") or {}).get("lastPeriodType", "REG")
    extra = f" {period}" if period in ("OT", "SO") else ""
    if us["score"] > them["score"]:
        code = "W"
    else:
        code = "OTL" if extra else "L"
    return code, f"{us['score']}-{them['score']}{extra} {'vs' if home else '@'} {them['abbrev']}"


def matchup(game):
    home = game["homeTeam"]["abbrev"] == TEAM
    opponent = game["awayTeam"]["abbrev"] if home else game["homeTeam"]["abbrev"]
    when = local_time(game)
    return f"{'vs' if home else '@'} {opponent}", f"{when:%a, %b} {when.day} · {when:%-I:%M %p} ET"


def season():
    games = [g for g in fetch(f"club-schedule-season/{TEAM}/now")["games"] if g.get("gameType") == REGULAR_SEASON]
    played = [g for g in games if g.get("gameState") in ("OFF", "FINAL")]
    upcoming = [g for g in games if g.get("gameState") in ("FUT", "PRE", "LIVE", "CRIT")]
    team = None
    if played:
        team = next(t for t in fetch("standings/now")["standings"] if t["teamAbbrev"]["default"] == TEAM)
    return team, played, upcoming


def text(x, y, value, size, color=WHITE, weight=400, anchor="start", spacing=0):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" letter-spacing="{spacing}">{escape(value)}</text>')


def card(team, played, upcoming):
    w, h = 720, 236
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Toronto Maple Leafs season card">',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}</style>',
        f'<rect width="{w}" height="{h}" rx="16" fill="{BLUE}"/>',
        f'<path d="M300 0 H{w - 16} A16 16 0 0 1 {w} 16 V{h - 16} A16 16 0 0 1 {w - 16} {h} H300 Z" fill="{DEEP}"/>',
        text(28, 42, "TORONTO MAPLE LEAFS", 13, MUTED, 700, spacing=2),
    ]

    if team is None:   # before the opener, or offseason
        parts.append(text(28, 110, "0-0-0", 56, WHITE, 800))
        if upcoming:
            opp, when = matchup(upcoming[0])
            parts += [text(28, 145, "Season starts soon", 15, MUTED),
                      text(330, 70, "OPENING NIGHT", 12, MUTED, 700, spacing=1.5),
                      text(330, 104, opp, 30, WHITE, 800), text(330, 132, when, 15, MUTED)]
        else:
            parts += [text(28, 145, "Offseason", 15, MUTED),
                      text(330, 104, "This is the year.", 26, WHITE, 800),
                      text(330, 132, "(It's always the year.)", 15, MUTED)]
    else:
        record = f"{team['wins']}-{team['losses']}-{team['otLosses']}"
        parts += [
            text(28, 108, record, 56, WHITE, 800),
            text(28, 140, f"{team['points']} PTS · {ordinal(team['divisionSequence'])} in the {team['divisionName']}", 15, WHITE, 600),
        ]
        # stat strip: goals for/against, last 10, streak
        stats = [("GF", str(team["goalFor"])), ("GA", str(team["goalAgainst"])),
                 ("L10", f"{team['l10Wins']}-{team['l10Losses']}-{team['l10OtLosses']}"),
                 ("STREAK", f"{team['streakCode']}{team['streakCount']}")]
        x = 28
        for label, value in stats:
            parts += [text(x, 178, label, 11, MUTED, 700, spacing=1), text(x, 200, value, 18, WHITE, 700)]
            x += 64 if label != "L10" else 76

        # right panel: last game, next game, last five
        code, line = result(played[-1])
        parts += [text(330, 46, "LAST GAME", 12, MUTED, 700, spacing=1.5),
                  f'<rect x="330" y="58" width="{18 + 10 * len(code)}" height="24" rx="6" fill="{RESULT_COLORS[code]}"/>',
                  text(339 + 5 * len(code), 75, code, 13, WHITE, 800, "middle"),
                  text(360 + 10 * len(code), 77, line, 20, WHITE, 700)]
        if upcoming:
            opp, when = matchup(upcoming[0])
            parts += [text(330, 120, "NEXT GAME", 12, MUTED, 700, spacing=1.5),
                      text(330, 146, opp, 20, WHITE, 700), text(330 + 12 * len(opp) + 8, 146, when, 15, MUTED)]
        parts.append(text(330, 186, "LAST 5", 12, MUTED, 700, spacing=1.5))
        x = 330
        for g in played[-5:]:
            c, _ = result(g)
            parts += [f'<rect x="{x}" y="196" width="44" height="22" rx="6" fill="{RESULT_COLORS[c]}"/>',
                      text(x + 22, 212, c, 12, WHITE, 800, "middle")]
            x += 52

    updated = datetime.now(TORONTO)
    parts += [text(w - 24, h - 14, f"Updated {updated:%b} {updated.day} · NHL API", 10, MUTED, 400, "end"), "</svg>"]
    return "\n".join(parts)


def main():
    svg = card(*season())
    CARD.parent.mkdir(exist_ok=True)
    CARD.write_text(svg)
    print(f"wrote {CARD}")


if __name__ == "__main__":
    main()
