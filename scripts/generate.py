#!/usr/bin/env python3
"""
Generates the Nothing-style SVG assets for the profile README.

Stdlib only. Reads live data from GitHub (profile, repos, contribution calendar),
writes assets/*-dark.svg and assets/*-light.svg.

    python3 scripts/generate.py
"""
import base64
import datetime as dt
import json
import os
import re
import urllib.request
from html import escape

USER = "TechMaharishi"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
FONTS = os.path.join(ASSETS, "fonts")

W = 800  # shared canvas width

# ── Nothing tokens (references/tokens.md) ────────────────────────────────────
THEMES = {
    "dark": dict(
        black="#000000", surface="#111111", border="#222222", border_v="#333333",
        disabled="#666666", secondary="#999999", primary="#E8E8E8", display="#FFFFFF",
        dot_bg="#2A2A2A", dot_bg_op="0.9",
    ),
    "light": dict(
        black="#F5F5F5", surface="#FFFFFF", border="#E8E8E8", border_v="#CCCCCC",
        disabled="#999999", secondary="#666666", primary="#1A1A1A", display="#000000",
        dot_bg="#D4D4D4", dot_bg_op="0.9",
    ),
}
ACCENT = "#D71921"
SUCCESS = "#4A9E5C"

# ── 5x7 dot-matrix glyphs (stand-in for NDot / Doto) ─────────────────────────
GLYPHS = {
    "V": ["10001"] * 5 + ["01010", "00100"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "L": ["10000"] * 6 + ["11111"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "U": ["10001"] * 6 + ["01110"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
}

MONO_ADV = 0.612  # Space Mono advance (em)


# ── data ─────────────────────────────────────────────────────────────────────
def http_get(url, accept=None):
    headers = {"User-Agent": "techmaharishi-profile-generator"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    if accept:
        headers["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read().decode("utf-8")


def fetch_profile():
    return json.loads(http_get(f"https://api.github.com/users/{USER}"))


def fetch_repos():
    return json.loads(http_get(f"https://api.github.com/users/{USER}/repos?per_page=100"))


def fetch_contributions():
    html = http_get(f"https://github.com/users/{USER}/contributions")
    total = int(re.search(r"([\d,]+)\s+contributions\s+in the last year", re.sub(r"\s+", " ", html)).group(1).replace(",", ""))
    tips = {m.group(1): m.group(2) for m in re.finditer(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', html)}
    days = []
    for m in re.finditer(r'<td[^>]*?data-date="([\d-]+)"[^>]*?id="(contribution-day-component-[\d-]+)"[^>]*?data-level="(\d)"', html):
        date, cid, level = m.group(1), m.group(2), int(m.group(3))
        tip = tips.get(cid, "")
        n = re.match(r"(\d+)\s+contribution", tip)
        days.append((dt.date.fromisoformat(date), level, int(n.group(1)) if n else 0))
    days.sort()
    return total, days


# ── svg helpers ──────────────────────────────────────────────────────────────
def font_css(faces):
    spec = {
        "mono400": ("Space Mono", 400, "space-mono-400"),
        "mono700": ("Space Mono", 700, "space-mono-700"),
        "sans400": ("Space Grotesk", 400, "space-grotesk-400"),
        "sans500": ("Space Grotesk", 500, "space-grotesk-500"),
    }
    out = []
    for key in faces:
        fam, wt, fn = spec[key]
        with open(os.path.join(FONTS, fn + ".woff2"), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        out.append(f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "".join(out)


def css(t):
    return (
        f".lab{{font:400 11px 'Space Mono',monospace;letter-spacing:.08em;fill:{t['secondary']}}}"
        f".labd{{font:400 11px 'Space Mono',monospace;letter-spacing:.08em;fill:{t['disabled']}}}"
        f".val{{font:400 13px 'Space Mono',monospace;letter-spacing:.04em;fill:{t['primary']}}}"
        f".disp{{font:400 12px 'Space Mono',monospace;letter-spacing:.08em;fill:{t['display']}}}"
        f".h{{font:400 34px 'Space Grotesk',sans-serif;letter-spacing:-.02em;fill:{t['display']}}}"
        f".h2{{font:500 20px 'Space Grotesk',sans-serif;letter-spacing:-.01em;fill:{t['display']}}}"
        f".body{{font:400 14px 'Space Grotesk',sans-serif;letter-spacing:.01em;fill:{t['secondary']}}}"
        ".blink{animation:blink 2s steps(1) infinite}"
        "@keyframes blink{0%{opacity:1}50%{opacity:.15}}"
        "@media (prefers-reduced-motion:reduce){.blink{animation:none}}"
    )


def svg(w, h, t, faces, title, body, extra_defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title><defs><style>{font_css(faces)}{css(t)}</style>{extra_defs}</defs>"
        f"{body}</svg>\n"
    )


def panel(w, h, t):
    return f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="16" fill="{t["black"]}" stroke="{t["border"]}"/>'


def text(x, y, s, cls, anchor="start"):
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return f'<text x="{x}" y="{y}" class="{cls}"{a}>{escape(s)}</text>'


def mono_w(s, size, ls_em=0.0):
    return len(s) * size * (MONO_ADV + ls_em)


def dot_text(s, x0, y0, pitch, r, fill, opacity=1.0):
    """Dot-matrix string. (x0, y0) = centre of the first dot. Returns (svg, columns)."""
    out, col = [], 0
    for ch in s:
        g = GLYPHS[ch]
        for ry, row in enumerate(g):
            for rx, bit in enumerate(row):
                if bit == "1":
                    out.append(f'<circle cx="{x0 + (col + rx) * pitch}" cy="{y0 + ry * pitch}" r="{r}"/>')
        col += len(g[0]) + 1
    op = f' opacity="{opacity}"' if opacity != 1.0 else ""
    return f'<g fill="{fill}"{op}>{"".join(out)}</g>', col - 1


def dot_bg_pattern(t, pitch, ox, oy, r=1.1):
    return (
        f'<pattern id="dg" width="{pitch}" height="{pitch}" patternUnits="userSpaceOnUse" x="{ox}" y="{oy}">'
        f'<circle cx="{pitch/2}" cy="{pitch/2}" r="{r}" fill="{t["dot_bg"]}" opacity="{t["dot_bg_op"]}"/></pattern>'
    )


def wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + (1 if cur else 0) > n:
            lines.append(cur)
            cur = w_
        else:
            cur = f"{cur} {w_}".strip()
    if cur:
        lines.append(cur)
    return lines


# ── assets ───────────────────────────────────────────────────────────────────
def build_hero(t):
    H = 480
    # dot centres sit on a 20px lattice offset (10,10) so the bg pattern lines up
    pat = dot_bg_pattern(t, 20, 0, 0)
    l1, _ = dot_text("VISHAL", 50, 90, 20, 6.5, t["display"])
    l2, cols = dot_text("KUMAR", 50, 250, 20, 6.5, t["display"], 0.4)
    red_x, red_y = 50 + (cols + 1) * 20, 250 + 6 * 20
    body = (
        panel(W, H, t)
        + f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="15" fill="url(#dg)"/>'
        + text(50, 46, "TECHMAHARISHI", "disp")
        + text(750, 46, "FULL-STACK DEVELOPER", "lab", "end")
        + l1 + l2
        + f'<circle class="blink" cx="{red_x}" cy="{red_y}" r="7.5" fill="{ACCENT}"/>'
        + text(50, 440, "BUILDING SCALABLE SAAS APPS", "lab")
        + text(750, 440, "GITHUB / SINCE 2018", "lab", "end")
    )
    return svg(W, H, t, ["mono400"], "Vishal Kumar, full-stack developer", body, pat)


def build_about(t, profile):
    H = 372
    year = profile["created_at"][:4]
    company = (profile.get("company") or "").strip() or "-"
    rows = [
        ("LOCATION", (profile.get("location") or "-").upper(), None),
        ("COMPANY", company.upper(), None),
        ("ROLE", "FULL-STACK DEV", None),
        ("FOCUS", "SCALABLE SAAS", None),
        ("ON GITHUB", f"SINCE {year}", None),
    ]
    if profile.get("hireable"):
        rows.append(("STATUS", "OPEN TO WORK", SUCCESS))
    parts = [
        panel(W, H, t),
        text(40, 46, "01 — ABOUT", "lab"),
        text(760, 46, "PROFILE", "labd", "end"),
        text(40, 130, "Crafting elegant", "h"),
        text(40, 172, "solutions for", "h"),
        text(40, 214, "complex problems.", "h"),
        text(40, 270, "Full-stack developer building", "body"),
        text(40, 292, "scalable SaaS applications.", "body"),
    ]
    y = 84
    for label, value, color in rows:
        parts.append(f'<line x1="440" y1="{y + 42}" x2="760" y2="{y + 42}" stroke="{t["border"]}"/>')
        parts.append(text(440, y + 26, label, "lab"))
        if color:
            vw = mono_w(value, 13, 0.04)
            parts.append(f'<circle cx="{760 - vw - 12}" cy="{y + 22}" r="3" fill="{color}"/>')
            parts.append(f'<text x="760" y="{y + 26}" class="val" text-anchor="end" style="fill:{color}">{escape(value)}</text>')
        else:
            parts.append(text(760, y + 26, value, "val", "end"))
        y += 42
    return svg(W, H, t, ["mono400", "sans400"], "About Vishal Kumar", "".join(parts))


def build_stack(t, repos):
    # language share across original (non-fork) repos
    counts = {}
    for r in repos:
        if not r["fork"] and r["language"]:
            counts[r["language"]] = counts.get(r["language"], 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    total = sum(counts.values())

    groups = [
        ("BACKEND", ["NESTJS", "TYPEORM", "MONGOOSE", "REDIS", "BULL", "OPENAI"]),
        ("FRONTEND", ["REACT", "NEXT.JS", "TAILWIND", "ZUSTAND", "VITE"]),
        ("RUNTIME + TOOLS", ["NODE.JS", "EXPRESS", "TYPESCRIPT", "CAPACITOR"]),
    ]
    H = 636
    parts = [
        panel(W, H, t),
        text(40, 46, "02 — STACK", "lab"),
        text(760, 46, "BY REPO COUNT + DAY JOB", "labd", "end"),
        text(40, 94, "LANGUAGES", "lab"),
    ]
    N, x0, bw = 50, 40, 720
    gap = 2
    sw = (bw - gap * (N - 1)) / N
    y = 120
    opac = [1.0, 0.7, 0.5, 0.4, 0.3]
    for i, (lang, n) in enumerate(top):
        share = n / total
        filled = max(1, round(share * N))
        parts.append(text(40, y + 14, lang.upper(), "disp"))
        parts.append(text(760, y + 14, f"{n} REPOS · {round(share * 100)}%", "lab", "end"))
        segs = []
        for s in range(N):
            fill = t["display"] if s < filled else t["border"]
            op = f' opacity="{opac[i]}"' if s < filled and opac[i] != 1.0 else ""
            segs.append(f'<rect x="{x0 + s * (sw + gap):.2f}" y="{y + 26}" width="{sw:.2f}" height="10" fill="{fill}"{op}/>')
        parts.append("".join(segs))
        y += 56

    y += 14
    for label, tags in groups:
        parts.append(text(40, y, label, "lab"))
        tx, ty = 40, y + 14
        for tag in tags:
            tw = mono_w(tag, 11, 0.06) + 28
            if tx + tw > 760:
                tx, ty = 40, ty + 34
            parts.append(
                f'<rect x="{tx + .5}" y="{ty + .5}" width="{tw:.1f}" height="26" rx="13" fill="none" stroke="{t["border_v"]}"/>'
                f'<text x="{tx + tw / 2:.1f}" y="{ty + 17}" class="lab" text-anchor="middle" style="fill:{t["primary"]}">{escape(tag)}</text>'
            )
            tx += tw + 8
        y = ty + 26 + 30
    return svg(W, H, t, ["mono400"], "Languages by repository and core technologies", "".join(parts))


def build_work_header(t, count):
    H = 56
    body = (
        text(0, 30, "03 — SELECTED WORK", "lab")
        + text(W, 30, f"{count:02d} / PROJECTS", "labd", "end")
        + f'<line x1="0" y1="46" x2="{W}" y2="46" stroke="{t["border"]}"/>'
    )
    return svg(W, H, t, ["mono400"], "Selected work", body)


def build_card(t, idx, title, desc, tags, url_label):
    cw, H = 396, 204
    lines = wrap(desc, 44)[:3]
    parts = [
        panel(cw, H, t),
        text(24, 38, f"{idx:02d}", "lab"),
        text(cw - 24, 38, url_label, "disp" if "LIVE" in url_label else "lab", "end"),
        text(24, 84, title, "h2"),
    ]
    for i, ln in enumerate(lines):
        parts.append(text(24, 114 + i * 20, ln, "body"))
    parts.append(text(24, H - 24, " · ".join(tags), "labd"))
    return svg(cw, H, t, ["mono400", "sans400", "sans500"], f"{title}: {desc}", "".join(parts))


def build_activity(t, total, days, profile):
    H = 340
    start = days[0][0]
    sunday0 = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    pitch, gx, gy = 13.5, 46, 196
    active = sum(1 for d in days if d[2] > 0)
    best = max(d[2] for d in days)

    num, _ = dot_text(str(total), 40, 84, 11, 3.4, t["display"])
    parts = [
        panel(W, H, t),
        text(40, 46, "04 — ACTIVITY", "lab"),
        text(760, 46, "LAST 12 MONTHS", "labd", "end"),
        num,
        text(310, 104, "CONTRIBUTIONS", "disp"),
    ]
    stats = [("ACTIVE DAYS", str(active)), ("BEST DAY", str(best)), ("PUBLIC REPOS", str(profile["public_repos"]))]
    for i, (k, v) in enumerate(stats):
        parts.append(text(520, 78 + i * 22, k, "lab"))
        parts.append(text(760, 78 + i * 22, v, "val", "end"))

    last_month = None
    cells = {0: [], 1: [], 2: [], 3: [], 4: []}
    for d, level, _n in days:
        col = (d - sunday0).days // 7
        row = (d.weekday() + 1) % 7
        cells[level].append((gx + col * pitch, gy + row * pitch))
        if row == 0 and d.month != last_month:
            last_month = d.month
            if col < 51:
                parts.append(text(gx - 4 + col * pitch, gy - 22, d.strftime("%b").upper(), "labd"))
    lv_style = {0: (t["border"], 1.0), 1: (t["display"], 0.3), 2: (t["display"], 0.55), 3: (t["display"], 0.8), 4: (t["display"], 1.0)}
    for level, pts in cells.items():
        fill, op = lv_style[level]
        circles = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3"/>' for x, y in pts)
        opa = f' opacity="{op}"' if op != 1.0 else ""
        parts.append(f'<g fill="{fill}"{opa}>{circles}</g>')

    # legend
    ly = H - 28
    lx = 676  # first legend dot centre
    parts.append(text(lx - 14, ly + 4, "LESS", "labd", "end"))
    for i in range(5):
        fill, op = lv_style[i]
        opa = f' opacity="{op}"' if op != 1.0 else ""
        parts.append(f'<circle cx="{lx + i * 15}" cy="{ly}" r="3.3" fill="{fill}"{opa}/>')
    parts.append(text(lx + 4 * 15 + 14, ly + 4, "MORE", "labd"))
    return svg(W, H, t, ["mono400", "mono700"], f"{total} contributions in the last year", "".join(parts))


def build_footer(t):
    H = 96
    today = dt.date.today().isoformat()
    body = (
        panel(W, H, t)
        + text(40, 54, "[ END OF FILE ]", "disp")
        + text(760, 54, f"SYNCED {today}", "labd", "end")
        + f'<circle cx="{40 + mono_w("[ END OF FILE ]", 12, 0.08) + 18:.1f}" cy="50" r="3" fill="{ACCENT}" class="blink"/>'
    )
    return svg(W, H, t, ["mono400"], "End of file", body)


# ── curated projects (copy written from each repo's README) ──────────────────
PROJECTS = [
    ("StackTube_AI", "StackTube AI",
     "AI-curated computer engineering videos with smart search refinement and focused learning paths.",
     ["TYPESCRIPT", "AI SEARCH"]),
    ("react_to_apk", "APK Automator",
     "Upload a React build, get an Android APK. Wraps your app in Capacitor and builds it for you.",
     ["NEXT.JS", "CAPACITOR", "ANDROID"]),
    ("roadmap", "The Depth Roadmap",
     "Self-hosted tracker for an 8-track learning roadmap. Username and PIN login, progress in MongoDB.",
     ["HTML", "MONGODB", "VERCEL"]),
    ("webworks", "WebWorks",
     "Marketing site for a digital agency: strategic design, content and performance marketing.",
     ["TYPESCRIPT"]),
    ("pycray", "Pycray",
     "Mini event manager. Create, search and delete events with persistent local state.",
     ["NEXT.JS", "ZUSTAND", "TAILWIND"]),
    ("Movix", "Movix",
     "Movie and TV discovery with search, trending and top-rated lists, and infinite scroll.",
     ["JAVASCRIPT"]),
]


def write(name, content):
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  {name:28s} {len(content) / 1024:6.1f} KB")


def main():
    profile = fetch_profile()
    repos = fetch_repos()
    total, days = fetch_contributions()
    by_name = {r["name"]: r for r in repos}
    print(f"{USER}: {len(repos)} repos, {total} contributions, {len(days)} days")

    cards = []
    for repo, title, desc, tags in PROJECTS:
        r = by_name.get(repo)
        home = (r or {}).get("homepage")
        url = home if home else f"https://github.com/{USER}/{repo}"
        cards.append((repo, title, desc, tags, url, "LIVE ↗" if home else "REPO ↗"))

    for mode, t in THEMES.items():
        write(f"hero-{mode}.svg", build_hero(t))
        write(f"about-{mode}.svg", build_about(t, profile))
        write(f"stack-{mode}.svg", build_stack(t, repos))
        write(f"work-header-{mode}.svg", build_work_header(t, len(cards)))
        for i, (repo, title, desc, tags, _url, label) in enumerate(cards, 1):
            write(f"card-{i:02d}-{mode}.svg", build_card(t, i, title, desc, tags, label))
        write(f"activity-{mode}.svg", build_activity(t, total, days, profile))
        write(f"footer-{mode}.svg", build_footer(t))

    write_readme(cards)


def pic(name, alt, extra=""):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">'
        f'<img src="assets/{name}-dark.svg" alt="{escape(alt)}" width="{extra or "100%"}"></picture>'
    )


def write_readme(cards):
    rows = []
    for i in range(0, len(cards), 2):
        pair = []
        for j, (repo, title, desc, _tags, url, _l) in enumerate(cards[i:i + 2], i + 1):
            pair.append(f'<a href="{url}">{pic(f"card-{j:02d}", f"{title}: {desc}", "49%")}</a>')
        rows.append("<p align=\"center\">" + "".join(pair) + "</p>")

    readme = f"""<!-- Generated by scripts/generate.py. Edit the script, not the SVGs. -->
<p align="center">
{pic("hero", "Vishal Kumar, full-stack developer")}
</p>

<p align="center">
{pic("about", "About Vishal Kumar")}
</p>

<p align="center">
{pic("stack", "Languages by repository and core technologies")}
</p>

<p align="center">
{pic("work-header", "Selected work")}
</p>

{chr(10).join(rows)}

<p align="center">
{pic("activity", "Contribution activity over the last 12 months")}
</p>

<p align="center">
{pic("footer", "End of file")}
</p>
"""
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    print("  README.md")


if __name__ == "__main__":
    main()
