"""把 atoms/explain/*.md 生成为线上原子库 docs/atoms/。

页面结构：
  /atoms/            总览：按「档位 → 族」分类（核心 / 常用 / 签名），可按引擎筛选
  /atoms/<id>.html   单个原子讲透页
数据来源：atoms/index.json（权威编号与族）+ atoms/explain/<engine>.md（讲透正文）
"""
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).parent))
import build_articles as ba  # noqa: E402
from build_articles import ROOT, page  # noqa: E402

OUT = ROOT / "docs" / "atoms"
EXP = ROOT / "atoms" / "explain"
TIERS = ["核心", "常用", "签名"]
TIER_NOTE = {
    "核心": "跨文体通用、决定文章成败。学写作先练这一档。",
    "常用": "多数文体可用，要看场合。",
    "签名": "某位作者的标志动作。学来理解与欣赏，初学不建议直接模仿。",
}

CSS = """
.al{max-width:1080px;margin:0 auto;padding:64px 32px 40px}
.al h1{font:900 36px/1.4 var(--serif);letter-spacing:.12em}
.al .lead{font:400 16.5px/2 var(--serif);color:var(--ink2);margin:14px 0 26px;max-width:36em}
.al .stat{font:12px var(--mono);letter-spacing:.14em;color:var(--ink2);margin-bottom:28px}
.filt{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 36px}
.filt button{border:1px solid var(--rule);background:none;color:var(--ink2);font:13px var(--sans);padding:3px 11px;cursor:pointer}
.filt button.on,.filt button:hover{border-color:var(--ink);color:var(--ink)}
.tier{border-top:1px solid var(--ink);padding:30px 0 10px}
.tier>h2{font:900 26px/1.4 var(--serif);letter-spacing:.14em}
.tier>p{color:var(--ink2);font-size:14.5px;margin:6px 0 18px}
.fam{margin:20px 0 8px}
.fam h3{font:600 16px var(--serif);letter-spacing:.1em;margin-bottom:10px}
.fam h3 small{font:12px var(--mono);color:var(--ink2);margin-left:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));border-top:1px solid var(--rule);border-left:1px solid var(--rule)}
.card{display:block;background:var(--paper);border:0;border-right:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:14px 16px}
.card:hover{background:#EFE9DC}
.card b{display:block;font:600 15.5px/1.5 var(--serif)}
.card .eng{font:11px var(--mono);letter-spacing:.1em;color:var(--ink2)}
.card .one{font-size:13.5px;color:var(--ink2);margin-top:4px;line-height:1.7}
.tier.core>h2{color:var(--zhu)}
.ad{max-width:36em;margin:0 auto;padding:56px 24px 40px}
.ad .crumb{font:12px var(--mono);letter-spacing:.14em;color:var(--ink2)}
.ad h1{font:900 30px/1.45 var(--serif);letter-spacing:.06em;margin:10px 0 8px}
.ad .tags{font-size:13px;color:var(--ink2);margin-bottom:26px}
.ad .tags span{border:1px solid var(--rule);padding:1px 8px;margin-right:6px}
.ad .body{font:400 16.5px/2 var(--serif)}
.ad .body p{margin:0 0 1em}
.ad .body strong{font-weight:600;color:var(--ink)}
.ad .body blockquote{border-left:2px solid var(--zhu);margin:.6em 0 1.2em;padding:2px 0 2px 16px;color:var(--ink2)}
.ad .body ul{padding-left:1.4em;margin:0 0 1em}
@media(max-width:640px){.al,.ad{padding-left:20px;padding-right:20px}}
"""

JS = """
document.querySelectorAll('.filt button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('.filt button').forEach(x=>x.classList.toggle('on',x===b));
 const e=b.dataset.e;document.querySelectorAll('.card').forEach(c=>c.style.display=(!e||c.dataset.e===e)?'':'none');
 document.querySelectorAll('.fam').forEach(f=>f.style.display=[...f.querySelectorAll('.card')].some(c=>c.style.display!=='none')?'':'none');
 document.querySelectorAll('.tier').forEach(t=>t.style.display=[...t.querySelectorAll('.card')].some(c=>c.style.display!=='none')?'':'none')});
"""


def esc(s):
    return html.escape(str(s or ""))


def slug(aid):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", aid)


def parse_explain(path):
    """返回 {id: {name, family, tier, one, md}}；engine 总述单独返回。"""
    t = path.read_text(encoding="utf-8")
    parts = re.split(r"^## +", t, flags=re.M)
    head, out = parts[0], {}
    for p in parts[1:]:
        first, _, body = p.partition("\n")
        m = re.match(r"(\S+)\s+(.*)", first.strip())
        if not m:
            continue
        aid, name = m.group(1), m.group(2).strip()
        fam = re.search(r"\*\*族\*\*[:：]\s*([^*\n]+?)\s*(\*\*|$)", body, re.M)
        tier = re.search(r"\*\*档位\*\*[:：]\s*(核心|常用|签名)", body)
        one = re.search(r"\*\*一句话\*\*[:：]\s*(.+)", body)
        out[aid] = dict(name=name, family=fam.group(1).strip() if fam else "",
                        tier=tier.group(1) if tier else "常用",
                        one=one.group(1).strip() if one else "", md=body.strip())
    intro = re.sub(r"^#.*\n", "", head).strip()
    return intro, out


