# Brief: renders report.pdf from report.tex with ReportLab, for machines with no LaTeX
# toolchain. It is NOT a LaTeX engine: it understands only the restricted subset that
# report.tex uses (sections, paragraphs, itemize/enumerate, tabular with booktabs rules,
# figure, table, lstlisting, abstract, \cite/\ref, simple math, bibliography from refs.bib).
# The .tex stays the single source of truth; real LaTeX (Overleaf) will typeset the same file.
# Usage: python3 pca_routing/assignment/report/build_pdf.py   ->   report/report.pdf

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle, XPreformatted)

HERE = Path(__file__).resolve().parent
LIB = "/usr/share/fonts/truetype/liberation/"
DJV = "/usr/share/fonts/truetype/dejavu/"

pdfmetrics.registerFont(TTFont("Body", LIB + "LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Body-B", LIB + "LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Body-I", LIB + "LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Body-BI", LIB + "LiberationSerif-BoldItalic.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-BI")
pdfmetrics.registerFont(TTFont("Mono", DJV + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("Mono-B", DJV + "DejaVuSansMono-Bold.ttf"))
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-B", italic="Mono", boldItalic="Mono-B")

BASE = 10.5
S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=BASE, leading=BASE * 1.32,
                           alignment=TA_JUSTIFY, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="Body-B", fontSize=15, leading=19, spaceBefore=14, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Body-B", fontSize=12, leading=15, spaceBefore=10, spaceAfter=4),
    "para": ParagraphStyle("para", parent=None, fontName="Body", fontSize=BASE, leading=BASE * 1.32,
                           alignment=TA_JUSTIFY, spaceBefore=4, spaceAfter=6),
    "title": ParagraphStyle("title", fontName="Body-B", fontSize=19, leading=25, alignment=TA_CENTER,
                            spaceAfter=14),
    "author": ParagraphStyle("author", fontName="Body", fontSize=13, leading=17, alignment=TA_CENTER,
                             spaceAfter=4),
    "caption": ParagraphStyle("caption", fontName="Body", fontSize=9.5, leading=12, alignment=TA_CENTER,
                              spaceBefore=3, spaceAfter=10),
    "item": ParagraphStyle("item", fontName="Body", fontSize=BASE, leading=BASE * 1.32,
                           alignment=TA_JUSTIFY, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=9, leading=11),
    "abstract": ParagraphStyle("abstract", fontName="Body", fontSize=9.8, leading=13, alignment=TA_JUSTIFY,
                               leftIndent=1.0 * cm, rightIndent=1.0 * cm, spaceAfter=10),
    "bib": ParagraphStyle("bib", fontName="Body", fontSize=9.5, leading=12, leftIndent=18,
                          firstLineIndent=-18, spaceAfter=3),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.6, leading=9.6, backColor=colors.Color(.96, .96, .96),
                           borderColor=colors.Color(.6, .6, .6), borderWidth=0.5, borderPadding=4,
                           leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=2),
}

# ---------------------------------------------------------------------------
# inline LaTeX -> ReportLab paragraph markup
# ---------------------------------------------------------------------------

MATH_SYMBOLS = {
    "Theta": "Θ", "Omega": "Ω", "infty": "∞", "cdot": "·", "times": "×", "le": "≤", "leq": "≤",
    "ge": "≥", "geq": "≥", "to": "→", "rightarrow": "→", "sum": "Σ", "mu": "μ", "approx": "≈",
    "ne": "≠", "ldots": "…", "ell": "ℓ", "delta": "δ", "in": '<font name="Mono">∈</font>',
}
MATH_ROMAN = {"log", "min", "max", "sin", "cos"}  # function names stay upright


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def read_group(s: str, i: int) -> tuple[str, int]:
    """s[i] must be '{'; returns (content, index after the matching '}')."""
    assert s[i] == "{", s[i:i + 20]
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces: " + s[i:i + 40])


