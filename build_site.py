#!/usr/bin/env python3
"""Build a single self-contained index.html for the AI Labor-Market Policy lit reviews.

Renders each lit-reviews/0X-*.md into an HTML tab panel, plus an Overview landing
page. In-text citation keys (e.g. [Schochet2012]) are linked to a per-review
"References" endnote list parsed from refs/library.bib. No server or external assets
required — open index.html in any browser.
"""
import os
import re
import markdown

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_root(start):
    """Walk up until we find the project root (has lit-reviews/ and refs/library.bib)."""
    d = start
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "lit-reviews")) and \
           os.path.isfile(os.path.join(d, "refs", "library.bib")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return start


ROOT = _find_root(SCRIPT_DIR)
LITDIR = os.path.join(ROOT, "lit-reviews")
BIB = os.path.join(ROOT, "refs", "library.bib")
OUT = os.path.join(SCRIPT_DIR, "index.html")  # write next to this script (deployed folder)

# (id, filename, short tab label, full title, section tag, one-line description)
REVIEWS = [
    ("01", "01-ai-labor-reallocation-shock.md", "Reallocation Shock",
     "AI's Labor Impact as a Reallocation Shock", "Conceptual motivation",
     "AI as a dislocation / reallocation shock, not a net-jobs apocalypse — demand falls in some occupations and rises in others, with no frictionless transition."),
    ("02", "02-wioa-and-almp-fragmentation.md", "WIOA Fragmentation",
     "WIOA and the Fragmentation of US Workforce Policy", "Conceptual motivation",
     "The fragmented patchwork of ~40+ federal workforce programs, and why it is too tangled to retrofit — motivating an overlay that targets demand directly."),
    ("03", "03-retraining-efficacy.md", "Retraining Efficacy",
     "The Efficacy of Worker Retraining", "Motivation + Policy",
     "Detached classroom retraining shows near-null returns; sectoral, employer-linked, job-attached training delivers large, durable gains. Tie training to a real job."),
    ("04", "04-trade-adjustment-assistance.md", "Trade Adjustment",
     "Trade Adjustment Assistance: Precedent and Cautionary Tale", "Motivation + Policy",
     "TAA is the closest ancestor of a 'technology adjustment' program — and its consistently negative record is the central cautionary tale."),
    ("05", "05-job-guarantee-proposals.md", "Job Guarantees",
     "Government Job-Guarantee Proposals: The Political Alternative", "Conceptual motivation",
     "The left's rising answer to AI displacement (Tcherneva, Sanders, Steyer 2026) — and why public make-work is the weakest-evidenced design."),
    ("06", "06-almp-international-evidence.md", "ALMP Evidence",
     "What Works in Active Labor Market Policy: The International Evidence", "Motivation + Policy",
     "The international evidence: public employment ranks last; private wage subsidies plus job-search assistance work — conditional on targeting and retention design."),
    ("07", "07-elevate-design-teardown.md", "ELEVATE (internal)",
     "ELEVATE Act Design Teardown", "Internal / background",
     "Full teardown of the bill that inspired the program, mapped to keep/change/drop design decisions. Internal reference."),
]

md = markdown.Markdown(extensions=["extra", "sane_lists", "smarty", "toc"])


# ---------------------------------------------------------------------------
# Bibliography: parse refs/library.bib and render in-text citations as links
# ---------------------------------------------------------------------------

def parse_bibtex(text):
    """Minimal brace-aware BibTeX parser -> {key: {field: value}}."""
    # drop %-comment lines (this file uses % for comments)
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("%"))
    entries = {}
    i, n = 0, len(text)
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        brace = text.find("{", at)
        if brace < 0:
            break
        depth, j = 0, brace
        while j < n:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[brace + 1:j]
        i = j + 1
        comma = body.find(",")
        if comma < 0:
            continue
        key = body[:comma].strip()
        entries[key] = _parse_fields(body[comma + 1:])
    return entries


def _parse_fields(s):
    fields, i, n = {}, 0, len(s)
    while i < n:
        m = re.match(r"\s*([A-Za-z]+)\s*=\s*", s[i:])
        if not m:
            break
        name = m.group(1).lower()
        i += m.end()
        if i < n and s[i] == "{":
            depth, j = 0, i
            while j < n:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            val = s[i + 1:j]
            i = j + 1
        elif i < n and s[i] == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 1
            val = s[i + 1:j]
            i = j + 1
        else:
            m2 = re.match(r"[^,]+", s[i:])
            val = m2.group(0).strip() if m2 else ""
            i += m2.end() if m2 else 1
        fields[name] = re.sub(r"\s+", " ", val).strip()
        m3 = re.match(r"\s*,\s*", s[i:])
        if m3:
            i += m3.end()
    return fields


