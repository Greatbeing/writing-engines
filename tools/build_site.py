"""采风 · 母品牌首页与两个子产品总览页（/ 与 /eval/）。

结构见 SITE.md：
  /           采风：主张 + 三扇门（引擎 / 讲义 / 评测）+ 三者如何咬合
  /engines/   写作引擎（原首页正文，迁移后由本脚本修补导航）
  /lecture/   写作讲义（build_lecture.py）
  /eval/      写作评测：批改台 + AI 腔检查器 + 盲评体系
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_articles as ba  # noqa: E402
from build_articles import ROOT, page  # noqa: E402

DOCS = ROOT / "docs"
GH = "https://github.com/Greatbeing/writing-engines"

# 三道风痕各属一个子产品：粗墨=引擎，细墨=讲义，朱红=评测
STROKES = [
    ("M4 14 C30 6, 56 24, 92 12", "#1A1A1A", "2.6"),
    ("M12 30 C36 22, 58 38, 82 28", "#1A1A1A", "2"),
    ("M20 46 C40 39, 58 53, 72 44", "#B23A2B", "2.6"),
]


def mark(only=None, w=120):
    ps = []
    for i, (d, c, sw) in enumerate(STROKES):
        op = "1" if only is None or only == i else ".18"
        ps.append(f'<path d="{d}" stroke="{c}" stroke-width="{sw}" opacity="{op}"/>')
    return (f'<svg class="mk" viewBox="0 0 96 56" width="{w}" fill="none" stroke-linecap="round" '
            f'aria-hidden="true">{"".join(ps)}</svg>')


def counts():
    engines = sorted(p.parent.name for p in ROOT.glob("*-writing/SKILL.md"))
    lectures = sorted((DOCS / "lecture").glob("[0-9][0-9].html"))
    arts = [p for p in (DOCS / "articles").glob("*.html") if p.name != "index.html" and p.stat().st_size > 2000]
    try:
        j = json.loads((ROOT / "atoms/index.json").read_text(encoding="utf-8"))
        atoms = len(j) if isinstance(j, list) else len(j.get("atoms") or j.get("items") or [])
    except Exception:
        atoms = 0
    days = [p for p in (DOCS / "daily").glob("20*.html")]
    return dict(engines=len(engines), lectures=len(lectures), arts=len(arts), atoms=atoms, days=len(days))


CSS = """
.home{max-width:1080px;margin:0 auto;padding:0 32px}
.h-hero{min-height:calc(100vh - 57px);padding:72px 0 64px;border-bottom:1px solid var(--ink);display:grid;
  grid-template-columns:minmax(0,1fr) minmax(0,.72fr);gap:clamp(40px,6vw,96px);align-items:center}
.h-hero h1{font:900 clamp(40px,5vw,72px)/1.28 var(--serif);letter-spacing:.08em}
.h-hero h1 span{display:block;white-space:nowrap}
.h-hero h1 .last{margin-top:.12em}
.h-hero .en{font:400 11px var(--mono);letter-spacing:.32em;text-transform:uppercase;color:var(--ink2);
  margin:34px 0 22px;white-space:nowrap}