def math_to_markup(m: str) -> str:
    """The small math subset used in report.tex -> italic letters, sub/superscripts, symbols."""
    out, i = [], 0

    def sub_sup(i: int, tag: str) -> int:
        i += 1
        if i < len(m) and m[i] == "{":
            grp, i = read_group(m, i)
        else:
            grp, i = m[i], i + 1
        out.append(f"<{tag}>{math_to_markup(grp)}</{tag}>")
        return i

    while i < len(m):
        c = m[i]
        if c == "\\":
            mm = re.match(r"\\([A-Za-z]+)", m[i:])
            if mm:
                name = mm.group(1)
                i += len(mm.group(0))
                if name in MATH_SYMBOLS:
                    out.append(MATH_SYMBOLS[name])
                elif name in MATH_ROMAN:
                    out.append(name)
                elif name in ("text", "mathrm"):
                    grp, i = read_group(m, i)
                    out.append(esc(grp))
                elif name in ("bigl", "bigr", "left", "right"):
                    pass
                else:
                    raise ValueError(f"unsupported math command \\{name}")
            else:  # \  \, \; \{ \} \%
                nxt = m[i + 1]
                out.append({" ": " ", ",": "\u2009", ";": "\u2005"}.get(nxt, esc(nxt)))
                i += 2
        elif c == "^":
            i = sub_sup(i, "super")
        elif c == "_":
            i = sub_sup(i, "sub")
        elif c.isalpha():
            j = i
            while j < len(m) and m[j].isalpha():
                j += 1
            out.append(f"<i>{m[i:j]}</i>")
            i = j
        elif c in "{}":
            i += 1
        else:
            out.append(esc(c))
            i += 1
    return "".join(out)


class Ctx:
    """Label numbering and citation numbering shared across the two passes."""

    def __init__(self) -> None:
        self.labels: dict[str, str] = {}
        self.cites: list[str] = []
        self.bib_numbers: dict[str, int] = {}


def inline(text: str, ctx: Ctx) -> str:
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c == "$":
            j = text.index("$", i + 1)
            out.append(math_to_markup(text[i + 1:j]))
            i = j + 1
        elif c == "\\":
            mm = re.match(r"\\([A-Za-z]+)\*?", text[i:])
            if not mm:
                nxt = text[i + 1]
                out.append({"&": "&amp;", "%": "%", "_": "_", "#": "#", "{": "{", "}": "}", "$": "$",
                            " ": " ", ",": "\u2009", "\\": "<br/>"}.get(nxt, esc(nxt)))
                i += 2
                continue
            name, i = mm.group(1), i + len(mm.group(0))
            if name in ("texttt", "emph", "textit", "textbf", "url", "textsc"):
                grp, i = read_group(text, i)
                if name == "texttt":
                    out.append('<font name="Mono" size="%.1f">%s</font>' % (BASE - 1.2, inline_tt(grp)))
                elif name in ("emph", "textit"):
                    out.append("<i>%s</i>" % inline(grp, ctx))
                elif name == "textbf":
                    out.append("<b>%s</b>" % inline(grp, ctx))
                else:
                    out.append(inline(grp, ctx))
            elif name == "cite":
                grp, i = read_group(text, i)
                nums = sorted(ctx.bib_numbers.get(k.strip(), 0) for k in grp.split(","))
                out.append("[" + ", ".join(str(n) if n else "?" for n in nums) + "]")
            elif name in ("ref", "pageref"):
                grp, i = read_group(text, i)
                out.append(ctx.labels.get(grp, "??"))
            elif name == "ldots":
                out.append("…")
            else:
                raise ValueError(f"unsupported text command \\{name}")
        elif c == "~":
            out.append("\u00a0")
            i += 1
        elif text.startswith("---", i):
            out.append("—")
            i += 3
        elif text.startswith("--", i):
            out.append("–")
            i += 2
        elif text.startswith("``", i):
            out.append("“")
            i += 2
        elif text.startswith("''", i):
            out.append("”")
            i += 2
        elif c in "{}":
            i += 1
        else:
            out.append(esc(c))
            i += 1
    return "".join(out)


