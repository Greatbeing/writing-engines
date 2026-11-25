#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 味检测器 v0.2 —— 按引擎打分的文体感知评测器
================================================

v0.1 的问题是它在测「书面语密度」，却把结果叫「AI 味」。
结果它惩罚了三家引擎自己要求的装置：
  · 活人感要求「大量「」访谈式引用」→ v0.1 按引号密度扣分
  · 活人感 / 官方体要求「不是A而是B」金句结构 → v0.1 按「破公式」扣分
v0.2 把这两项改成**可配权重**：同一种装置，在需要它的文体里是加分项，
在克制的文体里才是扣分项。这就是 PRODUCT.md 说的「文体感知」，不用 LLM 也能做。

口径统一
--------
v0.1 的书面腔走「每千字密度」、长句走「绝对条数」——一篇 5000 字的稿子和
一篇 500 字的稿子，同样 6 个长句扣同样 15 分，总分没法横向比。
v0.2 全部改成比率或密度：
  · 词表类 → 每千字命中数（hits / 1000 chars）
  · 长句   → 长句占句数比（ratio）
  · 排比   → 最长同构连续句长度（run，已是长度无关量）
短文本另加阻尼：不足 400 字按 400 字归一，否则 130 字里出现一个「因此」，
密度会被放大成 7.7/千字，虚高得没法用。

用法
----
    python3 tools/ai-flavor-checker.py 文章.md
    python3 tools/ai-flavor-checker.py --engine human-voice-writing 文章.md
    python3 tools/ai-flavor-checker.py --engine feature-writing a.md b.md
    python3 tools/ai-flavor-checker.py --stdin < 文章.txt
    python3 tools/ai-flavor-checker.py --list-engines
    python3 tools/ai-flavor-checker.py --json --engine guanfang-writing 文章.md

退出码：0 = 全部通过该引擎门槛；1 = 有文本未过；2 = 参数/环境错误。
（v0.1 恒为 0，没法当门禁用。）

注意
----
本文件在无 Python 环境的沙箱内写成，未经实际执行。合并前请先跑一次：
    python3 tools/ai-flavor-checker.py --selftest
它与 tools/tests/test_checker.py 覆盖同一批断言。
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- 词表
# 三档，权重不同。v0.1 把所有词塞进两个平表，是「因此」和「赋能」同罪的原因。

# 硬档：真正的 AI 腔 / 公文黑话，出现即扣，零容忍
HARD_OFFICIAL = [
    "赋能", "抓手", "闭环", "底层逻辑", "颗粒度", "对齐", "范式", "彰显",
    "重塑", "颠覆", "由此可见", "值得注意的是", "不难发现", "毋庸置疑",
    "众所周知", "综上所述", "总而言之", "归根结底", "换而言之", "换言之",
    "从某种意义上说", "在一定程度上", "不可否认", "拉开帷幕", "新的篇章",
]

# 软档：正常中文连接词。存在是合法的，密度过高才是问题。
SOFT_OFFICIAL = [
    "因此", "然而", "此外", "从而", "进而", "与此同时", "显而易见",
    "进行", "作出", "这一", "旨在", "以期", "进一步",
]

# 空转档：抽象名词。单用无罪，扎堆说明没写具体的事。
ABSTRACT = [
    "价值", "意义", "未来", "格局", "认知", "智慧", "本质", "真相", "层面",
    "维度", "系统", "力量", "精神", "灵魂", "境界", "高度", "情怀", "初心",
    "远方", "使命", "愿景", "担当", "责任", "人生", "生命",
]

# 口语档：活人感的正向信号（v0.1 里叫「口语抵充」，方向对，词表混了单字噪音）
COLLOQUIAL = [
    "说白了", "就是说", "反正", "的事儿", "还挺", "确实", "算了吧", "哥们",
    "呗", "嘛", "咱", "其实", "居然", "压根", "愣是", "硬是", "就这",
]

