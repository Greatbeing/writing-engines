#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格蒸馏 v0.1 —— 一批同一作者的文章 → 一个符合 SPEC 的引擎草稿
==================================================================

    语料（本地，不入库）
      → ① 统计   句长/段长/标点/高频词      （纯代码，可复现）
      → ② 抽取   每篇抽候选原子 + ≤30 字证据   （LLM，逐篇）
      → ③ 归并   跨篇聚类、数支持篇数、归族、与库内原子查重 （LLM + 代码计数）
      → ④ 指纹   从统计量里挑 4–7 条可数指标      （代码出数，LLM 只挑）
      → ⑤ 成稿   按 SPEC 七节写 SKILL.md + references + test-prompts （LLM）
      → ⑥ 门禁   lint_skill.py --strict           （代码）

产物在 drafts/distill/<engine>/，人工审过才挪到仓库根目录。

三条硬规则（与 CONTRIBUTING 的准入门槛一致）
--------------------------------------------
1. **支持篇数由代码数，不由模型说。** 模型只负责把候选归到同一簇；
   簇里来自几篇不同文章，是 Python 数的。< 2 篇自动标「单源待验证」。
2. **原文不出本机。** 证据只保留 ≤ 30 字的片段，用于人工核对；
   产物里不出现整段原文。语料目录建议放 sources/local/（已在 .gitignore）。
