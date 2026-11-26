#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""explain-pilot：讲透文档教学效果盲评（A=通用指令，B=+讲透全文）。

用法：
  python eval/explain-pilot/pilot.py blind      # 抽签(固定种子) → key.json / assign.json / blind/<R>/<pid>/{X,Y}.md
  python eval/explain-pilot/pilot.py flavor     # 跑 tools/ai-flavor-checker.py 记录两组分数 → flavor.json
  python eval/explain-pilot/pilot.py score      # 读 ratings.csv，按 eval/score.py 的 Wilson 汇总 B 胜率 → results.json
复用 eval/score.py 的 wilson()，口径与主评测一致：区间下限 > 50% 才算通过。
"""
import csv, json, random, subprocess, sys, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUNS, BLIND = HERE / "runs", HERE / "blind"
RATERS = ["R1", "R2", "R3"]
SEED = 20261126
HARD_LEAKS = ["小处切入", "冷笔白描", "淡收", "手法", "讲透", "原子", "凡尔赛体"]

spec = importlib.util.spec_from_file_location("score", ROOT / "eval" / "score.py")
score = importlib.util.module_from_spec(spec); spec.loader.exec_module(score)

tasks = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
items = tasks["items"]


def blind():
    rng = random.Random(SEED)
    key, assign = {}, {}
    for i, it in enumerate(items):
        labs = ["X", "Y"]; rng.shuffle(labs)
        key[it["id"]] = {labs[0]: "A", labs[1]: "B"}
        assign[it["id"]] = [RATERS[i % 3], RATERS[(i + 1) % 3]]
    (HERE / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    (HERE / "assign.json").write_text(json.dumps(assign, indent=2), encoding="utf-8")
    hits = 0
    for it in items:
        pid = it["id"]
        for lab, cond in key[pid].items():
            body = (RUNS / f"{pid}--{cond}.md").read_text(encoding="utf-8")
            for kw in HARD_LEAKS:
                if kw in body:
                    hits += 1; print(f"[leak?] {pid}--{cond}: {kw}")
            for r in assign[pid]:
                d = BLIND / r / pid; d.mkdir(parents=True, exist_ok=True)
                (d / f"{lab}.md").write_text(body, encoding="utf-8")
                (d / "draft.md").write_text(it["draft"], encoding="utf-8")
    print(f"[ok] blind built, leak hits={hits}")


def flavor():
    out = {}
    for it in items:
        eng = tasks["atoms"][it["atom"]]["checker_engine"]
        for cond in "AB":
            f = RUNS / f"{it['id']}--{cond}.md"
            p = subprocess.run([sys.executable, str(ROOT / "tools" / "ai-flavor-checker.py"),
                                "--json", "--engine", eng, str(f)], capture_output=True)
            r = json.loads(p.stdout.decode("utf-8"))["results"][0]
            out[f"{it['id']}--{cond}"] = {"atom": it["atom"], "engine": eng,
                                          "total": r["total"], "passed": r["passed"]}
    (HERE / "flavor.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in out.items():
        print(k, v["total"], v["passed"])


def do_score():
    key = json.loads((HERE / "key.json").read_text(encoding="utf-8"))
    atom_of = {it["id"]: it["atom"] for it in items}
    agg = {}
    rows = list(csv.DictReader((HERE / "ratings.csv").open(encoding="utf-8-sig")))
    for r in rows:
        cond = key[r["item"]][r["pick"].strip().upper()]
        for g in (atom_of[r["item"]], "ALL"):
            a = agg.setdefault(g, [0, 0]); a[1] += 1; a[0] += cond == "B"
    res = {}
    for g, (k, n) in agg.items():
        lo, p, hi = score.wilson(k, n)
        res[g] = {"B_wins": k, "n": n, "p": round(p, 3), "lo": round(lo, 3), "hi": round(hi, 3),
                  "verdict": "通过" if lo > 0.5 else ("反向" if hi < 0.5 else "不确定")}
        print(g, res[g])
    (HERE / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    {"blind": blind, "flavor": flavor, "score": do_score}[sys.argv[1]]()
