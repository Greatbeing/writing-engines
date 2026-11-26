#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日评审（评审端）：对当天由写作端发布的文章做独立评审。

跑在哪：Instabox 云机 god。
模型：本机 magpie 网关。

产出：
  drafts/daily/reviews/YYYY-MM-DD.md   人读的评审
  drafts/daily/state.json 的 reviews[]  机读记录（分数、结论）

判据：拿该引擎 SKILL.md 的「风格指纹」逐条核对，给 1–5 分。
  ≥4  合格
   3   勉强（指出必须改的一句）
  ≤2  不合格（评审里标红，并在 state 里标记 needs_fix，供人决定是否撤稿）

用法：
  python3 tools/daily/review.py                 # 评最近一篇
  python3 tools/daily/review.py --date 2026-11-26
  python3 tools/daily/review.py --dry-run
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WRITING_HOME", Path(__file__).resolve().parents[2])).resolve()
DAILY = ROOT / "drafts" / "daily"
STATE = DAILY / "state.json"
REVDIR = DAILY / "reviews"


def sh(cmd, timeout=900):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                          shell=isinstance(cmd, str))


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"runs": [], "reviews": []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fingerprints(engine):
    """只取 SKILL.md 里「风格指纹」一节 —— 评审要对照的就是它。"""
    text = (ROOT / engine / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s*风格指纹.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return (m.group(1).strip() if m else "(该引擎未列出风格指纹)")


def score(engine, path):
    r = sh([sys.executable, "tools/ai-flavor-checker.py", str(path), "--engine", engine])
    m = re.search(r"合计 1 篇，均值 ([0-9.]+)", r.stdout)
    return float(m.group(1)) if m else None


def pick_run(st, date):
    runs = [r for r in st.get("runs", []) if r.get("date") == date]
    return runs[-1] if runs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    st = load_state()
    run = pick_run(st, a.date)
    if not run:
        print(f"[review] {a.date} 没有发布记录，跳过。")
        return 0

    art = ROOT / run["file"]
    if not art.exists():
        print(f"[review] 找不到文章 {run['file']}", file=sys.stderr)
        return 2
    engine = run["engine"]
    body = art.read_text(encoding="utf-8")
    conf = score(engine, art)
    limit = None
    cfg = json.loads((ROOT / "tools" / "engine_profiles.json").read_text(encoding="utf-8"))
    limit = (cfg["profiles"].get(engine) or cfg["profiles"]["generic"]).get("pass_below", 30)

    sysf = DAILY / "_rev_sys.txt"
    usrf = DAILY / "_rev_usr.txt"
    sysf.write_text(
        "你是一位严苛的中文文学编辑。只输出评审本身，不要寒暄。"
        "评审要具体到句子，不说‘结构不错’这类空话。",
        encoding="utf-8")
    usrf.write_text(f"""请评审下面这篇文章。它由「{engine}」引擎生成。

引擎要求的风格指纹（逐条核对，每条给 过 / 不过 / 部分）：
{fingerprints(engine)}

机检参考：AI 味分 {conf}（该引擎门槛 <{limit}）。

文章：
---
{body}
---

按这个结构输出 Markdown：

## 一句话结论
（合格 / 勉强 / 不合格，并说明理由）

## 指纹逐条核对
| 指纹 | 判定 | 依据（引用原文片段，≤20字） |

## 最该改的一句
（引出原句，给出改法）

## 评分
X / 5（只给数字）

要求：判定要能被别人复核；不要重写全文；不要超过 600 字。
""", encoding="utf-8")

    if a.dry_run:
        print(f"[review] dry-run：{run['title']}｜{engine}｜分 {conf}")
        print(usrf.read_text(encoding="utf-8")[:700])
        return 0

    r = sh([str(ROOT / "tools" / "daily" / "llm.sh"), str(sysf), str(usrf)])
    if r.returncode != 0:
        print(f"[review] 模型调用失败：{(r.stderr or '')[:400]}", file=sys.stderr)
        return 3
    review = r.stdout.strip()

    m = re.search(r"(\d)\s*/\s*5", review)
    stars = int(m.group(1)) if m else 3

    REVDIR.mkdir(parents=True, exist_ok=True)
    out = REVDIR / f"{a.date}.md"
    out.write_text(
        f"""# 评审 · {a.date}

- 文章：《{run['title']}》
- 引擎：`{engine}`
- 机检：{conf}（门槛 <{limit}）
- 评审：{'合格' if stars >= 4 else ('勉强' if stars == 3 else '不合格')}（{stars}/5）

{review}
""", encoding="utf-8")

    st.setdefault("reviews", []).append({
        "date": a.date, "engine": engine, "title": run["title"],
        "stars": stars, "file": out.relative_to(ROOT).as_posix(), "by": "god",
        "verdict": "pass" if stars >= 4 else ("borderline" if stars == 3 else "needs_fix"),
    })
    save_state(st)

    subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"review({engine}): {run['title']} {stars}/5"],
                   cwd=ROOT, capture_output=True)
    for i in range(1, 5):
        subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "master"],
                       cwd=ROOT, capture_output=True)
        p = subprocess.run(["git", "push", "origin", "HEAD:master"], cwd=ROOT, capture_output=True)
        if p.returncode == 0:
            print(f"[review] 已提交评审《{run['title']}》 {stars}/5 → {out.relative_to(ROOT)}")
            return 0
        time.sleep(8 * i)
    print("[review] 推送失败", file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())