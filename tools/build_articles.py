#!/usr/bin/env python3
"""把各引擎 examples/*.md 生成为官网文章页：docs/articles/。

用法：python tools/build_articles.py
新增文章：把 .md 放进某个引擎的 examples/，重新运行本脚本并提交 docs/。
"""
import html, re, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "articles"
ENGINES = {  # 引擎目录 -> (风名, 文体, 短名)
    "human-voice-writing": ("城市之风", "活人感", "human"),
    "guanfang-writing":    ("庙堂之风", "官方体", "guanfang"),
    "feature-writing":     ("人间之风", "特稿",   "feature"),
}

LOGO = ('<svg viewBox="0 0 96 56" width="{w}" fill="none" stroke-linecap="round" aria-hidden="true">'
        '<path d="M4 14 C30 6, 56 24, 92 12" stroke="#1A1A1A" stroke-width="2.6"/>'
        '<path d="M12 30 C36 22, 58 38, 82 28" stroke="#1A1A1A" stroke-width="2"/>'
        '<path d="M20 46 C40 39, 58 53, 72 44" stroke="#B23A2B" stroke-width="2.6"/></svg>')

CSS = """
:root{--paper:#F5F1E8;--ink:#1A1A1A;--ink2:#5A564E;--rule:#D8D1C2;--zhu:#B23A2B;
--serif:'Noto Serif SC','Source Han Serif SC','Songti SC',serif;
--sans:-apple-system,'PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif;
--mono:'JetBrains Mono',ui-monospace,Consolas,monospace;--fs:18px}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);font:16px/1.9 var(--sans);-webkit-font-smoothing:antialiased}
body.night{--paper:#1C1B19;--ink:#E6E0D3;--ink2:#9C968A;--rule:#3A3731}
::selection{background:var(--zhu);color:var(--paper)}
a{color:inherit;text-decoration:none;border-bottom:1px solid var(--rule)}
a:hover{border-color:var(--zhu)}
nav{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--rule)}
nav .in{max-width:1080px;margin:0 auto;padding:0 32px;display:flex;justify-content:space-between;align-items:center;height:56px}
nav .brand{font:600 17px var(--serif);letter-spacing:.2em;border:0;display:flex;gap:10px;align-items:center}
nav .tools{display:flex;gap:6px;font-size:13px;color:var(--ink2)}
nav .tools a,nav .tools button{border:1px solid var(--rule);background:none;color:inherit;font:13px var(--sans);padding:3px 10px;cursor:pointer}
nav .tools button:hover,nav .tools a:hover{border-color:var(--zhu);color:var(--zhu)}
#bar{position:fixed;top:56px;left:0;height:2px;background:var(--zhu);width:0;z-index:6}
/* 列表 */
.list{max-width:760px;margin:0 auto;padding:72px 32px 40px}
.list h1{font:900 34px/1.4 var(--serif);letter-spacing:.12em}
.list .intro{color:var(--ink2);margin:12px 0 48px}
.item{display:block;border:0;border-top:1px solid var(--ink);padding:28px 0}
.item:last-child{border-bottom:1px solid var(--ink)}
.item .feng{font:600 12px var(--serif);letter-spacing:.3em;color:var(--zhu)}
.item h2{font:600 23px/1.6 var(--serif);margin:6px 0 8px}
.item:hover h2{color:var(--zhu)}
.item p{color:var(--ink2);font-size:15px}
.item .meta{font:12px var(--mono);color:var(--ink2);margin-top:10px;letter-spacing:.05em}
/* 正文 */
article{max-width:34em;margin:0 auto;padding:64px 24px 40px;font-size:var(--fs)}
article .head{border-bottom:1px solid var(--ink);padding-bottom:28px;margin-bottom:36px}
article .feng{font:600 13px var(--serif);letter-spacing:.3em;color:var(--zhu)}
article h1{font:900 1.75em/1.45 var(--serif);letter-spacing:.04em;margin:10px 0 14px}
article .meta{font:13px var(--sans);color:var(--ink2);letter-spacing:.05em}
.body{font-family:var(--serif);line-height:2;text-align:justify}
.body p{margin:0 0 1.15em}
.body h2{font:600 1.15em/1.6 var(--serif);margin:2.2em 0 .9em;padding-left:14px;border-left:3px solid var(--zhu)}
.body h3{font:600 1.05em var(--serif);margin:1.8em 0 .7em}
.body blockquote{border-left:2px solid var(--rule);padding:2px 0 2px 18px;color:var(--ink2);margin:1.4em 0}
.body ul,.body ol{padding-left:1.6em;margin:0 0 1.15em}
.body strong{font-weight:600;background:linear-gradient(transparent 62%,rgba(178,58,43,.16) 0)}
.body hr{border:0;text-align:center;margin:2.4em 0}.body hr::after{content:"· · ·";color:var(--ink2);letter-spacing:.6em}
.body table{border-collapse:collapse;width:100%;font:14px/1.7 var(--sans);margin:1.4em 0}
.body th,.body td{border-bottom:1px solid var(--rule);padding:8px 6px;text-align:left}
.body img{max-width:100%}
.note{max-width:34em;margin:0 auto;padding:0 24px 24px;font-size:13px;color:var(--ink2)}
.note .box{border-top:1px solid var(--ink);padding-top:16px}
.pager{max-width:34em;margin:0 auto;padding:8px 24px 64px;display:flex;justify-content:space-between;gap:16px;font-size:14px}
.pager a{border:0;color:var(--ink2)}.pager a:hover{color:var(--zhu)}
footer{max-width:1080px;margin:0 auto;padding:40px 32px 56px;border-top:1px solid var(--rule);display:flex;gap:14px;align-items:center;font:600 14px var(--serif);letter-spacing:.2em}
@media(max-width:600px){article{padding-top:40px}.list{padding-top:48px}nav .in{padding:0 16px}}
@media print{nav,#bar,.pager,footer{display:none}body{background:#fff}}
"""

