#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把云端 agent 的每日写作过程生成为 docs/daily/（「批改台」）。

每天一页，按写作的真实顺序展示：
  一、撰稿   每一稿的机检分和打回原因（落选稿可展开）
  二、终稿   全文；收录的惊艳句用朱红底线标出
  三、评改   评审 agent 的逐条核对和「最该改的一句」
  四、这一课 从当天评改里提炼的一条可复用经验

另有 docs/daily/gems.html：句库（惊艳句）+ 经验库。

数据来源（都由 tools/daily/ 的写作端、评审端产出）：
  drafts/daily/state.json            runs / reviews / gems / lessons
  drafts/daily/process/<date>.json   每一稿的原文与打回原因（write.py 记录）
  drafts/daily/reviews/<date>.md     评审全文（review.py 记录）

用法：python tools/build_daily.py
"""
import html
import json
import re
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import page, ROOT  # noqa: E402

DAILY = ROOT / "drafts" / "daily"
OUT = ROOT / "docs" / "daily"

ENGINE_CN = {
    "sanlian-writing": "三联体", "sushi-writing": "苏轼白话体", "luxun-writing": "鲁迅体",
    "wangxiaobo-writing": "王小波体", "zhangailing-writing": "张爱玲体", "lijuan-writing": "李娟体",
    "yuhua-writing": "余华体", "standup-writing": "脱口秀体", "rmrb-writing": "人民日报体",
    "wangzengqi-writing": "汪曾祺体", "jinyong-writing": "金庸体", "mao-writing": "毛泽东体",
    "human-voice-writing": "活人感体", "guanfang-writing": "官方体", "feature-writing": "特稿体",
    "gongwen-writing": "公文体", "zhexuan-writing": "哲选体",
}

CSS = """
.dl{max-width:760px;margin:0 auto;padding:56px 28px 40px}
.dl h1{font:900 clamp(26px,4vw,36px)/1.35 var(--serif);letter-spacing:.04em;margin:6px 0 4px}
.dl .sub{font:12px var(--mono);color:var(--ink2);letter-spacing:.18em}
.dl .meta{font-size:13.5px;color:var(--ink2);margin:10px 0 0}
.dl hr.rule{border:0;border-top:1px solid var(--zhu);width:64px;margin:18px 0 30px}
.dl h2{font:600 20px/1.6 var(--serif);letter-spacing:.06em;margin:48px 0 14px;padding-left:14px;position:relative}
.dl h2::before{content:"";position:absolute;left:0;top:.55em;width:5px;height:5px;background:var(--zhu)}
.dl .step{border-left:1px solid var(--rule);padding:2px 0 10px 18px;margin:0 0 14px;position:relative}
.dl .step::before{content:"";position:absolute;left:-4px;top:9px;width:7px;height:7px;border-radius:50%;background:var(--ink2)}
.dl .step.win::before{background:var(--zhu)}
.dl .step b{font-weight:600}
.dl .step .why{color:var(--ink2);font-size:14.5px;margin-top:4px}
.dl details{margin-top:6px;font-size:14.5px}
.dl details summary{cursor:pointer;color:var(--ink2)}
.dl details .draft{white-space:pre-wrap;font:400 15px/1.85 var(--serif);color:var(--ink2);
  border-left:2px solid var(--rule);padding:6px 0 6px 14px;margin-top:8px;max-height:420px;overflow:auto}