RE_HARD_PATTERN = re.compile(r"在(?:这个|当今|当下)[^，。！？]{0,12}(?:时代|社会|背景)")
RE_FORMULA = re.compile(r"(?:不是|并非|而非)[^。！？\n]{1,30}?而是")
RE_DIGITS = re.compile(r"\d+(?:\.\d+)?")
# 「这一」多数时候是指示代词（这一类、这一次、这一代人），不是连接词。
# v0.2 把它整词计入软档，凡「这一」必扣分——实测在正常中文里假阳性极多
# （19 篇稿子里大批命中 3 分左右，全是「这一类」「这一条」）。这里按后接量词排除。
RE_YIZHE_DEMON = re.compile(r"这一[类种点块次条年天切步代部些边头回场层]")
RE_SENT_SPLIT = re.compile(r"(?<=[。！？!?])")


# ---------------------------------------------------------------- 基础度量
def load_profiles():
    path = HERE / "engine_profiles.json"
    if not path.exists():
        sys.exit(f"[error] 缺少配置：{path}\n请与 ai-flavor-checker.py 放在同一目录。")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"[error] {path} 不是合法 JSON：{exc}")


def clean(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)      # 代码块
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)       # 图片
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # 链接留文字
    text = re.sub(r"^[#>\-\*\s]+", "", text, flags=re.M)   # 行首标记
    return text


def split_sentences(text):
    out = []
    for raw in RE_SENT_SPLIT.split(text):
        s = raw.strip()
        if strip_punct(s):
            out.append(s)
    return out


def strip_punct(s):
    return s.rstrip("。！？!?…；;」』”’\"' ").strip()


def density(hits, chars):
    """每千字命中数。不足 400 字按 400 字归一，避免短文本虚高。"""
    norm = max(chars, 400)
    return hits * 1000.0 / norm


def count_list(text, words):
    found = {}
    for w in words:
        n = text.count(w)
        if n:
            found[w] = n
    return found


def _common_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _common_suffix(a, b):
    n = 0
    for x, y in zip(reversed(a), reversed(b)):
        if x != y:
            break
        n += 1
    return n


def max_parallel_run(sentences):
    """最长「同构连续句」长度：连续 ≥3 句，共享 ≥2 字的首部或尾部，且长度接近。

    v0.1 只看结尾**一个**字，于是任何三句都以「了」结尾就误报。
    v0.2 前身改成「首字相同 + 尾字相同」，又漏掉了最常见的排比形态
    ——「春天来了。夏天来了。秋天来了。」首字全不同、只有「来了」重复。
    现在改为：共享 ≥2 字的前缀或后缀（这是中文排比最稳的表面证据），
    再叠长度约束（句式镜像的句子长度通常接近）。

    已知局限（刻意的）：只靠表面重复的句法排比会漏检，例如
    「他来了。她笑了。天亮了。」——结构上是排比，表面只有单字相同。
    宁可漏检不误报：这一维只占 10 分，误报会让好文章白扣分，
    漏检只是少扣一点。这与词表「保守收录」的哲学一致。
    """
    best, run = 1, 1
    prev = strip_punct(sentences[0]) if sentences else ""
    for cur_raw in sentences[1:]:
        cur = strip_punct(cur_raw)
        if not prev or not cur:
            run, prev = 1, cur
            continue
        close_len = abs(len(prev) - len(cur)) <= max(2, 0.25 * max(len(prev), len(cur)))
        shared = _common_prefix(prev, cur) >= 2 or _common_suffix(prev, cur) >= 2
        if shared and close_len:
            run += 1
            best = max(best, run)
        else:
            run = 1
        prev = cur
    return best


