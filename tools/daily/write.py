#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日自动写作（写作端）：随机挑引擎 → 自助选题 → 写作 → 质检 → 构建 → 推送。

跑在哪：Instabox 云机 being（见 tools/daily/README.md）。
模型：本机 magpie 网关（tools/daily/llm.sh），不需要外部 API key。

门禁（任一不过就打回重写，最多 3 稿；全不过则当天不发布）：
  1. 中文字数 850–2200
  2. 违禁词 0 命中
  3. ai-flavor-checker 分数低于该引擎的 pass_below
  4. 首行是 `# 标题`

用法：
  python3 tools/daily/write.py --dry-run      # 只选题、打印提示词
  python3 tools/daily/write.py --engine mao-writing
  python3 tools/daily/write.py                # 正式
"""
import argparse
import datetime as dt
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WRITING_HOME", Path(__file__).resolve().parents[2])).resolve()
DAILY = ROOT / "drafts" / "daily"
STATE = DAILY / "state.json"
LOGDIR = DAILY / "logs"

BANNED = [
    "众所周知", "毋庸置疑", "综上所述", "总而言之", "由此可见", "值得注意的是",
    "赋能", "抓手", "闭环", "底层逻辑", "颗粒度", "范式", "彰显", "重塑", "对齐",
    "这就是生活", "我终于明白", "愿我们", "人间烟火最抚凡人心", "治愈",
    "绝绝子", "一口入魂", "yyds", "内卷的本质", "作为AI", "作为一个AI",
]


def sh(cmd, timeout=600, env=None):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout, env=env, shell=isinstance(cmd, str))


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"runs": [], "reviews": []}


def save_state(st):
    DAILY.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def engines():
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name.endswith("-writing"))


def pass_below(engine):
    cfg = json.loads((ROOT / "tools" / "engine_profiles.json").read_text(encoding="utf-8"))
    prof = cfg["profiles"].get(engine) or cfg["profiles"]["generic"]
    return float(prof.get("pass_below", 30))


def pick_engine(st, force=None):
    if force:
        return force
    cutoff = (dt.date.today() - dt.timedelta(days=6)).isoformat()
    recent = {r["engine"] for r in st.get("runs", []) if r.get("date", "") >= cutoff}
    pool = [e for e in engines() if e not in recent] or engines()
    return random.choice(pool)


def skill_body(engine):
    text = (ROOT / engine / "SKILL.md").read_text(encoding="utf-8")
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S).strip()


def existing_titles(engine, st=None, days=30):
    titles = []
    for f in sorted((ROOT / engine / "examples").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", t, re.M)
        titles.append(m.group(1).strip() if m else f.stem)
    if st:
        titles += [r["title"] for r in st.get("runs", [])][-days:]
    return titles[:40]


def recent_issues(st, limit=6):
    """把最近几次评审指出的问题汇总，避免同一个毛病反复犯。"""
    out = []
    for rv in st.get("reviews", [])[-5:]:
        for it in rv.get("issues", []) or []:
            if it and it not in out:
                out.append(it)
    return out[:limit]


def sys_prompt(engine, issues=None):
    avoid = ""
    if issues:
        avoid = ("\n\n近期评审反复指出的问题（这一次要对准，不是清零）：\n"
                 + "\n".join(f"- {x}" for x in issues) + "\n")
    return f"""你是一位严守写作引擎规范的中文作者。你只输出文章，不解释、不寒暄、不评论自己。{avoid}

下面是你要执行的引擎文档。**风格指纹**与**红线**两节是硬约束：

{skill_body(engine)}

## 一条硬规则：不要为了达标而清零

「风格指纹」里给的是**区间**，不是越少越好。例如「口语词 ≤3 处」意味着
**1 到 3 处**——写到 0 处同样不合格；「金句 ≤3 处」不是不许有金句；
「比喻 ≤2 个」不是不许打比方的意思，是别超。

逐条自检时，每一项都要落在指纹写的区间内：**没超，也要有。**
"""


def usr_prompt(engine, avoid, fb=""):
    av = "\n".join(f"- {t}" for t in avoid) if avoid else "（无）"
    return f"""用「{engine}」这个引擎写一篇中文文章。

1. 自选题目。避开这些已有题目及其近似：
{av}
2. 篇幅：正文 1000–1400 个汉字（少于 900 字直接不合格）。
3. 第一行必须是 `# 标题`，空一行后是正文，Markdown，段落之间空一行。
4. 结尾另起一行写 `> 综合创作。`
5. 不要出现：{"、".join(BANNED[:18])}。
6. 不要写成对某个具体真人的评价，也不要点名真实品牌、真实机构。
7. 直接开始写，不要写"好的""以下是"之类。

只输出文章。
{fb}
"""


def expand_prompt(engine, avoid, prev, chars):
    """字数不足时，让模型在上一稿基础上扩写；换题重写既贵又容易再犯同样的错。"""
    return f"""下面这篇用「{engine}」引擎写的稿子只有 {chars} 字，篇幅不够。

请在**保留原题目、原结构、原语气**的前提下扩写，把正文补到 1100–1400 个汉字：
- 加细节、加动作、加一句对白，不要加议论、不要加排比、不要加总结段。
- 不要另起一篇，不要换题目。

原稿：
---
{prev}
---

