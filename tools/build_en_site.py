#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采风英文站（独立 GitHub Pages：https://greatbeing.github.io/caifeng-en/）。

输出到仓库外的 caifeng-en/ 目录（可用 --out 指定），站点根即英文首页：
  /            English home
  engines/     engines overview
  atoms/       atom library + atoms/<id>.html（来自 atoms/en.json、atoms/en/*.json）
  lectures/    lectures：i18n/en/lectures/<同名>.md 有则生成英文页，无则链中文站并标 (Chinese)
  eval/        evaluation（英文文本 i18n/en/eval.html）
站内链接全部相对路径；需要中文时链中文站绝对 URL 并标 (Chinese)。

用法：python tools/build_en_site.py [--out DIR]
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_articles as ba  # noqa: E402
from build_articles import page, ROOT  # noqa: E402
from build_site import GH, CSS, ATOM_CSS, ATOM_SVG, ATOM_JS, counts, mark  # noqa: E402

ZH = "https://greatbeing.github.io/writing-engines/"
OUT = ROOT.parent / "caifeng-en"
I18N = ROOT / "i18n/en"


def en_shell(t, rel, enrel, zh_href, on=""):
    """把 page() 的中文外壳改成英文。rel 为原 docs/en 布局下的相对前缀（比新站深一层），zh_href 指中文页。"""
    nr = rel[3:]
    zh = zh_href if zh_href.startswith("http") else ZH + re.sub(r"^(\.\./)+", "", zh_href)
    t = t.replace('<html lang="zh-CN">', '<html lang="en">', 1)
    t = t.replace(' · 采风</title>', ' · Caifeng</title>', 1)
    t = re.sub(r'<a class="brand" href="[^"]*">', f'<a class="brand" href="{nr or "./"}">', t, count=1)
    items = [("engines", "Engines", "engines/"), ("atoms", "Atoms", "atoms/"),
             ("lectures", "Lectures", "lectures/"), ("eval", "Evaluation", "eval/")]
    nav = "".join(f'<a class="{"on" if k == on else ""}" href="{nr}{h}">{n}</a>' for k, n, h in items)
    t = re.sub(r'<div class="snav">.*?</div>', lambda m: f'<div class="snav">{nav}<a href="{GH}">GitHub ↗</a></div>',
               t, count=1, flags=re.S)
    t = t.replace(">夜读</button>", ">Night</button>").replace('aria-label="夜读"', 'aria-label="Night"')
    t = t.replace(ba.EN_SITE_LINK, "")
    t = t.replace('<div class="tools">', f'<a class="lang" href="{zh}">中文</a><div class="tools">', 1)
    return t.replace("</style>", LANG_CSS + "</style>", 1)


# ---- English home ----
GH_EN = GH + "/blob/master/README.en.md"
LANG_CSS = ("nav a.lang{border:0;font:12px var(--mono);letter-spacing:.18em;color:var(--ink2);margin-left:22px}"
            "nav a.lang:hover{color:var(--zhu)}")
EN_CSS = """
.h-hero h1.en-h{letter-spacing:.01em;font-size:clamp(34px,4.2vw,58px);line-height:1.22}
.h-hero h1.en-h span{white-space:normal}
.enb{border-top:1px solid var(--ink);padding:48px 0 52px;display:grid;grid-template-columns:200px 1fr;gap:40px}
.enb h2{font:600 20px/1.5 var(--serif)}
.enb p,.enb li{font:400 16px/1.9 var(--serif);color:var(--ink2)}
.enb p+p{margin-top:12px}.enb ul{list-style:none}.enb li{border-top:1px solid var(--rule);padding:8px 0}
.enb code,.enb pre{font:13px/1.7 var(--mono)}
.enb pre{border:1px solid var(--rule);padding:14px 16px;overflow:auto;margin:12px 0}
.enb table{border-collapse:collapse;width:100%;font:14.5px/1.6 var(--serif)}
.enb td,.enb th{border-top:1px solid var(--rule);padding:7px 10px 7px 0;text-align:left;vertical-align:top}
.enb th{font-weight:600;color:var(--ink)}.enb td{color:var(--ink2)}
@media(max-width:820px){.enb{grid-template-columns:1fr;gap:14px}}
"""
EN_ENGINES = [
    ("sanlian-writing", "Lived-in city observation (Sanlian Life Lab style)", "Ready"),
    ("zhexuan-writing", "Official commentary (Zhejiang Propaganda style)", "Ready"),
    ("feature-writing", "Profile features (<i>Renwu</i> magazine style)", "Ready"),
    ("gongwen-writing", "Government official documents (GB/T 9704-2012)", "Ready"),
    ("sushi-writing", "Su Shi-style vernacular essays (苏轼体)", "Trial"),
    ("luxun-writing", "Lu Xun-style essay (鲁迅体)", "Trial"),
    ("wangxiaobo-writing", "Wang Xiaobo-style humorous argument (王小波体)", "Trial"),
    ("zhangailing-writing", "Eileen Chang-style prose (张爱玲体)", "Trial"),
    ("lijuan-writing", "Li Juan-style plain-sketch prose (李娟体)", "Trial"),
    ("yuhua-writing", "Yu Hua-style detached narration (余华体)", "Trial"),
    ("standup-writing", "Chinese stand-up comedy scripts (脱口秀稿)", "Trial"),
    ("versailles-writing", "&ldquo;Versailles&rdquo; humblebrag (凡尔赛体)", "Trial"),
    ("guanfang-writing", "<i>People&rsquo;s Daily</i> commentary (人民日报评论体)", "Trial"),
    ("wangzengqi-writing", "Wang Zengqi-style prose (汪曾祺体)", "Trial"),
    ("jinyong-writing", "Jin Yong-style wuxia narrative (金庸体)", "Trial"),
    ("acheng-writing", "Ah Cheng-style plain-sketch narrative (阿城体)", "Trial"),
    ("mao-writing", "Mao Zedong-style argumentative prose (毛泽东文章体)", "Trial"),
]


def home_en(c):
    rows = "".join(f'<tr><td><a href="{GH}/tree/master/{d}"><code>{d}</code></a></td><td>{g}</td><td>{s}</td></tr>'
                   for d, g, s in EN_ENGINES)
    return f"""<main class="home">
<section class="h-hero"><div><h1 class="en-h"><span>Collect the style.</span><span>Learn the method.</span><span class="last">Find your own.</span></h1>
<p class="en">采其风 · 得其法 · 自成一体</p>
<div class="rule"></div>
<p class="sub">Caifeng is a project for learning to write. It breaks the styles of established writers into atoms, teaches the atoms as lessons, and tests the results. The aim is not to sound like anyone, but to arrive at a style of your own.</p></div>
{ATOM_SVG}</section>
<section class="enb"><h2>What an engine is</h2><div>
<p>A genre is a set of operating rules its authors never state. An engine takes a genre apart to a grain you can execute, then reassembles the parts into something that can write new pieces.</p>
<pre>engine = atomic techniques × style fingerprint × red-line review</pre>
<p>Atoms govern how a piece is thought up; the fingerprint, how a draft is checked; red lines, what must never appear. A template makes you sound like it; an engine means you don&rsquo;t have to.</p></div></section>
<section class="enb"><h2>Engines</h2><div>
<p>{c['engines']} engines, {c['atoms']} atoms. Four are ready; the rest are on trial. Individual engine files are in Chinese.</p>
<table><tr><th>Engine</th><th>Genre</th><th>Status</th></tr>{rows}</table>
<p><a href="engines/">Browse all engines →</a> &nbsp; <a href="{ZH}articles/">Sample pieces (Chinese) →</a></p></div></section>
<section class="enb"><h2>Atom library</h2><div>
<p>Lay the engines side by side and many moves turn out to be the same move. The cross-engine library holds {c['atoms']} atoms in {c['fams']} shared families plus {c['uniq']} unique ones. Different authors are different combinations of the same atoms.</p>
<p><a href="atoms/">Atom library →</a></p></div></section>
<section class="enb"><h2>Teaching layer</h2><div>
<p>Three tracks: recognize single atoms, see how authors combine them, then diagnose your own drafts. {c['lectures']} lectures so far, each one technique: see it in the original, take it apart, write it yourself.</p>
<p><a href="lectures/">Lectures →</a> &nbsp; <a href="eval/">Evaluation →</a></p></div></section>
<section class="enb"><h2>Install</h2><div>
<p>Each engine is a self-contained <code>SKILL.md</code> directory with no code dependencies. Copy it into your host&rsquo;s skills path (OpenClaw, Claude Code, or any host that reads <code>SKILL.md</code>).</p>
<pre>git clone {GH}.git
cp -r writing-engines/luxun-writing ~/.openclaw/workspace/skills/</pre>
<p><a href="{GH_EN}">Read the English README on GitHub ↗</a></p></div></section>
</main>"""


def add_lang(t, href, label):
    t = t.replace('<div class="tools">', f'<a class="lang" href="{href}">{label}</a><div class="tools">', 1)
    return t.replace("</style>", LANG_CSS + "</style>", 1)


def add_lang_nav(t, href, label):
    """引擎页导航没有 tools 区：把语言切换放在导航末尾。"""
    if 'class="lang"' in t:
        return t
    t = t.replace("</div></nav>", f'<a class="lang" href="{href}">{label}</a></div></nav>', 1)
    return t.replace("</style>", LANG_CSS + "</style>", 1)


# ---- English sub-pages ----
EN_GLOSSARY = ROOT / "atoms/en.json"  # 族名、原子名、一句话定义、引擎短名的英文译名表


def en_glossary():
    return json.loads(EN_GLOSSARY.read_text(encoding="utf-8"))


def esc(s):
    import html as _h
    return _h.escape(str(s or ""))


def build_en_engines(c):
    idx = json.loads((ROOT / "atoms/index.json").read_text(encoding="utf-8"))
    n = {}
    for a in idx:
        n[a["engine"]] = n.get(a["engine"], 0) + 1
    names = en_glossary()["engines"]
    rows = "".join(
        f'<tr><td>{esc(names.get(d, d))}</td><td>{g}</td><td>{s}</td><td>{n.get(d, 0)}</td>'
        f'<td><a href="{GH}/tree/master/{d}"><code>{d}</code> ↗</a></td></tr>' for d, g, s in EN_ENGINES)
    ready = sum(1 for _, _, s in EN_ENGINES if s == "Ready")
    body = f"""<main class="home">
<section class="enb first"><h2>Writing engines</h2><div>
<p>A genre is a set of operating rules its authors never state. An engine takes a genre apart to a grain you can execute, then reassembles the parts into something that can write new pieces.</p>
<pre>engine = atomic techniques × style fingerprint × red-line review</pre>
<p>Atoms govern how a piece is thought up; the fingerprint, how a draft is checked; red lines, what must never appear. Each engine is a self-contained <code>SKILL.md</code> directory with no code dependencies.</p></div></section>
<section class="enb"><h2>The engines</h2><div>
<p>{c['engines']} engines, {c['atoms']} atoms. {ready} are ready; the rest are on trial. Atom counts come from <code>atoms/index.json</code>. Engine files are in Chinese.</p>
<table><tr><th>Engine</th><th>Genre</th><th>Status</th><th>Atoms</th><th>Directory</th></tr>{rows}</table>
<p><a href="../atoms/">Browse the atom library →</a></p></div></section>
<section class="enb"><h2>How an engine is built</h2><div>
<ol class="steps"><li><b>Sample.</b> Choose a genre with clear boundaries and collect real, high-quality texts.</li>
<li><b>Extract atoms.</b> Take each text apart into its smallest techniques, then merge them into composable operations.</li>
<li><b>Fix the fingerprint.</b> Turn &ldquo;sounds like it&rdquo; into features that can be counted and compared.</li>
<li><b>Draw red lines.</b> Write down what gives the style away when misused, with a replacement for each.</li>
<li><b>Feed back from use.</b> Write real pieces with the engine; where they fail, revise the atoms and red lines.</li></ol>
<p>Every engine follows the same seven-section contract (<a href="{GH}/blob/master/SPEC.md">SPEC.md ↗</a>) and must pass the ten checks in <code>lint_skill.py</code>: complete frontmatter, all seven sections, no full-text corpus, and complete sample output.</p></div></section>
<section class="enb"><h2>Install and use</h2><div>
<p><code>SKILL.md</code> with frontmatter is a common format. With OpenClaw:</p>
<pre>git clone {GH}.git
# each engine directory is self-contained: copy one, or all
cp -r writing-engines/*-writing ~/.openclaw/workspace/skills/</pre>
<p>For Claude Code or any other host that reads <code>SKILL.md</code>, put the engine directory in its skills path. After writing, you can check the result:</p>
<pre># score a piece for AI flavor against one engine
python tools/ai-flavor-checker.py article.md --engine sanlian-writing
# library-wide lint, assertions and regression tests
python tools/lint_skill.py --all
python tools/run_prompts.py --all</pre>
<p><a href="{GH_EN}">Read the English README on GitHub ↗</a></p></div></section>
</main>"""
    ba.SECTION = "engines"
    t = page("Writing engines", f"<style>{EN_CSS}{EN_SUB_CSS}</style>" + body, "../")
    (OUT / "engines").mkdir(parents=True, exist_ok=True)
    (OUT / "engines/index.html").write_text(
        en_shell(t, "../../", "../", "../../engines/", "engines"), encoding="utf-8")


EN_SECTIONS = [("why", "Why it works"), ("example", "From the source"), ("breakdown", "Taking it apart"),
               ("overdo", "Overdone"), ("when_not", "When not to use it"), ("exercise", "Five-minute exercise"),
               ("check", "Self-check"), ("adjacent", "Adjacent atoms")]
TIER_EN = {"核心": "Core", "常用": "Common", "签名": "Signature"}


def _aslug(aid):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", aid)


def en_atom_data():
    """atoms/en/<engine>.json → {id: {section: markdown}}；缺失或不完整的原子不计入。"""
    out = {}
    for f in sorted((ROOT / "atoms/en").glob("*.json")):
        for aid, v in json.loads(f.read_text(encoding="utf-8")).get("atoms", {}).items():
            if all(str(v.get(k, "")).strip() for k, _ in EN_SECTIONS):
                out[aid] = v
    return out


def build_en_atom_pages(idx, g, data):
    import markdown
    import build_atoms as bt
    tiers = {}
    for f in sorted((ROOT / "atoms/explain").glob("*.md")):
        for aid, v in bt.parse_explain(f)[1].items():
            tiers[aid] = v["tier"]
    fam_en, eng_en, at = g["families"], g["engines"], g["atoms"]
    known = {a["id"] for a in idx}

    def link_ids(h):
        # 相邻原子里的 id：有英文页链英文页，否则链中文页
        def rep(m):
            aid = m.group(0)
            if aid not in known:
                return aid
            href = f"{_aslug(aid)}.html" if aid in data else f"{ZH}atoms/{_aslug(aid)}.html"
            return f'<a href="{href}">{aid}</a>'
        return re.sub(r"(?<![\w./])[a-z]+\.\d+(?![\w])", rep, h)

    ba.SECTION = "engines"
    for a in idx:
        aid = a["id"]
        if aid not in data:
            continue
        d = data[aid]
        name, one = at.get(aid, [a["name"], ""])
        parts = [f"<p><strong>In one line:</strong> {esc(one)}</p>"]
        for k, label in EN_SECTIONS:
            src = re.sub(r"(?m)^(?![ \t]*(?:[-*+] |\d+\. |>))(.+)\n(?=[ \t]*(?:[-*+] |\d+\. |>))", r"\1\n\n", d[k].strip())
            h = markdown.markdown(src, extensions=["sane_lists"])
            if k == "adjacent":
                h = link_ids(h)
            parts.append(f"<p><strong>{label}</strong></p>{h}")
        tier = TIER_EN.get(tiers.get(aid, "常用"), "Common")
        reason = str(d.get("tier_reason", "")).strip()
        content = (f'<article class="ad"><div class="crumb"><a href="index.html">Atoms</a> · '
                   f'{esc(eng_en.get(a["engine"], a["engine"]))} · {esc(aid)}</div>'
                   f'<h1>{esc(name)}</h1><div class="tags"><span>{tier}</span>'
                   f'<span>Family · {esc(fam_en.get(a["family"], a["family"]))}</span></div>'
                   + (f'<p style="font-size:13.5px;color:var(--ink2);margin:-14px 0 22px">{esc(reason)}</p>' if reason else "")
                   + f'<div class="body">{"".join(parts)}</div></article>'
                   '<div class="pager" style="max-width:36em;margin:0 auto;padding:0 24px 56px">'
                   '<a href="index.html">← Atom library</a></div>')
        t = page(f"{name} · Atoms", content + f"<style>{bt.CSS}</style>", "../")
        (OUT / f"atoms/{_aslug(aid)}.html").write_text(
            en_shell(t, "../../", "../", f"{ZH}atoms/{_aslug(aid)}.html", "atoms"), encoding="utf-8")


def build_en_atoms():
    idx = json.loads((ROOT / "atoms/index.json").read_text(encoding="utf-8"))
    g = en_glossary()
    fam_en, eng_en, at = g["families"], g["engines"], g["atoms"]
    data = en_atom_data()
    (OUT / "atoms").mkdir(parents=True, exist_ok=True)
    for old in (OUT / "atoms").glob("*.html"):
        if old.name != "index.html":
            old.unlink()
    build_en_atom_pages(idx, g, data)
    missing = [a["id"] for a in idx if a["id"] not in data]
    print(f"built en atoms: {len(idx) - len(missing)} English page(s); missing translations: {len(missing)}"
          + (f" ({', '.join(missing[:10])}{' …' if len(missing) > 10 else ''})" if missing else ""))

    def href(a):
        return (f'{_aslug(a["id"])}.html' if a["id"] in data else f'{ZH}atoms/{_aslug(a["id"])}.html')

    def zh(a):
        return "" if a["id"] in data else ' <span class="zh">(Chinese)</span>'
    groups = {}
    for a in idx:
        groups.setdefault(a["family"], []).append(a)
    order = sorted(groups, key=lambda f: (f == "独有", -len(groups[f]), f))
    secs, toc = [], []
    for k, f in enumerate(order, 1):
        name = fam_en.get(f, f)
        aid = f"f{k}"
        toc.append(f'<a href="#{aid}">{esc(name)} <small>{len(groups[f])}</small></a>')
        items = "".join(
            f'<li><a href="{href(a)}">'
            f'<b>{esc(at.get(a["id"], [a["name"], ""])[0])}</b></a>{zh(a)}'
            f'<span class="eng">{esc(eng_en.get(a["engine"], a["engine"]))}</span>'
            f'<div class="one">{esc(at.get(a["id"], ["", ""])[1])}</div></li>' for a in groups[f])
        note = ("Moves found in one engine only." if f == "独有"
                else f"Shared across {len({a['engine'] for a in groups[f]})} engines.")
        secs.append(f'<section class="enb" id="{aid}"><h2>{esc(name)}<small>{len(groups[f])} · {esc(f)}</small></h2>'
                    f'<div><p>{note}</p><ul class="alist">{items}</ul></div></section>')
    shared = len([f for f in groups if f != "独有"])
    body = (f'<main class="home"><section class="enb first"><h2>Atom library</h2><div>'
            '<p>Lay the engines side by side and many moves turn out to be the same move. An atom is one such move: '
            'small enough to practise, general enough to recombine. Different authors are different combinations of the same atoms.</p>'
            f'<p class="stat">{len(idx)} atoms · {shared} shared families · {len(groups.get("独有", []))} unique · '
            f'{len({a["engine"] for a in idx})} engines</p>'
            + ('<p>Each atom has a full page in English; quotations from authors still in copyright are kept in Chinese with a short gloss.</p>'
               if not missing else '<p>Atoms marked (Chinese) do not have an English page yet and link to the Chinese one.</p>') +
            f'<nav class="toc">{"".join(toc)}</nav></div></section>{"".join(secs)}</main>')
    ba.SECTION = "engines"
    t = page("Atom library", f"<style>{EN_CSS}{EN_SUB_CSS}</style>" + body, "../")
    (OUT / "atoms").mkdir(parents=True, exist_ok=True)
    (OUT / "atoms/index.html").write_text(
        en_shell(t, "../../", "../", "../../atoms/", "atoms"), encoding="utf-8")


EN_SUB_CSS = """
.enb.first{border-top:0;padding-top:64px}
.enb h2 small{display:block;font:12px var(--mono);letter-spacing:.12em;color:var(--ink2);margin-top:4px}
.enb .stat{font:12px var(--mono);letter-spacing:.14em}
.toc{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:16px;font-size:14px}
.toc a{border:0}.toc a:hover{color:var(--zhu)}.toc small{font:11px var(--mono);color:var(--ink2)}
.alist li{padding:10px 0}.alist b{font-weight:600;color:var(--ink)}
.alist a{border:0}.alist a:hover b{color:var(--zhu)}
.alist .zh{font:11px var(--mono);color:var(--ink2)}
.alist .eng{float:right;font:11px var(--mono);letter-spacing:.1em;color:var(--ink2)}
.alist .one{font-size:14.5px;line-height:1.75}
.steps{list-style:decimal;padding-left:1.3em}.steps li{border-top:0;padding:4px 0}.steps b{font-weight:600;color:var(--ink)}
"""


# ---- English lectures (i18n/en/lectures/*.md, same names as lecture/*.md) ----
def build_en_lectures():
    import markdown
    import build_lecture as bl
    out = OUT / "lectures"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    zh_files = sorted(bl.LEC.glob("*.md"))
    en_dir = I18N / "lectures"
    items, missing = [], []
    have = [f for f in zh_files if (en_dir / f.name).exists()]
    for f in zh_files:
        slug = f.stem.split("-")[0]
        ef = en_dir / f.name
        if not ef.exists():
            missing.append(f.name)
            items.append((slug, bl.render(f)[0], "", False))
            continue
        text = ef.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else f.stem
        body = markdown.markdown(text[m.end():] if m else text, extensions=["tables", "sane_lists"])
        body = re.sub(r'(<h2>[^<]*(?:[Ee]xercise|你的练习)[^<]*</h2>)(.*?)(?=<h2>|<hr\s*/?>|\Z)',
                      lambda x: x.group(1) + '<div class="homework">' + x.group(2) + "</div>", body, flags=re.S)
        one = re.search(r"^>\s*\*\*(.+?)\*\*", text, re.M)
        items.append((slug, title, (one.group(1) if one else "").strip(), True))
        i = have.index(f)
        prev = have[i - 1] if i > 0 else None
        nxt = have[i + 1] if i + 1 < len(have) else None

        def ttl(p):
            t2 = (en_dir / p.name).read_text(encoding="utf-8")
            mm = re.search(r"^#\s+(.+)$", t2, re.M)
            return mm.group(1).strip() if mm else p.stem
        pager = ('<div class="pager">'
                 + (f'<a href="{prev.stem.split("-")[0]}.html">← {html.escape(ttl(prev))}</a>' if prev else "<span></span>")
                 + (f'<a href="{nxt.stem.split("-")[0]}.html">{html.escape(ttl(nxt))} →</a>' if nxt else "<span></span>")
                 + "</div>")
        content = (f'<article class="lec"><div class="sub">CAIFENG · WRITING LECTURES</div>'
                   f'<h1>{html.escape(title)}</h1><hr class="rule"><div class="body">{body}</div></article>{pager}')
        ba.SECTION = "lecture"
        t = page(title + " · Lectures", content + f"<style>{bl.CSS}</style>", "../")
        (out / f"{slug}.html").write_text(en_shell(t, "../../", "../", f"lecture/{slug}.html", "lectures"), encoding="utf-8")
    lst = "".join(
        f'<a class="item" href="{s + ".html" if en else ZH + "lecture/" + s + ".html"}"><div class="no">LECTURE {k}</div>'
        f'<h2>{html.escape(t)}{"" if en else " <small>(Chinese)</small>"}</h2>'
        + (f'<div class="one">{html.escape(o)}</div>' if o else "") + "</a>"
        for k, (s, t, o, en) in enumerate(items, 1))
    idx = (f'<section class="list"><h1>Writing lectures</h1>'
           f'<p class="lead">Writing as a craft you can learn. One lecture, one move: see it in the original, '
           f'take it apart, then write it yourself.</p><div class="brandline">COLLECT THE STYLE · LEARN THE METHOD · FIND YOUR OWN</div>{lst}</section>'
           f'<div class="foot"><div class="box"></div><p>{len(items)} lectures in three seasons. Each has five parts: one move, '
           f'how the masters do it, what AI makes of it, one revision, and your exercise.'
           + (f' Lectures marked (Chinese) are not translated yet and open on the Chinese site.' if missing else "")
           + f'</p></div><style>{bl.CSS}</style>')
    ba.SECTION = "lecture"
    t = page("Writing lectures", idx, "../")
    (out / "index.html").write_text(en_shell(t, "../../", "../", "lecture/", "lectures"), encoding="utf-8")
    print(f"built en lectures: {len(items) - len(missing)} English, missing translations: {len(missing)}"
          + (f" ({', '.join(missing)})" if missing else ""))
    return len(missing)


def build_en_eval(c):
    body = (I18N / "eval.html").read_text(encoding="utf-8").format(days=c["days"], GH=GH, ZH=ZH, MARK=mark(2, 110))
    ba.SECTION = "eval"
    t = page("Evaluation", f"<style>{CSS}</style>" + body, "../")
    (OUT / "eval").mkdir(parents=True, exist_ok=True)
    (OUT / "eval/index.html").write_text(en_shell(t, "../../", "../", "eval/", "eval"), encoding="utf-8")


def main():
    global OUT
    if "--out" in sys.argv:
        OUT = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    c = counts()
    ba.SECTION = ""
    t = page("Collect the style. Learn the method. Find your own.",
             f"<style>{CSS}{ATOM_CSS}{EN_CSS}</style>" + home_en(c) + f"<script>{ATOM_JS}</script>", "")
    (OUT / "index.html").write_text(en_shell(t, "../", "", ""), encoding="utf-8")
    build_en_engines(c)
    build_en_atoms()
    miss = build_en_lectures()
    build_en_eval(c)
    shutil.copy(ROOT / "docs/favicon.svg", OUT / "favicon.svg")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built en site → {OUT}; lectures missing: {miss}")


if __name__ == "__main__":
    main()
