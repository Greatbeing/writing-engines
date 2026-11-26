#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采风编辑部流水线：选题 → 撰稿 → 评审 → 修改 → 发布，外加引擎迭代。

两个角色：
  撰稿人（being）：topic / draft / revise / publish
  评审人（god）  ：review / evolve 的裁判

一篇稿子一个目录 drafts/pipeline/<id>/，meta.json 记状态：
  topic → drafted → reviewed → (revise ≤2 轮) → approved → published
                                             ↘ rejected
每一步都只看 meta.json 的状态推进，所以任一台机器挂了，另一台下次接着跑。

评审标准（取代旧的「指纹逐条打勾」）：
  1. 读者会不会读下去（1–5）
  2. 最像这位作者的一处、最不像的一处（各引一句）
  3. 只改一处：原句 → 改句
  指纹只作证据，不计分。禁止「为了凑指纹而加词」的建议。

引擎迭代（evolve，每周一次/引擎）：
  汇总该引擎近期评审里「最不像」的句子 → 让模型给 SKILL.md 提一处修改 →
  同一选题用旧版、新版各写一篇 → 评审人盲比（顺序随机）→
  新版赢且 lint 通过才落盘，否则只留提案记录。

用法：
  python3 tools/pipeline/pipeline.py step          # 推进所有能推进的稿子（撰稿端）
  python3 tools/pipeline/pipeline.py review        # 评审所有待评稿（评审端）
  python3 tools/pipeline/pipeline.py evolve [--engine X] [--dry-run]
  python3 tools/pipeline/pipeline.py status
"""
import argparse
import datetime as dt
import json
import random
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "daily"))
import write as W  # noqa: E402  复用门禁、checker、git、模型调用

ROOT = W.ROOT
PIPE = ROOT / "drafts" / "pipeline"
EVO = PIPE / "_evolve"
WORK = Path(tempfile.mkdtemp(prefix="writing-pipe-"))
MAX_REVISE = 2
PASS_STARS = 4

NO_PADDING = ("禁止的建议：为了让某条风格指纹「出现」而往句子里加词（例如在句首加「说白了」）。"
              "指纹是这位作者的自然倾向，不是配额。好的修改只会让句子更像人话、更准。")


# ---------- 基础 ----------
def llm(system, user):
    s, u = WORK / "s.txt", WORK / "u.txt"
    s.write_text(system, encoding="utf-8")
    u.write_text(user, encoding="utf-8")
    return W.call_llm(s, u)


def pieces():
    PIPE.mkdir(parents=True, exist_ok=True)
    out = []
    for d in sorted(PIPE.iterdir()):
        if d.is_dir() and (d / "meta.json").exists():
            out.append((d, json.loads((d / "meta.json").read_text(encoding="utf-8"))))
    return out


def save(d, meta):
    meta["updated"] = dt.datetime.now().isoformat(timespec="seconds")
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def last_draft(d, meta):
    return (d / f"draft-v{meta['version']}.md").read_text(encoding="utf-8")


def json_block(text):
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except json.JSONDecodeError:
        return {}


def pick_engine():
    """轮换：选最久没写过的引擎（不再随机）。"""
    last = {e: "" for e in W.engines()}
    for _, m in pieces():
        last[m["engine"]] = max(last.get(m["engine"], ""), m.get("created", ""))
    return sorted(last, key=lambda e: (last[e], e))[0]


# ---------- 1. 选题 ----------
def do_topic(engine=None):
    engine = engine or pick_engine()
    avoid = W.existing_titles(engine) + [m.get("topic", "") for _, m in pieces()]
    out = llm("你是一位资深选题编辑。只输出 JSON。",
              f"""为写作引擎「{engine}」出 3 个选题，再自己挑最好的一个。

引擎文档摘要：
{W.skill_body(engine)[:1500]}

标准：这位作者真的会写的题；有具体场景和人；不追热点、不写真人真品牌。
避开：{"；".join(avoid[-30:]) or "无"}