def inline_tt(text: str) -> str:
    return esc(re.sub(r"\\([_#%&{}$])", r"\1", text).replace("\\textbackslash", "\\"))


# ---------------------------------------------------------------------------
# document parsing
# ---------------------------------------------------------------------------

def strip_comments(tex: str) -> str:
    """Drop % comments (not \\%) outside lstlisting blocks."""
    out, in_lst = [], False
    for line in tex.splitlines():
        if r"\begin{lstlisting}" in line:
            in_lst = True
        if in_lst:
            out.append(line)
            if r"\end{lstlisting}" in line:
                in_lst = False
            continue
        out.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(out)


def get_cmd(tex: str, name: str) -> str:
    i = tex.index("\\" + name + "{")
    return read_group(tex, i + len(name) + 1)[0]


def split_blocks(body: str) -> list[tuple]:
    """Top-level body -> list of (kind, payload). Environments are kept whole."""
    blocks, i = [], 0
    env = re.compile(r"\\begin\{(lstlisting|figure|table|itemize|enumerate|abstract)\}")
    buf: list[str] = []

    def flush():
        txt = "\n".join(buf).strip()
        buf.clear()
        if txt:
            for para in re.split(r"\n\s*\n", txt):
                if para.strip():
                    blocks.append(("text", para.strip()))

    lines = body.split("\n")
    while i < len(lines):
        line = lines[i]
        m = env.search(line)
        if m and line.strip().startswith("\\begin"):
            flush()
            name = m.group(1)
            chunk = [line]
            while not re.search(r"\\end\{%s\}" % name, lines[i]):
                i += 1
                chunk.append(lines[i])
            blocks.append((name, "\n".join(chunk)))
        else:
            buf.append(line)
        i += 1
    flush()
    return blocks


def number_labels(blocks: list[tuple], ctx: Ctx) -> None:
    sec = sub = fig = tab = lst = 0
    for kind, payload in blocks:
        if kind == "text":
            m = re.match(r"\\(section|subsection)\{.*?\}\s*(\\label\{([^}]*)\})?", payload, re.S)
            if m:
                if m.group(1) == "section":
                    sec, sub = sec + 1, 0
                    num = str(sec)
                else:
                    sub += 1
                    num = f"{sec}.{sub}"
                if m.group(3):
                    ctx.labels[m.group(3)] = num
        elif kind in ("figure", "table", "lstlisting"):
            lab = re.search(r"\\label\{([^}]*)\}", payload) or re.search(r"label=\{([^}]*)\}", payload)
            if kind == "figure":
                fig += 1
                n = fig
            elif kind == "table":
                tab += 1
                n = tab
            else:
                lst += 1
                n = lst
            if lab:
                ctx.labels[lab.group(1)] = str(n)


def parse_bib(path: Path) -> dict[str, dict]:
    entries = {}
    txt = path.read_text(encoding="utf8")
    for m in re.finditer(r"@(\w+)\{([^,]+),", txt):
        start = m.end()
        depth, j = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(txt[j], 0)
            j += 1
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\d+)", txt[start:j - 1]):
            v = fm.group(2)
            fields[fm.group(1).lower()] = v[1:-1] if v.startswith("{") else v
        entries[m.group(2).strip()] = {"type": m.group(1), **fields}
    return entries