3. **每个阶段落盘、可续跑。** 中间结果写 work/*.json，改了某一步，
   用 --from 从那一步重跑，不重复花前面的调用。

用法
----
    python tools/distill.py --corpus sources/local/某作者 --engine mouren-writing --label 某某体
    python tools/distill.py ... --from merge        # 从归并开始重跑
    python tools/distill.py ... --stats-only        # 只出统计，不调模型
    python tools/distill.py ... --prompts-only      # 不调模型，把第一步提示词写出来手工跑

模型：OpenAI 兼容接口。默认 MAGPIE_BASE=http://127.0.0.1:3425/v1，
key 取 MAGPIE_GATEWAY_KEY（或 ~/.dsh/.env），模型取 LLM_MODEL（默认 group/daily）。
退出码：0 成功；1 门禁未过；2 参数/环境错误。
"""
import argparse
import collections
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "atoms" / "index.json"
SPEC = ROOT / "SPEC.md"
OUT = ROOT / "drafts" / "distill"
STAGES = ["stats", "extract", "merge", "fingerprint", "scaffold", "lint"]
EVID_MAX = 30
MIN_ARTICLES = 3          # 少于 3 篇不跑：没法交叉验证
RECOMMENDED = 10          # CONTRIBUTING 准入线

# ------------------------------------------------------------------ 模型

def _env_key():
    k = os.environ.get("MAGPIE_GATEWAY_KEY") or os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    env = Path.home() / ".dsh" / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("MAGPIE_GATEWAY_KEY="):
                return line.split("=", 1)[1].strip().strip('"\'')
    return None


class LLM:
    def __init__(self, prompts_dir=None):
        self.base = os.environ.get("MAGPIE_BASE", "http://127.0.0.1:3425/v1").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "group/daily")
        self.key = _env_key()
        self.prompts_dir = prompts_dir   # 非空 = 只写提示词
        self.n = 0

    def __call__(self, system, user, tag):
        self.n += 1
        if self.prompts_dir:
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            (self.prompts_dir / f"{self.n:03d}-{tag}.md").write_text(
                f"# system\n\n{system}\n\n# user\n\n{user}\n", encoding="utf-8")
            return None
        if not self.key:
            sys.exit("缺模型 key：设置 MAGPIE_GATEWAY_KEY，或用 --prompts-only / --stats-only")
        body = json.dumps({"model": self.model, "temperature": 0.2, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.base + "/chat/completions", data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        for i in range(4):
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    return json.loads(r.read())["choices"][0]["message"]["content"]
            except (urllib.error.URLError, TimeoutError, KeyError) as e:
                if i == 3:
                    raise
                print(f"  模型调用失败（{e}），{5 * 2 ** i}s 后重试", file=sys.stderr)
                time.sleep(5 * 2 ** i)


def parse_json(text):
    if text is None:
        return None
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    raw = m.group(1) if m else text
    for opener, closer in (("[", "]"), ("{", "}")):
        a, b = raw.find(opener), raw.rfind(closer)
        if a != -1 and b > a:
            try:
                return json.loads(raw[a:b + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("模型没有返回可解析的 JSON：" + text[:200])

# ------------------------------------------------------------------ 语料

def load_corpus(d):
    files = sorted(p for p in Path(d).rglob("*") if p.suffix in (".md", ".txt") and p.is_file())
    docs = []
    for i, p in enumerate(files, 1):
        t = p.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")
        t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)          # frontmatter
        t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)                    # 图片
        if len(re.findall(r"[\u4e00-\u9fff]", t)) < 300:
            print(f"  跳过 {p.name}：不足 300 字", file=sys.stderr)
            continue
        title = next((l.lstrip("# ").strip() for l in t.splitlines() if l.strip()), p.stem)
        docs.append({"id": f"A{i:02d}", "file": p.name, "title": title[:40], "text": t})
    return docs

# ------------------------------------------------------------------ ① 统计

SENT = re.compile(r"[^。！？!?…]+[。！？!?…]+[”」』]?")
PUNCT = "，。、；：？！“”「」——…（）《》"


def stats(docs):
    sents, paras, chars, pc = [], [], 0, collections.Counter()
    first_lens, last_lens, bigr = [], [], collections.Counter()
    per_doc = []
    for d in docs:
        ps = [p.strip() for p in d["text"].split("\n") if p.strip() and not p.startswith("#")]
        cj = sum(len(re.findall(r"[\u4e00-\u9fff]", p)) for p in ps)
        ss = [s for p in ps for s in SENT.findall(p)]
        lens = [len(re.findall(r"[\u4e00-\u9fff]", s)) for s in ss if s.strip()]
        lens = [x for x in lens if x]
        if not lens:
            continue
        sents += lens
        paras += [len(re.findall(r"[\u4e00-\u9fff]", p)) for p in ps]
        chars += cj
        first_lens.append(lens[0]); last_lens.append(lens[-1])
        for ch in "".join(ps):
            if ch in PUNCT:
                pc[ch] += 1
        cjk = "".join(re.findall(r"[\u4e00-\u9fff]+", d["text"]))
        bigr.update(cjk[i:i + 2] for i in range(len(cjk) - 1))
        per_doc.append({"id": d["id"], "chars": cj, "sent_mean": round(statistics.mean(lens), 1)})

    def pct(xs, q):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(len(xs) * q))]

    per1k = {k: round(v * 1000 / chars, 2) for k, v in pc.most_common()}
    common = set("的了是在我他她你们这那一个不有和就也都说着")
    top = [w for w, _ in bigr.most_common(400) if not (set(w) & common)][:40]
    return {
        "articles": len(per_doc), "chars": chars,
        "sentence": {"mean": round(statistics.mean(sents), 1), "median": statistics.median(sents),
                     "p10": pct(sents, .1), "p90": pct(sents, .9),
                     "short_le8_ratio": round(sum(x <= 8 for x in sents) / len(sents), 3),
                     "long_ge40_ratio": round(sum(x >= 40 for x in sents) / len(sents), 3)},
        "paragraph": {"mean": round(statistics.mean(paras), 1), "median": statistics.median(paras),
                      "short_le20_ratio": round(sum(x <= 20 for x in paras) / len(paras), 3)},
        "opening_sentence_mean": round(statistics.mean(first_lens), 1),
        "closing_sentence_mean": round(statistics.mean(last_lens), 1),
        "punct_per_1k_chars": per1k,
        "top_bigrams": top,              # 孤立的二字词，不构成复制
        "per_article": per_doc,
    }

# ------------------------------------------------------------------ 库内现状

def library():
    atoms = json.loads(INDEX.read_text(encoding="utf-8"))
    fams = collections.defaultdict(list)
    for a in atoms:
        fams[a["family"]].append(a["name"])
    return atoms, dict(fams)


SYS_BASE = ("你是写作风格分析员，任务是从文章里拆出「原子技法」。原子是一个**认知或写作动作**"
            "（「先替读者说出嫌弃，再给出回答」），不是形容词（「有张力」），也不是句式模板。"
            "只依据给你的文本，不调用对作者的既有印象；看不出来就少写，宁缺毋滥。只输出 JSON。")

# ------------------------------------------------------------------ ② 抽取

def extract(docs, llm, label, fams):
    fam_list = "、".join(k for k in fams if k != "独有")
    out = []
    for d in docs:
        user = (f"文体：{label}。下面是一篇文章（编号 {d['id']}）。\n"
                f"抽出 4–8 个这篇里**真实执行了**的原子。每个给：\n"
                f'{{"name":"四到八字的动作名","action":"一句话说清怎么做",'
                f'"trigger":"什么情况下用","evidence":"原文中能证明它的片段，≤{EVID_MAX}字，逐字摘",'
                f'"family":"从这些族里选最接近的一个：{fam_list}；都不像就写 独有"}}\n'
                f"输出 JSON 数组。\n\n<<<文章\n{d['text'][:12000]}\n文章>>>")
        res = parse_json(llm(SYS_BASE, user, f"extract-{d['id']}"))
        if res is None:
            continue
        for c in res:
            ev = str(c.get("evidence", ""))[:EVID_MAX]
            # 证据必须真在原文里：模型编造的证据直接丢
            c["evidence_found"] = bool(ev) and re.sub(r"\s", "", ev)[:12] in re.sub(r"\s", "", d["text"])
            c["evidence"] = ev
            c["article"] = d["id"]
            out.append(c)
        print(f"  {d['id']} {d['title'][:16]}：{len(res)} 个候选")
    return out

# ------------------------------------------------------------------ ③ 归并

def merge(cands, llm, label, fams):
    cands = [c for c in cands if c.get("evidence_found")]
    numbered = [{"k": i, "name": c["name"], "action": c["action"], "family": c.get("family", "独有"),
                 "art": c["article"]} for i, c in enumerate(cands)]
    lib = {k: v[:12] for k, v in fams.items() if k != "独有"}
    user = (f"文体：{label}。下面是从多篇文章里抽出的候选原子（k 是编号，art 是来源文章）。\n"
            f"1. 把说的是**同一个动作**的候选并成一簇（名字不同但动作相同也要并）。\n"
            f"2. 每簇给一个最准的 name / action / trigger / family。\n"
            f"3. 对照库里已有原子（按族列出），若某簇与已有原子是同一动作，填 same_as。\n"
            f"4. 把只是风格形容、不是动作的簇标 drop=true。\n"
            f'输出 JSON 数组：[{{"name":"","action":"","trigger":"","family":"","members":[k...],'
            f'"same_as":"已有原子名或空","drop":false,"common_error":"这个动作最常见的写坏方式"}}]\n\n'
            f"库内已有原子：{json.dumps(lib, ensure_ascii=False)}\n\n"
            f"候选：{json.dumps(numbered, ensure_ascii=False)}")
    res = parse_json(llm(SYS_BASE, user, "merge"))
    if res is None:
        return None
    atoms = []
    for cl in res:
        if cl.get("drop"):
            continue
        mem = [cands[k] for k in cl.get("members", []) if isinstance(k, int) and 0 <= k < len(cands)]
        arts = sorted({m["article"] for m in mem})          # ← 支持篇数由代码数
        atoms.append({**{k: cl.get(k, "") for k in ("name", "action", "trigger", "family",
                                                      "same_as", "common_error")},
                      "support": len(arts), "articles": arts,
                      "evidence": [{"article": m["article"], "text": m["evidence"]} for m in mem][:4],
                      "status": "交叉验证" if len(arts) >= 2 else "单源待验证"})
    atoms.sort(key=lambda a: (-a["support"], a["family"] == "独有"))
    return atoms

# ------------------------------------------------------------------ ④ 指纹

def fingerprint(st, atoms, llm, label):
    user = (f"文体：{label}。下面是这位作者语料的统计量（代码算的，真实）和已归并的原子。\n"
            f"挑 4–7 条**可数**的风格指纹：每条必须能在一篇新稿子里数出来并判对错，"
            f"阈值从统计量里取（给区间，不给单点）。不要「语言生动」这类不可数的。\n"
            f'输出 JSON 数组：[{{"metric":"指标名","how":"怎么数","target":"阈值区间","basis":"依据哪个统计量"}}]\n\n'
            f"统计：{json.dumps({k: v for k, v in st.items() if k != 'per_article'}, ensure_ascii=False)}\n"
            f"原子：{json.dumps([a['name'] for a in atoms], ensure_ascii=False)}")
    return parse_json(llm(SYS_BASE, user, "fingerprint"))

# ------------------------------------------------------------------ ⑤ 成稿

def scaffold(engine, label, docs, st, atoms, fp, llm, dest):
    spec = SPEC.read_text(encoding="utf-8")[:6000]
    keep = [a for a in atoms if a["status"] == "交叉验证"][:16]
    pending = [a for a in atoms if a["status"] != "交叉验证"]
    user = (f"按下面的 SPEC 写引擎 {engine}（{label}）的 SKILL.md。\n"
            f"- frontmatter：name: {engine}；description ≤ 300 字，说清什么时候用。\n"
            f"- 七节齐全、顺序固定；全文 ≤ 3800 字符。\n"
            f"- 原子表只用下面给的交叉验证原子，编号、动作、一句例证（例证自己造，不引原文）。\n"
            f"- 风格指纹直接用给的指纹。\n"
            f"- 能力边界至少一条真的会拦住用户的限制；红线每条配「改成什么」。\n"
            f"- 原子详解指向 references/atom-ops.md，红线细则指向 references/red-lines.md。\n"
            f"只输出 SKILL.md 正文（markdown），不要代码围栏。\n\n"
            f"SPEC：\n{spec}\n\n原子：{json.dumps(keep, ensure_ascii=False)}\n\n指纹：{json.dumps(fp, ensure_ascii=False)}")
    skill = llm("你是引擎作者，严格遵守契约，不写形容词堆砌，不写鸡汤和金句。", user, "skill")

    user_t = (f"为引擎 {engine}（{label}）写 test-prompts.json：3 条题目，每条含可被正则或计数判定的 assertions。"
              f'格式：[{{"id":"t1","prompt":"写作题","assertions":[{{"type":"regex|max_chars|min_chars|not_regex","value":"..."}}]}}]'
              f"\n参考原子：{json.dumps([a['name'] for a in keep], ensure_ascii=False)}")
    tests = parse_json(llm(SYS_BASE, user_t, "tests"))
    if skill is None:
        return
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "references").mkdir(exist_ok=True)
    (dest / "examples").mkdir(exist_ok=True)
    (dest / "SKILL.md").write_text(re.sub(r"^```\w*\n|\n```$", "", skill.strip()) + "\n", encoding="utf-8")
    (dest / "test-prompts.json").write_text(json.dumps(tests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ops = [f"# {len(atoms)} 个原子操作详解（蒸馏草稿，待人工核）\n\n",
           f"由 `tools/distill.py` 从 {st['articles']} 篇语料生成。支持篇数由代码计数；"
           f"证据片段 ≤ {EVID_MAX} 字，**发布前逐条核对原文**。\n"]
    for i, a in enumerate(atoms, 1):
        ev = "；".join(f"{e['article']}「{e['text']}」" for e in a["evidence"])
        dup = f"\n**库内同动作**：{a['same_as']}（考虑复用其族，不新建）" if a.get("same_as") else ""
        ops.append(f"\n---\n\n## {i}. {a['name']}\n\n**族**：{a['family']}\n**定义**：{a['action']}\n"
                   f"**触发**：{a['trigger']}\n**证据**（{a['support']} 篇，{a['status']}）：{ev}\n"
                   f"**常见错误**：{a.get('common_error') or '待补'}{dup}\n")
    (dest / "references" / "atom-ops.md").write_text("".join(ops), encoding="utf-8")

    src = ["# 蒸馏来源（元数据）\n\n> 本目录不含原文。证据片段仅供核对。\n\n| 编号 | 篇名 | 字数 |\n|---|---|---|\n"]
    for d, p in zip(docs, st["per_article"]):
        src.append(f"| {d['id']} | {d['title']} | {p['chars']} |\n")
    (dest / "references" / "sources.md").write_text("".join(src), encoding="utf-8")
    (dest / "references" / "red-lines.md").write_text(
        "# 红线细则（待人工补全）\n\n蒸馏只能抽出「作者做了什么」，抽不出「作者绝不做什么」。"
        "这一份必须由懂这个文体的人写。\n", encoding="utf-8")
    if pending:
        (dest / "references" / "pending.md").write_text(
            "# 单源待验证原子\n\n只在 1 篇里出现。补语料后重跑 merge，够 2 篇自动升级。\n\n"
            + "".join(f"- **{a['name']}**（{a['articles'][0] if a['articles'] else '?'}）：{a['action']}\n" for a in pending),
            encoding="utf-8")

# ------------------------------------------------------------------ 主流程

def main(argv=None):
    ap = argparse.ArgumentParser(description="风格蒸馏：语料 → 引擎草稿")
    ap.add_argument("--corpus", required=True, help="语料目录（.md/.txt，一篇一个文件）")
    ap.add_argument("--engine", required=True, help="引擎目录名，如 mouren-writing")
    ap.add_argument("--label", default=None, help="文体中文名，如 某某体")
    ap.add_argument("--from", dest="start", choices=STAGES, default="stats")
    ap.add_argument("--stats-only", action="store_true")
    ap.add_argument("--prompts-only", action="store_true")
    a = ap.parse_args(argv)

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*-writing", a.engine):
        print("引擎名须形如 xxx-writing", file=sys.stderr); return 2
    if not Path(a.corpus).is_dir():
        print(f"语料目录不存在：{a.corpus}", file=sys.stderr); return 2
    label = a.label or a.engine
    base = OUT / a.engine
    work = base / "work"
    work.mkdir(parents=True, exist_ok=True)
    dest = base / a.engine
    llm = LLM(base / "prompts" if a.prompts_only else None)
    _, fams = library()
    run = lambda s: STAGES.index(s) >= STAGES.index(a.start)
    J = lambda n: work / f"{n}.json"
    load = lambda n: json.loads(J(n).read_text(encoding="utf-8"))
    dump = lambda n, o: J(n).write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")

    docs = load_corpus(a.corpus)
    if len(docs) < MIN_ARTICLES:
        print(f"只有 {len(docs)} 篇可用语料，至少 {MIN_ARTICLES} 篇才能交叉验证", file=sys.stderr); return 2
    if len(docs) < RECOMMENDED:
        print(f"提示：{len(docs)} 篇低于准入线 {RECOMMENDED} 篇，产物只能算试用", file=sys.stderr)

    print("① 统计")
    st = stats(docs) if run("stats") or not J("stats").exists() else load("stats")
    dump("stats", st)
    s = st["sentence"]
    print(f"  {st['articles']} 篇 / {st['chars']} 字；句长均值 {s['mean']}，中位 {s['median']}，"
          f"短句(≤8) {s['short_le8_ratio']:.0%}，长句(≥40) {s['long_ge40_ratio']:.0%}")
    if a.stats_only:
        return 0

    print("② 抽取")
    if run("extract") or not J("candidates").exists():
        cands = extract(docs, llm, label, fams)
        if a.prompts_only:
            print(f"提示词已写到 {llm.prompts_dir}（后续步骤依赖本步结果，先停在这里）"); return 0
        dump("candidates", cands)
    cands = load("candidates")
    fake = sum(not c.get("evidence_found") for c in cands)
    print(f"  {len(cands)} 个候选，证据在原文里找不到而丢弃 {fake} 个")

    print("③ 归并")
    if run("merge") or not J("atoms").exists():
        dump("atoms", merge(cands, llm, label, fams))
    atoms = load("atoms")
    ok = sum(x["status"] == "交叉验证" for x in atoms)
    print(f"  {len(atoms)} 个原子：交叉验证 {ok}，单源 {len(atoms) - ok}，"
          f"与库内同动作 {sum(bool(x.get('same_as')) for x in atoms)}")
    for x in atoms[:20]:
        print(f"   [{x['support']}] {x['family']:<6} {x['name']}" + (f"  ≈{x['same_as']}" if x.get("same_as") else ""))

    print("④ 指纹")
    if run("fingerprint") or not J("fingerprint").exists():
        dump("fingerprint", fingerprint(st, atoms, llm, label))
    fp = load("fingerprint")
    for f in fp:
        print(f"   {f['metric']}：{f['target']}")

    if run("scaffold") or not dest.exists():
        print("⑤ 成稿"); scaffold(a.engine, label, docs, st, atoms, fp, llm, dest)

    print("⑥ 门禁")
    gate = ok >= 8
    print(f"  原子 ≥ 8 条交叉验证：{'过' if gate else '未过'}（{ok}）")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "lint_skill.py"), str(dest), "--strict"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    print("  lint：" + ((r.stdout + r.stderr).strip().splitlines() or ["(无输出)"])[-1])
    print(f"\n草稿：{dest.relative_to(ROOT)}\n下一步：人工核证据 → 补 red-lines.md → 写一篇 examples/ → 跑 eval/ 盲评")
    return 0 if (gate and r.returncode == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
