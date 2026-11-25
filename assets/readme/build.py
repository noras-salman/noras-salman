#!/usr/bin/env python3
"""Generate the animated SVGs used by the profile README (dark + light variants).

Usage:
  pip install fonttools brotli
  python build.py --fonts <dir with Google Fonts TTFs> --icons <simple-icons/icons dir>

Fonts expected in --fonts (from github.com/google/fonts, OFL):
  InstrumentSerif-Regular.ttf, InstrumentSerif-Italic.ttf,
  JetBrainsMono[wght].ttf, Geist[wght].ttf
Fonts are subset to the glyphs used and embedded as base64 WOFF2, so the SVGs
render identically on GitHub without any external requests.
"""
import argparse, base64, io, math, os, re
from collections import defaultdict
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = os.path.dirname(os.path.abspath(__file__))

PALETTES = {
    "dark": dict(bg="#0b0c10", bg2="#101218", line="#22262f", line2="#2e333e", paper="#ece8df",
                 muted="#8d929c", dim="#5a606b", signal="#f2a65a", mint="#8fd9c0",
                 grid="rgba(236,232,223,.05)", grid2="rgba(236,232,223,.022)",
                 top="#161a22", right="#101319", left="#0b0d11", svctop="#14211e",
                 aitop="#33241a", airight="#1b1510", aileft="#14100c", glow=".40", tile="#12151b"),
    "light": dict(bg="#f7f5f0", bg2="#efece5", line="#dedad1", line2="#cfcac0", paper="#15171c",
                  muted="#5d636e", dim="#8a8f99", signal="#d9772b", mint="#2b8f73",
                  grid="rgba(21,23,28,.06)", grid2="rgba(21,23,28,.028)",
                  top="#ffffff", right="#ebe8e1", left="#e0dcd3", svctop="#e6f4ef",
                  aitop="#fbe6d2", airight="#f1d5bb", aileft="#e8c7a7", glow=".28", tile="#ffffff"),
}

# ---------------------------------------------------------------- fonts
FONT_FILES = {
    "serif": ("InstrumentSerif-Regular.ttf", None),
    "serif-i": ("InstrumentSerif-Italic.ttf", None),
    "mono": ("JetBrainsMono[wght].ttf", 500),
    "sans": ("Geist[wght].ttf", 400),
    "sans-b": ("Geist[wght].ttf", 600),
}
FAMILY = {"serif": "NS Serif", "serif-i": "NS Serif Italic", "mono": "NS Mono", "sans": "NS Sans", "sans-b": "NS Sans Bold"}


class Doc:
    """Collects SVG body + which glyphs each font needs."""
    def __init__(self):
        self.chars = defaultdict(set)
        self.parts = []

    def text(self, font, s, **attrs):
        self.chars[font].update(s)
        a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        esc = s.replace("&", "&amp;").replace("<", "&lt;")
        return f'<text font-family="{FAMILY[font]}" {a}>{esc}</text>'


def font_face(fonts_dir, key, chars):
    fname, wght = FONT_FILES[key]
    font = TTFont(os.path.join(fonts_dir, fname))
    if wght is not None and "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": wght})
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)) + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{FAMILY[key]}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def finish(doc, fonts_dir, w, h, css, body, title):
    title = title.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    faces = "".join(font_face(fonts_dir, k, v) for k, v in doc.chars.items() if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{title}"><title>{title}</title><style>{faces}{css}'
            '@media (prefers-reduced-motion:reduce){*{animation:none!important}.fx{opacity:1!important;transform:none!important}}'
            f'</style>{body}</svg>')


BASE_CSS = """
.fx{opacity:0;animation:rise 1s cubic-bezier(.22,1,.36,1) forwards}
@keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.drop{opacity:0;animation:drop 1s cubic-bezier(.22,1,.36,1) forwards}
@keyframes drop{from{opacity:0;transform:translateY(-46px)}to{opacity:1;transform:none}}
.fade{opacity:0;animation:fade 1s ease forwards}
@keyframes fade{to{opacity:1}}
.base{stroke-dasharray:1200;stroke-dashoffset:1200;animation:draw 1.6s cubic-bezier(.22,1,.36,1) .2s forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.wire{stroke-dasharray:3 6;animation:flow 1.1s linear infinite}
@keyframes flow{to{stroke-dashoffset:-18}}
.glow{animation:glow 3s ease-in-out infinite}
@keyframes glow{0%,100%{opacity:.45}50%{opacity:1}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pls 2.6s ease-in-out infinite}
@keyframes pls{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.35);opacity:.5}}
.blink{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
"""


