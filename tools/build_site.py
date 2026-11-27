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
    try:
        fl = [a.get("family") for a in j]
        fams, uniq = len(set(fl) - {"独有"}), fl.count("独有")
    except Exception:
        fams = uniq = 0
    return dict(engines=len(engines), lectures=len(lectures), arts=len(arts), atoms=atoms, days=len(days),
                fams=fams, uniq=uniq)


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

# 开场：宣纸上三道风痕依次落笔，各配一句——采其风、得其法、自成一体；朱红最后落定，纸幕上卷露出首页。
# 每次会话只放一次；点击或按键即跳过；减弱动效时不放。约 3s。
INTRO_CSS = """
#intro{display:none}
html.intro #intro{display:flex;position:fixed;inset:0;z-index:60;background:var(--paper);align-items:center;justify-content:center;
  cursor:pointer;animation:in-lift .9s cubic-bezier(.76,0,.24,1) 2.25s forwards}
html.intro body{overflow:hidden}
@keyframes in-lift{to{transform:translateY(-100%)}}
.in-wrap{display:grid;grid-template-columns:auto auto;align-items:center;gap:clamp(20px,3vw,40px)}
.in-wrap svg{width:min(52vw,440px);height:auto;overflow:visible}
.in-wrap path{stroke-dasharray:140;stroke-dashoffset:140;animation:in-draw .7s cubic-bezier(.65,0,.25,1) forwards}
.in-wrap path:nth-child(1){animation-delay:.15s}.in-wrap path:nth-child(2){animation-delay:.6s}.in-wrap path:nth-child(3){animation-delay:1.05s}
@keyframes in-draw{to{stroke-dashoffset:0}}
.in-ch{display:grid;grid-template-rows:repeat(3,1fr);height:min(30vw,256px);font:600 clamp(15px,1.6vw,19px)/1 var(--serif);color:var(--ink2);letter-spacing:.2em}
.in-ch span{display:flex;align-items:center;opacity:0;transform:translateX(-6px);animation:in-ch .6s ease forwards}
.in-ch span:nth-child(1){animation-delay:.55s}.in-ch span:nth-child(2){animation-delay:1s}
.in-ch span:nth-child(3){animation-delay:1.45s;color:var(--zhu)}
@keyframes in-ch{to{opacity:1;transform:none}}
.in-foot{position:absolute;left:0;right:0;bottom:12vh;text-align:center;font:400 11px var(--mono);letter-spacing:.5em;
  color:var(--ink2);opacity:0;animation:in-ch .8s ease 1.5s forwards}
html.intro .h-hero h1 span{opacity:0;animation:in-ink 1s cubic-bezier(.2,.7,.2,1) forwards}
html.intro .h-hero h1 span:nth-child(1){animation-delay:2.7s}
html.intro .h-hero h1 span:nth-child(2){animation-delay:2.88s}
html.intro .h-hero h1 span:nth-child(3){animation-delay:3.06s}
@keyframes in-ink{from{opacity:0;filter:blur(10px);transform:translateY(.2em)}to{opacity:1;filter:none;transform:none}}
html.intro .h-hero .mk path{animation-delay:2.9s}
html.intro .h-hero .mk path:nth-child(2){animation-delay:3.1s}
html.intro .h-hero .mk path:nth-child(3){animation-delay:3.3s}
html.skip #intro{animation:in-lift .5s cubic-bezier(.76,0,.24,1) forwards!important}
@media(prefers-reduced-motion:reduce){html.intro #intro{display:none}html.intro body{overflow:auto}
  html.intro .h-hero h1 span{animation:none;opacity:1}}
"""
INTRO_HTML = (
    '<script>(function(h){try{if(!sessionStorage.cfIntro&&!matchMedia("(prefers-reduced-motion: reduce)").matches){'
    'h.classList.add("intro");sessionStorage.cfIntro=1}}catch(e){}})(document.documentElement)</script>'
    '<div id="intro" aria-hidden="true"><div class="in-wrap">'
    '<svg viewBox="0 0 96 56" fill="none" stroke-linecap="round">'
    '<path d="M4 14 C30 6, 56 24, 92 12" stroke="#1A1A1A" stroke-width="2.2"/>'
    '<path d="M12 30 C36 22, 58 38, 82 28" stroke="#1A1A1A" stroke-width="1.7"/>'
    '<path d="M20 46 C40 39, 58 53, 72 44" stroke="#B23A2B" stroke-width="2.2"/></svg>'
    '<div class="in-ch"><span>采其风</span><span>得其法</span><span>自成一体</span></div></div>'
    '<p class="in-foot">CAIFENG</p></div>'
    '<script>(function(){const h=document.documentElement;if(!h.classList.contains("intro"))return;'
    'const i=document.getElementById("intro");const end=()=>{h.classList.add("skip");'
    'setTimeout(()=>{h.classList.remove("intro","skip");i.remove()},520)};'
    'i.addEventListener("click",end);addEventListener("keydown",end,{once:true});'
    'i.addEventListener("animationend",e=>{if(e.animationName==="in-lift"){h.classList.remove("intro");i.remove()}})})()</script>'
)