# ---------------------------------------------------------------- 打分
def measure(text):
    """把文本压成 9 个 0 起底的原始量，打分交给 profile。"""
    body = clean(text)
    flat = re.sub(r"\s+", "", body)
    chars = len(flat)
    sents = split_sentences(body)
    n_sent = len(sents) or 1

    hard = count_list(flat, HARD_OFFICIAL)
    hard_n = sum(hard.values()) + len(RE_HARD_PATTERN.findall(flat))
    _soft = count_list(flat, SOFT_OFFICIAL)
    if "这一" in _soft:
        _soft["这一"] = max(0, _soft["这一"] - len(RE_YIZHE_DEMON.findall(flat)))
    soft_n = sum(_soft.values())
    abs_n = sum(count_list(flat, ABSTRACT).values())
    col_n = sum(count_list(flat, COLLOQUIAL).values())
    digit_n = len(RE_DIGITS.findall(flat))
    quote_n = flat.count("「") + flat.count("“")
    formula_n = len(RE_FORMULA.findall(flat))
    long_n = sum(1 for s in sents if len(strip_punct(s)) > 60)
    par_run = max_parallel_run(sents)

    return {
        "chars": chars,
        "sentences": n_sent,
        "hard_n": hard_n,
        "soft_n": soft_n,
        "abs_n": abs_n,
        "col_n": col_n,
        "digit_n": digit_n,
        "quote_n": quote_n,
        "formula_n": formula_n,
        "long_ratio": (long_n / n_sent) if n_sent else 0.0,
        "parallel_run": par_run,
        "hits": {"hard": hard, "soft": _soft,
                 "abs": count_list(flat, ABSTRACT), "col": count_list(flat, COLLOQUIAL)},
    }


# 每个分项的原始量 → 0..cap 的分数。cap 之和 = 100。
CAPS = {"hard": 25, "soft": 20, "abstract": 15, "long": 15, "parallel": 10, "formula": 10}
REWARD_CAPS = {"colloquial": 15, "concrete": 10, "dialogue": 10}


def raw_scores(m, chars):
    d = lambda n: density(n, chars)  # noqa: E731
    par = m["parallel_run"]
    par_score = 0.0
    if par >= 3:
        par_score = min(CAPS["parallel"], 6 + (par - 3) * 2)
    return {
        "hard": min(CAPS["hard"], d(m["hard_n"]) * 8),
        "soft": min(CAPS["soft"], d(m["soft_n"]) * 3),
        "abstract": min(CAPS["abstract"], d(m["abs_n"]) * 2.5),
        "long": min(CAPS["long"], m["long_ratio"] * 50),
        "parallel": par_score,
        "formula": min(CAPS["formula"], d(m["formula_n"]) * 3),
        "colloquial": min(REWARD_CAPS["colloquial"], d(m["col_n"]) * 2),
        "concrete": min(REWARD_CAPS["concrete"], d(m["digit_n"]) * 1.5),
        "dialogue": min(REWARD_CAPS["dialogue"], d(m["quote_n"]) * 1.2),
    }


def score_text(text, profile):
    m = measure(text)
    chars = m["chars"]
    if chars == 0:
        return None
    raw = raw_scores(m, chars)
    pen = sum(raw[k] * profile["penalty"].get(k, 1.0) for k in CAPS)
    rew = sum(raw[k] * profile["reward"].get(k, 1.0) for k in REWARD_CAPS)
    total = max(0.0, min(100.0, pen - rew))
    return {
        "total": round(total, 1),
        "raw": {k: round(v, 1) for k, v in raw.items()},
        "measured": m,
        "passed": total < profile["pass_below"],
    }


def grade(total, profile):
    if total < profile["pass_below"]:
        return f"通过（{profile['label']}）"
    if total < profile["pass_below"] + 15:
        return "轻度 AI 味"
    if total < profile["pass_below"] + 35:
        return "明显 AI 味"
    return "AI 味爆表"


def top_hits(d, k=5):
    if not d:
        return "-"
    return " ".join(f"{w}×{n}" for w, n in sorted(d.items(), key=lambda x: -x[1])[:k])


