#!/usr/bin/env python3
"""同题四体对照页：demo/<题号>/*.md -> docs/compare/<题号>.html

用法：python tools/build_compare.py
每个题目目录放 baseline.md / human-voice.md / guanfang.md / feature.md，有几篇放几篇。
"""
import html, json, re, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_articles import page  # 复用文章页的外壳、配色与夜读

OUT = ROOT / "docs" / "compare"
VERSIONS = [  # 文件名, 标签, 副标, 是否引擎
    ("baseline.md",    "裸模型",   "不加载任何引擎", False),
    ("human-voice.md", "城市之风", "活人感 · human-voice-writing", True),
    ("guanfang.md",    "庙堂之风", "官方体 · guanfang-writing", True),
    ("feature.md",     "人间之风", "特稿 · feature-writing", True),
]

CSS = """
.cmp{max-width:1280px;margin:0 auto;padding:56px 32px 24px}
.cmp h1{font:900 30px/1.4 var(--serif);letter-spacing:.08em}
.cmp .q{margin:14px 0 6px;font:400 17px/1.8 var(--serif)}
.cmp .mat{font-size:13.5px;color:var(--ink2);margin-bottom:22px}
.cmp .mat summary{cursor:pointer;color:var(--ink)}
.cmp .mat li{margin:6px 0 0 1.4em}
.tabs{display:none;gap:0;border:1px solid var(--ink);margin-bottom:20px}
.tabs button{flex:1;background:none;border:0;border-right:1px solid var(--rule);padding:10px 4px;font:600 13px var(--serif);letter-spacing:.15em;color:var(--ink2);cursor:pointer}
.tabs button:last-child{border:0}.tabs button.on{background:var(--ink);color:var(--paper)}
.grid{display:grid;grid-template-columns:repeat(var(--n),1fr);border-top:1px solid var(--ink)}
.col{padding:22px 22px 32px;border-right:1px solid var(--rule);min-width:0}
.col:last-child{border-right:0}
.col .tag{font:600 12px var(--serif);letter-spacing:.3em;color:var(--zhu)}
.col.base .tag{color:var(--ink2)}
.col .sub{font:12px var(--mono);color:var(--ink2);margin:2px 0 10px}
.col .stat{font:12px var(--mono);color:var(--ink2);padding-bottom:14px;border-bottom:1px dashed var(--rule);margin-bottom:18px}
.col .body{font-size:15.5px;line-height:1.95}
.col .body h1{font:600 1.25em/1.5 var(--serif);margin:0 0 1em}
.col .body h2{font-size:1.05em}
.col .fold{position:relative;max-height:30em;overflow:hidden}
.col .fold::after{content:"";position:absolute;left:0;right:0;bottom:0;height:5em;background:linear-gradient(transparent,var(--paper))}
.col.open .fold{max-height:none}.col.open .fold::after{display:none}
.col .more{margin-top:12px;background:none;border:1px solid var(--rule);color:var(--ink2);font:13px var(--sans);padding:4px 14px;cursor:pointer}
.col .more:hover{border-color:var(--zhu);color:var(--zhu)}
.how{max-width:1280px;margin:0 auto;padding:8px 32px 56px;font-size:13px;color:var(--ink2)}
.how .box{border-top:1px solid var(--ink);padding-top:14px}
@media(max-width:900px){.tabs{display:flex}.grid{grid-template-columns:1fr;border-top:0}
 .col{display:none;border:0;padding:0}.col.act{display:block}.col .fold{max-height:none}.col .fold::after,.col .more{display:none}}
"""

JS = """
document.querySelectorAll('.more').forEach(b=>b.onclick=()=>{const c=b.closest('.col');
 c.classList.toggle('open');b.textContent=c.classList.contains('open')?'收起':'展开全文'});
const tb=document.querySelectorAll('.tabs button'),cs=document.querySelectorAll('.col');
tb.forEach((b,i)=>b.onclick=()=>{tb.forEach(x=>x.classList.remove('on'));cs.forEach(x=>x.classList.remove('act'));
 b.classList.add('on');cs[i].classList.add('act')});
"""


def chars(md):
    return len(re.sub(r"\s|[#>*_`|\-]", "", md))


def build(tid, topic, folder):
    cols, tabs = [], []
    for i, (fn, tag, sub, eng) in enumerate(VERSIONS):
        f = folder / fn
        if not f.exists():
            continue
        md = f.read_text(encoding="utf-8")
        md = re.sub(r"(?m)^\s*\*引擎产出示例.*$", "", md)  # 去掉文末说明，对照页统一注明
        body = markdown.markdown(md, extensions=["tables", "sane_lists"])
        first = not cols
        cols.append(f"""<div class="col{'' if eng else ' base'}{' act' if first else ''}">
<div class="tag">{tag}</div><div class="sub">{html.escape(sub)}</div>
<div class="stat">{chars(md)} 字</div>
<div class="fold"><div class="body">{body}</div></div><button class="more">展开全文</button></div>""")
        tabs.append(f'<button class="{"on" if first else ""}">{tag}</button>')
    mats = "".join(f"<li>{html.escape(m['name'])}（{html.escape(m['tag'])}）：{html.escape(m['scene'])}。「{html.escape(m['quote'])}」</li>"
                   for m in topic.get("material", []))
    content = f"""<style>{CSS}</style>
<section class="cmp"><h1>同题四体 · {tid}</h1>
<p class="q">{html.escape(topic['prompt'])}</p>
<details class="mat"><summary>四个版本拿到的同一份素材（合成，人物虚构）</summary><ul>{mats}</ul></details>
<div class="tabs">{''.join(tabs)}</div>
<div class="grid" style="--n:{len(cols)}">{''.join(cols)}</div></section>
<div class="how"><div class="box">做法：四版拿到完全相同的题目与素材，唯一的变量是加载哪个引擎。
裸模型与活人感、特稿两版由独立 agent 分别生成（裸模型不读仓库任何文件）；官方体版为人工按引擎流程撰写，非独立生成。
这是展示，不是评测——胜率以 <a href="https://github.com/Greatbeing/writing-engines/blob/master/eval/RESULTS.md">eval/RESULTS.md</a> 的盲评为准。
源文件：<a href="https://github.com/Greatbeing/writing-engines/tree/master/demo/{tid}">demo/{tid}/</a></div></div>
<script>{JS}</script>"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tid}.html").write_text(page(f"同题四体 · {tid}", content, "../"), encoding="utf-8")
    return len(cols)


def main():
    topics = {t["id"]: t for t in json.loads((ROOT / "eval" / "prompts.json").read_text(encoding="utf-8"))["topics"]}
    n = 0
    for d in sorted((ROOT / "demo").iterdir()):
        if d.is_dir() and d.name in topics:
            k = build(d.name, topics[d.name], d)
            print(f"  compare/{d.name}.html  {k} 版")
            n += 1
    print(f"built {n} compare page(s)")


if __name__ == "__main__":
    main()