def grid_bg(p, w, h, rid):
    return (f'<defs><pattern id="g1{rid}" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{p["grid2"]}"/></pattern>'
            f'<pattern id="g2{rid}" width="120" height="120" patternUnits="userSpaceOnUse"><path d="M120 0H0V120" fill="none" stroke="{p["grid"]}"/></pattern>'
            f'<radialGradient id="glow{rid}"><stop offset="0" stop-color="{p["signal"]}" stop-opacity="{p["glow"]}"/><stop offset="1" stop-color="{p["signal"]}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="clip{rid}"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>'
            f'<rect width="{w}" height="{h}" rx="14" fill="{p["bg"]}"/>'
            f'<g clip-path="url(#clip{rid})"><rect width="{w}" height="{h}" fill="url(#g1{rid})"/><rect width="{w}" height="{h}" fill="url(#g2{rid})"/>')


# ---------------------------------------------------------------- banner
def banner(p, fonts_dir):
    W, H = 1280, 370
    d = Doc()
    o = [grid_bg(p, W, H, "b")]
    o.append(f'<ellipse cx="1010" cy="220" rx="360" ry="260" fill="url(#glowb)" opacity=".55"/>')

    # text block
    o.append(f'<g class="fx" style="animation-delay:.1s">{d.text("mono", "SOFTWARE ENGINEER  ·  SYSTEMS ARCHITECT", x=64, y=84, font_size=14, letter_spacing="2.4", fill=p["signal"])}</g>')
    o.append(f'<g class="fx" style="animation-delay:.25s">{d.text("serif", "Noräs", x=60, y=198, font_size=132, letter_spacing="-3", fill=p["paper"])}</g>')
    o.append(f'<g class="fx" style="animation-delay:.4s">{d.text("serif-i", "Salman", x=338, y=198, font_size=132, letter_spacing="-3", fill=p["signal"])}</g>')
    o.append(f'<g class="fx" style="animation-delay:.6s">{d.text("sans", "High-availability systems, applied AI and engineering leadership.", x=64, y=250, font_size=22, fill=p["muted"])}</g>')
    o.append(f'<g class="fx" style="animation-delay:.75s"><circle cx="70" cy="305" r="4" fill="{p["mint"]}"><animate attributeName="opacity" values="1;.3;1" dur="2.4s" repeatCount="indefinite"/></circle>'
             f'{d.text("mono", "BOGOTÁ, COLOMBIA  ·  FROM SWEDEN  ·  IN TECH SINCE 2011", x=86, y=310, font_size=13, letter_spacing="1.6", fill=p["muted"])}</g>')

    # isometric architecture
    S, OX, OY = 20, 1010, 86
    P = lambda x, y, z=0: (OX + (x - y) * S * .866, OY + (x + y) * S * .5 - z * S)
    pts = lambda a: " ".join(f"{x:.1f},{y:.1f}" for x, y in a)

    def box(x, y, z, w, dd, h, stroke, top=None, right=None, left=None):
        t = [P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + dd, z + h), P(x, y + dd, z + h)]
        r = [P(x + w, y, z), P(x + w, y + dd, z), P(x + w, y + dd, z + h), P(x + w, y, z + h)]
        l = [P(x, y + dd, z), P(x + w, y + dd, z), P(x + w, y + dd, z + h), P(x, y + dd, z + h)]
        s = f'stroke="{stroke}" stroke-width="1" stroke-linejoin="round"'
        return (f'<polygon points="{pts(l)}" fill="{left or p["left"]}" {s}/>'
                f'<polygon points="{pts(r)}" fill="{right or p["right"]}" {s}/>'
                f'<polygon points="{pts(t)}" fill="{top or p["top"]}" {s}/>'), P(x + w / 2, y + dd / 2, z + h)

    o.append(f'<polygon class="base" points="{pts([P(0,0),P(10,0),P(10,10),P(0,10)])}" fill="none" stroke="{p["line2"]}"/>')
    gl = []
    for i in range(1, 10):
        a, b = P(i, 0), P(i, 10); gl.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
        a, b = P(0, i), P(10, i); gl.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    o.append(f'<g class="fade" style="animation-delay:.8s" stroke="{p["grid"]}">{"".join(gl)}</g>')

    C = {}
    comps = [
        ("db", 1.0, (7.4, .8, 0, 1.8, 1.8, 2.2, p["dim"])),
        ("edge", 1.15, (.8, .8, 0, 1.8, 1.8, 1.0, p["dim"])),
        ("svc1", 1.3, (3.6, 1.2, 0, 1.4, 1.4, 1.6, p["mint"], p["svctop"])),
        ("queue", 1.45, (6.0, 2.4, 0, .9, 5.2, .7, p["dim"])),
        ("svc2", 1.6, (3.6, 4.3, 0, 1.4, 1.4, 1.6, p["mint"], p["svctop"])),
        ("svc3", 1.75, (3.6, 7.4, 0, 1.4, 1.4, 1.6, p["mint"], p["svctop"])),
        ("ai", 1.95, (7.4, 5.2, 0, 1.8, 1.8, 3.0, p["signal"], p["aitop"], p["airight"], p["aileft"])),
        ("lb", 2.1, (.8, 4.4, 0, 1.8, 1.8, .5, p["dim"])),
    ]
    for key, delay, args in comps:
        svg, c = box(*args)
        C[key] = c
        extra = ""
        if key == "ai":
            cx, cy = P(8.3, 6.1, 1.5)
            extra = f'<ellipse class="glow" cx="{cx:.1f}" cy="{cy:.1f}" rx="90" ry="60" fill="url(#glowb)"/>'
        o.append(f'<g class="drop" style="animation-delay:{delay}s">{extra}{svg}</g>')

    wires = [("edge", "svc1"), ("lb", "svc2"), ("edge", "lb"), ("lb", "svc3"), ("svc1", "queue"), ("svc2", "queue"),
             ("svc3", "queue"), ("queue", "db"), ("queue", "ai"), ("ai", "db")]
    wl = []
    for i, (a, b) in enumerate(wires):
        A, B = C[a], C[b]
        mx, my = (A[0] + B[0]) / 2, min(A[1], B[1]) - 20
        path = f"M{A[0]:.1f},{A[1]:.1f} Q{mx:.1f},{my:.1f} {B[0]:.1f},{B[1]:.1f}"
        hot = "ai" in (a, b)
        col = p["signal"] if hot else p["mint"]
        wl.append(f'<path class="wire" d="{path}" fill="none" stroke="{col}" stroke-opacity="{.6 if hot else .45}"/>')
        wl.append(f'<circle r="2.4" fill="{col}"><animateMotion dur="{1.7 + (i % 4) * .35:.2f}s" begin="{2.4 + i * .27:.2f}s" repeatCount="indefinite" path="{path}"/></circle>')
    for i, k in enumerate(["svc1", "svc2", "svc3"]):
        wl.append(f'<circle class="pulse" style="animation-delay:{i*.4}s" cx="{C[k][0]:.1f}" cy="{C[k][1]:.1f}" r="2.6" fill="{p["mint"]}"/>')
    o.append(f'<g class="fade" style="animation-delay:2.4s">{"".join(wl)}</g>')

    lab = []
    def label(key, dx, dy, txt, col):
        x, y = C[key]; lx, ly = x + dx, y + dy; s = 1 if dx > 0 else -1
        lab.append(f'<path d="M{x:.1f},{y:.1f} L{lx:.1f},{ly:.1f} L{lx + s*22:.1f},{ly:.1f}" stroke="{p["line2"]}" fill="none"/>')
        lab.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{p["muted"]}"/>')
        lab.append(d.text("mono", txt, x=f"{lx + s*27:.1f}", y=f"{ly + 3.5:.1f}", font_size=10.5, fill=col, text_anchor="start" if s > 0 else "end"))
    label("edge", -40, -40, "api gateway", p["muted"])
    label("svc1", 26, -66, "services ×3", p["mint"])
    label("db", 30, -40, "datastore", p["muted"])
    label("ai", 92, 30, "llm / ml engine", p["signal"])
    label("queue", 46, 84, "event bus", p["muted"])
    label("lb", -34, 40, "load balancer", p["muted"])
    o.append(f'<g class="fade" style="animation-delay:2.7s">{"".join(lab)}</g>')

    o.append("</g>")  # clip
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{p["line"]}"/>')
    return finish(d, fonts_dir, W, H, BASE_CSS, "".join(o), "Noräs Salman: software engineer and systems architect")


