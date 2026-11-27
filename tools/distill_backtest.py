#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蒸馏回测：拿一个现有引擎的范文跑 distill.py，和人工原子对照。

    python tools/distill_backtest.py gongwen-writing
    python tools/distill_backtest.py --next          # 轮转：挑最久没回测的引擎（每周定时器用）

回测问的是：工具从范文里拆出来的，和人从原作里拆出来的，重合多少。
- 召回 = 人工原子里有多少被工具抽到（模型判同一动作，代码算比例）
- 新增 = 工具抽到、人工表里没有的（可能是漏写，也可能是噪音，人看）
范文是引擎自己写的，不是原作，所以这是下限测试：连自家范文都拆不出自家原子，
工具就不可信。结果追加到 eval/distill-backtest.md。
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import distill as D  # noqa: E402

REPORT = ROOT / "eval" / "distill-backtest.md"


def human_atoms(engine):
    t = (ROOT / engine / "references" / "atom-ops.md").read_text(encoding="utf-8")
    return [re.sub(r"^[A-Z]?\d+[\.、]\s*", "", h).strip()
            for h in re.findall(r"^##\s+(.+)$", t, re.M)]


def pick_next():
    done = set(re.findall(r"^### \S+ · (\S+-writing)", REPORT.read_text(encoding="utf-8"), re.M)) if REPORT.exists() else set()
    engines = sorted(p.parent.name for p in ROOT.glob("*-writing/references/atom-ops.md")
                     if len(list(p.parent.glob("examples/*.md"))) >= 3)
    todo = [e for e in engines if e not in done]
    return (todo or engines)[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", nargs="?")
    ap.add_argument("--next", action="store_true")
    a = ap.parse_args(argv)
    engine = pick_next() if a.next or not a.engine else a.engine
    bt = "bt-" + engine
    print(f"回测 {engine}")
    r = subprocess.run([sys.executable, str(HERE / "distill.py"), "--corpus", str(ROOT / engine / "examples"),
                        "--engine", bt, "--label", engine], capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    print(r.stdout[-1500:])
    atoms_f = D.OUT / bt / "work" / "atoms.json"
    if not atoms_f.exists():
        print(r.stderr[-800:], file=sys.stderr); return 2
    got = json.loads(atoms_f.read_text(encoding="utf-8"))
    human = human_atoms(engine)
    names = [f"{i}. {x['name']}：{x['action']}" for i, x in enumerate(got)]
    res = D.parse_json(D.LLM()(D.SYS_BASE,
        "左边是人工写的原子名，右边是工具抽出的原子（编号：名：动作）。"
        "对左边每一个，找右边说的是同一个动作的编号，没有就填 -1。"
        '输出 JSON 数组：[{"human":"","match":编号}]\n\n'
        f"左：{json.dumps(human, ensure_ascii=False)}\n右：{json.dumps(names, ensure_ascii=False)}", "backtest")) or []
    hit = {x["human"]: x.get("match", -1) for x in res if isinstance(x, dict)}
    matched = [h for h in human if isinstance(hit.get(h), int) and 0 <= hit[h] < len(got)]
    used = {hit[h] for h in matched}
    extra = [got[i]["name"] for i in range(len(got)) if i not in used]
    recall = len(matched) / len(human) if human else 0
    ok = sum(x["status"] == "交叉验证" for x in got)

    line = [f"\n### {dt.date.today()} · {engine}\n\n",
            f"- 语料：自家 examples/（{len(list((ROOT / engine / 'examples').glob('*.md')))} 篇）\n",
            f"- 工具抽出 {len(got)} 个（交叉验证 {ok}）；人工 {len(human)} 个\n",
            f"- **召回 {len(matched)}/{len(human)} = {recall:.0%}**\n",
            f"- 抽到：{'、'.join(matched) or '无'}\n",
            f"- 漏掉：{'、'.join(h for h in human if h not in matched) or '无'}\n",
            f"- 工具新增（人看：漏写还是噪音）：{'、'.join(extra) or '无'}\n"]
    if not REPORT.exists():
        REPORT.write_text("# 蒸馏回测\n\n> `tools/distill_backtest.py` 自动追加。拿现有引擎自家范文跑蒸馏，"
                          "和人工原子对照。范文不是原作，这是下限测试。\n", encoding="utf-8")
    with REPORT.open("a", encoding="utf-8") as f:
        f.write("".join(line))
    print("".join(line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
