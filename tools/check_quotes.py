#!/usr/bin/env python3
"""引语核对：成文里的人物引语，必须能在素材里找到出处。

为什么需要这个工具
------------------
活人感引擎有一条红线「无来源案例=造假」。实测 t05 的首版仍然给受访者补了一句
引语、编了一段心理活动、添了个没有来源的数字。checker 给了满分（它不懂语义），
lint 只查格式，红线写在文档里但写的时候并不执行。真正拦住它的是 agent 逐条
对照素材——那是好习惯，不是流程保证。

这个工具把那一遍对照变成机械检查。

用法
----
  python tools/check_quotes.py                 # 检查 demo/*/ 下全部成文
  python tools/check_quotes.py demo/t05/sanlian.md
  python tools/check_quotes.py --strict          # 非逐字也算不合格（可作门禁）
  python tools/check_quotes.py --selftest

退出码：0 无自造 / 1 有疑似自造 / 2 参数错误

判据（三级）
------------
引号里的内容不一定都是人物引语——作者常拿「」给概念命名（「出片」「不划算」）。
所以先分流，再比对：

1. **术语**：短于 8 字且不含人称代词/说话动词 → 视为概念命名，跳过。
2. **人物引语**：其余一律比对。用相似度而非严格子串，因为作者会省字
   （「今天想吃什么」来自「问你今天到底想吃什么」）。
   - ≥ 0.85 视为逐字（容许省略）
   - 0.60–0.85 报 **非逐字**：有出处但改写了，引号里不该改写
   - < 0.60 报 **疑似自造**

已知局限
--------
只查引号内。不在引号里的编造（凭空写「她当时愣住了」）它看不见——
那类只能靠人对照素材。
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUNCT = re.compile(r"[\s，。、；：！？…—－·,.!?;:\"'“”‘’「」『』（）()《》【】\[\]~～]")
QUOTE_RE = re.compile(r"「([^」]{2,})」|『([^』]{2,})』|“([^”]{2,})”|\"([^\"]{2,})\"")
SPEECH = re.compile(r"[我你他她俺咱您]|说|问|道|讲|答|回|称|念叨|吐槽|抱怨|表示|骂|喊")
SPEECH_VERB = re.compile(r"说|问|道|讲|答|回|称|念叨|吐槽|抱怨|表示|喊")
THIRD_PERSON = re.compile(r"他|她|其|该|对方")
SHORT = 8
OK_LINE, WARN_LINE = 0.85, 0.60


def norm(s: str) -> str:
    return PUNCT.sub("", s)


def load_materials():
    """题号 -> (素材片段列表, 人物名列表)。"""
    data = json.loads((ROOT / "eval" / "prompts.json").read_text(encoding="utf-8"))
    out = {}
    for t in data["topics"]:
        frags = [norm(t["prompt"])]
        names = []
        for m in t.get("material", []):
            if m.get("name"):
                names.append(m["name"])
            for k in ("tag", "name", "scene", "quote"):
                if m.get(k):
                    frags.append(norm(m[k]))
        out[t["id"]] = ([f for f in frags if f], names)
    return out


def extract_quotes(text):
    """-> [(引语, 起始位置, 结束位置)]"""
    for m in QUOTE_RE.finditer(text):
        q = next(g for g in m.groups() if g).strip()
        yield q, m.start(), m.end()


def attributed(text, start, end, names, window=30) -> bool:
    """引号附近（同一句内）是否在转述某个具体人物的对话？

    作者大量使用「」给概念命名（「出片」「不划算」「能不能说」），这些不是引语。
    真正危险的是**把话安到某个具体的人头上**——那个人没说过这句话。
    所以只在人名旁边做严格核对。

    三个限定，每条都是实测踩出来的：
    - 只取**同一段落**：姓名常出现在下一段，跨段取窗口会大面积误报。
    - 只取**同一句话**：长段落里往往「某人说：『真引语』」之后，作者又用「」命名
      一个概念；段落级窗口会把它也当成那个人说的话。
    - 排除「施强们」这类**泛指**：加了「们」就不是在引这个人。
    """
    para_start = text.rfind("\n", 0, start) + 1
    para_end = text.find("\n", end)
    para = text[para_start: para_end if para_end != -1 else len(text)]
    off = para_start
    # 句界：往前到最近的句号/问号/叹号
    head = para[: start - off]
    cut = max(head.rfind("。"), head.rfind("！"), head.rfind("？"))
    seg = head[cut + 1:] if cut != -1 else head
    tail = para[end - off:]
    cut2 = min([p for p in (tail.find("。"), tail.find("！"), tail.find("？")) if p != -1] or [len(tail)])
    seg += para[start - off: end - off] + tail[: cut2 + 1]
    for n in names:
        idx = 0
        while (i := seg.find(n, idx)) != -1:
            nxt = seg[i + len(n): i + len(n) + 1]
            if nxt not in "们等这该类伙":      # 泛指不算引用
                return True
            idx = i + len(n)
    # 有人名在前一句、引语这句只剩「她说：「……」」的情况。
    # 只看人名会漏掉这类，而它恰恰是最常见的转述句式，也是编造最容易发生的地方。
    # 但不能只看动词——「说「躺平」比说「…」容易得多」这类作者自己的论述里也有「说」，
    # 所以还要求出现第三人称，才判定为在转述别人。
    if SPEECH_VERB.search(seg) and THIRD_PERSON.search(seg):
        return True
    return False


def lcs_len(a: str, b: str) -> int:
    """最长公共子序列长度。用 DP，字符串都短，够快。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0] * (len(b) + 1)
        for j, cb in enumerate(b, 1):
            cur[j] = prev[j - 1] + 1 if ca == cb else max(prev[j], cur[j - 1])
        prev = cur
    return prev[-1]


