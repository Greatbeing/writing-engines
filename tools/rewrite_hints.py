#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行级改写建议：把「你这篇 72 分」变成「第 3 句，这五个字删掉」。

用法：
    python tools/rewrite_hints.py 稿子.md
    python tools/rewrite_hints.py 稿子.md --engine luxun-writing
    python tools/rewrite_hints.py 稿子.md --md 报告.md     # 写成 markdown
    python tools/rewrite_hints.py --selftest

为什么要有这一步
----------------
ai-flavor-checker 会告诉你「AI 味 72 分，硬档命中 3 处」。对一个想学写作的人，
这句话没有用——他不知道是哪三处，也不知道改成什么。

这个脚本做两件事：
1. **定位**：每个问题落到具体句子、具体字。
2. **给改法**：每条规则都写明「为什么」和「怎么改」，并给一个只改这一句的示例。

白名单原则：只处理清单里列出的规则。没命中的句子一个字都不动，
不重排段落，不改结构。改写建议是**建议**，不自动写回原文件。

与 ai-flavor-checker 的关系：共用同一套词表与分句逻辑（直接 import），
所以两边的判定不会打架。分数看 checker，改法看这里。
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

_spec = importlib.util.spec_from_file_location("aifc", HERE / "ai-flavor-checker.py")
aifc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aifc)

# ---------------------------------------------------------------- 规则表
# 每条规则：{id, 检测函数, 为什么, 怎么改, 示例}
# 示例一律是「只改这一句」的最小改动，不是重写。

HARD_REPLACE = {
    "赋能": "帮上忙／起到作用", "抓手": "办法／切入点", "闭环": "完整走完一遍",
    "底层逻辑": "最根本的原因", "颗粒度": "细到什么程度", "对齐": "对上／统一",
    "范式": "做法／套路", "彰显": "显出", "重塑": "改造", "颠覆": "推翻",
    "由此可见": "（直接删掉，接下一句）", "值得注意的是": "（直接删掉）",
    "不难发现": "（直接删掉）", "毋庸置疑": "（直接删掉）",
    "众所周知": "（直接删掉）", "综上所述": "（直接删掉）",
    "总而言之": "（直接删掉）", "归根结底": "说到底",
    "换而言之": "（直接删掉）", "换言之": "（直接删掉）",
    "从某种意义上说": "（直接删掉）", "在一定程度上": "（直接删掉）",
    "不可否认": "（直接删掉）", "拉开帷幕": "开始", "新的篇章": "新的一段",
}


def find_sentences(text):
    """保留偏移量的分句，供定位用。"""
    out, start = [], 0
    for m in re.finditer(r"[^。！？!?\n]+[。！？!?]?", text):
        s = m.group(0)
        if s.strip():
            out.append((s, m.start(), m.end()))
    return out


def hits_in(sentence, words):
    return [w for w in words if w in sentence]


def hint_hard(sent):
    ws = hits_in(sent, aifc.HARD_OFFICIAL)
    if not ws:
        return None
    reps = [f"「{w}」→ {HARD_REPLACE.get(w, '换成一个具体的动作或事实')}" for w in ws]
    return {
        "rule": "硬档黑话",
        "why": "这类词不是错字，是「看起来像结论，其实什么都没说」。出现即扣。",
        "how": "要么换成具体动作，要么整句删掉——多数情况下删掉后句子更清楚。",
        "detail": reps,
    }


def hint_soft(sent):
    ws = hits_in(sent, aifc.SOFT_OFFICIAL)
    # 「这一」后接量词时是指示代词，不是连接词，不提示（与 checker 同一规则）
    if "这一" in ws and aifc.RE_YIZHE_DEMON.search(sent):
        rest = [w for w in ws if w != "这一"]
        ws = rest
    if not ws:
        return None
    return {
        "rule": "连接词偏多",
        "why": "「因此／然而／此外」本身合法，密度高说明句子之间靠连接词撑着，不是靠内容衔接。",
        "how": "删掉连接词，让两句话直接并排；读者读得懂逻辑，就不需要路标。",
        "detail": [f"「{w}」→ 试着删掉，看句意是否还成立" for w in ws],
    }


def hint_abstract(sent):
    ws = hits_in(sent, aifc.ABSTRACT)
    if len(ws) < 1:
        return None
    return {
        "rule": "抽象名词",
        "why": "「价值／意义／本质／格局」单用无罪，但一句话里出现两个以上，通常是在用大词代替具体的事。",
        "how": "问自己：这个词具体指什么？把答案写出来替换它。",
        "detail": [f"「{w}」→ 具体是什么？" for w in ws],
    }


def hint_formula(sent):
    m = aifc.RE_FORMULA.search(sent)
    if not m:
        return None
    return {
        "rule": "「不是A而是B」公式",
        "why": "这个句式用一次是有力的，反复用变成腔调。多数情况下它想说的是：A 不对，B 才对。",
        "how": "拆成两句：先说 A 的问题（给一个事实），再说 B（给一个事实）。",
        "detail": [f"命中：{m.group(0)}…"],
    }


