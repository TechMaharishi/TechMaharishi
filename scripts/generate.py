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


def section(x, y, s):
    """Panel label with a red signal dot, Nothing's recording-light motif."""
    return f'<circle cx="{x + 3}" cy="{y - 4}" r="3" fill="{ACCENT}"/>' + text(x + 14, y, s, "lab")


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
    H = 260
    # one line: VISHAL (35 cols) + 3 blank cols + KUMAR (29 cols) + period.
    # Dot centres sit on a 10px lattice offset (5,5) so the bg pattern lines up.
    pitch, r, x0, y0 = 10, 3.5, 45, 95
    pat = dot_bg_pattern(t, pitch, 0, 0, 0.9)
    l1, _ = dot_text("VISHAL", x0, y0, pitch, r, t["display"])
    l2, cols = dot_text("KUMAR", x0 + 38 * pitch, y0, pitch, r, t["display"], 0.4)
    red_x, red_y = x0 + (38 + cols + 1) * pitch, y0 + 6 * pitch
    body = (
        panel(W, H, t)
        + f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="15" fill="url(#dg)"/>'
        + text(45, 46, "TECHMAHARISHI", "disp")
        + text(755, 46, "FULL-STACK DEVELOPER", "lab", "end")
        + l1 + l2
        + f'<circle class="blink" cx="{red_x}" cy="{red_y}" r="4.5" fill="{ACCENT}"/>'
        + text(45, 222, "I TURN HARD PROBLEMS INTO WORKING SOFTWARE", "lab")
        + text(755, 222, "GITHUB / SINCE 2018", "lab", "end")
    )
    return svg(W, H, t, ["mono400"], "Vishal Kumar, full-stack developer", body, pat)


def build_about(t, profile):
    H = 346
    year = profile["created_at"][:4]
    rows = [
        ("LOCATION", (profile.get("location") or "-").upper(), None),
        ("ROLE", "FULL-STACK DEV", None),
        ("FOCUS", "END-TO-END DELIVERY", None),
        ("ON GITHUB", f"SINCE {year}", None),
    ]
    if profile.get("hireable"):
        rows.append(("STATUS", "OPEN TO WORK", SUCCESS))
    parts = [
        panel(W, H, t),
        section(40, 46, "ABOUT"),
        text(760, 46, "PROFILE", "labd", "end"),
        text(40, 130, "You bring the", "h"),
        text(40, 172, "problem. I ship", "h"),
        f'<text x="40" y="214" class="h">the solution<tspan style="fill:{ACCENT}">.</tspan></text>',
        text(40, 270, "Full-stack developer across web, mobile and", "body"),
        text(40, 292, "backend. I help businesses untangle messy", "body"),
        text(40, 314, "problems and ship software that holds up.", "body"),
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


def build_stack(t):
    groups = [
        ("FRONTEND", ["REACT", "NEXT.JS", "TYPESCRIPT", "JAVASCRIPT", "TAILWIND", "REDUX", "ZUSTAND", "VITE"]),
        ("MOBILE", ["REACT NATIVE", "EXPO", "CAPACITOR"]),
        ("BACKEND", ["NODE.JS", "NESTJS", "EXPRESS", "TYPEORM", "MONGOOSE", "BULL"]),
        ("DATA + AI", ["MONGODB", "REDIS", "OPENAI"]),
    ]
    parts = [section(40, 46, "STACK"), text(760, 46, "TOOLS I USE", "labd", "end")]
    y = 92
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
        y = ty + 26 + 34
    H = int(y - 4)
    return svg(W, H, t, ["mono400"], "Technologies and tools", panel(W, H, t) + "".join(parts))


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
        section(40, 46, "ACTIVITY"),
        text(760, 46, "LAST 12 MONTHS", "labd", "end"),
        num,
        text(310, 104, "CONTRIBUTIONS", "disp"),
    ]
    stats = [("ACTIVE DAYS", str(active)), ("BEST DAY", str(best)), ("PUBLIC REPOS", str(profile["public_repos"]))]
    for i, (k, v) in enumerate(stats):
        parts.append(text(520, 78 + i * 22, k, "lab"))
        if k == "BEST DAY":
            parts.append(f'<text x="760" y="{78 + i * 22}" class="val" text-anchor="end" style="fill:{ACCENT}">{v}</text>')
        else:
            parts.append(text(760, 78 + i * 22, v, "val", "end"))

    last_month = None
    cells = {0: [], 1: [], 2: [], 3: [], 4: []}
    best_pt = None
    for d, level, _n in days:
        col = (d - sunday0).days // 7
        row = (d.weekday() + 1) % 7
        if _n == best and best_pt is None:
            best_pt = (gx + col * pitch, gy + row * pitch)
            continue
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

    if best_pt:
        parts.append(f'<circle cx="{best_pt[0]:.1f}" cy="{best_pt[1]:.1f}" r="3.8" fill="{ACCENT}"/>')

    # legend
    ly = H - 28
    lx = 652  # first legend dot centre ("MORE" ends at the 760 margin)
    parts.append(text(lx - 14, ly + 4, "LESS", "labd", "end"))
    for i in range(5):
        fill, op = lv_style[i]
        opa = f' opacity="{op}"' if op != 1.0 else ""
        parts.append(f'<circle cx="{lx + i * 15}" cy="{ly}" r="3.3" fill="{fill}"{opa}/>')
    parts.append(text(lx + 4 * 15 + 14, ly + 4, "MORE", "labd"))
    return svg(W, H, t, ["mono400", "mono700"], f"{total} contributions in the last year", "".join(parts))


def write(name, content):
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  {name:28s} {len(content) / 1024:6.1f} KB")


def main():
    profile = fetch_profile()
    repos = fetch_repos()
    total, days = fetch_contributions()
    print(f"{USER}: {len(repos)} repos, {total} contributions, {len(days)} days")

    for mode, t in THEMES.items():
        write(f"hero-{mode}.svg", build_hero(t))
        write(f"about-{mode}.svg", build_about(t, profile))
        write(f"stack-{mode}.svg", build_stack(t))
        write(f"activity-{mode}.svg", build_activity(t, total, days, profile))

    write_readme()


def pic(name, alt, extra=""):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">'
        f'<img src="assets/{name}-dark.svg" alt="{escape(alt)}" width="{extra or "100%"}"></picture>'
    )


def write_readme():
    blocks = [
        ("hero", "Vishal Kumar, full-stack developer"),
        ("about", "About Vishal Kumar"),
        ("stack", "Technologies and tools"),
        ("activity", "Contribution activity over the last 12 months"),
    ]
    body = "\n\n".join(f'<p align="center">\n{pic(n, a)}\n</p>' for n, a in blocks)
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write("<!-- Generated by scripts/generate.py. Edit the script, not the SVGs. -->\n" + body + "\n")
    print("  README.md")


if __name__ == "__main__":
    main()