# 原子动效：hero 右侧的三道风痕由墨点（原子）组成。
# 墨点先散落在纸面上，再沿各自的笔道归位、聚成三道风痕（拆解→重组）；
# 鼠标靠近时墨点被拨散，移开后重新归位。减弱动效时只显示静态笔画。
ATOM_CSS = """
.h-hero .atoms{width:100%;max-width:380px;justify-self:center;align-self:center;overflow:visible;touch-action:none}
.h-hero .atoms .ghost{opacity:0;transition:opacity 1.2s ease}
.h-hero .atoms.done .ghost{opacity:.9}
.h-hero .atoms .cap{font:400 3px var(--mono);letter-spacing:.6px;fill:var(--ink2);opacity:0;transition:opacity .8s ease}
.h-hero .atoms.done .cap{opacity:1}
@media(prefers-reduced-motion:reduce){.h-hero .atoms circle{display:none}.h-hero .atoms .ghost{opacity:1}}
"""
ATOM_SVG = (
    '<svg class="atoms" viewBox="-8 -10 112 80" fill="none" stroke-linecap="round" aria-hidden="true">'
    '<path class="ghost" d="M4 14 C30 6, 56 24, 92 12" stroke="#1A1A1A" stroke-width="2.6"/>'
    '<path class="ghost" d="M12 30 C36 22, 58 38, 82 28" stroke="#1A1A1A" stroke-width="2"/>'
    '<path class="ghost" d="M20 46 C40 39, 58 53, 72 44" stroke="#B23A2B" stroke-width="2.6"/>'
    '<g class="dots"></g>'
    '<text class="cap" x="-6" y="66">ATOMS → ENGINE</text></svg>'
)
ATOM_JS = """
(()=>{const sv=document.querySelector('.h-hero .atoms');if(!sv)return;
if(matchMedia('(prefers-reduced-motion: reduce)').matches){sv.classList.add('done');return}
const NS='http://www.w3.org/2000/svg',g=sv.querySelector('.dots'),paths=[...sv.querySelectorAll('.ghost')];
const P=[];paths.forEach((p,k)=>{const L=p.getTotalLength(),n=[46,36,26][k],r=[1.25,1.0,1.25][k],col=p.getAttribute('stroke');
 for(let i=0;i<n;i++){const t=(i+.5)/n*L,q=p.getPointAtLength(t);
  const c=document.createElementNS(NS,'circle');c.setAttribute('r',(r*(.75+Math.random()*.5)).toFixed(2));c.setAttribute('fill',col);g.appendChild(c);
  const a=Math.random()*6.283,d=18+Math.random()*34;
  P.push({c,hx:q.x,hy:q.y,x:48+Math.cos(a)*d*1.3,y:28+Math.sin(a)*d,vx:0,vy:0,ph:Math.random()*6.283,
   delay:k*260+Math.random()*420})}});
let t0=null,mx=-999,my=-999,settled=false;
sv.addEventListener('pointermove',e=>{const b=sv.getBoundingClientRect(),vb=sv.viewBox.baseVal;
 mx=vb.x+(e.clientX-b.left)/b.width*vb.width;my=vb.y+(e.clientY-b.top)/b.height*vb.height});
sv.addEventListener('pointerleave',()=>{mx=my=-999});
const start=document.documentElement.classList.contains('intro')?4300:250;
function step(ts){if(t0===null)t0=ts;const el=ts-t0-start;let moving=0;
 for(const p of P){const live=el>p.delay;let fx=0,fy=0;
  if(live){fx=(p.hx-p.x)*.045;fy=(p.hy-p.y)*.045}
  else{fx=Math.cos(ts/900+p.ph)*.02;fy=Math.sin(ts/1100+p.ph)*.02}
  const dx=p.x-mx,dy=p.y-my,d2=dx*dx+dy*dy;if(d2<140){const f=(140-d2)/140*.9;fx+=dx*f*.12;fy+=dy*f*.12}
  p.vx=(p.vx+fx)*.82;p.vy=(p.vy+fy)*.82;p.x+=p.vx;p.y+=p.vy;
  const br=live?Math.sin(ts/1400+p.ph)*.12:0;
  p.c.setAttribute('cx',p.x.toFixed(2));p.c.setAttribute('cy',(p.y+br).toFixed(2));
  if(Math.abs(p.vx)+Math.abs(p.vy)>.02||!live)moving++}
 if(!settled&&el>1800&&moving===0){settled=true;sv.classList.add('done')}
 requestAnimationFrame(step)}
requestAnimationFrame(step)})();
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
{ATOM_SVG}</section>
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
    # 页内「原子库」一节只是概览，与独立的原子库页重名：子目录里只留一个「原子库」，直达独立页。
    sub = "".join(f'<a href="{h}">{n}</a>' for h, n in anchors if h not in ("#yuan", "#atoms"))
    sub += ('<span class="sep" aria-hidden="true"></span>'
            '<a href="../atoms/">原子库</a><a href="../articles/">范文</a><a href="../compare/">同题四体</a>')
    new = (f'<nav><div class="wrap"><a class="brand" href="../">{ba.LOGO.format(w=26)}采风</a>'
           f'{ba.site_nav("../")}</div></nav><div class="subnav"><div class="wrap">{sub}</div></div>')
    t = re.sub(r"<nav>.*?</nav>", new, t, count=1, flags=re.S)
    css = ("nav .snav{display:flex;gap:26px;font-size:13.5px;letter-spacing:.16em}"
           "nav .snav a{border:0;color:var(--ink2);padding:17px 0 16px;border-bottom:1px solid transparent}"
           "nav .snav a:hover{color:var(--zhu)}nav .snav a.on{color:var(--ink);border-bottom-color:var(--ink)}"
           ".subnav{border-bottom:1px solid var(--rule)}.subnav .wrap{display:flex;gap:24px;flex-wrap:wrap;"
           "font-size:13px;color:var(--ink2);letter-spacing:.1em;padding-top:10px;padding-bottom:10px}"
           ".subnav a{border:0}.subnav a:hover{color:var(--zhu)}"
           ".subnav .sep{width:1px;align-self:stretch;background:var(--rule)}")
    if ".subnav{" not in t:
        t = t.replace("</style>", css + "\n</style>", 1)
    t = t.replace("<h1>采其风，得其法，<br>自成一体。</h1>", "<h1>写作引擎</h1>")
    return t


# 进入动效以 site_intro 为准（覆盖上面的旧版开场）
from site_intro import INTRO_CSS, INTRO_HTML  # noqa: E402,F811


# ---- English home (docs/en/index.html) ----
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
<p><a href="engines/">Browse all engines →</a> &nbsp; <a href="../articles/">Sample pieces (Chinese) →</a></p></div></section>
<section class="enb"><h2>Atom library</h2><div>
<p>Lay the engines side by side and many moves turn out to be the same move. The cross-engine library holds {c['atoms']} atoms in {c['fams']} shared families plus {c['uniq']} unique ones. Different authors are different combinations of the same atoms.</p>
<p><a href="atoms/">Atom library →</a></p></div></section>
<section class="enb"><h2>Teaching layer</h2><div>
<p>Three tracks: recognize single atoms, see how authors combine them, then diagnose your own drafts. {c['lectures']} lectures so far, each one technique: see it in the original, take it apart, write it yourself.</p>
<p><a href="../lecture/">Lectures (Chinese) →</a> &nbsp; <a href="../eval/">Evaluation (Chinese) →</a></p></div></section>
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


def build_en(c):
    ba.SECTION = ""
    t = page("Collect the style. Learn the method. Find your own.",
             f"<style>{CSS}{ATOM_CSS}{EN_CSS}</style>" + home_en(c) + f"<script>{ATOM_JS}</script>", "../")
    (DOCS / "en").mkdir(exist_ok=True)
    (DOCS / "en/index.html").write_text(en_shell(t, "../", "", "../"), encoding="utf-8")
    build_en_engines(c)
    build_en_atoms()


# ---- English sub-pages (docs/en/engines/, docs/en/atoms/) ----
EN_GLOSSARY = ROOT / "atoms/en.json"  # 族名、原子名、一句话定义、引擎短名的英文译名表


def en_shell(t, rel, enrel, zh_href, on=""):
    """把 page() 的中文外壳改成英文：lang、标题、导航（引擎/原子库指英文页，讲义/评测指中文并标注）、中文切换。"""
    t = t.replace('<html lang="zh-CN">', '<html lang="en">', 1)
    t = t.replace(' · 采风</title>', ' · Caifeng</title>', 1)
    t = t.replace(f'<a class="brand" href="{rel}">', f'<a class="brand" href="{enrel or "./"}">', 1)
    t = re.sub(r'<a class="[^"]*" href="[^"]*engines/">引擎</a>',
               f'<a class="{"on" if on == "engines" else ""}" href="{enrel}engines/">Engines</a>'
               f'<a class="{"on" if on == "atoms" else ""}" href="{enrel}atoms/">Atoms</a>', t, count=1)
    t = t.replace(">讲义</a>", ">Lectures (Chinese)</a>").replace(">评测</a>", ">Evaluation (Chinese)</a>")
    t = t.replace(">夜读</button>", ">Night</button>")
    return add_lang(t, zh_href, "中文")


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
    t = page("Writing engines", f"<style>{EN_CSS}{EN_SUB_CSS}</style>" + body, "../../")
    (DOCS / "en/engines").mkdir(parents=True, exist_ok=True)
    (DOCS / "en/engines/index.html").write_text(
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
            href = f"{_aslug(aid)}.html" if aid in data else f"../../atoms/{_aslug(aid)}.html"
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
        t = page(f"{name} · Atoms", content + f"<style>{bt.CSS}</style>", "../../")
        (DOCS / f"en/atoms/{_aslug(aid)}.html").write_text(
            en_shell(t, "../../", "../", f"../../atoms/{_aslug(aid)}.html", "atoms"), encoding="utf-8")


def build_en_atoms():
    idx = json.loads((ROOT / "atoms/index.json").read_text(encoding="utf-8"))
    g = en_glossary()
    fam_en, eng_en, at = g["families"], g["engines"], g["atoms"]
    data = en_atom_data()
    (DOCS / "en/atoms").mkdir(parents=True, exist_ok=True)
    for old in (DOCS / "en/atoms").glob("*.html"):
        if old.name != "index.html":
            old.unlink()
    build_en_atom_pages(idx, g, data)
    missing = [a["id"] for a in idx if a["id"] not in data]
    print(f"built en atoms: {len(idx) - len(missing)} English page(s); missing translations: {len(missing)}"
          + (f" ({', '.join(missing[:10])}{' …' if len(missing) > 10 else ''})" if missing else ""))

    def href(a):
        return (f'{_aslug(a["id"])}.html' if a["id"] in data else f'../../atoms/{_aslug(a["id"])}.html')

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
    t = page("Atom library", f"<style>{EN_CSS}{EN_SUB_CSS}</style>" + body, "../../")
    (DOCS / "en/atoms").mkdir(parents=True, exist_ok=True)
    (DOCS / "en/atoms/index.html").write_text(
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

def main():
    c = counts()
    ba.SECTION = ""
    (DOCS / "index.html").write_text(add_lang(
        page("采其风，得其法，自成一体", f"<style>{CSS}{INTRO_CSS}{ATOM_CSS}</style>" + INTRO_HTML + home(c) + f"<script>{ATOM_JS}</script>", ""),
        "en/", "EN"), encoding="utf-8")
    build_en(c)
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
        e.write_text(add_lang_nav(unify_nav(e.read_text(encoding="utf-8")), "../en/engines/", "EN"), encoding="utf-8")
    print("built site:", c)


if __name__ == "__main__":
    main()
