"""
Generates a "Days vs Consistency" line chart (rolling 7-day activity rate)
from a GitHub user's real public contribution calendar.

Run manually:
    python assets/generate_consistency_graph.py <github-username>

Used automatically by .github/workflows/consistency-graph.yml (daily cron).
"""

import sys
import re
import json
from datetime import datetime
from urllib.request import Request, urlopen

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def fetch_contributions(username: str):
    url = f"https://github.com/users/{username}/contributions"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as resp:
        html = resp.read().decode("utf-8")

    id_date = dict(
        re.findall(r'data-date="([\d-]+)"[^>]*id="(contribution-day-component-[\d-]+)"', html)
    )
    id_date = {v: k for k, v in id_date.items()}

    id_tooltip = dict(
        re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', html)
    )

    def parse_count(text: str) -> int:
        if text.startswith("No contributions"):
            return 0
        m = re.match(r"(\d+)\s+contribution", text)
        return int(m.group(1)) if m else 0

    records = []
    for cid, date in id_date.items():
        cnt = parse_count(id_tooltip.get(cid, ""))
        records.append((date, cnt))

    records.sort()
    return records


def build_chart(records, out_svg: str, out_png: str):
    dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in records]
    counts = [c for _, c in records]

    window = 7
    consistency = []
    for i in range(len(counts)):
        lo = max(0, i - window + 1)
        chunk = counts[lo:i + 1]
        active_days = sum(1 for x in chunk if x > 0)
        consistency.append((active_days / len(chunk)) * 100)

    current_streak = 0
    for c in reversed(counts):
        if c > 0:
            current_streak += 1
        else:
            break

    longest = 0
    run = 0
    for c in counts:
        if c > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    avg_consistency = sum(consistency) / len(consistency)

    BG = "#0d1117"
    GRID = "#30363d"
    TEXT = "#c9d1d9"
    ACCENT = "#00C2FF"
    FILL = "#7A5CFF"

    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.plot(dates, consistency, color=ACCENT, linewidth=2.2, zorder=3, solid_capstyle="round")
    ax.fill_between(dates, consistency, 0, color=FILL, alpha=0.30, zorder=2)

    ax.set_ylim(0, 105)
    ax.set_ylabel("Consistency (%)", color=TEXT, fontsize=10)
    ax.set_title(
        "Days vs Consistency  —  rolling 7-day activity rate",
        color="#e8edf3", fontsize=13, pad=14, loc="center", fontweight="bold",
    )

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate(rotation=30, ha="right")

    ax.tick_params(colors=TEXT, labelsize=8.5)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.7)

    summary = f"Current streak: {current_streak}d      Longest streak: {longest}d      Avg consistency: {avg_consistency:.0f}%"
    fig.text(0.5, -0.05, summary, ha="center", color=ACCENT, fontsize=11, fontweight="bold")

    plt.tight_layout()
    plt.savefig(out_svg, facecolor=BG, bbox_inches="tight")
    plt.savefig(out_png, facecolor=BG, bbox_inches="tight", dpi=200)


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "Atharv-T2006"
    records = fetch_contributions(username)
    if not records:
        print("No contribution data found — check the username.")
        sys.exit(1)
    build_chart(records, "assets/consistency_graph.svg", "assets/consistency_graph.png")
    print(f"Generated consistency graph for {username} from {len(records)} days of data.")