.h-hero .rule{width:48px;height:1px;background:var(--ink);margin:0 0 22px}
.h-hero .sub{font:400 16px/2.05 var(--serif);color:var(--ink2);max-width:25em}
.h-hero .mk{width:100%;max-width:340px;justify-self:center;align-self:center}
.mk path{stroke-dasharray:140;stroke-dashoffset:140;animation:e-draw 1.4s cubic-bezier(.6,0,.2,1) forwards}
.mk path:nth-child(2){animation-delay:.25s}.mk path:nth-child(3){animation-delay:.5s}
@media(prefers-reduced-motion:reduce){.mk path{animation:none;stroke-dashoffset:0}}
.doors{display:grid;grid-template-columns:repeat(3,1fr);border-bottom:1px solid var(--ink)}
.door{display:flex;flex-direction:column;gap:14px;border:0;padding:40px 32px 44px;border-right:1px solid var(--rule)}
.door:first-child{padding-left:0}.door:last-child{border-right:0;padding-right:0}
.door .no{font:12px var(--mono);letter-spacing:.2em;color:var(--ink2)}
.door .mk{width:96px}
.door h2{font:900 30px/1.3 var(--serif);letter-spacing:.12em}
.door .verb{font:600 14px var(--serif);letter-spacing:.3em;color:var(--ink2)}
.door p{font:400 15.5px/1.95 var(--serif);color:var(--ink2);flex:1}
.door .num{font:12px var(--mono);letter-spacing:.1em;color:var(--ink2);border-top:1px solid var(--rule);padding-top:12px}
.door .go{font-size:14px;letter-spacing:.15em}
.door:hover h2{color:var(--zhu)}
.loop{padding:72px 0 80px;display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:56px}
.loop h3{font:900 26px/1.5 var(--serif);letter-spacing:.08em}
.loop ol{list-style:none;counter-reset:s}
.loop li{counter-increment:s;border-top:1px solid var(--rule);padding:18px 0 18px 56px;position:relative;font:400 16px/1.95 var(--serif)}
.loop li::before{content:counter(s,cjk-ideographic);position:absolute;left:0;top:18px;font:600 15px var(--serif);color:var(--ink2)}
.loop li b{font-weight:600}
.who{border-top:1px solid var(--ink);padding:48px 0 72px;font:400 17px/2.1 var(--serif);color:var(--ink2);max-width:40em}
.who b{color:var(--ink);font-weight:600}
/* 评测页 */
.ev{max-width:820px;margin:0 auto;padding:72px 32px 48px}
.ev .mk{width:110px;margin-bottom:22px}
.ev h1{font:900 38px/1.4 var(--serif);letter-spacing:.12em}
.ev .lead{font:400 17px/2 var(--serif);color:var(--ink2);margin:16px 0 40px;max-width:34em}
.tool{border-top:1px solid var(--ink);padding:30px 0 34px;display:grid;grid-template-columns:150px 1fr;gap:28px}
.tool .k{font:12px var(--mono);letter-spacing:.18em;color:var(--ink2);padding-top:6px}
.tool h2{font:600 22px/1.5 var(--serif);margin-bottom:8px}
.tool p{font:400 15.5px/1.95 var(--serif);color:var(--ink2)}
.tool .st{display:inline-block;margin-top:12px;font:12px var(--mono);letter-spacing:.1em;border:1px solid var(--rule);padding:2px 10px}
.tool .st.live{border-color:var(--zhu);color:var(--zhu)}
.tool .links{margin-top:12px;display:flex;gap:22px;font-size:14px}
@media(max-width:820px){.h-hero,.loop{grid-template-columns:1fr}.h-hero{min-height:0;padding:56px 0 48px}.h-hero .mk{justify-self:start;max-width:200px;order:-1}.h-hero .en{white-space:normal}
 .doors{grid-template-columns:1fr}.door,.door:first-child,.door:last-child{padding:32px 0;border-right:0;border-bottom:1px solid var(--rule)}
 .tool{grid-template-columns:1fr;gap:8px}.home,.ev{padding-left:20px;padding-right:20px}}
"""


def home(c):
    doors = [
        (0, "壹", "写作引擎", "拆法", "engines/",
         "每一种文风背后，都有一套作者没说出口的规则。把它拆成可操作的原子，再装配成能直接用的引擎。",
         f"{c['engines']} 个引擎 · {c['atoms']} 个原子 · {c['arts']} 篇范文"),
        (1, "贰", "写作讲义", "教法", "lecture/",
         "原子不是给机器背的。一讲一个手法：先看原文怎么做，再拆开为什么管用，最后自己动手写一遍。",
         f"{c['lectures']} 讲"),
        (2, "叁", "写作评测", "验法", "eval/",
         "写得好不好，不靠自夸。每天一篇，机检打回、评审逐条核对、改一句给你看——引擎和讲义管不管用，在这里见分晓。",
         f"批改台 {c['days']} 天 · 盲评待开跑"),
    ]
    d = "".join(
        f'<a class="door" href="{href}"><span class="no">{no}</span>{mark(i, 96)}'
        f'<h2>{name}</h2><span class="verb">{verb}</span><p>{desc}</p>'
        f'<span class="num">{num}</span><span class="go">进入 →</span></a>'
        for i, no, name, verb, href, desc, num in doors)
    return f"""<main class="home">
