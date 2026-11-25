#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 40 份写作任务书（10 题 × 4 版）。

用法：
    python3 eval/tasks.py                 # 写到 eval/runs/tasks/
    python3 eval/tasks.py --only t01      # 只出某一题
    python3 eval/tasks.py --print t01     # 直接打到屏幕，不落盘

产出：
    eval/runs/tasks/<topic>--<engine>.brief.md    任务书（喂给模型）
    eval/runs/<topic>--<engine>.out.md            模型输出（你自己存到这个路径）

为什么任务书要落成文件，而不是让 README 描述一遍：
四版之间必须严格相同的东西（题目、素材包、字数、约束），一旦靠「照着做」，
就有四份不一样的手工版本。落成文件后，四版共用的部分由同一个函数渲染。

关键的公平性约束
----------------
· baseline 的任务书**不含任何技法提示**，只给题目 + 素材 + 字数。
· 引擎版的任务书多一行「按 <engine>/SKILL.md 写作」，其余字字相同。
· 两份都明令：正文里不得出现引擎名、技法名、SKILL.md 等字样。
  模型经常把指令抄进正文——这会毁掉盲评。`blind.py` 会检测并拦下。

说明：本文件在无 Python 沙箱内写成，未经实际执行。
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINES = ["baseline", "human-voice-writing", "guanfang-writing", "feature-writing"]

NO_LEAK = (
    "【输出要求】\n"
    "1. 只输出文章的标题与正文，不要输出任何说明、思考过程、Markdown 代码围栏。\n"
    "2. 正文中**不得出现**以下任何字样：引擎名、文体流派名（活人感／官方体／特稿体／"
    "浙江宣传体）、技法名称（原子、风格指纹、红线、SKILL.md）、以及任何「按某方法论写作」"
    "的自我说明。\n"
    "3. 素材我已给出，直接使用，不要编造新的访谈对象；也不要声明「本故事纯属虚构」。\n"
)

MATERIAL_TMPL = "【素材】（可直接使用，均为脱敏后的合成样本）\n{material}\n"


def load():
    data = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))
    return data["topics"]


def render_material(samples):
    out = []
    for i, s in enumerate(samples, 1):
        out.append(f"{i}. {s['tag']}，{s['name']}。{s['scene']}。"
                   f"他说：「{s['quote']}」")
    return "\n".join(out)


def brief(topic, engine):
    """渲染一份任务书。四版共用同一段 prompt/material/constraints 文本。"""
    head = []
    if engine == "baseline":
        head.append("请完成下面这篇写作任务。\n")
    else:
        head.append(f"请先加载并严格遵循 `{engine}/SKILL.md`，再完成下面这篇写作任务。\n")

    body = [
        f"【题目】\n{topic['prompt']}\n",
        MATERIAL_TMPL.format(material=render_material(topic["material"])),
        f"【体裁与篇幅】\n{topic['constraints']['length']}；"
        f"{topic['constraints']['format']}。\n",
        NO_LEAK,
    ]
    return "".join(head + body)


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成 eval 写作任务书")
    ap.add_argument("--only", help="只处理某个题号，如 t01")
    ap.add_argument("--print", dest="print_topic", help="打印某题的四份任务书，不落盘")
    args = ap.parse_args(argv)

    topics = load()
    if args.print_topic:
        t = next((x for x in topics if x["id"] == args.print_topic), None)
        if not t:
            sys.exit(f"[error] 没有题号 {args.print_topic}")
        for eng in ENGINES:
            print(f"{'=' * 60}\n# {t['id']} · {eng}\n{'=' * 60}")
            print(brief(t, eng))
        return 0

    if args.only:
        topics = [t for t in topics if t["id"] == args.only]
        if not topics:
            sys.exit(f"[error] 没有题号 {args.only}")

    out_dir = HERE / "runs" / "tasks"
    out_dir.mkdir(parents=True, exist_ok=True)

    n = 0
    for t in topics:
        for eng in ENGINES:
            path = out_dir / f"{t['id']}--{eng}.brief.md"
            path.write_text(brief(t, eng), encoding="utf-8")
            n += 1

    print(f"[ok] 已生成 {n} 份任务书 → {out_dir}")
    print()
    print("下一步：对每份任务书各生成一次，输出存到 eval/runs/<题号>--<引擎>.out.md")
    print("        例：eval/runs/t01--baseline.out.md")
    print()
    print("三条纪律（否则整轮作废）：")
    print("  · 四版用同一模型、同一温度、同一轮次；每版只生成一次，**不许挑最好的一版**")
    print("  · 引擎版必须真的加载对应 SKILL.md；baseline 不得加载任何写作方法论")
    print("  · 生成失败/拒答也照原样存下并命名为 .out.md，内容写 FAIL ——失败也是结果")
    print()
    print("存齐 40 份后：python3 eval/blind.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