def hint_long(sent):
    core = aifc.strip_punct(sent)
    if len(core) <= 60:
        return None
    # 找最靠中间的逗号/分号断句
    cands = [i for i, ch in enumerate(sent) if ch in "，；、"]
    if not cands:
        return None
    mid = min(cands, key=lambda i: abs(i - len(sent) // 2))
    return {
        "rule": "长句（≥60 字）",
        "why": f"这一句 {len(core)} 字。长句不是错，但中文一口气读不完时，读者会断错地方。",
        "how": "在下面标的位置断成两句；断完读一遍，如果第二句缺主语就补上。",
        "detail": [f"建议断在：「{sent[max(0,mid-8):mid]}」/「{sent[mid+1:mid+9]}」"],
    }


def hint_parallel(sents, idx):
    """连续三句同构：只在第三句上给一次提示。"""
    if idx < 2:
        return None
    run = aifc.max_parallel_run([s for s, _, _ in sents[: idx + 1]])
    if run >= 3 and aifc.max_parallel_run([s for s, _, _ in sents[:idx]]) < run:
        return {
            "rule": "排比同构（连续 ≥3 句）",
            "why": "三句结构相同，读起来有气势，但也容易被当成模板。",
            "how": "留两句最强的，第三句换结构：改成一个短句、一个反问、或一个具体细节。",
            "detail": [f"从「{sents[idx-2][0][:12]}…」起共 {run} 句同构"],
        }
    return None


RULES = [hint_hard, hint_soft, hint_abstract, hint_formula, hint_long]


def analyse(text, engine=None):
    cfg = aifc.load_profiles()
    prof = cfg["profiles"].get(engine or cfg.get("default_profile", "generic"),
                               cfg["profiles"]["generic"])
    res = aifc.score_text(text, prof)
    sents = find_sentences(aifc.clean(text))
    findings = []
    for i, (s, a, b) in enumerate(sents):
        items = []
        for rule in RULES:
            h = rule(s)
            if h:
                items.append(h)
        h = hint_parallel(sents, i)
        if h:
            items.append(h)
        if items:
            findings.append({"index": i + 1, "sentence": s.strip(), "items": items})
    return res, prof, sents, findings


def render_text(path, res, prof, sents, findings):
    out = [f"== 行级改写建议：{path}", "",
           f"   checker：{res['total']}/100（{prof['label']}，门槛 < {prof['pass_below']}）"
           f"  规模：{res['measured']['chars']} 字 / {len(sents)} 句",
           f"  命中问题句：{len(findings)} 句（占 {len(findings)/max(1,len(sents)):.0%}）", "",
           "  说明：只处理清单内的规则；没列出的句子一个字都不动。建议要人过一遍再改。", ""]
    if not findings:
        out.append("  没有命中任何规则。这篇在「AI 腔」这一维度上没问题。")
        return "\n".join(out)
    for f in findings:
        out.append(f"  ── 第 {f['index']} 句 ──")
        out.append(f"     {f['sentence'][:70]}{'…' if len(f['sentence']) > 70 else ''}")
        for it in f["items"]:
            out.append(f"     [{it['rule']}] {it['why']}")
            out.append(f"       怎么改：{it['how']}")
            for d in it["detail"]:
                out.append(f"       · {d}")
        out.append("")
    return "\n".join(out)


def render_md(path, res, prof, sents, findings):
    L = [f"# 行级改写建议：{Path(path).name}", "",
         f"- checker：**{res['total']}**/100（{prof['label']}，门槛 < {prof['pass_below']}）",
         f"- 规模：{res['measured']['chars']} 字 / {len(sents)} 句",
         f"- 命中问题句：**{len(findings)}** 句（占 {len(findings)/max(1,len(sents)):.0%}）", "",
         "> 只处理清单内的规则；没列出的句子一个字都不动。建议要人过一遍再改。", "",
         "| 句号 | 原文 | 问题 | 怎么改 |", "|---|---|---|---|"]
    for f in findings:
        rules = "、".join(it["rule"] for it in f["items"])
        hows = "；".join(it["how"] for it in f["items"])
        src = f["sentence"].replace("|", "\\|")
        src = src if len(src) <= 40 else src[:40] + "…"
        L.append(f"| {f['index']} | {src} | {rules} | {hows} |")
    L.append("")
    for f in findings:
        L.append(f"### 第 {f['index']} 句")
        L.append("")
        L.append(f"> {f['sentence']}")
        L.append("")
        for it in f["items"]:
            L.append(f"**{it['rule']}** — {it['why']}")
            L.append("")
            L.append(f"怎么改：{it['how']}")
            L.append("")
            for d in it["detail"]:
                L.append(f"- {d}")
            L.append("")
    return "\n".join(L) + "\n"


def selftest():
    good = ("楼下修鞋的老周，最近把摊子挪到了地铁口。他说这边人多，一天能多修七八双。"
            "我问他冷不冷，他指指脚边一个暖水瓶。摊子上压着块木板，用红漆写着修鞋修伞改衣。")
    bad = ("在当今这个快速变化的时代，我们不难发现，赋能已经成为衡量价值的重要维度。"
           "因此，我们需要重新审视个体与系统之间的关系，从而在更高层面上实现对齐。")
    _, _, _, fg = analyse(good)
    _, _, _, fb = analyse(bad)
    ok = len(fg) == 0 and len(fb) >= 1
    print(f"自检：干净样本命中 {len(fg)} 句（应 0）／AI 腔样本命中 {len(fb)} 句（应 ≥1）")
    print("结果：通过" if ok else "结果：失败——规则表被改坏了")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="行级改写建议")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--engine", default=None)
    ap.add_argument("--md", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.files:
        print(__doc__)
        return 2
    out = []
    for p in a.files:
        path = Path(p)
        if not path.exists():
            sys.exit(f"[error] 找不到文件：{p}")
        text = path.read_text(encoding="utf-8", errors="replace")
        res, prof, sents, findings = analyse(text, a.engine)
        if res is None:
            print(f"  {p}：无正文，跳过")
            continue
        out.append(render_text(p, res, prof, sents, findings))
        if a.md:
            Path(a.md).write_text(render_md(p, res, prof, sents, findings), encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