<section class="h-hero"><div><h1><span>采其风，</span><span>得其法，</span><span class="last">自成一体。</span></h1>
<p class="en">Collect the style · Learn the method · Find your own</p>
<div class="rule"></div>
<p class="sub">采风是一个教人写作的项目。先把名家的文风拆成原子，再把原子讲成课，最后用评测验证——目的不是让你像谁，是让你写出自己的风格。</p></div>
{mark(None, 380)}</section>
<section class="doors">{d}</section>
<section class="loop"><h3>三件事，<br>是同一件事的三步。</h3>
<ol><li><b>拆。</b>读一位作者，把他反复使用的动作找出来，写成能照做的原子，装进引擎。</li>
<li><b>教。</b>把原子讲成课：原文示范、为什么管用、换一个题目练一遍。</li>
<li><b>验。</b>每天用引擎写一篇，交给机检和评审打回、评改；评改里提炼出的经验，再回头修引擎、补讲义。</li></ol></section>
<section class="who">给<b>学生</b>、<b>文字工作者</b>，和所有想把字写好的人。<br>拆解是手段，模仿是阶段，最后要长出来的，是你自己的声音。</section>
</main>"""


def eval_page(c):
    blind = (ROOT / "eval/RESULTS.md").read_text(encoding="utf-8") if (ROOT / "eval/RESULTS.md").exists() else ""
    ran = "是否已跑 | **否**" not in blind
    return f"""<main class="ev">{mark(2, 110)}
