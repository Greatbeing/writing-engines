#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目维护：体检、构建一致性、周报。

两种角色，两台机器各跑自己的：
  being  --mode build   每天：重建站点，产物与源不一致才提交；顺带轻体检
  god    --mode audit   每天：只读体检（不改仓库），把问题记进报告
  god    --mode weekly  每周：汇总一周的发布/评审/体检，出周报

原则
----
1. **只读的活不提交。** audit 模式一律不动仓库，报告写进 drafts/maint/。
2. **确定性的活才自动修。** build 模式只做「重跑生成器、产物过期就重提交」这一件事，
   因为它的结果完全由源文件决定，人不需要判断。
3. **失败不掩盖。** 任一检查失败都会进报告并让退出码非 0，但不中断、不回滚。

用法：
    python3 tools/maint/maintain.py --mode build
    python3 tools/maint/maintain.py --mode audit
    python3 tools/maint/maintain.py --mode weekly
    python3 tools/maint/maintain.py --mode audit --no-push   # 只跑不提交
"""
import argparse
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WRITING_HOME", Path(__file__).resolve().parents[2])).resolve()
MAINT = ROOT / "drafts" / "maint"
LOGDIR = ROOT / "drafts" / "daily" / "logs"


def sh(cmd, timeout=900):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout, shell=isinstance(cmd, str))


def today():
    return dt.date.today().isoformat()


def push(times=5):
    for i in range(1, times + 1):
        sh(["git", "pull", "--rebase", "--autostash", "origin", "master"])
        r = sh(["git", "push", "origin", "HEAD:master"])
        if r.returncode == 0:
            return True
        time.sleep(8 * i)
    return False


def commit(msg):
    r = sh(["git", "add", "-A"])
    c = sh(["git", "commit", "-m", msg])
    return c.returncode == 0 and "nothing to commit" not in (c.stdout + c.stderr)


# ---------------------------------------------------------------- 检查项
def check_lint():
    r = sh([sys.executable, "tools/lint_skill.py", "--all"])
    tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
    return r.returncode == 0, tail[0]


def check_prompts():
    r = sh([sys.executable, "tools/run_prompts.py", "--all"])
    m = re.search(r"失败断言 (\d+) 条", r.stdout or "")
    n = int(m.group(1)) if m else -1
    return n == 0, f"失败断言 {n} 条"


def check_checker():
    r = sh([sys.executable, "tools/tests/test_checker.py"])
    return r.returncode == 0, (r.stdout or "").strip().splitlines()[-1:] and \
        (r.stdout or "").strip().splitlines()[-1] or ""


def check_quotes():
    r = sh([sys.executable, "tools/check_quotes.py"])
    m = re.search(r"疑似自造 (\d+)", r.stdout or "")
    n = int(m.group(1)) if m else -1
    return n == 0, f"疑似自造 {n} 处"


def check_links():
    """docs/ 下所有本地链接是否都能落到文件。"""
    bad = []
    base = ROOT / "docs"
    for p in list(base.glob("**/*.html")):
        try:
            t = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for href in re.findall(r'href="([^"#?]+\.html)"', t):
            if href.startswith(("http", "//")):
                continue
            if not (p.parent / href).exists():
                bad.append(f"{p.relative_to(base)} → {href}")
    return not bad, f"断裂 {len(bad)} 处" + ("；" + "；".join(bad[:3]) if bad else "")


def check_pending():
    """统计语料里还挂着「待核 / 未逐字核对」的篇目，提醒人工处理。"""
    n_unverified = 0
    files = []
    for f in (ROOT).glob("*-writing/references/sources.md"):
        t = f.read_text(encoding="utf-8")
        if "未逐字核对" in t or "待核" in t:
            n_unverified += 1
            files.append(f.parent.parent.name)
    return n_unverified == 0, f"{n_unverified} 个引擎的 sources.md 仍标未核对：" + "、".join(files[:6])


def check_examples():
    """每个引擎至少 1 篇 examples；新引擎常漏。"""
    missing = []
    for d in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name.endswith("-writing")):
        if not list((d / "examples").glob("*.md")):
            missing.append(d.name)
    return not missing, ("缺 examples：" + "、".join(missing)) if missing else "全部有示例"


CHECKS = [
    ("引擎契约 lint", check_lint),
    ("引擎断言", check_prompts),
    ("checker 回归", check_checker),
    ("引语核对", check_quotes),
    ("站点链接", check_links),
    ("示例齐全", check_examples),
]


# ---------------------------------------------------------------- build 模式
def mode_build():
    """重建站点；产物与源不一致才提交。这是唯一允许自动改仓库的模式。"""
    log = []
    ok = True
    for gen in ("tools/build_articles.py", "tools/build_compare.py"):
        r = sh([sys.executable, gen])
        log.append(f"- `{gen}` → {'ok' if r.returncode == 0 else 'FAIL'}"
                   + ("" if r.returncode == 0 else f"：{(r.stderr or '')[-200:]}"))
        ok &= r.returncode == 0
    if not ok:
        return False, log + ["构建失败，未提交"], ""

    dirty = sh(["git", "status", "--porcelain", "docs"]).stdout.strip()
    if not dirty:
        return True, log + ["站点产物已是最新，无需提交"], ""

    # 产物有变化：先跑一遍体检，全过才提交（避免把坏产物推上线）
    results = run_checks()
    bad = [f"{n}：{d}" for n, o, d in results if not o]
    if bad:
        return False, log + ["产物有变化但体检未过，未提交"] + bad, ""

    n = len(dirty.splitlines())
    if commit(f"chore(site): 重建站点产物（{n} 个文件有变化）"):
        pushed = push()
        log.append(f"- 已提交 {n} 个产物文件，推送{'成功' if pushed else '失败'}")
        return pushed, log, ""
    return False, log + ["提交失败"], ""


# ---------------------------------------------------------------- audit 模式
def run_checks():
    out = []
    for name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as exc:                      # noqa: BLE001
            ok, detail = False, f"检查自身出错：{type(exc).__name__}: {exc}"
        out.append((name, ok, detail))
    return out


def mode_audit(no_push=False):
    results = run_checks()
    bad = [x for x in results if not x[1]]
    lines = [f"# 体检 · {today()}", "",
             f"- 结论：**{'通过' if not bad else f'{len(bad)} 项有问题'}**",
             f"- 机器：{platform.node()}", ""]
    lines += ["| 检查项 | 结果 | 详情 |", "|---|---|---|"]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'✅' if ok else '❌'} | {detail or ''} |")
    # 未核对清单单独列：它不是错误，是需要人工处理的技术债
    unv = [x for x in results if x[0] == "引语核对"]
    if unv and not unv[0][1]:
        lines += ["", "> 未核对是技术债不是 bug：语料原文不入库，核对要人工对书。", ""]
    lines += ["", "## 本周待办提示", ""]
    runs, reviews = load_state()
    needs = [r for r in reviews if r.get("verdict") == "needs_fix"]
    if needs:
        lines.append(f"- 评审不合格待处理：{len(needs)} 篇（最近：{needs[-1].get('title','')}）")
    else:
        lines.append("- 无待处理的评审不合格项")
    lines.append("- 语料「待核」项需人工对书核对（见上表引语核对一行）")

    MAINT.mkdir(parents=True, exist_ok=True)
    path = MAINT / f"health-{today()}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:6]))
    print(f"[maint] 报告 → {path.relative_to(ROOT)}")

    if not no_push:
        if commit(f"chore(maint): 每日体检 {today()}（{len(bad)} 项待处理）"):
            push()
    return not bad, [], ""


# ---------------------------------------------------------------- weekly 模式
def load_state():
    p = ROOT / "drafts" / "daily" / "state.json"
    if not p.exists():
        return [], []
    d = json.loads(p.read_text(encoding="utf-8"))
    # 同一天重跑会有多条记录，只保留最后一次
    def dedup(items):
        by = {}
        for it in items:
            by[it.get("date")] = it
        return [by[k] for k in sorted(by)]
    return dedup(d.get("runs", [])), dedup(d.get("reviews", []))


def mode_weekly(no_push=False):
    runs, reviews = load_state()
    week_ago = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    r7 = [r for r in runs if r.get("date", "") >= week_ago]
    v7 = [v for v in reviews if v.get("date", "") >= week_ago]
    stars = [v.get("stars") for v in v7 if isinstance(v.get("stars"), int)]
    avg = round(sum(stars) / len(stars), 2) if stars else None

    gitlog = sh(["git", "log", "--since=7 days ago", "--oneline"]).stdout.strip().splitlines()

    lines = [f"# 周报 · {dt.date.today().isocalendar()[0]}-W{dt.date.today().isocalendar()[1]:02d}", "",
             f"周期：{week_ago} 起七天", "",
             "## 产出", "",
             f"- 发布文章 **{len(r7)}** 篇",
             f"- 收到评审 **{len(v7)}** 篇"
             + (f"，平均 **{avg}/5**" if avg is not None else ""),
             f"- 仓库提交 **{len(gitlog)}** 次", ""]
    if r7:
        lines += ["| 日期 | 引擎 | 机检 | 评审 | 标题 |", "|---|---|---|---|---|"]
        rv = {v["date"]: v for v in v7}
        for r in r7:
            v = rv.get(r["date"], {})
            lines.append(f"| {r['date']} | {r['engine']} | {r.get('score','-')} | "
                         f"{v.get('stars','-')}/5 | {r.get('title','')[:24]} |")
    # 通病汇总
    iss = []
    for v in v7:
        for x in v.get("issues", []) or []:
            k = x.split("（")[0].strip()
            if k and k not in iss:
                iss.append(k)
    lines += ["", "## 这周反复出现的问题", ""]
    lines += [f"- {x}" for x in iss[:8]] or ["- 无"]

    lines += ["", "## 下周建议", ""]
    if avg is not None and avg < 3.5:
        lines.append("- 评审均分偏低：先别加引擎，回到出问题的引擎修「风格指纹」的写法和提示词。")
    if len(r7) < 5:
        lines.append("- 发布天数不足：检查定时器是否被重启打断（`bash tools/daily/status.sh`）。")
    if not iss:
        lines.append("- 本周无重复问题，可以尝试提高篇幅要求或增加一次跨引擎对照。")

    MAINT.mkdir(parents=True, exist_ok=True)
    path = MAINT / f"weekly-{dt.date.today().isoformat()}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:10]))
    print(f"[maint] 周报 → {path.relative_to(ROOT)}")

    if not no_push:
        if commit(f"chore(maint): 周报 {today()}"):
            push()
    return True, [], ""


def prune_logs(days=45):
    cut = time.time() - days * 86400
    for d in (LOGDIR, MAINT):
        if not d.exists():
            continue
        for f in d.glob("*"):
            try:
                if f.is_file() and f.stat().st_mtime < cut:
                    f.unlink()
            except OSError:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["build", "audit", "weekly"], required=True)
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    prune_logs()
    if a.mode == "build":
        ok, log, _ = mode_build()
    elif a.mode == "audit":
        ok, log, _ = mode_audit(a.no_push)
    else:
        ok, log, _ = mode_weekly(a.no_push)
    for line in log:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())