输出 ```json {{"candidates":["..","..",".."],"pick":"..","angle":"一句话切口","why":"为什么适合这个引擎"}}```""")
    j = json_block(out)
    if not j.get("pick"):
        raise RuntimeError("选题输出无法解析：" + out[:200])
    pid = f"{dt.date.today().isoformat()}-{engine.replace('-writing', '')}"
    d = PIPE / pid
    d.mkdir(parents=True, exist_ok=True)
    (d / "topic.md").write_text(
        f"# 选题：{j['pick']}\n\n- 引擎：`{engine}`\n- 切口：{j.get('angle', '')}\n- 理由：{j.get('why', '')}\n"
        f"- 备选：{' / '.join(j.get('candidates', []))}\n", encoding="utf-8")
    meta = {"id": pid, "engine": engine, "topic": j["pick"], "angle": j.get("angle", ""),
            "status": "topic", "version": 0, "created": dt.datetime.now().isoformat(timespec="seconds"),
            "history": []}
    save(d, meta)
    print(f"[选题] {pid}：{j['pick']}")
    return d, meta


# ---------- 2. 撰稿 / 4. 修改 ----------
def write_with_gate(engine, user, skill=None):
    """撰稿并过机械门禁（字数/违禁词/checker）；最多 3 稿。"""
    system = W.sys_prompt(engine) if skill is None else W.sys_prompt(engine).replace(W.skill_body(engine), skill)
    fb = ""
    for _ in range(3):
        text = llm(system, user + fb)
        bad = W.judge(text, engine)
        tmp = WORK / "probe.md"
        tmp.write_text(text, encoding="utf-8")
        sc = W.check_score(engine, tmp)
        if sc is not None and sc >= W.pass_below(engine):
            bad.append(f"checker {sc}")
        if not bad:
            return text, sc
        fb = f"\n\n上一稿被打回：{'；'.join(bad)}。重写。"
    return None, None


def draft_prompt(meta):
    return (f"用「{meta['engine']}」写一篇中文文章。题目方向：{meta['topic']}。切口：{meta['angle']}。\n"
            "正文 1000–1400 汉字；第一行 `# 标题`；结尾另起一行 `> 综合创作。`；不点名真人真品牌。只输出文章。")


def do_draft(d, meta):
    text, sc = write_with_gate(meta["engine"], draft_prompt(meta))
    if not text:
        meta["status"] = "rejected"; meta["history"].append("撰稿三稿均未过机械门禁")
        return save(d, meta)
    meta["version"] = 1
    (d / "draft-v1.md").write_text(text, encoding="utf-8")
    meta.update(status="drafted", checker=sc)
    meta["history"].append(f"v1 撰稿 checker={sc}")
    save(d, meta)
    print(f"[撰稿] {meta['id']} v1 checker={sc}")


def do_revise(d, meta):
    rv = meta["reviews"][-1]
    prev = last_draft(d, meta)
    user = (f"下面是你的稿子和评审意见。只按意见改，保留题目、结构和语气，不要另起一篇。\n\n"
            f"评审：读下去意愿 {rv.get('readability')}/5。最不像作者的地方：{rv.get('least_like')}\n"
            f"建议修改：{rv.get('fix_from')} → {rv.get('fix_to')}\n其他：{rv.get('note', '')}\n\n"
            f"{NO_PADDING}\n\n原稿：\n---\n{prev}\n---\n输出修改后的完整文章。")
    text, sc = write_with_gate(meta["engine"], user)
    if not text:
        meta["status"] = "rejected"; meta["history"].append("修改稿未过机械门禁")
        return save(d, meta)
    meta["version"] += 1
    (d / f"draft-v{meta['version']}.md").write_text(text, encoding="utf-8")
    meta.update(status="drafted", checker=sc)
    meta["history"].append(f"v{meta['version']} 修改 checker={sc}")
    save(d, meta)
    print(f"[修改] {meta['id']} v{meta['version']}")


# ---------- 3. 评审 ----------
REVIEW_SYS = ("你是一位严苛的中文文学编辑，替读者把关。判断标准只有一个：这篇值不值得读完、像不像那位作者。"
              "评审具体到句子。" + NO_PADDING)


def review_text(engine, text):
    out = llm(REVIEW_SYS, f"""评审这篇「{engine}」引擎写的文章。

作者风格参考（只作证据，不逐条打分）：
{W.skill_body(engine)[:2000]}

文章：
---
{text}
---