JS = """
const b=document.body,k='cf-read';
const s=JSON.parse(localStorage.getItem(k)||'{}');
if(s.fs)document.documentElement.style.setProperty('--fs',s.fs+'px');
if(s.night)b.classList.add('night');
function save(){localStorage.setItem(k,JSON.stringify(s))}
document.querySelectorAll('[data-fs]').forEach(x=>x.onclick=()=>{
  s.fs=Math.min(24,Math.max(15,(s.fs||18)+(+x.dataset.fs)));
  document.documentElement.style.setProperty('--fs',s.fs+'px');save()});
const n=document.getElementById('night');
if(n)n.onclick=()=>{s.night=!s.night;b.classList.toggle('night',s.night);save()};
const bar=document.getElementById('bar');
if(bar)addEventListener('scroll',()=>{const h=document.documentElement;
  bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100||0)+'%'},{passive:true});
"""


def page(title, body, rel, reader=False):
    tools = ('<div class="tools"><button data-fs="-1" aria-label="缩小字号">A−</button>'
             '<button data-fs="1" aria-label="放大字号">A＋</button>'
             '<button id="night" aria-label="夜读">夜读</button>'
             f'<a href="{rel}articles/">目录</a></div>') if reader else \
            f'<div class="tools"><button id="night">夜读</button><a href="{rel}">首页</a></div>'
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · 采风</title>
<link rel="icon" href="{rel}favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;900&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<nav><div class="in"><a class="brand" href="{rel}">{LOGO.format(w=26)}采风</a>{tools}</div></nav>
{'<div id="bar"></div>' if reader else ''}
{body}
<footer>{LOGO.format(w=40)}采风 · CAIFENG</footer>
<script>{JS}</script></body></html>
"""


def collect():
    arts = []
    for eng, (feng, kind, short) in ENGINES.items():
        for f in sorted((ROOT / eng / "examples").glob("*.md")):
            text = f.read_text(encoding="utf-8")
            m = re.match(r"\s*#\s+(.+)", text)
            title = m.group(1).strip() if m else f.stem
            body_md = text[m.end():] if m else text
            date = f.stem[:10] if re.match(r"\d{4}-\d{2}-\d{2}", f.stem) else ""
            paras = [p.strip() for p in body_md.split("\n\n") if p.strip() and not p.lstrip().startswith(("#", ">", "|", "-"))]
            plain = re.sub(r"[*_`]", "", paras[0]) if paras else ""
            chars = len(re.sub(r"\s|[#>*_`|\-]", "", body_md))
            slug = f"{date}-{short}" if date else f"{short}-{len(arts)}"
            arts.append(dict(src=f.relative_to(ROOT).as_posix(), title=title, md=body_md, date=date,
                             feng=feng, kind=kind, eng=eng, excerpt=plain[:90] + ("…" if len(plain) > 90 else ""),
                             chars=chars, mins=max(1, round(chars / 450)), slug=slug))
    arts.sort(key=lambda a: a["date"], reverse=True)
    return arts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()
    arts = collect()
    for i, a in enumerate(arts):
        body = markdown.markdown(a["md"], extensions=["tables", "sane_lists"])
        prev = arts[i - 1] if i > 0 else None
        nxt = arts[i + 1] if i + 1 < len(arts) else None
        pager = ('<div class="pager">'
                 + (f'<a href="{prev["slug"]}.html">← {html.escape(prev["title"])}</a>' if prev else '<span></span>')
                 + (f'<a href="{nxt["slug"]}.html">{html.escape(nxt["title"])} →</a>' if nxt else '<span></span>')
                 + '</div>')
        content = f"""<article>
<div class="head"><div class="feng">{a['feng']} · {a['kind']}</div>
<h1>{html.escape(a['title'])}</h1>
<div class="meta">{a['date']} · 约 {a['chars']} 字 · 读完约 {a['mins']} 分钟</div></div>
<div class="body">{body}</div></article>
<div class="note"><div class="box">本文是引擎 <code>{a['eng']}</code> 的模型产出示例，不是语料原文。
源文件：<a href="https://github.com/Greatbeing/writing-engines/blob/master/{a['src']}">{html.escape(a['src'])}</a></div></div>
{pager}"""
        (OUT / f"{a['slug']}.html").write_text(page(a["title"], content, "../", reader=True), encoding="utf-8")
    items = "".join(f"""<a class="item" href="{a['slug']}.html"><div class="feng">{a['feng']} · {a['kind']}</div>
<h2>{html.escape(a['title'])}</h2><p>{html.escape(a['excerpt'])}</p>
<div class="meta">{a['date']} · {a['chars']} 字 · {a['mins']} 分钟</div></a>""" for a in arts)
    idx = f"""<section class="list"><h1>文章</h1>
<p class="intro">引擎写出来的东西。不讲方法，只看成品。<br>想看差别：<a href="../compare/">同题四体 · 同一份素材，四种写法 →</a></p>{items}</section>"""
    (OUT / "index.html").write_text(page("文章", idx, "../"), encoding="utf-8")
    print(f"built {len(arts)} articles -> {OUT.relative_to(ROOT)}")
    for a in arts:
        print(f"  {a['slug']}.html  {a['title']}")


if __name__ == "__main__":
    sys.exit(main())
