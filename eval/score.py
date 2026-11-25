#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval 汇总脚本 —— 把盲排结果算成三个数字。

输入：eval/key.json（唯一事实来源，先有 key 才有评分表）
    {"t01": {"A": "baseline", "B": "human-voice-writing", ...}, ...}
    标签 A-D 在每题内唯一且完整；键名必须覆盖 prompts.json 的全部题号。

输入：eval/rankings.csv
    topic,rater,rank1,rank2,rank3,rank4,note
    rank1 = 写得最好的那一篇的匿名标签

用法：
    python3 eval/score.py --make-key            # 首次：生成随机 key.json（固定种子，可复现）
    python3 eval/score.py --template > eval/rankings.csv
    python3 eval/score.py --selftest            # 验证算术没坏
    python3 eval/score.py --input eval/rankings.csv > eval/RESULTS.md

设计上刻意做对的一件事：**key 是唯一事实来源，不在模板阶段重新抽签。**
第一版这里是个坑——模板每次重跑都会换标签，导致评分者照着上次的标签填表、
脚本按新的 key 解析，结果全错而且看不出来。

说明：本文件在无 Python 沙箱内写成，未经实际执行。首次使用请先跑 --selftest。
"""

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINES = ["baseline", "human-voice-writing", "guanfang-writing", "feature-writing"]
LABELS = ["A", "B", "C", "D"]
SHORT = {"baseline": "baseline", "human-voice-writing": "活人感",
         "guanfang-writing": "官方体", "feature-writing": "特稿"}
BORDA = {0: 4, 1: 3, 2: 2, 3: 1}   # 第 1 名 4 分，第 4 名 1 分


# ---------------------------------------------------------------- 输入
def topic_ids():
    data = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))
    return [t["id"] for t in data["topics"]]


def make_key(path, seed=20261125):
    rng = random.Random(seed)
    key = {}
    for tid in topic_ids():
        labels = LABELS[:]
        rng.shuffle(labels)
        key[tid] = dict(zip(labels, ENGINES))
    path.write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    return key


def load_key(path):
    if not path.exists():
        sys.exit(f"[error] 缺 {path}\n先跑：python3 eval/score.py --make-key")
    key = json.loads(path.read_text(encoding="utf-8"))
    missing = [t for t in topic_ids() if t not in key]
    if missing:
        sys.exit(f"[error] key.json 缺题号：{', '.join(missing)}；重跑 --make-key")
    for tid, mapping in key.items():
        if sorted(mapping) != LABELS:
            sys.exit(f"[error] {tid} 的标签不是 A-D 完整四件：{sorted(mapping)}")
        if sorted(mapping.values()) != sorted(ENGINES):
            sys.exit(f"[error] {tid} 的引擎重复或缺失：{sorted(mapping.values())}")
    return key


def load_rankings(path):
    rows, bad = [], 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            topic = (r.get("topic") or "").strip()
            rater = (r.get("rater") or "").strip()
            order = [(r.get(f"rank{i}") or "").strip().upper() for i in range(1, 5)]
            if not topic and not rater and not any(order):
                continue                      # 空白行
            if not topic or not rater:
                bad += 1
                print(f"[warn] 缺 topic/rater，跳过：{r}", file=sys.stderr)
                continue
            if len(set(order)) != 4 or any(o not in LABELS for o in order):
                bad += 1
                print(f"[warn] {topic}/{rater} 排序不完整或重复：{order}，跳过", file=sys.stderr)
                continue
            rows.append({"topic": topic, "rater": rater, "order": order,
                         "note": (r.get("note") or "").strip()})
    if bad:
        print(f"[warn] 共跳过 {bad} 行，请检查 rankings.csv", file=sys.stderr)
    return rows


def resolve(rows, key):
    out = []
    for r in rows:
        mapping = key.get(r["topic"])
        if mapping is None:
            sys.exit(f"[error] rankings.csv 里有未知题号 {r['topic']}，"
                     f"key.json 里没有它。检查是否把别的批次的表混进来了。")
        out.append({"topic": r["topic"], "rater": r["rater"],
                    "engine_order": [mapping[l] for l in r["order"]],
                    "note": r["note"]})
    return out


# ---------------------------------------------------------------- 计算
def spearman(order_a, order_b):
    """两个完整排序的 Spearman ρ（无并列，n=4）。"""
    n = len(order_a)
    pos_b = {v: i for i, v in enumerate(order_b)}
    d2 = sum((i - pos_b[v]) ** 2 for i, v in enumerate(order_a))
    return 1 - (6 * d2) / (n * (n * n - 1))


def win_rate(resolved, a, b):
    """a 排在 b 之前 的比例。"""
    win = tot = 0
    for r in resolved:
        o = r["engine_order"]
        tot += 1
        if o.index(a) < o.index(b):
            win += 1
    return (win / tot if tot else float("nan")), win, tot


def wilson(k, n, z=1.96):
    """胜率的 Wilson 95% 置信区间。返回 (下限, 点估计, 上限)。

    为什么必须有这个：n=20 时，纯随机数据的胜率很容易落在 55%–70%，
    只看点估计会把噪声判成「通过」。实测过——用完全随机的排序喂进上一版脚本，
    它输出了「H1 通过 60% / H2 通过 75%」。
    所以判据必须看**区间下限**，而不是点估计。
    """
    if n <= 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / d), p, min(1.0, (centre + margin) / d))


def rate_stat(k, n):
    lo, p, hi = wilson(k, n)
    return {"win": k, "tot": n, "p": p, "lo": lo, "hi": hi}


def sep_stat(k, n):
    """可区分度：偏离 50% 的程度，以及该偏离是否显著（区间不含 50%）。"""
    lo, p, hi = wilson(k, n)
    if p != p:
        return {"p": float("nan"), "lo": float("nan"), "hi": float("nan"), "sep": float("nan"),
                "significant": False}
    sep = max(p, 1 - p)
    # 区间整体落在 50% 的同一侧，才算真的能分开
    significant = (lo > 0.5) or (hi < 0.5)
    return {"p": p, "lo": lo, "hi": hi, "sep": sep, "significant": significant}


def compute(resolved):
    borda, top1 = defaultdict(float), defaultdict(int)
    per_topic = {}
    for t in sorted({r["topic"] for r in resolved}):
        rows = [r for r in resolved if r["topic"] == t]
        score = defaultdict(float)
        for r in rows:
            for pos, eng in enumerate(r["engine_order"]):
                score[eng] += BORDA[pos]
            top1[r["engine_order"][0]] += 1
        for eng, s in score.items():
            borda[eng] += s
        per_topic[t] = {"borda": dict(score),
                        "best": max(score.items(), key=lambda kv: (kv[1], kv[0]))[0],
                        "n_raters": len(rows),
                        "rankings": [r["engine_order"] for r in rows]}

    rhos = []
    by_rater = defaultdict(dict)
    for r in resolved:
        by_rater[r["rater"]][r["topic"]] = r["engine_order"]
    raters = sorted(by_rater)
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            for t in set(by_rater[raters[i]]) & set(by_rater[raters[j]]):
                rhos.append(spearman(by_rater[raters[i]][t], by_rater[raters[j]][t]))

    return {"borda": dict(borda), "top1": dict(top1), "per_topic": per_topic,
            "mean_rho": (sum(rhos) / len(rhos)) if rhos else float("nan"),
            "n_rho": len(rhos), "n_topics": len(per_topic), "n_rankings": len(resolved)}


# ---------------------------------------------------------------- 判读
def verdict(h1_rates, h2_pairs, rho):
    """按 DESIGN.md §四 的阈值 + 置信区间判读。

    两条铁律：
    · **看区间，不看点估计。** n=20 时 60% 的下限约 39%，完全在噪声内。
    · **看短板，不看均值。** 一个引擎 80%、另一个 30%，不能说整体通过。
    """
    lines = []
    if h1_rates:
        engs = list(h1_rates.values())
        mean_lo = sum(s["lo"] for s in engs) / len(engs)
        mean_p = sum(s["p"] for s in engs) / len(engs)
        sig = [k for k, s in h1_rates.items() if s["lo"] > 0.5]
        dead = [k for k, s in h1_rates.items() if s["hi"] < 0.5]
        # 点估计明显落后但区间还跨着 50%：样本不够，不能叫定论，但值得点名
        lagging = [k for k, s in h1_rates.items()
                   if k not in dead and s["p"] < 0.45]
        detail = "，".join(f"{SHORT[k]} {s['p']:.0%}（{s['lo']:.0%}–{s['hi']:.0%}）"
                          for k, s in h1_rates.items())
        lines.append(f"- H1 胜率：均值 **{mean_p:.0%}**，区间下限均值 {mean_lo:.0%}。{detail}")

        if dead and len(dead) == len(engs):
            lines.append("- **H1 失败**：所有引擎的置信区间都整体低于 50%，"
                         "跑输了裸模型。**暂停加引擎，先修引擎。** "
                         "最大嫌疑：原子技法被写成了形容词，而不是可执行的动作。")
        elif sig and len(sig) == len(engs):
            lines.append(f"- **H1 通过（显著）**：{len(sig)}/{len(engs)} 个引擎的 95% 区间"
                         "整体高于 50%。这是可以对外说的结论。")
            if mean_p >= 0.9:
                lines.append("  - 警惕反向问题：baseline 是不是被跑坏了"
                             "（检查它是否漏给了素材包，或温度设成了 0 而引擎版不是）。")
        elif sig:
            names = "、".join(SHORT[k] for k in sig)
            nonsig = "、".join(SHORT[k] for k in h1_rates if k not in sig)
            lines.append(f"- H1 **部分显著**：{names} 的区间整体高于 50%；"
                         f"{nonsig} 的优势还在噪声内。")
        elif mean_p >= 0.5:
            lines.append(f"- H1 **方向性，未达显著**：均值 {mean_p:.0%} 看似领先，"
                         f"但下限均值仅 {mean_lo:.0%}，还不能排除「只是运气」。"
                         "要下结论，把题量从 10 扩到 25–30（CI 半宽约从 20pp 压到 12pp）。")
        else:
            lines.append(f"- H1 失败：均值 {mean_p:.0%} ≤ 50%。")

        if dead:
            lines.append(f"  - **短板**：{'、'.join(SHORT[k] for k in dead)} 的区间整体低于 50%，"
                         "当前是负资产，应下线或重做，不要靠平均值掩盖。")
        if lagging:
            lines.append(f"  - **疑似短板**：{'、'.join(SHORT[k] for k in lagging)} "
                         "点估计低于 45%，但区间还跨着 50%，样本不足以定论。"
                         "这是扩题的第一理由——n=20 时连 30% 都不算「显著落后」。")

    if h2_pairs:
        best_pair, best = max(h2_pairs.items(), key=lambda kv: kv[1]["sep"])
        # 区间是「A 的胜率」，A 落后时就翻到 B 那边再报，免得出现
        # 「可区分度 75%（11%–47%）」这种自相矛盾的写法
        a_name, _, b_name = best_pair.partition("/")
        if best["p"] >= 0.5:
            lead, lo, hi = a_name, best["lo"], best["hi"]
        else:
            lead, lo, hi = b_name, 1 - best["hi"], 1 - best["lo"]
        if best["significant"] and best["sep"] >= 0.70:
            lines.append(f"- **H2 通过**：{best_pair} 中 {lead} 领先 {best['sep']:.0%}"
                         f"（95% 区间 {lo:.0%}–{hi:.0%}），区间不含 50%。"
                         "「三个文体 OS」站得住。")
        elif best["significant"]:
            lines.append(f"- H2 **勉强**：{best_pair} 中 {lead} 领先 {best['sep']:.0%}"
                         f"（{lo:.0%}–{hi:.0%}），显著但幅度有限。"
                         "建议把「文体 OS」表述为「同一引擎的三种侧重」。")
        else:
            lines.append(f"- **H2 失败（未达显著）**：最强一对只有 {best['sep']:.0%}，"
                         f"且区间（{lo:.0%}–{hi:.0%}）跨过 50%，即「分不出三个引擎」。"
                         "要么合并成一个（诚实的做法），要么找出真正的差异点重做——"
                         "继续维护三份不可区分的 SKILL.md 是纯维护成本。"
                         "**注意：这也可能是题量太小，先扩题再定论。**")

    if rho == rho:
        if rho < 0.30:
            lines.append(f"- 评分者一致性 **不合格**（ρ={rho:.2f} < 0.30）："
                         "标准没对齐，本轮结论不要发布，重新对齐后重评。")
        elif rho < 0.50:
            lines.append(f"- 评分者一致性偏低（ρ={rho:.2f}）：结论仅供内部参考。")
        else:
            lines.append(f"- 评分者一致性可用（ρ={rho:.2f}）。")
    else:
        lines.append("- 评分者一致性：数据不足（至少要 2 位评分者 × 1 个共同题）。")
    return "\n".join(lines)


# ---------------------------------------------------------------- 渲染
def render(res, resolved):
    o = ["# eval 结果\n",
         f"> 由 `eval/score.py` 生成｜{res['n_topics']} 题｜{res['n_rankings']} 条排序判断\n",
         "> ⚠️ n=10 很小：胜率 60% 的 95% 置信区间约 26%–88%。"
         "本文只下方向性结论，不写「显著优于」。\n"]

    o += ["## 一、每题最优引擎\n", "| 题号 | 最优 | Borda 明细（4/3/2/1 分） | 评分者 |",
          "|---|---|---|---|"]
    for t, d in sorted(res["per_topic"].items()):
        detail = " · ".join(f"{SHORT.get(k, k)} {v:.0f}"
                            for k, v in sorted(d["borda"].items(), key=lambda kv: -kv[1]))
        o.append(f"| {t} | **{SHORT.get(d['best'], d['best'])}** | {detail} | {d['n_raters']} |")

    o += ["\n## 二、H1：引擎 vs 裸模型\n",
          "| 引擎 | 胜 | 负 | 胜率 | 95% 区间 | 判定 |", "|---|---|---|---|---|---|"]
    h1 = {}
    for eng in ENGINES:
        if eng == "baseline":
            continue
        _rate, win, tot = win_rate(resolved, eng, "baseline")
        st = rate_stat(win, tot)
        h1[eng] = st
        judge = ("显著领先" if st["lo"] > 0.5 else
                 ("显著落后" if st["hi"] < 0.5 else "噪声内"))
        o.append(f"| {SHORT.get(eng, eng)} | {win} | {tot - win} | **{st['p']:.0%}** | "
                 f"{st['lo']:.0%}–{st['hi']:.0%} | {judge} |")
    per_topic_raters = round(len(resolved) / res["n_topics"], 1) if res["n_topics"] else 0
    o += ["\n> 判定看的是**区间是否整体高于/低于 50%**，不是点估计。"
          f"本轮 {res['n_topics']} 题、每题约 {per_topic_raters} 位评分者，"
          f"每对比较 n={h1[next(iter(h1))]['tot'] if h1 else 0}。\n"]

    o += ["\n## 三、H2：引擎之间的可区分度\n",
          "| A | B | A 胜率 | A 胜率 95% 区间 | 可区分度 | 判定 |",
          "|---|---|---|---|---|---|"]
    h2 = {}
    others = [e for e in ENGINES if e != "baseline"]
    for i in range(len(others)):
        for j in range(i + 1, len(others)):
            a, b = others[i], others[j]
            _rate, win, tot = win_rate(resolved, a, b)
            st = sep_stat(win, tot)
            key = f"{SHORT.get(a, a)}/{SHORT.get(b, b)}"
            h2[key] = st
            if not st["significant"]:
                judge = "分不出（跨 50%）"
            elif st["sep"] >= 0.70:
                judge = "可区分"
            else:
                judge = "弱区分"
            o.append(f"| {SHORT.get(a, a)} | {SHORT.get(b, b)} | {st['p']:.0%} | "
                     f"{st['lo']:.0%}–{st['hi']:.0%} | {st['sep']:.0%} | {judge} |")

    o += ["\n## 四、评分者一致性\n",
          f"- 平均 Spearman ρ = **{res['mean_rho']:.2f}**（{res['n_rho']} 组比较）\n"
          if res["n_rho"] else "- 数据不足\n"]

    o += ["\n## 五、判读\n", verdict(h1, h2, res["mean_rho"]),
          "\n> **多重比较提醒**：本轮做了 3 次引擎对比较。单次 95% 区间意味着，"
          "即使三对完全无差别，也约有 14% 的概率至少有一对被判成「可区分」。"
          "所以 H2 只有一对通过时，结论应表述为「初步可区分」，"
          "而不是「三个文体各不相同」。这一句请不要因为结论好看就删掉。\n"]

    o += ["\n## 六、结论一句话\n",
          "> TBD — 跑完把这一行换成你自己的话。**不要**让脚本替你下结论。\n"]

    o += ["\n## 七、最像活人的句子（评分者 note 汇总）\n"]
    notes = [(r["topic"], r["rater"], r["note"]) for r in resolved if r["note"]]
    if notes:
        seen = set()
        for tid, rater, n in notes:
            if n in seen:            # 同一句话被多人写下时只记一次，后面注明出现在哪些题
                continue
            seen.add(n)
            src = ", ".join(sorted({t for t, _r, x in notes if x == n}))
            o.append(f"- {n}\n  - 出现于：{src}")
    else:
        o.append("_（暂无评分者备注）_")

    o += ["\n---\n", "本表由脚本生成，判读为规则输出；发布前请人工改写第六节。"]
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------- 自检
def selftest():
    """用可控假数据验证算术。三件事：胜率算对、ρ 算对、短板判读生效。"""
    # 场景：活人感总是第 1，官方体第 2，特稿第 3，baseline 第 4
    key = {t: {"A": "human-voice-writing", "B": "guanfang-writing",
               "C": "feature-writing", "D": "baseline"} for t in ("t01", "t02")}
    rows = [{"topic": t, "rater": "R1", "order": ["A", "B", "C", "D"], "note": ""}
            for t in ("t01", "t02")]
    res_rows = resolve(rows, key)
    ok = True

    rate, win, tot = win_rate(res_rows, "human-voice-writing", "baseline")
    if (win, tot, round(rate, 3)) != (2, 2, 1.0):
        print(f"[fail] 胜率：期望 (2,2,1.0)，得到 ({win},{tot},{rate})")
        ok = False

    if round(spearman(["A", "B", "C", "D"], ["A", "B", "C", "D"]), 3) != 1.0:
        print("[fail] 同序 ρ 应为 1.0")
        ok = False
    if round(spearman(["A", "B", "C", "D"], ["D", "C", "B", "A"]), 3) != -1.0:
        print("[fail] 逆序 ρ 应为 -1.0")
        ok = False

    res = compute(res_rows)
    if res["per_topic"]["t01"]["best"] != "human-voice-writing":
        print("[fail] 每题最优算错")
        ok = False
    if res["mean_rho"] != float("nan") and res["n_rho"] == 0:
        pass  # 单评分者无 ρ，符合预期
    if res["borda"]["human-voice-writing"] != 8:   # 2 题 × 4 分
        print(f"[fail] Borda：期望 8，得到 {res['borda'].get('human-voice-writing')}")
        ok = False

    v = verdict({"human-voice-writing": rate_stat(18, 20),
                 "guanfang-writing": rate_stat(2, 20),
                 "feature-writing": rate_stat(16, 20)},
                {"活人感/官方体": sep_stat(16, 20)}, 0.6)
    if "短板" not in v:
        print("[fail] 短板判读未触发（有引擎显著落后却给了整体通过的结论）")
        ok = False

    # n=20 时 6/20（30%）的区间上界约 0.52，还没到「显著落后」。
    # 这一条把「样本量的限制」写进测试，免得以后有人把它当成 bug 改掉。
    v_weak = verdict({"guanfang-writing": rate_stat(6, 20)}, {}, 0.6)
    if "**短板**：" in v_weak or "**疑似短板**" not in v_weak:
        print(f"[fail] 6/20 应判为「疑似短板」而非定论。输出：\n{v_weak}")
        ok = False

    # 关键回归：n=20 的 12/20（点估计 60%）恰恰落在噪声内，不能判「显著通过」。
    # 上一版脚本在这里会输出「H1 通过 60%」——用纯随机数据实测过。
    v_noise = verdict({"human-voice-writing": rate_stat(12, 20)}, {}, 0.6)
    if "**H1 通过（显著）**" in v_noise or "方向性" not in v_noise:
        print(f"[fail] 60%（n=20）被判成显著了。输出：\n{v_noise}")
        ok = False

    # 20/20 才该判显著
    v_strong = verdict({"human-voice-writing": rate_stat(20, 20)}, {}, 0.6)
    if "**H1 通过（显著）**" not in v_strong:
        print(f"[fail] 20/20 没判成显著。输出：\n{v_strong}")
        ok = False

    # H2：13/20（65%）区间跨 50%，不能算可区分
    v_h2 = verdict({}, {"活人感/官方体": sep_stat(13, 20)}, 0.6)
    if "H2 失败" not in v_h2:
        print(f"[fail] 65% 的引擎间差异被判成可区分了。输出：\n{v_h2}")
        ok = False

    # Wilson 区间本身
    lo, p, hi = wilson(12, 20)
    if not (0.36 < lo < 0.40 and 0.78 < hi < 0.82):
        print(f"[fail] Wilson(12,20) 区间异常：{lo:.3f}–{hi:.3f}")
        ok = False

    print("自检：全部通过" if ok else "自检：失败")
    return 0 if ok else 1


# ---------------------------------------------------------------- 入口
def load_assign():
    """每题由哪几位评分者评。缺文件时退化为「3 人全评」并提示。

    为什么必须有这层：10 题 × 4 篇 = 40 篇，若 3 人都评全部，
    每人要读约 3.6 万字，志愿者撑不住，最后拿到的是敷衍的排序。
    blind.py 按 2 人/题分配（每人 6–7 题），评分表必须跟着这个分配走。
    """
    path = HERE / "assign.json"
    if not path.exists():
        print("[warn] 缺 assign.json，按「3 位评分者全评」生成评分表。"
              "建议先跑 python3 eval/blind.py 生成分配。", file=sys.stderr)
        return {tid: ["R1", "R2", "R3"] for tid in topic_ids()}
    return json.loads(path.read_text(encoding="utf-8"))


def write_template(key, assign):
    # lineterminator="\n" 是必须的：Windows 上 sys.stdout 会把 \n 再翻成 \r\n，
    # 而 csv 默认已经写 \r\n，于是每行之间多出一个空行（实测 21 行 → 42 行）。
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["topic", "rater", "rank1", "rank2", "rank3", "rank4", "note"])
    n = 0
    for tid in sorted(key):
        for rater in assign.get(tid, []):
            w.writerow([tid, rater, "", "", "", "", ""])
            n += 1
    print(f"[ok] 生成 {n} 行评分表（{len(key)} 题 × 每题 {len(next(iter(assign.values())))} 位评分者）",
          file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="eval 汇总 / 评分表生成")
    ap.add_argument("--input", help="rankings.csv")
    ap.add_argument("--key", default=str(HERE / "key.json"))
    ap.add_argument("--make-key", action="store_true", help="生成 key.json（固定种子）")
    ap.add_argument("--template", action="store_true", help="按已有 key.json 输出空白评分表")
    ap.add_argument("--selftest", action="store_true", help="验证算术")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.make_key:
        key = make_key(Path(args.key))
        print(f"[ok] 已写 {args.key}（{len(key)} 题，固定种子 20261125）。"
              "不要把它给评分者看。", file=sys.stderr)
        return 0

    if args.template:
        write_template(load_key(Path(args.key)), load_assign())
        return 0

    if not args.input:
        ap.print_help()
        return 2

    key = load_key(Path(args.key))
    rows = load_rankings(Path(args.input))
    if not rows:
        sys.exit("[error] rankings.csv 里没有有效数据")

    resolved = resolve(rows, key)
    res = compute(resolved)

    if args.json:
        print(json.dumps({k: v for k, v in res.items()}, ensure_ascii=False, indent=2))
    else:
        print(render(res, resolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