def fmt_bib(e: dict) -> str:
    def clean(s: str) -> str:
        return re.sub(r"[{}]", "", s).replace("--", "–").replace("\\&", "&")

    authors = clean(e.get("author", "")).replace(" and ", "; ").replace("others", "et al").rstrip(".")
    parts = []
    if authors:
        parts.append(authors + ".")
    parts.append(clean(e.get("title", "")).rstrip(".") + ".")
    venue = e.get("journal") or e.get("booktitle") or e.get("howpublished") or ""
    vol = e.get("volume", "")
    if venue:
        v = "<i>%s</i>" % esc(clean(venue))
        if vol:
            v += ", " + vol + (f"({e['number']})" if "number" in e else "")
        if "pages" in e:
            v += ", pp. " + clean(e["pages"])
        parts.append(v + ",")
    parts.append(e.get("year", "") + ".")
    return esc_keep_tags(" ".join(parts))


def esc_keep_tags(s: str) -> str:
    return re.sub(r"&(?!amp;)", "&amp;", s)


# ---------------------------------------------------------------------------
# flowable builders
# ---------------------------------------------------------------------------

TEXT_W = A4[0] - 5 * cm


def build_table(payload: str, ctx: Ctx, number: int):
    cap = re.search(r"\\caption\{", payload)
    caption = read_group(payload, cap.end() - 1)[0] if cap else ""
    tab = re.search(r"\\begin\{tabular\}", payload)
    spec, after = read_group(payload, tab.end())
    inner = payload[after:payload.index("\\end{tabular}")]
    cols = re.findall(r"p\{[^}]*\}|[lrc]", spec)
    # rule positions are expressed as "line above row k"
    rows, rules = [], {}
    chunks = re.split(r"\\\\", inner)
    for chunk in chunks:
        rule_marks = re.findall(r"\\(toprule|midrule|bottomrule)", chunk)
        chunk = re.sub(r"\\(toprule|midrule|bottomrule)", "", chunk).strip()
        if rule_marks:
            rules[len(rows)] = rule_marks[0]
        if chunk:
            rows.append([c.strip() for c in chunk.split("&")])
    if rule_marks and rules.get(len(rows)) is None:
        rules[len(rows)] = rule_marks[-1]

    data, spans, plain = [], [], []
    for r, row in enumerate(rows):
        out_row, plain_row, c = [], [], 0
        for cell in row:
            mm = re.match(r"\\multicolumn\{(\d+)\}\{(\w)\}\{(.*)\}$", cell, re.S)
            ncols = 1
            if mm:
                ncols, cell = int(mm.group(1)), mm.group(3)
                spans.append(("SPAN", (c, r), (c + ncols - 1, r)))
            al = cols[c][0] if c < len(cols) else "l"
            st = ParagraphStyle("c", parent=S["cell"], alignment={"l": 0, "r": 2, "c": 1, "p": 0}[al])
            if mm:
                st = ParagraphStyle("c", parent=S["cell"], alignment=1)
            out_row.append(Paragraph(inline(cell, ctx), st))
            plain_row.append(cell)
            for _ in range(ncols - 1):
                out_row.append("")
                plain_row.append("")
            c += ncols
        data.append(out_row)
        plain.append(plain_row)

    ncol = len(cols)
    widths = [0.0] * ncol
    fixed = set()
    for ci, spec_c in enumerate(cols):
        if spec_c.startswith("p"):
            fixed.add(ci)
            widths[ci] = float(re.search(r"([\d.]+)cm", spec_c).group(1)) * cm
    for ci in range(ncol):
        if ci in fixed:
            continue
        w = 0.0
        for row in rows:
            if ci < len(row) and "\\multicolumn" not in row[ci]:
                txt = re.sub(r"\\[A-Za-z]+|[${}\\]", "", row[ci])
                w = max(w, pdfmetrics.stringWidth(txt, "Body", 9))
        widths[ci] = w + (26 if any('$' in r[ci] for r in rows if ci < len(r)) else 12)
    total = sum(widths)
    if total > TEXT_W:
        free = [ci for ci in range(ncol) if ci not in fixed]
        over = total - TEXT_W
        fsum = sum(widths[ci] for ci in free)
        for ci in free:
            widths[ci] -= over * widths[ci] / fsum
    t = Table(data, colWidths=widths, hAlign="CENTER")
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LEFTPADDING", (0, 0), (-1, -1), 4),
             ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    for k, kind in rules.items():
        w = 1.0 if kind in ("toprule", "bottomrule") else 0.5
        # per-column commands: ReportLab drops full-width line commands on rows next to a SPAN
        for ci in range(ncol):
            if k == 0:
                style.append(("LINEABOVE", (ci, 0), (ci, 0), w, colors.black))
            else:
                style.append(("LINEBELOW", (ci, k - 1), (ci, k - 1), w, colors.black))
    t.setStyle(TableStyle(style + spans))
    cap_p = Paragraph(f"<b>Table {number}.</b> {inline(caption, ctx)}", S["caption"])
    return KeepTogether([Spacer(1, 4), t, cap_p])