输出扩写后的完整文章，第一行仍是 `# 标题`，结尾保留 `> 综合创作。`。
"""


def call_llm(sysf, usrf):
    r = sh([str(ROOT / "tools" / "daily" / "llm.sh"), str(sysf), str(usrf)], timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"模型调用失败（{r.returncode}）：{(r.stderr or '').strip()[:500]}")
    out = r.stdout.strip()
    if not out:
        raise RuntimeError("模型返回空")
    return out


def check_score(engine, path):
    r = sh([sys.executable, "tools/ai-flavor-checker.py", str(path), "--engine", engine])
    m = re.search(r"合计 1 篇，均值 ([0-9.]+)", r.stdout)
    return float(m.group(1)) if m else None


def chars_of(text):
    return len(re.findall(r"[\u4e00-\u9fff]", re.sub(r"^>.*$", "", text, flags=re.M)))


def judge(text, engine):
    body = re.sub(r"^>.*$", "", text, flags=re.M)
    chars = len(re.findall(r"[\u4e00-\u9fff]", body))
    bad = []
    if chars < 850:
        bad.append(f"字数 {chars} < 850")
    elif chars > 2200:
        bad.append(f"字数 {chars} > 2200")
    hit = [w for w in BANNED if w in body]
    if hit:
        bad.append("违禁词：" + "、".join(hit))
    if not text.lstrip().startswith("# "):
        bad.append("首行不是 `# 标题`")
    return bad


def slug(title, date):
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")[:24]
    return f"{date}-{s}" if s else date


def git(*args):
    return sh(["git", *args], timeout=300)


def push(times=5):
    for i in range(1, times + 1):
        git("pull", "--rebase", "--autostash", "origin", "master")
        r = git("push", "origin", "HEAD:master")
        if r.returncode == 0:
            return True
        print(f"  push 第 {i} 次失败：{((r.stderr or r.stdout).strip()[-200:])}", file=sys.stderr)
        time.sleep(8 * i)
    return False


def prune_logs(days=45):
    """日志只留 45 天，避免长期跑把磁盘吃满（两台机器可用空间都不到 8G）。"""
    cut = time.time() - days * 86400
    for f in LOGDIR.glob("*") if LOGDIR.exists() else []:
        try:
            if f.is_file() and f.stat().st_mtime < cut:
                f.unlink()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--engine", default="")
    ap.add_argument("--max-try", type=int, default=3)
    a = ap.parse_args()

    today = dt.date.today().isoformat()
    st = load_state()
    engine = pick_engine(st, a.engine or None)
    avoid = existing_titles(engine, st)
    limit = pass_below(engine)
    DAILY.mkdir(parents=True, exist_ok=True)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    prune_logs()

    sysf, usrf = DAILY / "_sys.txt", DAILY / "_usr.txt"
    issues = recent_issues(st)
    sysf.write_text(sys_prompt(engine, issues), encoding="utf-8")
    usrf.write_text(usr_prompt(engine, avoid), encoding="utf-8")
    print(f"[daily] {today}｜引擎 {engine}（门槛 <{limit}）｜避开 {len(avoid)} 个旧题"
          f"｜评审通病 {len(issues)} 条")

    if a.dry_run:
        print(usrf.read_text(encoding="utf-8")[:800])
        return 0

    winner = None
    for attempt in range(1, a.max_try + 1):
        try:
            text = call_llm(sysf, usrf)
        except RuntimeError as e:
            print(f"[daily] {e}", file=sys.stderr)
            return 2
        title_m = re.search(r"^#\s+(.+)$", text, re.M)
        title = title_m.group(1).strip() if title_m else "(无标题)"
        path = ROOT / engine / "examples" / f"{slug(title, today)}.md"
        path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        bad = judge(text, engine)
        score = check_score(engine, path)
        if score is not None and score >= limit:
            bad.append(f"checker {score} ≥ {limit}")
        print(f"[daily] 第 {attempt} 稿《{title}》 分={score} " + ("通过" if not bad else "打回：" + "；".join(bad)))
        if not bad:
            winner = (path, title, score)
            break
        if bad and all(b.startswith("字数") for b in bad):
            usrf.write_text(expand_prompt(engine, avoid, text, chars_of(text)), encoding="utf-8")
        else:
            usrf.write_text(usr_prompt(engine, avoid,
                                       f"\n上一稿被打回，原因：{'；'.join(bad)}。请重写并务必避免。"),
                            encoding="utf-8")

    # 清掉这一轮所有落选稿，只留最终稿
    for f in (ROOT / engine / "examples").glob(f"{today}-*.md"):
        if not winner or f != winner[0]:
            f.unlink()
            print(f"  清理 {f.name}")

    if not winner:
        print("[daily] 三稿均未过质检，今天不发布。", file=sys.stderr)
        return 3

    path, title, score = winner
    r = sh([sys.executable, "tools/build_articles.py"], timeout=600)
    if r.returncode != 0:
        print("[daily] 站点构建失败，未推送：\n" + (r.stderr or "")[-600:], file=sys.stderr)
        return 4

    # 同一天重跑时替换旧记录，不要把同一天堆成多篇
    st["runs"] = [r for r in st.get("runs", []) if r.get("date") != today]
    st["runs"].append({
        "date": today, "engine": engine, "title": title, "score": score,
        "file": path.relative_to(ROOT).as_posix(), "by": "being",
    })
    # 只跑当天一篇时，把本次生成的两份提示词也留在日志里便于复盘
    (LOGDIR / f"{today}-{engine}.log").write_text(
        f"engine: {engine}\ntitle: {title}\nscore: {score}\n\n" + usrf.read_text(encoding="utf-8"),
        encoding="utf-8")
    save_state(st)

    git("add", "-A")
    cm = git("commit", "-m", f"daily({engine}): {title}")
    if cm.returncode != 0 and "nothing to commit" not in (cm.stdout + cm.stderr):
        print("[daily] commit 失败：" + (cm.stderr or "")[-400:], file=sys.stderr)
        return 5
    if not push():
        print("[daily] 推送失败", file=sys.stderr)
        return 6
    print(f"[daily] 已发布《{title}》 分={score} → {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())