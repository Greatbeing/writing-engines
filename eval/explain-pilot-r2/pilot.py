#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""explain-pilot-r2：三条件（A=通用 / C=手法名+一句话 / B=讲透原文全文）盲评。

  python eval/explain-pilot-r2/pilot.py prompts  # 生成 27 份写作提示 → prompts/<qid>--<cond>.md（B 段逐字切自 atoms/explain/）
  python eval/explain-pilot-r2/pilot.py blind    # 抽签 → key.json / assign.json / blind/<R>/<qid>/ ；judge/<qid>/ 给手法判定者
  python eval/explain-pilot-r2/pilot.py score    # 读 ratings.csv + judge.csv，解盲，算两两胜率(Wilson)与均值 → results.json / results.md
  python eval/explain-pilot-r2/pilot.py checks   # 淡收 B 稿照抄示范 / 冷笔 B 稿流水账 的机械检查 → checks.json
"""
import csv, json, random, re, sys, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUNS, BLIND, JUDGE, PROMPTS = HERE / "runs", HERE / "blind", HERE / "judge", HERE / "prompts"
RATERS = ["R1", "R2", "R3"]
CONDS = ["A", "B", "C"]
HARD_LEAKS = ["小处切入", "冷笔白描", "淡收", "手法", "讲透", "原子", "凡尔赛体"]

spec = importlib.util.spec_from_file_location("score", ROOT / "eval" / "score.py")
score = importlib.util.module_from_spec(spec); spec.loader.exec_module(score)
tasks = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
items, atoms = tasks["items"], tasks["atoms"]


def section(atom):
    """从讲透文件逐字切出该原子一节：从 '## <id>' 行到下一个 '---' 分隔行（不含）或文件尾。"""
    a = atoms[atom]
    lines = (ROOT / a["explain"]).read_text(encoding="utf-8").splitlines()
    i = lines.index(a["section"])
    j = next((k for k in range(i + 1, len(lines)) if lines[k].strip() == "---"), len(lines))
    return "\n".join(lines[i:j]).rstrip() + "\n"


def one_liner(atom):
    m = re.search(r"^\*\*一句话\*\*：(.+)$", section(atom), re.M)
    return m.group(1).strip()


def prompts():
    PROMPTS.mkdir(parents=True, exist_ok=True)
    g = tasks["generic_instruction"]
    for it in items:
        a = it["atom"]; name = atoms[a]["name"]
        body = {
            "A": f"{g}\n\n【原稿】\n{it['draft']}\n",
            "C": f"{g}\n\n请在改写中运用这一写作手法：{name}——{one_liner(a)}\n\n【原稿】\n{it['draft']}\n",
            "B": f"{g}\n\n请在改写中运用下面这份写作手法讲解（原文全文）：\n\n<<<讲解开始\n{section(a)}讲解结束>>>\n\n【原稿】\n{it['draft']}\n",
        }
        for c, t in body.items():
            (PROMPTS / f"{it['id']}--{c}.md").write_text(t, encoding="utf-8")
    # 校验 B 段与源文件逐字一致
    for a in atoms:
        assert section(a) in (ROOT / atoms[a]["explain"]).read_text(encoding="utf-8") + "\n"
    print(f"[ok] {len(items) * 3} prompts")


def blind():
    rng = random.Random(tasks["seed"])
    key, assign = {}, {}
    # 平衡抽签：纯 shuffle 在种子 20261127 下让 A 落在 Z 位 7/9 次（位置偏差风险），
    # 改为把 XYZ 的 6 种排列按固定种子打乱后轮转分配，使每个条件在每个位置上出现 3 次。
    import itertools
    perms = [list(p) for p in itertools.permutations(["X", "Y", "Z"])]
    rng.shuffle(perms)
    # 取 3 个两两"拉丁方"排列（每位置各条件恰 1 次），每组 3 题轮转
    latin = [p for p in perms if all(p[k] != perms[0][k] for k in range(3))][:2] + [perms[0]]
    for i, it in enumerate(items):
        labs = latin[i % 3]
        key[it["id"]] = dict(zip(labs, CONDS))
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
            for d in [BLIND / r / pid for r in assign[pid]] + [JUDGE / pid]:
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{lab}.md").write_text(body, encoding="utf-8")
                (d / "draft.md").write_text(it["draft"], encoding="utf-8")
    print(f"[ok] blind built, leak hits={hits}")


def _mean(xs):
    return round(sum(xs) / len(xs), 2) if xs else None


def do_score():
    key = json.loads((HERE / "key.json").read_text(encoding="utf-8"))
    atom_of = {it["id"]: it["atom"] for it in items}
    groups = list(atoms) + ["ALL"]
    pairs = [("B", "A"), ("B", "C"), ("C", "A")]
    wins = {g: {f"{a}>{b}": [0, 0] for a, b in pairs} for g in groups}
    vals = {g: {c: {"read": [], "nat": [], "ai": [], "tech": [], "rank": []} for c in CONDS} for g in groups}
    top1 = {g: {c: 0 for c in CONDS} for g in groups}
    agree = []
    by_item = {}
    for r in csv.DictReader((HERE / "ratings.csv").open(encoding="utf-8-sig")):
        k = key[r["item"]]
        order = [k[r[f"rank{i}"].strip().upper()] for i in (1, 2, 3)]
        assert sorted(order) == CONDS, r
        by_item.setdefault(r["item"], []).append(order)
        for g in (atom_of[r["item"]], "ALL"):
            for a, b in pairs:
                w = wins[g][f"{a}>{b}"]; w[1] += 1; w[0] += order.index(a) < order.index(b)
            top1[g][order[0]] += 1
            for lab, c in k.items():
                for f in ("read", "nat", "ai"):
                    vals[g][c][f].append(float(r[f"{lab}_{f}"]))
                vals[g][c]["rank"].append(order.index(c) + 1)
    for it, os_ in by_item.items():
        if len(os_) == 2:
            agree.append(os_[0] == os_[1])
    jp = HERE / "judge.csv"
    if jp.exists():
        for r in csv.DictReader(jp.open(encoding="utf-8-sig")):
            k = key[r["item"]]
            for g in (atom_of[r["item"]], "ALL"):
                for lab, c in k.items():
                    vals[g][c]["tech"].append(float(r[lab]))
    res = {"pairwise": {}, "means": {}, "top1": top1,
           "rater_full_order_agreement": f"{sum(agree)}/{len(agree)}"}
    for g in groups:
        res["pairwise"][g] = {}
        for pk, (k_, n) in wins[g].items():
            lo, p, hi = score.wilson(k_, n)
            res["pairwise"][g][pk] = {"wins": k_, "n": n, "p": round(p, 3), "lo": round(lo, 3), "hi": round(hi, 3),
                                      "verdict": "通过" if lo > 0.5 else ("反向" if hi < 0.5 else "不确定")}
        res["means"][g] = {c: {f: _mean(v) for f, v in vals[g][c].items()} for c in CONDS}
    (HERE / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# results（脚本生成，勿手改）", "", "## 两两胜率（排序中前者排在后者之前）", "",
          "| 组 | 对比 | 胜/次 | 胜率 | Wilson 95% | 判定 |", "|---|---|---|---|---|---|"]
    for g in groups:
        for pk, s in res["pairwise"][g].items():
            md.append(f"| {g} | {pk} | {s['wins']}/{s['n']} | {s['p']:.0%} | {s['lo']:.1%}–{s['hi']:.1%} | {s['verdict']} |")
    md += ["", "## 均值（read 可读、nat 自然、ai AI腔[越低越好]、tech 手法判定、rank 平均名次[越小越好]）", "",
           "| 组 | 条件 | read | nat | ai | tech | rank |", "|---|---|---|---|---|---|---|"]
    for g in groups:
        for c in CONDS:
            m = res["means"][g][c]
            md.append(f"| {g} | {c} | {m['read']} | {m['nat']} | {m['ai']} | {m['tech']} | {m['rank']} |")
    md += ["", f"第一名次数：{json.dumps(top1, ensure_ascii=False)}", "",
           f"两位评分者完整排序一致：{res['rater_full_order_agreement']} 题"]
    (HERE / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


def checks():
    demo = ["楼下", "唉，不说了", "不说了", "扔进抽屉", "早凉了", "埃塞俄比亚", "来了。", "另外几块"]
    out = {}
    for it in items:
        for c in CONDS:
            t = (RUNS / f"{it['id']}--{c}.md").read_text(encoding="utf-8")
            rec = {"chars": len(re.sub(r"\s", "", t))}
            if it["atom"] == "versailles.10":
                rec["demo_hits"] = [d for d in demo if d in t]
                rec["has_haha_or_joke"] = bool(re.search(r"哈哈|开玩笑|凡尔赛", t))
                rec["last_line"] = [l for l in t.strip().splitlines() if l.strip() and "综合创作" not in l][-1][-60:]
            if it["atom"] == "luxun.9":
                rec["timestamps"] = len(re.findall(r"[零一二两三四五六七八九十\d]+点(半|[零一二三四五六七八九十\d]+分?)?|\d{1,2}[:：]\d{2}", t))
                rec["exclaim"] = t.count("！") + t.count("!")
                rec["ling_ren_shen_shen"] = len(re.findall(r"令人|深深", t))
            out[f"{it['id']}--{c}"] = rec
    (HERE / "checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    {"prompts": prompts, "blind": blind, "score": do_score, "checks": checks}[sys.argv[1]]()