# ---------------------------------------------------------------- stack row
def icon_path(icons_dir, slug):
    s = open(os.path.join(icons_dir, slug + ".svg")).read()
    return re.search(r'<path d="([^"]+)"', s).group(1)


def stack(p, fonts_dir, icons_dir):
    items = [("TypeScript", "typescript"), ("JavaScript", "javascript"), ("Node.js", "nodedotjs"), ("Go", "go"),
             ("Python", "python"), ("AI / LLMs", None), ("AWS", None), ("Docker", "docker"), ("MongoDB", "mongodb"),
             ("RabbitMQ", "rabbitmq"), ("Vue.js", "vuedotjs"), ("React", "react"), ("Kotlin", "kotlin"), ("CI/CD", "githubactions")]
    W, H = 1280, 150
    d = Doc()
    o = [f'<rect width="{W}" height="{H}" rx="14" fill="{p["bg"]}"/><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{p["line"]}"/>']
    n = len(items); colw = (W - 64) / n
    for i, (name, slug) in enumerate(items):
        cx = 32 + colw * i + colw / 2
        tile = f'<rect x="{cx-27:.1f}" y="26" width="54" height="54" rx="12" fill="{p["tile"]}" stroke="{p["line2"]}"/>'
        hl = name in ("TypeScript", "AI / LLMs")
        if hl:
            tile = f'<rect x="{cx-27:.1f}" y="26" width="54" height="54" rx="12" fill="{p["tile"]}" stroke="{p["signal"]}"/>'
        col = p["signal"] if hl else p["paper"]
        if slug:
            ic = f'<g transform="translate({cx-13:.1f},40) scale({26/24:.4f})"><path d="{icon_path(icons_dir, slug)}" fill="{col}"/></g>'
        elif name == "AWS":
            ic = (d.text("sans-b", "aws", x=f"{cx:.1f}", y="56", font_size=19, fill=col, text_anchor="middle") +
                  f'<path d="M{cx-14:.1f} 61 Q{cx:.1f} 69 {cx+14:.1f} 61" stroke="{p["signal"]}" stroke-width="2.2" fill="none" stroke-linecap="round"/>'
                  f'<path d="M{cx+10:.1f} 59.5 L{cx+15:.1f} 60.5 L{cx+13.5:.1f} 65.5" stroke="{p["signal"]}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        else:  # AI / LLMs: tiny neural net
            pts_ = [(-9, -8), (-9, 8), (0, -10), (0, 0), (0, 10), (9, -5), (9, 5)]
            edges = [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4), (2, 5), (3, 5), (3, 6), (4, 6), (2, 6), (4, 5)]
            ic = "".join(f'<line x1="{cx+pts_[a][0]:.1f}" y1="{53+pts_[a][1]}" x2="{cx+pts_[b][0]:.1f}" y2="{53+pts_[b][1]}" stroke="{col}" stroke-opacity=".55" stroke-width="1"/>' for a, b in edges)
            ic += "".join(f'<circle cx="{cx+x:.1f}" cy="{53+y}" r="2.6" fill="{col}"><animate attributeName="opacity" values="1;.35;1" dur="1.8s" begin="{k*.2:.1f}s" repeatCount="indefinite"/></circle>' for k, (x, y) in enumerate(pts_))
        lbl = d.text("mono", name, x=f"{cx:.1f}", y="108", font_size=11.5, fill=p["muted"] if not hl else p["signal"], text_anchor="middle")
        o.append(f'<g class="fx" style="animation-delay:{.1 + i*.06:.2f}s">{tile}{ic}{lbl}</g>')
    return finish(d, fonts_dir, W, H, BASE_CSS, "".join(o), "Tech stack: TypeScript, JavaScript, Node.js, Go, Python, AI and LLMs, AWS, Docker, MongoDB, RabbitMQ, Vue.js, React, Kotlin, CI/CD")