先写不超过 300 字的评语，再输出：
```json
{{"readability":1-5,"most_like":"最像作者的一句（原文）","least_like":"最不像作者/最像AI的一句（原文）",
"fix_from":"要改的原句","fix_to":"改后的句子","stars":1-5,"note":"一句话"}}
```
stars：5 可以署名发表；4 小瑕疵可发；3 要改；≤2 题或结构有问题。""")
    j = json_block(out)
    j["text"] = out
    return j


def do_review(d, meta):
    rv = review_text(meta["engine"], last_draft(d, meta))
    v = meta["version"]
    (d / f"review-v{v}.md").write_text(rv.pop("text"), encoding="utf-8")
    stars = int(rv.get("stars") or 3)
    meta.setdefault("reviews", []).append({"version": v, **rv})
    if stars >= PASS_STARS:
        meta["status"] = "approved"
    elif stars <= 1 or v > MAX_REVISE:
        meta["status"] = "rejected"
    else:
        meta["status"] = "reviewed"
    meta["history"].append(f"v{v} 评审 {stars}/5 → {meta['status']}")
    save(d, meta)
    print(f"[评审] {meta['id']} v{v} {stars}/5 → {meta['status']}")


# ---------- 5. 发布 ----------
def do_publish(d, meta):
    text = last_draft(d, meta)
    title = (re.search(r"^#\s+(.+)$", text, re.M) or [None, meta["topic"]])[1].strip()
    dst = ROOT / meta["engine"] / "examples" / f"{W.slug(title, meta['id'][:10])}.md"
    dst.write_text(text, encoding="utf-8")
    r = W.sh([sys.executable, "tools/build_articles.py"], timeout=600)
    if r.returncode != 0:
        print("[发布] 站点构建失败，暂缓：" + (r.stderr or "")[-300:], file=sys.stderr)
        return
    meta.update(status="published", published=dst.relative_to(ROOT).as_posix(), title=title)
    meta["history"].append("发布")
    save(d, meta)
    print(f"[发布] {title} → {meta['published']}")


# ---------- 引擎迭代 ----------
def evolve(engine=None, dry=False):
    done = {p.name.split("__")[0] for p in EVO.glob("*.md")} if EVO.exists() else set()
    week = dt.date.today().strftime("%G-W%V")
    cands = {}
    for _, m in pieces():
        for rv in m.get("reviews", []):
            cands.setdefault(m["engine"], []).append(rv)
    pool = [engine] if engine else [e for e, rs in cands.items() if len(rs) >= 2 and f"{week}-{e}" not in done]
    if not pool:
        print("[迭代] 本周没有评审数据足够（≥2 条）的引擎。"); return
    eng = pool[0]
    rs = cands.get(eng, [])
    evidence = "\n".join(f"- {r.get('stars')}/5 最不像：{r.get('least_like')}｜建议：{r.get('fix_to')}" for r in rs[-8:])
    intel = PIPE / "_intel" / f"{eng}.md"
    if intel.exists():  # 外部情报：对标账号新文章里「引擎没写到的新手法」
        evidence += "\n\n外部对标文章拆解（节选）：\n" + intel.read_text(encoding="utf-8")[-3000:]
    old = W.skill_body(eng)
    prop = llm("你是写作引擎的维护者。只输出 JSON。" + NO_PADDING, f"""下面是引擎「{eng}」的 SKILL.md 和近期评审证据。
找出证据背后最常见的一个病根，给 SKILL.md 提**一处**修改（新增或替换一段，≤200 字）。
不要加配额式规则（「至少出现 N 次」）；写成作者的做法和理由。

证据：
{evidence or '（无）'}

SKILL.md：
{old}