def build_figure(payload: str, ctx: Ctx, number: int):
    cap = re.search(r"\\caption\{", payload)
    caption = read_group(payload, cap.end() - 1)[0]
    inc = re.search(r"\\includegraphics\[width=([\d.]+)\\textwidth\]\{([^}]*)\}", payload)
    frac, rel = float(inc.group(1)), inc.group(2)
    img_path = (HERE / rel).resolve()
    w = frac * TEXT_W
    from PIL import Image as PILImage
    with PILImage.open(img_path) as im:
        ratio = im.height / im.width
    img = Image(str(img_path), width=w, height=w * ratio)
    return KeepTogether([Spacer(1, 4), img, Paragraph(f"<b>Figure {number}.</b> {inline(caption, ctx)}", S["caption"])])


def build_listing(payload: str, ctx: Ctx, number: int):
    head = re.match(r"\\begin\{lstlisting\}\[(.*)\]\s*\n", payload)
    opts = head.group(1)
    cap = re.search(r"caption=\{", opts)
    caption = read_group(opts, cap.end() - 1)[0]
    code = payload[head.end():payload.index("\\end{lstlisting}")].rstrip("\n")
    numbered = "\n".join(f"{n:>2}  {esc(line)}" for n, line in enumerate(code.split("\n"), 1))
    for line in code.split("\n"):
        assert len(line) <= 84, f"listing line too long for the page ({len(line)}): {line}"
    pre = XPreformatted(numbered, S["code"])
    cap_p = Paragraph(f"<b>Listing {number}.</b> {inline(caption, ctx)}", S["caption"])
    return [KeepTogether([Spacer(1, 4), pre, cap_p])]


def build_list(payload: str, ctx: Ctx, ordered: bool):
    inner = re.sub(r"^\\begin\{\w+\}\s*|\\end\{\w+\}\s*$", "", payload.strip())
    items = [x.strip() for x in re.split(r"\\item\b", inner) if x.strip()]
    out = []
    for n, it in enumerate(items, 1):
        bullet = f"{n}." if ordered else "•"
        out.append(Paragraph(inline(" ".join(it.split()), ctx), S["item"], bulletText=bullet))
    # indent via a style copy
    for p in out:
        p.style = ParagraphStyle("li", parent=S["item"], leftIndent=18, bulletIndent=4)
    return out


