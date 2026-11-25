#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语料统计（L1 表层语言）：把"感觉这个作者句子短"变成数字。

用法：
    python tools/corpus_stats.py                 # 统计 tools/tests/fixtures/local/ 下全部语料
    python tools/corpus_stats.py --write         # 同时写出 corpus/<engine>/语言DNA.md
    python tools/corpus_stats.py --engine luxun  # 只看一家

为什么要有这一步
----------------
本仓库的 143 个原子是从阅读记忆里写出来的，不是从语料里数出来的。这正是
8 个引擎的 sources.md 都标着"引文未逐字核对"的根本原因：原子的说法没有
可核对的数字支撑，只有印象。

这个脚本补上那一半：词频、句长分布、标点比例、段落节奏。它不做判断，
只出数据。判断仍然写在 atom-ops.md 里，但现在可以被数字反驳。

重要：只输出**统计量与词表**，不输出任何句子。原文不入库，统计量可以入库
（数字与孤立的词不构成对作品的复制）。
"""
import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tools" / "tests" / "fixtures" / "local"
OUT = ROOT / "corpus"

SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])\s*")
CJK = r"\u4e00-\u9fff"
RE_CJK = re.compile(f"[{CJK}]")
RE_DIGIT = re.compile(r"\d+(?:\.\d+)?")
# 高频虚词：统计实词时排除
STOP = set("的了是在和有我他她它你们这那就也都说不是一"[:0])  # 保留占位，实际用下面二元过滤


def load_paragraphs(text):
    lines = [l.strip() for l in text.splitlines()]
    # 去掉来源注释行、单独的分隔线
    lines = [l for l in lines if l and not l.startswith("#") and not set(l) <= set("-—=*")]
    return [l for l in lines if len(RE_CJK.findall(l)) >= 8]  # 标题、短行不计入正文


def stats(paths):
    sents, paras_all, chars = [], [], 0
    ngram2 = collections.Counter()
    punct = collections.Counter()
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        paras = load_paragraphs(text)
        paras_all.extend(paras)
        for para in paras:
            body = para
            chars += len(RE_CJK.findall(body))
            for s in SENT_SPLIT.split(body):
                s = s.strip()
                if len(RE_CJK.findall(s)) >= 2:
                    sents.append(s)
            for ch in body:
                if ch in "，。、；：？！“”‘’「」（）—…·":
                    punct[ch] += 1
            # 二元实词：去掉含虚字的组合
            clean = RE_CJK.findall(body)
            for i in range(len(clean) - 1):
                g = clean[i] + clean[i + 1]
                if g[0] in "的了着过吗呢吧啊" or g[1] in "的了着过吗呢吧啊":
                    continue
                ngram2[g] += 1

    if not sents:
        return None
    lens = [len(RE_CJK.findall(s)) for s in sents]
    per_para = [len(SENT_SPLIT.split(p)) for p in paras_all if p.strip()]
    n = len(sents)
    return {
        "篇数": len(paths),
        "正文汉字数": chars,
        "句数": n,
        "平均句长": round(statistics.mean(lens), 1),
        "句长中位数": statistics.median(lens),
        "句长标准差": round(statistics.pstdev(lens), 1),
        "短句≤10字占比": round(sum(1 for x in lens if x <= 10) / n, 3),
        "长句≥50字占比": round(sum(1 for x in lens if x >= 50) / n, 3),
        "平均每段句数": round(statistics.mean(per_para), 1) if per_para else 0,
        "段落数": len(per_para),
        "标点": {
            "逗号/千字": round(punct["，"] * 1000 / chars, 1) if chars else 0,
            "句号/千字": round(punct["。"] * 1000 / chars, 1) if chars else 0,
            "顿号/千字": round(punct["、"] * 1000 / chars, 1) if chars else 0,
            "问号/千字": round(punct["？"] * 1000 / chars, 1) if chars else 0,
            "叹号/千字": round(punct["！"] * 1000 / chars, 1) if chars else 0,
            "破折号/千字": round(punct["—"] * 1000 / chars, 1) if chars else 0,
            "省略号/千字": round(punct["…"] * 1000 / chars, 1) if chars else 0,
            "引号开/千字": round((punct["“"] + punct["「"]) * 1000 / chars, 1) if chars else 0,
        },
        "数字/千字": round(len(RE_DIGIT.findall(" ".join(sents))) * 1000 / chars, 1) if chars else 0,
        "高频二字词": [[w, c] for w, c in ngram2.most_common(40) if c >= 3],
    }


def render(engine, s):
    lines = [f"# 语言DNA · {engine}", "",
             "> 由 `tools/corpus_stats.py` 从语料自动统计生成，**只含统计量与词表，不含任何原文句子**。",
             f"> 语料：本机 `tools/tests/fixtures/local/{engine}-*.txt`，共 {s['篇数']} 篇 / {s['正文汉字数']} 汉字（原文不入库）。",
             "> 用途：与 `references/atom-ops.md` 里的原子说法互证——原子说「句子短」，这里给出短到什么程度。", "",
             "## 一、节奏", "",
             "| 指标 | 值 |", "|---|---|",
             f"| 平均句长 | {s['平均句长']} 字 |",
             f"| 句长中位数 | {s['句长中位数']} 字 |",
             f"| 句长标准差 | {s['句长标准差']} |",
             f"| 短句（≤10 字）占比 | {s['短句≤10字占比']:.1%} |",
             f"| 长句（≥50 字）占比 | {s['长句≥50字占比']:.1%} |",
             f"| 平均每段句数 | {s['平均每段句数']} |",
             f"| 段落数 | {s['段落数']} |", "",
             "## 二、标点（每千字）", "",
             "| 标点 | 密度 |", "|---|---|"]
    for k, v in s["标点"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", f"数字密度：{s['数字/千字']} 个/千字", "",
              "## 三、高频二字词（实词粗筛，出现 ≥3 次）", ""]
    words = "、".join(f"{w}({c})" for w, c in s["高频二字词"][:40])
    lines += [words or "（无）", "",
              "## 四、怎么用这份数字", "",
              "- 写这个引擎时，句长与标点密度要对得上本表，否则是「像了样子、不像节奏」。",
              "- 与本表差距 >30% 时，先查是不是混进了别的文体的习惯。",
              "- 表里没有的东西（怎么想、怎么选材），看 `references/sources.md` 与 `atoms/index.json`。"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not FIX.exists():
        sys.exit(f"[error] 没有语料目录：{FIX}\n原文不入库，请先把语料放进去（见 tools/README.md）。")
    files = sorted(FIX.glob("*.txt"))
    groups = collections.defaultdict(list)
    for f in files:
        groups[f.stem.split("-")[0]].append(f)
    if a.engine:
        groups = {k: v for k, v in groups.items() if k == a.engine}

    result = {}
    for eng, paths in sorted(groups.items()):
        s = stats(paths)
        if not s:
            print(f"  {eng}: 语料过短，跳过")
            continue
        result[eng] = s
        print(f"== {eng}  {s['篇数']} 篇 / {s['正文汉字数']} 字 / 平均句长 {s['平均句长']}"
              f" / 短句 {s['短句≤10字占比']:.0%} / 长句 {s['长句≥50字占比']:.0%}")
        if a.write:
            d = OUT / eng
            d.mkdir(parents=True, exist_ok=True)
            (d / "语言DNA.md").write_text(render(eng, s), encoding="utf-8")
    if a.write:
        (OUT / "stats.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
        print(f"\n已写出 {len(result)} 份 → {OUT.relative_to(ROOT)}/")
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