输出 ```json {{"diagnosis":"病根","find":"原文中要被替换的一段（必须逐字存在；新增则填空串）","replace":"新段落","after_heading":"新增时放在哪个 ## 标题下"}}```""")
    j = json_block(prop)
    new = old
    if j.get("find") and j["find"] in old:
        new = old.replace(j["find"], j.get("replace", ""), 1)
    elif j.get("replace"):
        h = j.get("after_heading", "")
        i = old.find(h) if h else -1
        new = (old[: old.find("\n", i) + 1] + "\n" + j["replace"] + "\n" + old[old.find("\n", i) + 1:]) if i >= 0 \
            else old + "\n\n" + j["replace"] + "\n"
    if new == old:
        print("[迭代] 提案无法应用：" + prop[:200]); return

    # A/B：同一选题，旧版/新版各写一篇，盲比
    _, meta = do_topic(eng) if not dry else (None, {"engine": eng, "topic": "（dry-run）", "angle": ""})
    if dry:
        print(f"[迭代] dry-run {eng}\n病根：{j.get('diagnosis')}\n替换：{j.get('replace')}"); return
    a, _ = write_with_gate(eng, draft_prompt(meta), skill=old)
    b, _ = write_with_gate(eng, draft_prompt(meta), skill=new)
    verdict, winner = "无法比较（有一版未过门禁）", "old"
    if a and b:
        flip = random.random() < 0.5
        x, y = (b, a) if flip else (a, b)
        out = llm(REVIEW_SYS, f"两篇同题文章，哪篇更值得读完、更像「{eng}」的作者？\n\n【甲】\n{x}\n\n【乙】\n{y}\n\n"
                              "先写 100 字理由，最后一行只写「甲」或「乙」。")
        pick = out.strip().splitlines()[-1]
        new_won = ("甲" in pick) == flip
        winner, verdict = ("new" if new_won else "old"), out
    rec = EVO / f"{week}-{eng}__{winner}.md"
    EVO.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"# 引擎迭代 · {eng} · {week}\n\n- 病根：{j.get('diagnosis')}\n- 结果：**{winner} 胜**\n\n"
                   f"## 提案\n\n原：\n\n> {j.get('find') or '（新增）'}\n\n新：\n\n> {j.get('replace')}\n\n"
                   f"## 盲比\n\n{verdict}\n", encoding="utf-8")
    # 拿完 meta 对应的选题目录，避免占用轮换
    (PIPE / meta["id"]).joinpath("meta.json").unlink(missing_ok=True)
    if winner == "new":
        p = ROOT / eng / "SKILL.md"
        full = p.read_text(encoding="utf-8")
        backup = full
        p.write_text(full.replace(old, new, 1), encoding="utf-8")
        lint = W.sh([sys.executable, "tools/lint_skill.py", eng])
        if lint.returncode != 0:
            p.write_text(backup, encoding="utf-8")
            rec.write_text(rec.read_text(encoding="utf-8") + "\n\n**lint 未过，已回滚。**\n", encoding="utf-8")
            print("[迭代] 新版胜但 lint 未过，已回滚")
        else:
            print(f"[迭代] {eng} 新版胜，SKILL.md 已更新")
    else:
        print(f"[迭代] {eng} 旧版胜，只留提案记录")


# ---------- 调度 ----------
def commit(msg):
    W.git("add", "-A", "drafts/pipeline")
    W.git("add", "-A")
    W.git("commit", "-m", msg)
    W.push()


def step():
    """撰稿端：推进所有能推进的稿子；没有在途稿就新开一个选题。"""
    live = [(d, m) for d, m in pieces() if m["status"] not in ("published", "rejected")]
    if not live:
        live = [do_topic()]
    for d, m in live:
        if m["status"] == "topic":
            do_draft(d, m)
        elif m["status"] == "reviewed":
            do_revise(d, m)
        elif m["status"] == "approved":
            do_publish(d, m)
    commit("pipeline: 撰稿端推进")


def review_all():
    for d, m in pieces():
        if m["status"] == "drafted":
            do_review(d, m)
    commit("pipeline: 评审端推进")


def status():
    for _, m in pieces():
        stars = "/".join(str(r.get("stars")) for r in m.get("reviews", []))
        print(f"{m['id']:28} {m['status']:10} v{m['version']} 评分[{stars}] {m['topic'][:24]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["step", "review", "evolve", "status", "topic"])
    ap.add_argument("--engine")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "step":
        step()
    elif a.cmd == "review":
        review_all()
    elif a.cmd == "evolve":
        evolve(a.engine, a.dry_run)
        if not a.dry_run:
            commit(f"evolve: {a.engine or '轮值引擎'}")
    elif a.cmd == "topic":
        print(pick_engine()) if a.dry_run else do_topic(a.engine)
    else:
        status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