<h1>写作评测</h1>
<p class="lead">引擎说自己能写出某种风格，讲义说某个手法管用——这些话都要拿结果来验。评测分三层：每天的批改，机器的初筛，人的盲评。</p>
<section class="tool"><div class="k">01 · 每天</div><div>
<h2>批改台</h2><p>写作端每天用一个引擎写一篇；没过机检的稿子打回重写，过了的交给评审逐条核对风格要点、挑出最该改的一句、提炼一条经验。全程留档，落选稿也能展开看。</p>
<span class="st live">运行中 · {c['days']} 天</span>
<div class="links"><a href="../daily/">进入批改台 →</a><a href="../daily/gems.html">句库与经验 →</a></div></div></section>
<section class="tool"><div class="k">02 · 机器</div><div>
<h2>AI 腔检查器</h2><p>扫描套话、金句腔、排比堆砌、网感词，按引擎各自的口径打分。分数是门槛，不是评价：过了只说明没有明显的机器味，好不好还得人看。</p>
<span class="st">v0.2 · 16 档口径</span>
<div class="links"><a href="{GH}/blob/master/tools/ai-flavor-checker.py">源码 ↗</a></div></div></section>
<section class="tool"><div class="k">03 · 人</div><div>
<h2>盲评</h2><p>同一道题，引擎版与裸模型版打乱顺序交给评分者，不告诉谁是谁，每题两人。胜率用 Wilson 区间判定，样本不够就不下结论。</p>
<span class="st{' live' if ran else ''}">{'已出结果' if ran else '尚未开跑 · 结果页如实留空'}</span>
<div class="links"><a href="{GH}/blob/master/eval/DESIGN.md">设计 ↗</a><a href="{GH}/blob/master/eval/RESULTS.md">结果 ↗</a></div></div></section>
</main>"""


def patch_engines():
    """原首页正文已迁到 /engines/：修补相对路径与导航，去掉印章与开场动画。"""
    p = DOCS / "engines/index.html"
    t = p.read_text(encoding="utf-8")
    for a in ("articles/", "compare/", "lecture/", "daily/", "favicon.svg"):
        t = t.replace(f'href="{a}', f'href="../{a}').replace(f'src="{a}', f'src="../{a}')
    t = t.replace('href="../../', 'href="../')
    t = re.sub(r'<div id="intro".*?</div></div>\s*', "", t, flags=re.S)
    t = re.sub(r"\.seal\{.*?\n@keyframes stamp\{[^\n]*\n", "", t, flags=re.S)
    t = t.replace("h.classList.add('intro')", "void 0")
    t = re.sub(r'<a class="brand" href="[^"]*">', '<a class="brand" href="../">', t)
    t = re.sub(r"<li><a href=\"\.\./lecture/\">讲义</a></li>.*?(?=<li><a href=\"https://github)",
               '<li><a href="../articles/">范文</a></li><li><a href="../compare/">同题四体</a></li>'
               '<li class="sep"><a href="../lecture/">讲义</a></li><li><a href="../eval/">评测</a></li>',
               t, flags=re.S)
    t = t.replace("<title>采风 · Caifeng — 采其风，得其法，自成一体</title>", "<title>写作引擎 · 采风</title>")
    if "li.sep" not in t:
        t = t.replace("</style>", "nav li.sep{border-left:1px solid var(--rule);padding-left:28px}\n</style>", 1)
    p.write_text(t, encoding="utf-8")


def unify_nav(t):
    """引擎页沿用旧首页的手写导航：换成全站统一导航，页内锚点挪到导航下的一行子目录。"""
    anchors = re.findall(r'<li><a href="(#[^"]+)">([^<]+)</a></li>', t)
    sub = "".join(f'<a href="{h}">{n}</a>' for h, n in anchors if h != "#yuan")
    sub += '<a href="../articles/">范文</a><a href="../compare/">同题四体</a>'
    new = (f'<nav><div class="wrap"><a class="brand" href="../">{ba.LOGO.format(w=26)}采风</a>'
           f'{ba.site_nav("../")}</div></nav><div class="subnav"><div class="wrap">{sub}</div></div>')
    t = re.sub(r"<nav>.*?</nav>", new, t, count=1, flags=re.S)
    css = ("nav .snav{display:flex;gap:26px;font-size:13.5px;letter-spacing:.16em}"
           "nav .snav a{border:0;color:var(--ink2);padding:17px 0 16px;border-bottom:1px solid transparent}"
           "nav .snav a:hover{color:var(--zhu)}nav .snav a.on{color:var(--ink);border-bottom-color:var(--ink)}"
           ".subnav{border-bottom:1px solid var(--rule)}.subnav .wrap{display:flex;gap:24px;flex-wrap:wrap;"
           "font-size:13px;color:var(--ink2);letter-spacing:.1em;padding-top:10px;padding-bottom:10px}"
           ".subnav a{border:0}.subnav a:hover{color:var(--zhu)}")
    if ".subnav{" not in t:
        t = t.replace("</style>", css + "\n</style>", 1)
    t = t.replace("<h1>采其风，得其法，<br>自成一体。</h1>", "<h1>写作引擎</h1>")
    return t


def main():
    c = counts()
    ba.SECTION = ""
    (DOCS / "index.html").write_text(
        page("采其风，得其法，自成一体", f"<style>{CSS}</style>" + home(c), ""), encoding="utf-8")
    ba.SECTION = "eval"
    (DOCS / "eval").mkdir(exist_ok=True)
    (DOCS / "eval/index.html").write_text(
        page("写作评测", f"<style>{CSS}</style>" + eval_page(c), "../"), encoding="utf-8")
    # 引擎页由模板（原首页）生成，每次重建都从模板开始，保证幂等
    (DOCS / "engines").mkdir(exist_ok=True)
    (DOCS / "engines/index.html").write_text(
        (ROOT / "tools/templates/engines.html").read_text(encoding="utf-8"), encoding="utf-8")
    if True:
        patch_engines()
        e = DOCS / "engines/index.html"
        ba.SECTION = "engines"
        e.write_text(unify_nav(e.read_text(encoding="utf-8")), encoding="utf-8")
    print("built site:", c)


if __name__ == "__main__":
    main()