# ---------------------------------------------------------------- project cards
CARDS = [
    dict(slug="site", kicker="WEBSITE", title="Interactive résumé",
         desc=["Experience, applied AI and an isometric", "architecture explorer. Hand-built."],
         foot="noras-salman.github.io/noras-salman", art="browser"),
    dict(slug="baton", kicker="OPEN SOURCE", title="baton",
         desc=["Desktop app for Claude Code: park sessions", "as tasks, track PRs and get notified."],
         foot="github.com/noras-salman/baton", art="terminal"),
    dict(slug="ids", kicker="RESEARCH · CHALMERS × VOLVO CARS", title="In-vehicle intrusion detection",
         desc=["A lightweight IDS for the CAN bus, tested", "on a real in-vehicle network."],
         foot="M.Sc. thesis · 2017", art="shield"),
    dict(slug="saas", kicker="RESEARCH · BTH", title="The Labor–R&D nexus in SaaS",
         desc=["Stochastic frontier analysis of what", "drives profitability in SaaS firms."],
         foot="MBA thesis · 2023", art="chart"),
]


def card_art(p, kind, x, y):
    s, m, line = p["signal"], p["mint"], p["line2"]
    if kind == "browser":
        return (f'<g transform="translate({x},{y})"><rect width="150" height="104" rx="8" fill="{p["bg2"]}" stroke="{line}"/>'
                f'<path d="M0 22H150" stroke="{line}"/><circle cx="14" cy="11" r="3" fill="{line}"/><circle cx="25" cy="11" r="3" fill="{line}"/><circle cx="36" cy="11" r="3" fill="{line}"/>'
                f'<rect x="14" y="36" width="56" height="8" rx="2" fill="{s}"><animate attributeName="width" values="0;56;56;0" keyTimes="0;.35;.85;1" dur="4s" repeatCount="indefinite"/></rect>'
                f'<rect x="14" y="52" width="86" height="5" rx="2" fill="{line}"/><rect x="14" y="63" width="70" height="5" rx="2" fill="{line}"/>'
                f'<g transform="translate(112,74)"><polygon points="0,-12 14,-5 0,2 -14,-5" fill="none" stroke="{s}"/><polygon points="0,-4 14,3 0,10 -14,3" fill="none" stroke="{m}" opacity=".7"/></g></g>')
    if kind == "terminal":
        return (f'<g transform="translate({x},{y})"><rect width="150" height="104" rx="8" fill="{p["bg2"]}" stroke="{line}"/>'
                f'<path d="M16 30 L26 38 L16 46" stroke="{m}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<rect x="34" y="35" width="8" height="12" fill="{s}" class="blink"/>'
                f'<rect x="16" y="60" width="96" height="5" rx="2" fill="{line}"/><rect x="16" y="72" width="70" height="5" rx="2" fill="{line}"/><rect x="16" y="84" width="84" height="5" rx="2" fill="{line}"/>'
                f'<circle cx="130" cy="20" r="5" fill="{s}" class="pulse"/></g>')
    if kind == "shield":
        return (f'<g transform="translate({x},{y})">'
                f'<path d="M0 52 H150" stroke="{line}" stroke-dasharray="3 5"/>'
                f'<circle r="3" fill="{m}"><animateMotion dur="2.4s" repeatCount="indefinite" path="M0,52 H150"/></circle>'
                f'<path d="M75 8 L106 20 V48 C106 70 92 84 75 92 C58 84 44 70 44 48 V20 Z" fill="{p["bg2"]}" stroke="{s}" stroke-width="1.4"/>'
                f'<path d="M62 50 L72 60 L90 40" stroke="{m}" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>')
    return (f'<g transform="translate({x},{y})"><path d="M0 100H150M0 70H150M0 40H150M0 10H150" stroke="{line}"/>'
            f'<path d="M0 92 C30 90 44 74 62 68 S96 56 108 38 S136 16 150 10" stroke="{s}" stroke-width="2" fill="none" stroke-linecap="round" stroke-dasharray="260" stroke-dashoffset="260">'
            f'<animate attributeName="stroke-dashoffset" values="260;0;0;260" keyTimes="0;.45;.85;1" dur="4.5s" repeatCount="indefinite"/></path>'
            f'<circle cx="62" cy="68" r="4" fill="{p["bg"]}" stroke="{m}" stroke-width="1.6"/><circle cx="108" cy="38" r="4" fill="{p["bg"]}" stroke="{m}" stroke-width="1.6"/></g>')