def main():
    idx = json.loads((ROOT / "atoms/index.json").read_text(encoding="utf-8"))
    order = {a["id"]: i for i, a in enumerate(idx)}
    meta = {a["id"]: a for a in idx}
    items, intros = [], {}
    for f in sorted(EXP.glob("*.md")):
        eng = f.stem
        intro, d = parse_explain(f)
        intros[eng] = intro
        for aid, v in d.items():
            m = meta.get(aid, {})
            items.append(dict(id=aid, engine=m.get("engine", eng), name=m.get("name", v["name"]),
                              family=m.get("family") or v["family"] or "（未入库）",
                              tier=v["tier"], one=v["one"], md=v["md"], inlib=aid in meta))
    items.sort(key=lambda x: order.get(x["id"], 10 ** 6))
    OUT.mkdir(parents=True, exist_ok=True)
    ba.SECTION = "engines"
    short = {k: v[1] for k, v in ba.ENGINES.items()}

    # 单页
    for it in items:
        body = markdown.markdown(re.sub(r"^\*\*族\*\*.*$", "", it["md"], count=1, flags=re.M),
                                 extensions=["sane_lists"])
        content = (f'<article class="ad"><div class="crumb"><a href="index.html">原子库</a> · '
                   f'{esc(short.get(it["engine"], it["engine"]))} · {esc(it["id"])}</div>'
                   f'<h1>{esc(it["name"])}</h1><div class="tags"><span>{esc(it["tier"])}</span>'
                   f'<span>族 · {esc(it["family"])}</span></div><div class="body">{body}</div></article>'
                   '<div class="pager" style="max-width:36em;margin:0 auto;padding:0 24px 56px">'
                   '<a href="index.html">← 原子库</a></div>')
        (OUT / f"{slug(it['id'])}.html").write_text(
            page(f"{it['name']} · 原子库", content + f"<style>{CSS}</style>", "../"), encoding="utf-8")

    # 总览：档位 → 族
    tree = defaultdict(lambda: defaultdict(list))
    for it in items:
        tree[it["tier"]][it["family"]].append(it)
    engs = sorted({it["engine"] for it in items}, key=lambda e: list(ba.ENGINES).index(e) if e in ba.ENGINES else 99)
    filt = '<button class="on" data-e="">全部</button>' + "".join(
        f'<button data-e="{esc(e)}">{esc(short.get(e, e))}</button>' for e in engs)
    sec = []
    for tr in TIERS:
        fams = tree.get(tr)
        if not fams:
            continue
        n = sum(len(v) for v in fams.values())
        blocks = []
        for fam, lst in sorted(fams.items(), key=lambda kv: (kv[0] in ("独有", "（未入库）"), -len(kv[1]))):
            cards = "".join(
                f'<a class="card" data-e="{esc(i["engine"])}" href="{slug(i["id"])}.html">'
                f'<span class="eng">{esc(short.get(i["engine"], i["engine"]))}</span>'
                f'<b>{esc(i["name"])}</b><div class="one">{esc(i["one"])}</div></a>' for i in lst)
            blocks.append(f'<div class="fam"><h3>{esc(fam)}<small>{len(lst)}</small></h3>'
                          f'<div class="cards">{cards}</div></div>')
        sec.append(f'<section class="tier{" core" if tr == "核心" else ""}"><h2>{tr}<small style="font:12px var(--mono);'
                   f'margin-left:10px;color:var(--ink2)">{n}</small></h2><p>{TIER_NOTE[tr]}</p>{"".join(blocks)}</section>')
    cnt = {t: sum(len(v) for v in tree.get(t, {}).values()) for t in TIERS}
    content = (f'<main class="al"><h1>原子库</h1>'
               '<p class="lead">每一种文风，都由几十个可拆、可练、可重组的动作构成。这里把 17 个引擎的每一个原子讲透：'
               '它是什么、为什么管用、用过头会怎样、什么时候别用，以及一道五分钟的练习。</p>'
               f'<div class="stat">{len(items)} 个原子 · 核心 {cnt["核心"]} · 常用 {cnt["常用"]} · 签名 {cnt["签名"]}</div>'
               f'<div class="filt">{filt}</div>{"".join(sec)}</main>')
    (OUT / "index.html").write_text(
        page("原子库", content + f"<style>{CSS}</style><script>{JS}</script>", "../"), encoding="utf-8")
    print(f"built atoms: {len(items)} atom page(s); tiers {cnt}; engines {len(engs)}")


if __name__ == "__main__":
    main()