def build(tex_path: Path, pdf_path: Path) -> None:
    tex = strip_comments(tex_path.read_text(encoding="utf8"))
    body = tex[tex.index("\\begin{document}") + len("\\begin{document}"):tex.index("\\end{document}")]
    ctx = Ctx()

    bib = parse_bib(tex_path.with_name("refs.bib"))
    cited = []
    for m in re.finditer(r"\\cite\{([^}]*)\}", tex):
        for k in m.group(1).split(","):
            k = k.strip()
            assert k in bib, f"missing bib entry: {k}"
            if k not in cited:
                cited.append(k)

    def sort_key(k):  # plain.bst: by author, year, title
        e = bib[k]
        return (re.sub(r"[{}]", "", e.get("author", e.get("title", ""))).lower(), e.get("year", ""),
                e.get("title", "").lower())

    for n, k in enumerate(sorted(cited, key=sort_key), 1):
        ctx.bib_numbers[k] = n

    title = " ".join(get_cmd(tex, "title").replace("\\\\", "<br/>").split())
    authors = get_cmd(tex, "author").replace("\\and", "<br/>")
    date = get_cmd(tex, "date")

    body = re.sub(r"\\bibliography(style)?\{[^}]*\}", "", body)
    blocks = split_blocks(body)
    blocks = [b for b in blocks if not (b[0] == "text" and b[1] in ("\\maketitle",))]
    number_labels(blocks, ctx)

    story = [Spacer(1, 1.2 * cm),
             Paragraph(inline(title.replace("<br/>", "\\\\"), ctx), S["title"]),
             Paragraph(esc(authors), S["author"]), Paragraph(esc(date), S["author"]), Spacer(1, 0.8 * cm)]
    sec = sub = fig = tab = lst = 0
    for kind, payload in blocks:
        if kind == "text":
            if payload.startswith("\\maketitle"):
                payload = payload[len("\\maketitle"):].strip()
                if not payload:
                    continue
            m = re.match(r"\\(section|subsection)\{(.*?)\}\s*(?:\\label\{[^}]*\})?\s*(.*)$", payload, re.S)
            if m:
                if m.group(1) == "section":
                    sec, sub = sec + 1, 0
                    story.append(Paragraph(f"{sec}&nbsp;&nbsp;{inline(m.group(2), ctx)}", S["h1"]))
                else:
                    sub += 1
                    story.append(Paragraph(f"{sec}.{sub}&nbsp;&nbsp;{inline(m.group(2), ctx)}", S["h2"]))
                payload = m.group(3).strip()
                if not payload:
                    continue
            if payload.startswith("\\label"):
                payload = re.sub(r"^\\label\{[^}]*\}\s*", "", payload)
                if not payload:
                    continue
            pm = re.match(r"\\paragraph\{(.*?)\}\s*(.*)$", payload, re.S)
            if pm:
                story.append(Paragraph(f"<b>{inline(pm.group(1), ctx)}</b> {inline(' '.join(pm.group(2).split()), ctx)}",
                                       S["para"]))
            else:
                story.append(Paragraph(inline(" ".join(payload.split()), ctx), S["body"]))
        elif kind == "abstract":
            inner = re.sub(r"^\\begin\{abstract\}|\\end\{abstract\}\s*$", "", payload.strip()).strip()
            story.append(Paragraph("<b>Abstract</b>", ParagraphStyle("ah", parent=S["abstract"], alignment=TA_CENTER,
                                                                      spaceAfter=3)))
            story.append(Paragraph(inline(" ".join(inner.split()), ctx), S["abstract"]))
        elif kind == "itemize":
            story += build_list(payload, ctx, False)
        elif kind == "enumerate":
            story += build_list(payload, ctx, True)
        elif kind == "table":
            tab += 1
            story.append(build_table(payload, ctx, tab))
        elif kind == "figure":
            fig += 1
            story.append(build_figure(payload, ctx, fig))
        elif kind == "lstlisting":
            lst += 1
            story += build_listing(payload, ctx, lst)

    story.append(Paragraph("References", S["h1"]))
    for k in sorted(cited, key=sort_key):
        story.append(Paragraph(f"[{ctx.bib_numbers[k]}]&nbsp;&nbsp;{fmt_bib(bib[k])}", S["bib"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Body", 9)
        canvas.drawCentredString(A4[0] / 2, 1.4 * cm, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.5 * cm, bottomMargin=2.5 * cm,
                            title=re.sub(r"<[^>]+>|\\\\", " ", title).replace("--", "–"), author=re.sub(r"<[^>]+>", " ", authors))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {pdf_path}  ({len(story)} flowables, {len(cited)} references)")


if __name__ == "__main__":
    build(HERE / "report.tex", HERE / "report.pdf")
    sys.exit(0)