def report(name, res, profile):
    m, raw = res["measured"], res["raw"]
    print(f"== {name}")
    print(f"   {res['total']}/100 → {grade(res['total'], profile)}"
          f"（门槛 < {profile['pass_below']}）")
    print(f"   规模：{m['chars']} 字 / {m['sentences']} 句")
    print(f"   [硬档黑话 ] {raw['hard']:>4}/{CAPS['hard']:<2} 命中 {m['hard_n']:>2}：{top_hits(m['hits']['hard'])}")
    print(f"   [软档连接词] {raw['soft']:>4}/{CAPS['soft']:<2} 命中 {m['soft_n']:>2}：{top_hits(m['hits']['soft'])}")
    print(f"   [空转抽象 ] {raw['abstract']:>4}/{CAPS['abstract']:<2} 命中 {m['abs_n']:>2}：{top_hits(m['hits']['abs'])}")
    print(f"   [长句占比 ] {raw['long']:>4}/{CAPS['long']:<2} 长句占比 {m['long_ratio']:.0%}")
    print(f"   [排比同构 ] {raw['parallel']:>4}/{CAPS['parallel']:<2} 最长同构 {m['parallel_run']} 句")
    print(f"   [A而是B公式] {raw['formula']:>4}/{CAPS['formula']:<2} {m['formula_n']} 次")
    print(f"   抵充：口语 {raw['colloquial']:.1f}  具体数字 {raw['concrete']:.1f}  对话引号 {raw['dialogue']:.1f}")
    print()


def read_inputs(args):
    if args.stdin:
        return [("<stdin>", sys.stdin.read())]
    out = []
    for p in args.files:
        path = Path(p)
        if not path.exists():
            sys.exit(f"[error] 找不到文件：{p}")
        out.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
    return out


def selftest():
    """零依赖自检：不依赖 tools/tests，用来快速判断安装是否正常。"""
    good = (
        "楼下修鞋的老周，最近把摊子挪到了地铁口。他说这边人多，一天能多修七八双。"
        "我问他冷不冷，他指指脚边一个暖水瓶，说这玩意儿比棉裤管用。摊子上压着块木板，"
        "用红漆写着修鞋修伞改衣，字已经掉了一半。有人拿来一只断跟的单鞋，他翻过来看看，"
        "说粘一下还能穿，别扔。"
    )
    bad = (
        "在当今这个快速变化的时代，我们不难发现，效率已经成为衡量一切价值的重要维度。"
        "值得注意的是，这种转变并非偶然，而是深刻反映了社会结构的底层逻辑。因此，"
        "我们需要重新审视个体与系统之间的关系，从而在更高层面上实现对齐与赋能。"
    )
    prof = load_profiles()["profiles"]["generic"]
    g, b = score_text(good, prof)["total"], score_text(bad, prof)["total"]
    print(f"自检：人类样本 {g}（应 < 30） / AI 腔样本 {b}（应 ≥ 45）")
    ok = g < 30 and b >= 45
    print("结果：通过" if ok else "结果：失败——词表或权重被改坏了")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI 味检测器 v0.2（按引擎打分）")
    ap.add_argument("files", nargs="*", help="待检文本路径")
    ap.add_argument("--engine", default=None,
                    help="引擎名，见 --list-engines；缺省用配置里的 default_profile")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--list-engines", action="store_true", help="列出可用引擎配置")
    ap.add_argument("--selftest", action="store_true", help="跑内置自检")
    args = ap.parse_args(argv)

    cfg = load_profiles()

    if args.list_engines:
        for key, p in cfg["profiles"].items():
            print(f"{key:<22} 门槛 < {p['pass_below']:<3} {p['label']}")
        return 0

    if args.selftest:
        return selftest()

    engine = args.engine or cfg.get("default_profile", "generic")
    if engine not in cfg["profiles"]:
        sys.exit(f"[error] 未知引擎：{engine}\n可用：{', '.join(cfg['profiles'])}")
    profile = cfg["profiles"][engine]

    if not args.files and not args.stdin:
        ap.print_help()
        return 2

    results = []
    for name, text in read_inputs(args):
        res = score_text(text, profile)
        if res is None:
            print(f"== {name}\n   空输入，跳过\n")
            continue
        res["name"] = name
        results.append(res)
        if not args.json:
            report(name, res, profile)

    if args.json:
        print(json.dumps({"engine": engine, "profile": profile["label"],
                          "results": [{k: v for k, v in r.items() if k != "measured"}
                                      for r in results]},
                         ensure_ascii=False, indent=2))
    elif results:
        avg = sum(r["total"] for r in results) / len(results)
        npass = sum(1 for r in results if r["passed"])
        print(f"合计 {len(results)} 篇，均值 {avg:.1f}，通过 {npass}/{len(results)}"
              f"（{engine} 门槛 < {profile['pass_below']}）")

    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
