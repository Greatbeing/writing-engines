#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 lecture/*.md 生成为 docs/lecture/ 的线上讲义。

复用 build_articles 的外壳（导航、页脚、夜读、字号），只加讲义自己的排版规则：
  - 正文窄栏 720px，行高 1.95
  - 一级标题下压一道朱红细线
  - 「## 一、二、三」这类小节标题带朱红序号
  - 引用块（名家原文 / AI 反例）用左细线区分，不换色
  - 「你的练习」一节加浅底框，便于打印做作业

用法：python tools/build_lecture.py
"""
import html
import re
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import page, ROOT  # noqa: E402

LEC = ROOT / "lecture"
OUT = ROOT / "docs" / "lecture"

CSS = """
.lec{max-width:720px;margin:0 auto;padding:56px 28px 40px}
.lec h1{font:900 clamp(28px,4vw,40px)/1.3 var(--serif);letter-spacing:.06em;margin:0 0 6px}
.lec .sub{font:12px var(--mono);color:var(--ink2);letter-spacing:.18em;margin-bottom:8px}
.lec hr.rule{border:0;border-top:1px solid var(--zhu);width:64px;margin:18px 0 34px}
.body{font-size:17px;line-height:1.95}
.body h2{font:600 21px/1.6 var(--serif);letter-spacing:.04em;margin:44px 0 14px;padding-left:14px;position:relative}
.body h2::before{content:"";position:absolute;left:0;top:.55em;width:5px;height:5px;background:var(--zhu);border-radius:1px}
.body h3{font:600 17px/1.6 var(--serif);margin:26px 0 8px;color:var(--ink2)}
.body p{margin:0 0 16px}
.body blockquote{border-left:2px solid var(--ink);padding:2px 0 2px 18px;margin:18px 0;color:var(--ink2);font:400 17px/1.9 var(--serif)}
.body blockquote p{margin:0 0 10px}
.body blockquote p:last-child{margin:0}
.body strong{font-weight:600}
.body ul,.body ol{margin:0 0 16px 1.3em}
.body li{margin:6px 0}
.body hr{border:0;border-top:1px dashed var(--rule);margin:36px 0}
.body em{font-style:normal;color:var(--ink2)}
.body table{font-size:15px}
.pager{max-width:720px;margin:0 auto;padding:0 28px 56px;display:flex;justify-content:space-between;gap:16px;font-size:14px}
.pager a{border-bottom:1px solid var(--rule)}
.pager a:hover{border-color:var(--zhu);color:var(--zhu)}
.list{max-width:820px;margin:0 auto;padding:64px 32px 40px}
.list h1{font:900 34px/1.4 var(--serif);letter-spacing:.1em}
.list .lead{color:var(--ink2);margin:14px 0 10px;font:400 17px/1.9 var(--serif)}
.list .brandline{font:12px var(--mono);color:var(--ink2);letter-spacing:.18em;margin-bottom:36px}
.item{display:block;border:0;border-top:1px solid var(--ink);padding:24px 0}
.item:last-of-type{border-bottom:1px solid var(--ink)}
.item .no{font:600 12px var(--serif);letter-spacing:.3em;color:var(--zhu)}
.item h2{font:600 20px/1.6 var(--serif);margin:6px 0 0}
.item .one{color:var(--ink2);font-size:14.5px;margin-top:6px}
.foot{max-width:820px;margin:0 auto;padding:0 32px 64px;font-size:13px;color:var(--ink2)}
.foot .box{border-top:1px solid var(--zhu);padding-top:14px;max-width:64px}
.homework{background:#EFE9DC;border-left:2px solid var(--zhu);padding:4px 20px 6px;margin:10px 0 26px}
.homework p{margin:10px 0}
.homework ol,.homework ul{margin:8px 0 10px 1.3em}
@media(max-width:640px){.lec,.pager{padding-left:20px;padding-right:20px}.body{font-size:16.5px}}
"""


def render(md_path):
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else md_path.stem
    body_md = text[m.end():] if m else text
    body = markdown.markdown(body_md, extensions=["tables", "sane_lists"])
    # 「你的练习」一节加浅底框：便于打印做作业
    body = re.sub(r'(<h2>[^<]*你的练习[^<]*</h2>)(.*?)(?=<h2>|<hr\s*/?>|\Z)',
                  lambda x: x.group(1) + '<div class="homework">' + x.group(2) + "</div>", body, flags=re.S)
    return title, body


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()
    files = sorted(LEC.glob("*.md"))
    items = []
    for i, f in enumerate(files):
        title, body = render(f)
        slug = f.stem.split("-")[0]
        prev = files[i - 1] if i > 0 else None
        nxt = files[i + 1] if i + 1 < len(files) else None
        pager = ('<div class="pager">'
                 + (f'<a href="{prev.stem.split("-")[0]}.html">← {html.escape(render(prev)[0])}</a>' if prev else "<span></span>")
                 + (f'<a href="{nxt.stem.split("-")[0]}.html">{html.escape(render(nxt)[0])} →</a>' if nxt else "<span></span>")
                 + "</div>")
        content = (f'<article class="lec"><div class="sub">采风 · 讲义</div>'
                   f"<h1>{html.escape(title)}</h1><hr class=\"rule\">"
                   f'<div class="body">{body}</div></article>{pager}')
        (OUT / f"{slug}.html").write_text(page(title + " · 采风讲义", content + f"<style>{CSS}</style>", "../"), encoding="utf-8")
        one = re.search(r"^>\s*\*\*(.+?)\*\*", body_md_of(f), re.M)
        items.append((slug, title, (one.group(1) if one else "").strip()))
        print(f"  lecture/{slug}.html  {title}")

    def cn(n):
        d = "一二三四五六七八九"
        return d[n-1] if n < 10 else ("十" if n == 10 else "十" + d[n-11] if n < 20 else str(n))

    lst = "".join(
        f'<a class="item" href="{s}.html"><div class="no">第{cn(i+1)}讲</div>'
        f"<h2>{html.escape(t)}</h2>"
        + (f'<div class="one">{html.escape(o)}</div>' if o else "")
        + "</a>"
        for i, (s, t, o) in enumerate(items))
    idx = (f'<section class="list"><h1>采风 · 讲义</h1>'
           f'<p class="lead">把写作变成可以学的手艺。<br>一讲只教一个动作，写完就能改。</p>'
           f'<div class="brandline">采其风，得其法，成其体</div>{lst}</section>'
           f'<div class="foot"><div class="box"></div><p>三季共{cn(len(items))}讲：'
           + "、".join(t.split()[1][0] for _, t, _ in items if len(t.split()) > 1) + "。"
           f"每讲五节——一个动作、名家怎么写、AI 写成什么样、改一遍、你的练习。</p></div>"
           f"<style>{CSS}</style>")
    (OUT / "index.html").write_text(page("采风 · 讲义", idx, "../"), encoding="utf-8")
    print(f"built {len(items)} lecture(s) + index")


def body_md_of(f):
    return f.read_text(encoding="utf-8")


if __name__ == "__main__":
    main()