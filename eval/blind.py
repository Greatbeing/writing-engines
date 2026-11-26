#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 40 份模型输出做成盲评包。

用法：
    python3 eval/blind.py               # 按 assign 生成 eval/blind/<评分者>/<题号>/<标签>.md
    python3 eval/blind.py --check       # 只检测泄露与缺件，不写文件
    python3 eval/blind.py --force       # 有泄露也继续（不推荐，本轮结果将不可信）

为什么要有这一步
----------------
盲评最容易死在两件不起眼的事上：

1. **模型把指令抄进正文。** 「按原子 5 的场景微电影写法……」一旦出现在正文里，
   评分者立刻知道哪篇是引擎版。这一步检测并拦下。
2. **标签与映射错配。** 上一版 score.py 的模板每次重跑都重新抽签，导致评分者
   照旧标签填表、脚本按新 key 解析，结果全错且看不出来。这一步让 key 成为
   唯一事实来源，且每份盲评文件都从 key 派生。

还修了一个我自己的设计错误：原先假设「3 位评分者都评全部 10 题」，
那是每人读 40 篇（约 3.6 万字），不现实。现在每题只分给 2 位评分者，
每人 6–7 题（24–28 篇）。分配写进 eval/assign.json，可复现。

说明：本文件在无 Python 沙箱内写成，未经实际执行。
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
BLIND = HERE / "blind"
RATERS = ["R1", "R2", "R3"]
ENGINES = ["baseline", "sanlian-writing", "zhexuan-writing", "feature-writing"]
LABELS = ["A", "B", "C", "D"]

# 必须拦下的泄露：这些字样一旦出现在正文，评分者就能反推版本
HARD_LEAKS = [
    "SKILL.md", "sanlian-writing", "zhexuan-writing", "feature-writing",
    "风格指纹", "红线审查", "原子技法", "本引擎", "写作引擎",
    "浙江宣传体", "三联生活实验室", "《人物》杂志体",
]
# 只警告：可能是文章正常用词（比如一篇讨论「特稿」的文章）
SOFT_LEAKS = ["活人感", "官方体", "特稿体", "原子", "方法论"]


# ---------------------------------------------------------------- 分配
def build_assign(topics):
    """每题 2 位评分者，轮流分配。10 题 → 7/7/6，可复现。"""
    assign = {}
    for i, t in enumerate(topics):
        a, b = i % 3, (i + 1) % 3
        assign[t] = [RATERS[a], RATERS[b]]
    return assign


def load_assign(topics):
    path = HERE / "assign.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = [t for t in topics if t not in data]
        if missing:
            sys.exit(f"[error] assign.json 缺题号：{', '.join(missing)}；删掉它重新生成")
        return data
    data = build_assign(topics)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load_key(topics):
    path = HERE / "key.json"
    if not path.exists():
        sys.exit("[error] 缺 key.json。先跑：python3 eval/score.py --make-key")
    key = json.loads(path.read_text(encoding="utf-8"))
    missing = [t for t in topics if t not in key]
    if missing:
        sys.exit(f"[error] key.json 缺题号：{', '.join(missing)}；重跑 --make-key")
    return key


# ---------------------------------------------------------------- 泄露检测
def scan(text):
    """返回 (hard_hits, soft_hits)，各为 [(关键词, 上下文)]。"""
    hard, soft = [], []
    for kw in HARD_LEAKS:
        for m in re.finditer(re.escape(kw), text):
            s = max(0, m.start() - 20)
            hard.append((kw, text[s:m.end() + 20].replace("\n", " ")))
    for kw in SOFT_LEAKS:
        for m in re.finditer(re.escape(kw), text):
            s = max(0, m.start() - 20)
            soft.append((kw, text[s:m.end() + 20].replace("\n", " ")))
    return hard, soft


def strip_fence(text):
    """去掉模型爱加的 ```markdown 围栏。"""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
        t = re.sub(r"\n```\s*$", "", t)
    return t.strip() + "\n"


