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

LOGO = "https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg"   # white leaf, for a blue background
BLUE, WHITE, SOFT = "#00205B", "#FFFFFF", "#B9C6E0"   # Leafs blue and white; SOFT = white at reduced strength
FONT = '"Helvetica Neue",Helvetica,Arial,sans-serif'


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


def logo(x, y, width):
    """The Leafs logo, inlined (GitHub shows the card as an image, which can't load anything external)."""
    try:
        req = urllib.request.Request(LOGO, headers={"User-Agent": "leafs-readme"})
        with urllib.request.urlopen(req, timeout=30) as r:
            svg = r.read().decode()
    except Exception:
        return ""
    inner = svg[svg.index(">") + 1:svg.rindex("</svg>")]
    view = svg.split('viewBox="')[1].split('"')[0]
    vw, vh = (float(v) for v in view.split()[2:])
    return f'<svg x="{x}" y="{y}" width="{width}" height="{width * vh / vw:.0f}" viewBox="{view}">{inner}</svg>'


def text(x, y, value, size, color=WHITE, weight=400, anchor="start", italic=False):
    style = ' font-style="italic"' if italic else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}"{style}>{escape(value)}</text>')


def chip(x, y, code):
    """One past result: a solid white box for a win, an outline for a loss, a dashed outline for an OT/SO loss."""
    box = f'<rect x="{x}" y="{y}" width="34" height="24" rx="3"'
    if code == "W":
        return box + f' fill="{WHITE}"/>' + text(x + 17, y + 17, "W", 13, BLUE, 800, "middle")
    dash = ' stroke-dasharray="3 2"' if code == "OTL" else ""
    return (box + f' fill="none" stroke="{WHITE}" stroke-width="1.5"{dash}/>'
            + text(x + 17, y + 17, "OT" if code == "OTL" else "L", 12, WHITE, 700, "middle"))


def card(team, played, upcoming):
    w, h = 720, 250
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Toronto Maple Leafs season card">',
        f"<style>text{{font-family:{FONT}}}</style>",
        f'<clipPath id="r"><rect width="{w}" height="{h}" rx="14"/></clipPath>',
        f'<g clip-path="url(#r)">',
        f'<rect width="{w}" height="{h}" fill="{BLUE}"/>',
        # jersey hem stripes: thin, thick, thin
        f'<rect y="{h - 46}" width="{w}" height="4" fill="{WHITE}"/>',
        f'<rect y="{h - 36}" width="{w}" height="14" fill="{WHITE}"/>',
        f'<rect y="{h - 16}" width="{w}" height="4" fill="{WHITE}"/>',
        logo(10, 22, 210),
        f'<line x1="232" y1="34" x2="232" y2="176" stroke="{SOFT}" stroke-opacity="0.35"/>',
    ]

    if team is None:   # before the opener, or offseason
        parts.append(text(256, 92, "0-0-0", 60, WHITE, 900, italic=True))
        if upcoming:
            opp, when = matchup(upcoming[0])
            parts += [text(256, 124, "Puck drops soon", 16, SOFT, 600),
                      text(486, 72, "Opening night", 14, SOFT, 600),
                      text(486, 100, opp, 26, WHITE, 800), text(486, 124, when, 14, SOFT)]
        else:
            parts += [text(256, 124, "Offseason", 16, SOFT, 600),
                      text(486, 92, "This is the year.", 24, WHITE, 800, italic=True),
                      text(486, 118, "(It's always the year.)", 14, SOFT)]
    else:
        record = f"{team['wins']}-{team['losses']}-{team['otLosses']}"
        parts += [
            text(256, 92, record, 60, WHITE, 900, italic=True),
            text(256, 122, f"{team['points']} points · {ordinal(team['divisionSequence'])} in {team['divisionName']}",
                 15, SOFT, 600),
        ]
        x = 256
        for g in played[-5:]:
            parts.append(chip(x, 146, result(g)[0]))
            x += 40

        code, line = result(played[-1])
        word = {"W": "Won", "L": "Lost", "OTL": "Lost"}[code]
        parts += [text(486, 62, "Last game", 14, SOFT, 600),
                  text(486, 88, f"{word} {line}", 22, WHITE, 800)]
        if upcoming:
            opp, when = matchup(upcoming[0])
            parts += [text(486, 126, "Next game", 14, SOFT, 600),
                      text(486, 152, opp, 22, WHITE, 800), text(486, 172, when, 13, SOFT)]

    updated = datetime.now(TORONTO)
    parts += ["</g>", text(w - 14, h - 52, f"Updated {updated:%b} {updated.day}", 10, SOFT, 400, "end"), "</svg>"]
    return "\n".join(parts)


def main():
    svg = card(*season())
    CARD.parent.mkdir(exist_ok=True)
    CARD.write_text(svg)
    print(f"wrote {CARD}")


if __name__ == "__main__":
    main()