def card(p, fonts_dir, c):
    W, H = 640, 220
    d = Doc()
    o = [f'<rect width="{W}" height="{H}" rx="14" fill="{p["bg"]}"/><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{p["line"]}"/>']
    o.append(d.text("mono", c["kicker"], x=32, y=46, font_size=12.5, letter_spacing="1.8", fill=p["signal"]))
    o.append(d.text("serif", c["title"], x=30, y=96, font_size=40, letter_spacing="-.6", fill=p["paper"]))
    for i, line in enumerate(c["desc"]):
        o.append(d.text("sans", line, x=32, y=132 + i * 25, font_size=18, fill=p["muted"]))
    o.append(d.text("mono", c["foot"] + "  ↗", x=32, y=196, font_size=12.5, fill=p["dim"]))
    o.append(card_art(p, c["art"], 458, 58))
    return finish(d, fonts_dir, W, H, BASE_CSS, "".join(o), f'{c["title"]}: {" ".join(c["desc"])}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--icons", required=True)
    a = ap.parse_args()
    for mode, p in PALETTES.items():
        out = {f"banner-{mode}.svg": banner(p, a.fonts), f"stack-{mode}.svg": stack(p, a.fonts, a.icons)}
        for c in CARDS:
            out[f"card-{c['slug']}-{mode}.svg"] = card(p, a.fonts, c)
        for name, svg in out.items():
            with open(os.path.join(HERE, name), "w") as f:
                f.write(svg)
            print(f"{name:28s} {len(svg)/1024:6.1f} KB")


if __name__ == "__main__":
    main()