.art{font:400 17px/2 var(--serif)}
.art p{margin:0 0 16px}
.art h1,.art h2{display:none}
mark.gem{background:none;border-bottom:2px solid var(--zhu);padding-bottom:1px;color:inherit}
.gemnote{font-size:14px;color:var(--ink2);margin:-4px 0 14px}
.rev{font-size:15.5px;line-height:1.85}
.rev h2{font:600 16px/1.6 var(--serif);margin:26px 0 8px;padding:0}
.rev h2::before{display:none}
.rev table{font-size:14px;width:100%}
.rev blockquote{border-left:2px solid var(--ink);margin:12px 0;padding:0 0 0 14px;color:var(--ink2)}
.lesson{border-left:2px solid var(--zhu);background:#EFE9DC;padding:14px 20px;font:400 16.5px/1.9 var(--serif)}
.stars{font:12px var(--mono);letter-spacing:.1em}
.v-pass{color:#3c6e47}.v-borderline{color:#8a6d1f}.v-needs_fix{color:var(--zhu)}
.dlist{max-width:820px;margin:0 auto;padding:64px 32px 40px}
.dlist h1{font:900 34px/1.4 var(--serif);letter-spacing:.1em}
.dlist .lead{color:var(--ink2);margin:14px 0 30px;font:400 17px/1.9 var(--serif)}
.ditem{display:block;border:0;border-top:1px solid var(--ink);padding:22px 0}
.ditem:last-of-type{border-bottom:1px solid var(--ink)}
.ditem .no{font:12px var(--mono);letter-spacing:.14em;color:var(--ink2)}
.ditem h2{font:600 19px/1.6 var(--serif);margin:6px 0 4px}
.ditem .one{color:var(--ink2);font-size:14px}
.ditem .g{font:400 15.5px/1.8 var(--serif);margin-top:8px;padding-left:12px;border-left:2px solid var(--zhu)}
.gem-card{border-top:1px solid var(--rule);padding:22px 0}
.gem-card q{display:block;font:400 19px/1.9 var(--serif);quotes:none}
.gem-card .src{font-size:13px;color:var(--ink2);margin-top:8px}
.gem-card .why{font-size:14.5px;color:var(--ink2);margin-top:6px}
.tabs{display:flex;gap:22px;font-size:14px;margin:0 0 26px}
.tabs a{border-bottom:1px solid var(--rule)}.tabs a:hover{border-color:var(--zhu);color:var(--zhu)}
.empty{color:var(--ink2);font-size:14.5px}
.fix{border:1px solid var(--rule);padding:16px 20px;margin:0 0 18px}
.fix .lab{font:12px var(--mono);letter-spacing:.14em;color:var(--ink2);margin-top:6px}
.fix .before{font:400 16.5px/1.9 var(--serif);color:var(--ink2);text-decoration:line-through;text-decoration-color:var(--ink2)}
.fix .after{font:400 16.5px/1.9 var(--serif);border-left:2px solid var(--zhu);padding-left:12px}
@media(max-width:640px){.dl,.dlist{padding-left:20px;padding-right:20px}}
"""

VERDICT = {"pass": "合格", "borderline": "勉强", "needs_fix": "不合格"}


def esc(s):
    return html.escape(str(s or ""))


def load_state():
    p = DAILY / "state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def strip_head(md):
    """去掉文章首行标题与 `>` 元信息行，只留正文。"""
    md = re.sub(r"^#\s+.*$", "", md, count=1, flags=re.M)
    return re.sub(r"^>.*$", "", md, flags=re.M).strip()


def mark_gems(body_html, gems):
    for g in gems:
        t = html.escape(g["text"])
        if t and t in body_html:
            body_html = body_html.replace(t, f'<mark class="gem">{t}</mark>', 1)
    return body_html


def review_body(path):
    if not path.exists():
        return ""
    md = path.read_text(encoding="utf-8")
    md = re.sub(r"^#\s+.*$", "", md, count=1, flags=re.M)
    md = re.sub(r"^- (文章|引擎|机检|评审)：.*$", "", md, flags=re.M)
    md = re.sub(r"^## 评分\s*\n+.*$", "", md, flags=re.M)
    return markdown.markdown(md.strip(), extensions=["tables", "sane_lists"])


def best_fix(path):
    """从评审稿“最该改的一句”取出（原句, 改法）；改法去掉括号里的说明。"""
    if not path.exists():
        return None
    md = path.read_text(encoding="utf-8")
    m = re.search(r"^## 最该改的一句\s*\n(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    if not m:
        return None
    sec = m.group(1)
    a = re.search(r"原句[:：]\s*(.+)", sec)
    b = re.search(r"改法[:：]\s*(.+)", sec)
    if not (a and b):
        return None
    after = re.sub(r"[（(][^（）()]*[)）]\s*$", "", b.group(1).strip()).strip()
    return a.group(1).strip(), after


def day_page(date, run, review, proc, gems, lesson):
    eng = run.get("engine", "")
    title = run.get("title", "")
    parts = [f'<article class="dl"><div class="sub">采风 · 批改台 · {esc(date)}</div>',
             f"<h1>{esc(title)}</h1>",
             f'<div class="meta">{esc(ENGINE_CN.get(eng, eng))}　·　机检 {esc(run.get("score"))}'
             + (f'　·　评审 <span class="v-{esc(review.get("verdict"))}">'
                f'{esc(VERDICT.get(review.get("verdict"), ""))} {esc(review.get("stars"))}/5</span>'
                if review else "") + "</div>",
             '<hr class="rule">']

    # 一、撰稿
    parts.append("<h2>一、撰稿</h2>")
    atts = (proc or {}).get("attempts") or []
    if atts:
        for a in atts:
            win = a.get("passed")
            why = "通过门禁" if win else "打回：" + "；".join(a.get("bad") or [])
            parts.append(f'<div class="step{" win" if win else ""}"><b>第 {a.get("n")} 稿</b>'
                         f'　《{esc(a.get("title"))}》　机检 {esc(a.get("score"))}'
                         f'<div class="why">{esc(why)}</div>')
            if not win and a.get("text"):
                parts.append(f'<details><summary>展开这一稿</summary>'
                             f'<div class="draft">{esc(strip_head(a["text"]))}</div></details>')
            parts.append("</div>")
    else:
        parts.append('<p class="empty">这一天的逐稿记录没有保存（批改台上线前的旧稿）。</p>')

    # 二、终稿
    parts.append("<h2>二、终稿</h2>")
    art = ROOT / run.get("file", "")
    if art.exists():
        body = markdown.markdown(strip_head(art.read_text(encoding="utf-8")))
        if gems:
            parts.append(f'<p class="gemnote">朱红底线是今天收进句库的句子（{len(gems)} 句）。</p>')
        parts.append(f'<div class="art">{mark_gems(body, gems)}</div>')
    else:
        parts.append('<p class="empty">原文已撤下。</p>')

    # 三、评改
    parts.append("<h2>三、评改</h2>")
    fix = best_fix(ROOT / review["file"]) if review and review.get("file") else None
    if fix:
        parts.append('<div class="fix"><div class="lab">改前</div>'
                     f'<div class="before">{esc(fix[0])}</div>'
                     '<div class="lab">改后</div>'
                     f'<div class="after">{esc(fix[1])}</div></div>')
    rb = review_body(ROOT / review["file"]) if review and review.get("file") else ""
    parts.append(f'<div class="rev">{rb}</div>' if rb else '<p class="empty">评审尚未完成。</p>')

    # 四、这一课
    parts.append("<h2>四、这一课</h2>")
    parts.append(f'<div class="lesson">{esc(lesson["text"])}</div>' if lesson
                 else '<p class="empty">今天没有提炼出够格的经验——宁缺毋滥。</p>')
    if gems:
        parts.append("<h2>收进句库</h2>")
        for g in gems:
            parts.append(f'<div class="gem-card"><q>{esc(g["text"])}</q>'
                         f'<div class="why">{esc(g.get("why"))}</div></div>')
    parts.append('</article><div class="pager" style="max-width:760px;margin:0 auto;padding:0 28px 56px">'
                 '<a href="index.html">← 批改台</a> <a href="gems.html">句库与经验 →</a></div>')
    return "".join(parts)


def main():
    st = load_state()
    runs = sorted(st.get("runs", []), key=lambda r: r.get("date", ""), reverse=True)
    reviews = st.get("reviews", [])
    all_gems = st.get("gems", [])
    lessons = st.get("lessons", [])
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()

    items = []
    for run in runs:
        date = run["date"]
        rv = [r for r in reviews if r.get("date") == date and r.get("title") == run.get("title")]
        review = rv[-1] if rv else None
        pp = DAILY / "process" / f"{date}.json"
        proc = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else None
        gems = [g for g in all_gems if g.get("date") == date]
        ls = [x for x in lessons if x.get("date") == date]
        lesson = ls[-1] if ls else None
        (OUT / f"{date}.html").write_text(
            page(run.get("title", date) + " · 批改台", day_page(date, run, review, proc, gems, lesson)
                 + f"<style>{CSS}</style>", "../"), encoding="utf-8")
        n = len((proc or {}).get("attempts") or [])
        one = f"{ENGINE_CN.get(run.get('engine'), run.get('engine'))}"
        if n:
            one += f"　·　{n} 稿定稿"
        if review:
            one += f"　·　评审 {VERDICT.get(review.get('verdict'), '')} {review.get('stars')}/5"
        g = f'<div class="g">{esc(gems[0]["text"])}</div>' if gems else ""
        items.append(f'<a class="ditem" href="{date}.html"><div class="no">{esc(date)}</div>'
                     f'<h2>{esc(run.get("title"))}</h2><div class="one">{esc(one)}</div>{g}</a>')
        print(f"  daily/{date}.html  {run.get('title')}")

    idx = ('<section class="dlist"><h1>采风 · 批改台</h1>'
           '<p class="lead">云端的写作 agent 每天写一篇，评审 agent 每天批一篇。<br>'
           '这里不只放成品：每一稿为什么被打回、评审挑出哪一句、改完学到什么，都摊开给你看。</p>'
           '<div class="tabs"><a href="gems.html">句库与经验</a><a href="../lecture/">讲义</a></div>'
           + ("".join(items) or '<p class="empty">还没有每日稿。</p>') + "</section>")
    (OUT / "index.html").write_text(page("采风 · 批改台", idx + f"<style>{CSS}</style>", "../"), encoding="utf-8")

    gl = "".join(
        f'<div class="gem-card"><q>{esc(g["text"])}</q>'
        f'<div class="why">{esc(g.get("why"))}</div>'
        f'<div class="src"><a href="{esc(g["date"])}.html">《{esc(g.get("title"))}》· {esc(g["date"])}</a></div></div>'
        for g in sorted(all_gems, key=lambda x: x.get("date", ""), reverse=True))
    ll = "".join(
        f'<div class="gem-card"><div style="font:400 16.5px/1.9 var(--serif)">{esc(x["text"])}</div>'
        f'<div class="src"><a href="{esc(x["date"])}.html">{esc(x["date"])} · 《{esc(x.get("title"))}》</a></div></div>'
        for x in sorted(lessons, key=lambda x: x.get("date", ""), reverse=True))
    gp = ('<section class="dlist"><h1>句库与经验</h1>'
          '<p class="lead">句库只收「读到会停下来重读、换一个字就变差」的句子。大多数日子一句也没有。<br>'
          '经验库收评改里能直接拿去用的一条做法，不收道理。</p>'
          '<div class="tabs"><a href="index.html">← 批改台</a><a href="#lessons">经验库</a></div>'
          f'<h2 style="font:600 20px var(--serif);margin:10px 0 6px">句库　<span class="stars">{len(all_gems)}</span></h2>'
          + (gl or '<p class="empty">还没有够格的句子。</p>')
          + f'<h2 id="lessons" style="font:600 20px var(--serif);margin:44px 0 6px">经验库　<span class="stars">{len(lessons)}</span></h2>'
          + (ll or '<p class="empty">还没有。</p>') + "</section>")
    (OUT / "gems.html").write_text(page("句库与经验 · 采风", gp + f"<style>{CSS}</style>", "../"), encoding="utf-8")
    print(f"built daily: {len(items)} day(s), {len(all_gems)} gem(s), {len(lessons)} lesson(s)")


if __name__ == "__main__":
    main()