# ---------------------------------------------------------------- 主流程
def main(argv=None):
    ap = argparse.ArgumentParser(description="生成盲评包")
    ap.add_argument("--check", action="store_true", help="只检查，不写文件")
    ap.add_argument("--force", action="store_true", help="有硬泄露也继续")
    ap.add_argument("--from", dest="src", choices=["runs", "demo"], default="runs",
                    help="产出位置：runs（eval/runs/*.out.md）或 demo（demo/<题号>/<短名>.md）")
    ap.add_argument("--topics", default="", help="只处理这些题号，逗号分隔；默认全部")
    # 说明：--topics 是为「题量尚未补齐时先做一轮小规模盲评」而加的。
    # 只要 key.json 与 assign.json 覆盖了所选题目，子集就是自洽的。
    args = ap.parse_args(argv)

    prompts = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))["topics"]
    topics = [t["id"] for t in prompts]
    if args.topics:
        want = [t.strip() for t in args.topics.split(",") if t.strip()]
        unknown = [t for t in want if t not in topics]
        if unknown:
            sys.exit(f"[error] 未知题号：{', '.join(unknown)}")
        topics = want
    key = load_key(topics)
    assign = load_assign(topics)

    # demo 模式下，引擎名对应 demo/<题号>/ 下的短文件名
    DEMO_NAME = {"baseline": "baseline", "sanlian-writing": "sanlian",
                 "zhexuan-writing": "zhexuan", "feature-writing": "feature"}

    def out_path(tid, eng):
        if args.src == "runs":
            return RUNS / f"{tid}--{eng}.out.md"
        return HERE.parent / "demo" / tid / f"{DEMO_NAME[eng]}.md"

    # 1) 缺件检查
    missing = []
    for tid in topics:
        for eng in ENGINES:
            p = out_path(tid, eng)
            if not p.exists() or p.stat().st_size < 50:
                missing.append(str(p.relative_to(HERE.parent)))
    if missing:
        print(f"[error] 缺 {len(missing)} 份输出（或文件过小）：", file=sys.stderr)
        for m in missing:
            print(f"   {m}", file=sys.stderr)
        print("\nruns 模式先跑 eval/tasks.py；demo 模式见 demo/<题号>/。", file=sys.stderr)
        return 2

    # 2) 泄露检查 + 建内存里的盲评包
    bundle = {}          # {(rater, topic): {label: text}}
    hard_n = soft_n = 0
    fails = []
    for tid in topics:
        texts = {}
        for eng in ENGINES:
            raw = out_path(tid, eng).read_text(encoding="utf-8", errors="replace")
            # 引擎名 → 标签，方向：key[tid] 是 {label: engine}，这里反查
            label = next(l for l, e in key[tid].items() if e == eng)
            body = strip_fence(raw)
            texts[label] = body

            hard, soft = scan(body)
            if hard:
                hard_n += len(hard)
                fails.append((tid, eng, hard))
            soft_n += len(soft)

        for rater in assign[tid]:
            bundle[(rater, tid)] = texts

    if fails:
        print(f"[{'warn' if args.force else 'error'}] 检测到 {len(fails)} 处硬泄露：",
              file=sys.stderr)
        for tid, eng, hits in fails:
            print(f"  {tid}--{eng}:", file=sys.stderr)
            for kw, ctx in hits[:3]:
                print(f"     「{kw}」 …{ctx}…", file=sys.stderr)
        print("\n泄露会让评分者反推版本，整轮排序失效。"
              "\n处理方式：回到该篇输出，删掉泄露句后重存；"
              "\n或（不推荐）加 --force 强行继续，并在 RESULTS.md 里注明本轮有污染。",
              file=sys.stderr)
        if not args.force:
            return 1

    if soft_n:
        print(f"[note] 另有 {soft_n} 处软疑似（活人感/原子等），可能是文章正常用词，"
              "建议人工扫一眼。", file=sys.stderr)

    if args.check:
        print(f"[ok] {len(topics) * 4} 份齐全；硬泄露 {hard_n} 处，软疑似 {soft_n} 处。未写文件。")
        return 0

    # 3) 写盲评包
    if BLIND.exists():
        shutil.rmtree(BLIND)
    for (rater, tid), texts in sorted(bundle.items()):
        d = BLIND / rater / tid
        d.mkdir(parents=True, exist_ok=True)
        for label, body in texts.items():
            (d / f"{label}.md").write_text(body, encoding="utf-8")

    # 4) 清单（不含引擎，避免清单自己变成泄露源）
    manifest = BLIND / "MANIFEST.csv"
    rows = ["rater,topic,labels,files"]
    for (rater, tid), texts in sorted(bundle.items()):
        rows.append(f"{rater},{tid},{len(texts)},{len(list((BLIND / rater / tid).glob('*.md')))}")
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")

    per_rater = {}
    for (rater, tid) in bundle:
        per_rater[rater] = per_rater.get(rater, 0) + 1
    print(f"[ok] 盲评包已生成 → {BLIND}")
    for r, n in sorted(per_rater.items()):
        print(f"   {r}: {n} 题 / {n * 4} 篇")
    print()
    print("交给评分者的只有 eval/blind/<评分者>/ 这个目录。"
          "\n**不要**把 key.json、assign.json、eval/runs/ 一起发出去。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