def best_ratio(q, frags):
    """作者会省字，所以按「短边的多少被覆盖」算，而不是整串相似度。

    例：成文「今天想吃什么」与素材「问你今天到底想吃什么」，
    整串相似度只有 0.6，但短边 6 个字全被覆盖——那显然是引用，不是编造。
    """
    n = norm(q)
    if not n:
        return 1.0
    if any(n in f for f in frags):
        return 1.0
    best = 0.0
    for f in frags:
        if not f:
            continue
        best = max(best, lcs_len(n, f) / min(len(n), len(f)))
    return best


def is_subsequence(short: str, long: str) -> bool:
    """short 能否由 long 只做删除得到（不改字、不换序）。"""
    it = iter(long)
    return all(ch in it for ch in short)


def classify(q, frags):
    """-> ('ok'|'warn'|'fail'|'term', ratio)

    判据是「引语可以删减，不能改字」：
    - 归一化后是素材某段的子串 → 逐字
    - 是某段的子序列（只删了字，如省略号）→ 省略，仍算有出处
    - 需要换字才能对上 → 非逐字改写（引号里不该改写）
    - 怎么都对不上 → 疑似自造

    为什么不用「相似度 ≥ 0.85 就算逐字」：那样把「半小时」改成「两小时」
    会因为相似度 0.96 而漏掉——恰恰是最该抓的那类篡改。
    """
    n = norm(q)
    if any(n in f for f in frags if n):
        return "ok", 1.0
    for f in frags:
        if len(f) > len(n) and is_subsequence(n, f):
            return "ok", 1.0
    r = best_ratio(q, frags)
    if len(n) < SHORT and not SPEECH.search(q):
        return "term", r
    if r >= WARN_LINE:
        return "warn", r
    return "fail", r


def check(path, mats):
    tid = path.parent.name
    if tid not in mats:
        return None
    frags, names = mats[tid]
    text = path.read_text(encoding="utf-8")
    rows = []
    for q, s, e in extract_quotes(text):
        if not attributed(text, s, e, names):
            rows.append((q, "free", 1.0))
            continue
        rows.append((q,) + classify(q, frags))
    return rows


def main():
    if "--selftest" in sys.argv:
        frags = [norm("他问得很有礼貌，我答得也很有礼貌。回家我在楼下坐了半小时。"),
                 norm("超市太安静了，菜场会跟你吵架，问你今天到底想吃什么。")]
        cases = [
            ("他问得很有礼貌", "ok"),
            ("回家我在楼下坐半小时", "ok"),          # 省一个字，仍算逐字
            ("今天想吃什么", "ok"),                  # 省略「到底」
            ("填了才知道该往哪儿配", "fail"),        # 编的
            ("出片", "term"),                        # 概念命名
            ("我昨天一夜没睡", "fail"),              # 编的第一人称
        ]
        ok = True
        for q, exp in cases:
            got, r = classify(q, frags)
            flag = "✓" if got == exp else "✗"
            if got != exp:
                ok = False
            print(f"  {flag} {q!r:22} 期望 {exp:5} 实际 {got:5} ({r:.2f})")
        print(f"自检：{'通过' if ok else '失败'}（{len(cases)} 例）")
        return 0 if ok else 1

    strict = "--strict" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mats = load_materials()
    files = [Path(a).resolve() for a in args] if args else sorted(
        p for p in (ROOT / "demo").glob("*/*.md") if p.name != "PROMPT.md")
    n_fail = n_warn = n_ok = n_term = n_free = 0
    for f in files:
        rows = check(f, mats)
        if rows is None:
            continue
        fails = [(q, r) for q, k, r in rows if k == "fail"]
        warns = [(q, r) for q, k, r in rows if k == "warn"]
        n_ok += sum(1 for _, k, _ in rows if k == "ok")
        n_term += sum(1 for _, k, _ in rows if k == "term")
        n_free += sum(1 for _, k, _ in rows if k == "free")
        n_fail += len(fails)
        n_warn += len(warns)
        mark = "OK  " if not fails and not warns else ("FAIL" if fails else "WARN")
        try:
            label = f.relative_to(ROOT).as_posix()
        except ValueError:
            label = str(f)
        print(f"  {mark} {label:32} 引语 {len(rows)} 处")
        for q, r in fails:
            print(f"        [{r:.2f}] 疑似自造：{q}")
        for q, r in warns:
            print(f"        [{r:.2f}] 非逐字改写：{q}")
    print(f"\n共 {len(files)} 篇｜逐字 {n_ok}｜术语 {n_term}｜非人物引语 {n_free}｜非逐字 {n_warn}｜疑似自造 {n_fail}")
    if strict and n_warn:
        print("（--strict：非逐字也计为不合格）")
        return 1
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())