def _clean(x):
    return re.sub(r"[{}]", "", x).strip() if x else ""


def _esc(x):
    return (x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def format_reference(fields):
    """Return (html, url) for a bib entry's formatted reference string."""
    author = _clean(fields.get("author") or fields.get("organization") or "")
    if author:
        author = "; ".join(p.strip() for p in re.split(r"\s+and\s+", author))
    year = _clean(fields.get("year"))
    title = _clean(fields.get("title"))
    url = (fields.get("url") or "").strip()
    doi = _clean(fields.get("doi"))
    if not url and doi:
        url = "https://doi.org/" + doi
    venue = ""
    for f in ("journal", "booktitle", "institution", "publisher", "howpublished", "school"):
        if fields.get(f):
            venue = _clean(fields[f])
            break
    vol, num, pages = _clean(fields.get("volume")), _clean(fields.get("number")), _clean(fields.get("pages"))

    bits = []
    if author:
        bits.append(_esc(author) + ("" if author.endswith(".") else "."))
    if year:
        bits.append("(%s)." % _esc(year))
    if title:
        t = _esc(title)
        if not t.endswith((".", "?", "!")):
            t += "."
        bits.append('<span class="ref-title">%s</span>' % t)
    if venue:
        v = '<span class="ref-venue">%s</span>' % _esc(venue)
        det = ""
        if vol:
            det += " " + _esc(vol)
        if num:
            det += "(%s)" % _esc(num)
        if pages:
            det += ", " + _esc(pages)
        bits.append(v + det + ".")
    return " ".join(bits), url


CITE_RE = re.compile(r"\[([^\[\]\n]+)\]")
_CITELIKE = re.compile(r"^[A-Za-z][\w.:\-]*\d{2,4}[a-z]?$|^[A-Z][A-Za-z]+_[\w.\-]+$")


def linkify_citations(text, rid, keyset, seen, order, unresolved):
    """Replace [Key] / [Key1; Key2] in markdown source with anchor links.

    Only tokens present in keyset are linked; groups with no known keys are left
    untouched (so [speculative — ...] etc. survive). The first occurrence of each
    key gets an id so the reference list can link back to it.
    """
    def repl(m):
        toks = [t.strip() for t in m.group(1).split(";")]
        if not any(t in keyset for t in toks):
            for t in toks:  # record citation-looking-but-unknown tokens
                if t not in keyset and _CITELIKE.match(t):
                    unresolved.add(t)
            return m.group(0)
        out = []
        for t in toks:
            if t in keyset:
                if t not in seen:
                    seen.add(t)
                    order.append(t)
                    idattr = ' id="ref-%s-%s-1"' % (rid, t)
                else:
                    idattr = ""
                out.append('<a class="citelink"%s href="#cite-%s-%s">%s</a>'
                           % (idattr, rid, t, _esc(t)))
            else:
                if _CITELIKE.match(t):
                    unresolved.add(t)
                out.append(_esc(t))
        return "[" + "; ".join(out) + "]"

    return CITE_RE.sub(repl, text)


def references_html(rid, order, bib):
    if not order:
        return ""
    items = []
    for key in sorted(order, key=str.lower):
        html, url = format_reference(bib[key])
        src = (' <a class="ref-src" href="%s" target="_blank" rel="noopener" title="open source">&#8599;</a>' % _esc(url)) if url else ""
        back = ' <a class="ref-back" href="#ref-%s-%s-1" title="back to text">&#8617;</a>' % (rid, key)
        items.append('<li id="cite-%s-%s"><span class="ref-key">[%s]</span> %s%s%s</li>'
                     % (rid, key, _esc(key), html, src, back))
    return ('<h2 class="ref-head">References</h2>'
            '<p class="ref-note">%d sources cited in this review. '
            'In-text keys link here; &#8617; returns to the text.</p>'
            '<ul class="refs">%s</ul>' % (len(order), "".join(items)))


def render_md(path):
    md.reset()
    with open(path, encoding="utf-8") as f:
        return md.convert(f.read())


def render_review(path, rid, bib, keyset, unresolved):
    """Render a review: linkify citations in source, convert, append references."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    seen, order = set(), []
    src = linkify_citations(src, rid, keyset, seen, order, unresolved)
    md.reset()
    body = md.convert(src)
    return body + references_html(rid, order, bib)


CSS = """
:root{
  --ink:#1a1d24; --muted:#5b6472; --faint:#8a93a3; --line:#e6e9ef;
  --bg:#ffffff; --panel:#ffffff; --wash:#f5f7fa; --accent:#2f5d8a;
  --accent-soft:#eaf1f8; --warn-bg:#fbf3e6; --warn-line:#e3c989; --warn-ink:#8a6d18;
  --maxw:760px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--wash); color:var(--ink);
  font:17px/1.65 Charter,Georgia,"Iowan Old Style",serif;
  -webkit-font-smoothing:antialiased;
}
.masthead{
  background:var(--bg); border-bottom:1px solid var(--line);
}
.masthead .inner{max-width:var(--maxw); margin:0 auto; padding:30px 22px 22px}
.kicker{
  font:600 12px/1 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  letter-spacing:.14em; text-transform:uppercase; color:var(--accent); margin:0 0 10px;
}
.masthead h1{
  font:600 27px/1.25 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  margin:0; letter-spacing:-.01em;
}
.masthead p{margin:9px 0 0; color:var(--muted); font-size:16px}
nav.tabs{
  position:sticky; top:0; z-index:20; background:rgba(255,255,255,.92);
  backdrop-filter:saturate(140%) blur(6px); border-bottom:1px solid var(--line);
}
nav.tabs .inner{
  max-width:var(--maxw); margin:0 auto; padding:0 12px;
  display:flex; gap:2px; overflow-x:auto; scrollbar-width:thin;
}
nav.tabs button{
  flex:0 0 auto; appearance:none; background:none; border:none; cursor:pointer;
  padding:13px 12px 11px; margin:0; color:var(--muted);
  font:600 13px/1 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  border-bottom:2.5px solid transparent; white-space:nowrap; letter-spacing:.01em;
}
nav.tabs button .num{color:var(--faint); margin-right:6px; font-variant-numeric:tabular-nums}
nav.tabs button:hover{color:var(--ink)}
nav.tabs button[aria-selected="true"]{color:var(--accent); border-bottom-color:var(--accent)}
nav.tabs button[data-internal="1"][aria-selected="true"]{color:var(--warn-ink); border-bottom-color:var(--warn-line)}
main{max-width:var(--maxw); margin:0 auto; padding:0 22px 90px}
.panel{display:none; padding-top:34px}
.panel.active{display:block; animation:fade .25s ease}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.meta{
  font:600 12px/1.4 ui-sans-serif,system-ui,sans-serif; letter-spacing:.04em;
  text-transform:uppercase; color:var(--accent); margin:0 0 18px;
  display:flex; gap:10px; align-items:center; flex-wrap:wrap;
}
.meta .pill{background:var(--accent-soft); padding:4px 10px; border-radius:999px}
.meta .pill.warn{background:var(--warn-bg); color:var(--warn-ink)}
/* rendered markdown */
.doc h1{font:600 30px/1.25 ui-sans-serif,system-ui,sans-serif; letter-spacing:-.015em; margin:0 0 .55em}
.doc h2{
  font:600 21px/1.3 ui-sans-serif,system-ui,sans-serif; margin:2.1em 0 .5em;
  padding-bottom:.28em; border-bottom:1px solid var(--line);
}
.doc h3{font:600 17px/1.35 ui-sans-serif,system-ui,sans-serif; margin:1.7em 0 .4em}
.doc p{margin:0 0 1.05em}
.doc strong{font-weight:700}
.doc em{font-style:italic}
.doc a{color:var(--accent); text-decoration:none; border-bottom:1px solid var(--accent-soft)}
.doc a:hover{border-bottom-color:var(--accent)}
.doc ul,.doc ol{margin:0 0 1.1em; padding-left:1.4em}
.doc li{margin:.32em 0}
.doc li::marker{color:var(--faint)}
.doc blockquote{
  margin:1.3em 0; padding:14px 18px; background:var(--warn-bg);
  border-left:4px solid var(--warn-line); border-radius:0 6px 6px 0; color:var(--warn-ink);
  font-size:15.5px;
}
.doc blockquote p{margin:.4em 0}
.doc blockquote strong{color:var(--warn-ink)}
.doc hr{border:none; border-top:1px solid var(--line); margin:2.2em 0}
.doc table{
  width:100%; border-collapse:collapse; margin:1.4em 0; font-size:14.5px;
  font-family:ui-sans-serif,system-ui,sans-serif;
}
.doc th,.doc td{border:1px solid var(--line); padding:9px 11px; text-align:left; vertical-align:top}
.doc thead th{background:var(--wash); font-weight:600}
.doc tbody tr:nth-child(even){background:#fafbfd}
.doc code{
  background:var(--wash); border:1px solid var(--line); border-radius:4px;
  padding:1px 5px; font:14px/1 ui-monospace,SFMono-Regular,Menlo,monospace;
}
.doc em em{font-style:normal}
/* citations + references */
.doc a.citelink{
  color:var(--accent); text-decoration:none; border-bottom:1px dotted var(--accent);
  font-family:ui-sans-serif,system-ui,sans-serif; font-size:.92em;
  font-variant-numeric:tabular-nums; white-space:nowrap; padding:0 1px;
}
.doc a.citelink:hover{background:var(--accent-soft); border-bottom-style:solid}
.doc h2.ref-head{margin-top:2.4em}
.doc .ref-note{
  font:13px/1.5 ui-sans-serif,system-ui,sans-serif; color:var(--faint); margin:-.2em 0 1.1em;
}
.doc ul.refs{
  list-style:none; padding-left:0; margin:.4em 0 0;
  font:14px/1.55 ui-sans-serif,system-ui,sans-serif;
}
.doc ul.refs li{
  margin:0 0 .75em; padding:4px 8px 4px 1.5em; text-indent:-1.1em;
  color:var(--muted); border-radius:5px; scroll-margin-top:64px;
}
.doc ul.refs li:target{background:var(--accent-soft)}
.doc ul.refs li::marker{content:none}
.ref-key{font-weight:600; color:var(--ink); margin-right:2px}
.ref-title{color:var(--ink)}
.ref-venue{font-style:italic}
.doc a.ref-src,.doc a.ref-back{border:none; text-decoration:none; color:var(--accent); font-size:.95em}
.doc a.ref-src:hover,.doc a.ref-back:hover{color:var(--ink)}
.citelink:target,[id^="ref-"]:target{background:var(--accent-soft); border-radius:3px}
/* overview */
.lede{font-size:19px; line-height:1.6; color:var(--ink); margin:0 0 1.3em}
.twocol{display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:1.6em 0 2.2em}
.sec{background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:18px 20px}
.sec h3{font:600 15px/1.3 ui-sans-serif,system-ui,sans-serif; margin:0 0 8px; color:var(--accent)}
.sec p{margin:0; font-size:15.5px; color:var(--muted)}
.cards{display:grid; gap:11px; margin-top:14px}
.card{
  text-align:left; width:100%; background:var(--bg); border:1px solid var(--line);
  border-radius:10px; padding:15px 17px; cursor:pointer; transition:border-color .15s, transform .05s;
  font-family:inherit; color:inherit;
}
.card:hover{border-color:var(--accent); transform:translateY(-1px)}
.card .ttl{font:600 16px/1.35 ui-sans-serif,system-ui,sans-serif; margin:0 0 4px; display:flex; gap:9px; align-items:baseline}
.card .ttl .n{color:var(--faint); font-variant-numeric:tabular-nums; font-size:14px}
.card .tag{font:600 11px/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.05em; text-transform:uppercase; color:var(--accent); background:var(--accent-soft); padding:3px 8px; border-radius:999px; margin-left:auto}
.card .tag.warn{color:var(--warn-ink); background:var(--warn-bg)}
.card p{margin:6px 0 0; font-size:14.5px; color:var(--muted); line-height:1.5}
.foot{margin-top:30px; padding-top:18px; border-top:1px solid var(--line); color:var(--faint); font-size:13px; font-family:ui-sans-serif,system-ui,sans-serif}
@media (max-width:620px){
  :root{--maxw:100%}
  .twocol{grid-template-columns:1fr}
  body{font-size:16px}
}
"""

JS = """
const tabs = Array.from(document.querySelectorAll('nav.tabs button'));
const panels = Array.from(document.querySelectorAll('.panel'));
function show(id, push){
  tabs.forEach(t=>t.setAttribute('aria-selected', String(t.dataset.target===id)));
  panels.forEach(p=>p.classList.toggle('active', p.id===id));
  const sel = tabs.find(t=>t.dataset.target===id);
  if(sel) sel.scrollIntoView({inline:'nearest', block:'nearest'});
  window.scrollTo({top:0});
  if(push) history.replaceState(null,'', '#'+id);
}
tabs.forEach(t=>t.addEventListener('click',()=>show(t.dataset.target, true)));
document.querySelectorAll('[data-goto]').forEach(el=>
  el.addEventListener('click',()=>show(el.dataset.goto, true)));
const start = (location.hash||'').replace('#','');
show(panels.some(p=>p.id===start) ? start : 'overview', false);
"""


def overview_html():
    cards = []
    for rid, _f, _short, title, tag, desc in REVIEWS:
        warn = " warn" if rid == "07" else ""
        cards.append(
            f'<button class="card" data-goto="review-{rid}">'
            f'<div class="ttl"><span class="n">{rid}</span><span>{title}</span>'
            f'<span class="tag{warn}">{tag}</span></div>'
            f'<p>{desc}</p></button>'
        )
    return f"""
<div class="doc">
  <p class="lede">A labor-market policy proposal for addressing AI and other technology shocks, by
  Samuel Hammond and Sam Manning. The work is organized as two sections that can stand alone or
  combine into a white paper: a <strong>conceptual motivation</strong> and a <strong>policy
  proposal</strong> for a market-oriented &ldquo;technology adjustment assistance&rdquo; program
  that targets labor demand directly.</p>

  <p>The central claim is that AI&rsquo;s labor impact is best understood not as a uniform jobs
  apocalypse but as a <em>reallocation shock</em>: demand collapses in some occupations and surges
  in others, with no frictionless path for displaced workers to fill the rising roles. The standard
  toolkit answers this badly &mdash; federal workforce programs are fragmented, classroom retraining
  detached from employment shows weak returns, and the leading political alternative (a government
  job guarantee) is the design the evidence ranks <em>least</em> effective. The seven reviews below
  assemble the evidence base behind that argument.</p>

  <div class="twocol">
    <div class="sec"><h3>Section I &middot; Conceptual motivation</h3>
      <p>Frames the AI labor shock as reallocation and shows why the existing toolkit and the
      job-guarantee alternative misfit it. Draws chiefly on reviews 01, 02, 04, 05.</p></div>
    <div class="sec"><h3>Section II &middot; Policy proposal</h3>
      <p>A worker-following employment subsidy that targets demand, ties training to real jobs, and
      builds in automatic stabilizers. Draws chiefly on reviews 03, 06.</p></div>
  </div>

  <h2>The literature reviews</h2>
  <div class="cards">
    {''.join(cards)}
  </div>

  <p class="foot">Self-contained build &middot; reviews rendered from <code>lit-reviews/</code>.
  Review 07 is an internal background reference.</p>
</div>
"""


def build():
    with open(BIB, encoding="utf-8") as f:
        bib = parse_bibtex(f.read())
    keyset = set(bib)
    unresolved = set()

    tab_btns = ['<button data-target="overview" aria-selected="true">Overview</button>']
    panels = [f'<section class="panel active" id="overview">{overview_html()}</section>']
    for rid, fname, short, title, tag, desc in REVIEWS:
        internal = (rid == "07")
        internal_attr = ' data-internal="1"' if internal else ''
        tab_btns.append(
            f'<button data-target="review-{rid}"{internal_attr}>'
            f'<span class="num">{rid}</span>{short}</button>'
        )
        body = render_review(os.path.join(LITDIR, fname), rid, bib, keyset, unresolved)
        warn = " warn" if internal else ""
        meta = (f'<div class="meta"><span class="pill{warn}">{tag}</span>'
                f'<span class="pill{warn}">Review {rid}</span></div>')
        panels.append(
            f'<section class="panel" id="review-{rid}">{meta}<div class="doc">{body}</div></section>'
        )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Labor-Market Policy &mdash; Literature Reviews</title>
<style>{CSS}</style>
</head>
<body>
<header class="masthead"><div class="inner">
  <p class="kicker">Foundation work &middot; literature reviews</p>
  <h1>AI Labor-Market Policy Proposal</h1>
  <p>Background evidence for a market-oriented &ldquo;technology adjustment assistance&rdquo; program &middot; Hammond &amp; Manning</p>
</div></header>
<nav class="tabs"><div class="inner">{''.join(tab_btns)}</div></nav>
<main>{''.join(panels)}</main>
<script>{JS}</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT} ({len(doc):,} bytes)")
    print(f"bibliography: {len(bib)} entries parsed from {os.path.relpath(BIB, SCRIPT_DIR)}")
    if unresolved:
        print(f"WARNING: {len(unresolved)} in-text citation key(s) not found in library.bib "
              f"(left unlinked): {', '.join(sorted(unresolved))}")
    else:
        print("all citation-like in-text keys resolved to a bibliography entry")


if __name__ == "__main__":
    build()
