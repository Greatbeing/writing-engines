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
import tempfile
import time
from pathlib import Path

ROOT = Path(os.environ.get("WRITING_HOME", Path(__file__).resolve().parents[2])).resolve()
# 提示词临时文件放在仓库外：它包含整份 SKILL.md，放在仓库内会被 lint 的「语料全文」规则误判
WORK = Path(tempfile.mkdtemp(prefix="writing-daily-"))
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


def extract_issues(review):
    """从「指纹逐条核对」表里抽出判为“不过”的那些项，供写作端下次自查。"""
    issues = []
    for line in review.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and ("不过" in cells[1] or "不 过" in cells[1]):
            name, why = cells[0], cells[2]
            issues.append(f"{name}（{why}）" if why and why != "-" else name)
    return issues[:8]


def extract_gems(review, article):
    """从评审里取「惊艳句」与「这一课」。

    惊艳句必须逐字出现在原文里（防止评审改写或编造），每篇最多 2 句，8–80 字。
    这一课 ≤60 字，写「无」或空即不收。
    """
    def section(name):
        m = re.search(rf"^##\s*{name}\s*\n(.*?)(?=^##\s|\Z)", review, re.S | re.M)
        return m.group(1).strip() if m else ""

    gems = []
    sec = section("惊艳句")
    if sec and not re.fullmatch(r"[（(]?无[)）。.]?", sec):
        for m in re.finditer(r"^>\s*(.+?)\s*$\n+(?:理由[：:]\s*(.+))?", sec, re.M):
            text = m.group(1).strip().strip("「」“”\"")
            why = (m.group(2) or "").strip()
            if 8 <= len(text) <= 80 and text in article and len(gems) < 2:
                gems.append({"text": text, "why": why})
    lesson = section("这一课").splitlines()[0].strip() if section("这一课") else ""
    lesson = lesson.strip("（）() ")
    if lesson in ("", "无", "无。") or len(lesson) > 60:
        lesson = ""
    return gems, lesson


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

    sysf = WORK / "rev_sys.txt"
    usrf = WORK / "rev_usr.txt"
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

## 惊艳句
（从原文中逐字摘出，最多 2 句；格式：`> 原句` 下一行 `理由：……`。
标准极高：必须同时满足——①读到会停下来重读；②换一个字就变差；③不是套话、不是金句腔、不是排比；④离开上下文单独拿出来仍然成立。
宁缺毋滥：大多数文章一句都没有，没有就只写「无」。）

## 这一课
（一条可复用的写作经验，一句话，≤60 字，必须是能照着做的动作，如「写一个地方只写一样东西」；不许写道理和感悟。没有够格的就写「无」。）

## 评分
X / 5（只给数字）

要求：判定要能被别人复核；不要重写全文；不要超过 800 字。
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

    issues = extract_issues(review)
    gems, lesson = extract_gems(review, body)
    st["gems"] = [g for g in st.get("gems", []) if g.get("date") != a.date] + [
        {"date": a.date, "engine": engine, "title": run["title"], **g} for g in gems]
    st["lessons"] = [x for x in st.get("lessons", []) if x.get("date") != a.date] + (
        [{"date": a.date, "engine": engine, "title": run["title"], "text": lesson}] if lesson else [])
    st.setdefault("reviews", []).append({
        "date": a.date, "engine": engine, "title": run["title"],
        "stars": stars, "file": out.relative_to(ROOT).as_posix(), "by": "god",
        "issues": issues,
        "verdict": "pass" if stars >= 4 else ("borderline" if stars == 3 else "needs_fix"),
    })
    save_state(st)

    subprocess.run([sys.executable, "tools/build_daily.py"], cwd=ROOT, capture_output=True)
    subprocess.run([sys.executable, "tools/build_site.py"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"review({engine}): {run['title']} {stars}/5"],
                   cwd=ROOT, capture_output=True)
    for i in range(1, 5):
        subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "master"],
                       cwd=ROOT, capture_output=True)
        p = subprocess.run(["git", "push", "origin", "HEAD:master"], cwd=ROOT, capture_output=True)
        if p.returncode == 0:
            print(f"[review] 已提交评审《{run['title']}》 {stars}/5"
                  f"（记下 {len(issues)} 条通病）→ {out.relative_to(ROOT)}")
            return 0
        time.sleep(8 * i)
    print("[review] 推送失败", file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())