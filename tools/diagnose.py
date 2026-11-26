#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风格诊断 v0.1 —— 一篇文章用到了哪些原子族、缺哪几种
====================================================

输入一篇 .md，输出四样东西：

  1. 规模：字数、句数、平均句长
  2. checker 分：generic 一份，给了 --engine 再加一份该引擎的
  3. 命中的原子族估计：用**可判定的表层特征**做启发式
  4. 最缺的三个族 + 对应练习链接

边界（必须先读）
----------------
这是**启发式估计，非人工判断**。它只数表面证据：首句长度、数字、引号、
转折词、排比同构、末句形态、代词与习惯副词……每条规则都在输出里写明
「依据」与「证据」，你可以逐条反驳它。

它做不到的事：
  · 判不出「独有」的 63 个原子（那些要读引擎自己的原子表）
  · 判不出反讽、留白、言外之意——这些没有可靠的表面特征
  · 判不出好坏，只判「有没有这个动作」
  · 对练习册/合集（例如 learn/01-练习-认原子.md）运行，统计对象是全文，
    结果只用于确认工具能跑通，不代表其中任何一段

为什么不叫「评分」：分数会让人以为它知道自己在说什么。

用法
----
    python tools/diagnose.py 稿子.md
    python tools/diagnose.py --engine luxun-writing 稿子.md
    python tools/diagnose.py --json 稿子.md
    python tools/diagnose.py --list-families

数据来源：atoms/index.json（182 个原子 = 18 个族 + 63 个独有）。
退出码：0 = 正常输出；2 = 参数或文件错误。
"""

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

README_LINK = "learn/README.md"
EX01 = "learn/01-练习-认原子.md"
EX02 = "learn/02-练习-仿写.md"
EX03 = "learn/03-练习-组合.md"

# 族 → (练习文件, 锚点, 说明)。锚点与两份练习文件的 ## 标题一致。
PRACTICE = {
    "小处起笔": (EX02, "#小处起笔", "第 1 题"),
    "冷笔白描": (EX02, "#冷笔白描", "第 2 题"),
    "数据压舱": (EX02, "#数据压舱", "第 3 题"),
    "预设驳论": (EX02, "#预设驳论", "第 4 题"),
    "不收的收尾": (EX02, "#不收的收尾", "第 5 题"),
    "正经夸张": (EX02, "#正经夸张", "第 6 题"),
    "换层级": (EX02, "#换层级", "第 7 题"),
    "金句断语": (EX02, "#金句断语", "第 8 题"),
    "自嘲": (EX03, "#练习三", "组合题三"),
    "回环呼应": (EX03, "#练习三", "组合题三"),
    "比喻": (EX03, "#练习二", "组合题二"),
    "分类拆解": (EX03, "#练习四", "组合题四"),
    "号召落点": (EX03, "#练习四", "组合题四"),
    "命名": (EX01, "#q2", "第 2 题"),
    "典型画像": (EX01, "#q2", "第 2 题"),
    "排比/三段": (EX01, "#q9", "第 9 题"),
    "反转揭底": (EX01, "#q11", "第 11 题"),
    "古今对照": (EX01, "#q3", "第 3 题"),
}

# ---------------------------------------------------------------- 词表

EMOTION_WORDS = [
    "感动", "难过", "伤心", "痛苦", "美丽", "伟大", "温暖", "幸福", "激动",
    "绝望", "孤独", "心酸", "震撼", "美好", "悲哀", "凄凉", "欢喜", "愤怒",
    "委屈", "温柔", "心疼", "沉重", "苍凉", "可怜", "可怕", "可惜", "惊人",
]

SELF_MOCK = [
    "惭愧", "心虚", "不懂", "不会", "说错", "没出息", "怂", "认了", "不好意思",
    "丢人", "我也", "我这人", "算不上", "说不好", "不知道", "不敢", "懒得",
    "吃不出来", "不干净", "算不上", "笨", "可笑", "荒唐", "数学不好",
]

SUMMARY_TAIL = [
    "总之", "因此", "所以说", "我们应该", "让我们", "相信", "希望", "必将",
    "意义", "价值", "启示", "展望", "这才是", "这就是", "愿每", "值得",
]

ABSTRACT_WORDS = [
    "时代", "社会", "格局", "认知", "本质", "价值", "意义", "未来", "情怀",
    "使命", "愿景", "力量", "精神", "灵魂", "境界", "高度",
]

CONCRETE_PLACES = [
    "楼下", "单位", "小区", "家里", "厨房", "阳台", "路口", "街上", "店里",
    "摊", "车上", "群里", "会议", "办公室", "饭桌", "门口", "床边", "菜市场",
    "地铁", "公交", "车站", "码头", "渡口", "车间", "工地", "食堂", "教室",
    "冰箱", "抽屉", "床头", "窗外", "院子", "巷子", "街角", "柜台", "桌面",
]

# 强数据：货币、度量、时间。是「可查证、能当论据」的那一类，
# 与「二十个人」「三百年」这种叙述性数量分开算。
RE_STRONG_NUM = re.compile(
    r"[0-9一二三四五六七八九十百千万两]{1,8}(?:元|块|毛|里|米|斤|分钟|小时|岁|升|吨|公斤|平方米|度)"
)
RE_MEASURE = re.compile(
    r"[0-9一二三四五六七八九十百千万两]{1,6}"
    r"(?:个|只|张|条|根|片|棵|双|把|块|间|座|杯|碗|辆|栋|台|件|本|位|名"
    r"|岁|米|分钟|小时|天|年|月|日|次|回|遍|斤|升|元|毛|里)"
)
RE_DIGIT = re.compile(r"\d+(?:\.\d+)?")
RE_QUOTE = re.compile(r"“([^”]{1,12})”|「([^」]{1,12})」")

# 逗号连接的中文长句里，checker 的句子切分只认 。！？，这里沿用它的口径。

# ---------------------------------------------------------------- 加载


def _load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"[error] 读不了 {path}：{exc}")


def load_checker():
    path = HERE / "ai-flavor-checker.py"
    if not path.exists():
        sys.exit(f"[error] 缺少 {path}；diagnose.py 必须和 checker 放在同一目录")
    spec = importlib.util.spec_from_file_location("aifc", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ATOMS = _load_json(ROOT / "atoms" / "index.json")
FAMILY_COUNT = Counter(a["family"] for a in ATOMS)
FAMILY_ENGINES = defaultdict(set)
for _a in ATOMS:
    FAMILY_ENGINES[_a["family"]].add(_a["engine"].replace("-writing", ""))
SHARED_FAMILIES = [f for f, _ in FAMILY_COUNT.most_common() if f != "独有"]

# ---------------------------------------------------------------- 文本准备


def prepare(text):
    """去掉 markdown 骨架，留下正文；返回段落、句子、无空白全文。

    练习文件里的引文块（>）保留文字：诊断一个文件时，我们想知道这个文件
    整体在演示什么动作，而不是替某一段单独打分。
    """
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if s.startswith("#") or re.fullmatch(r"[-*_]{3,}", s):
            continue
        if s.count("|") >= 2:  # 表格行不是散文
            continue
        was_quote = s.startswith(">")
        s = re.sub(r"^>\s*", "", s)
        # 引文块可能是正文（练习材料），也可能是稿头的元信息（题目/时长/试写稿声明）。
        # 后者不参与诊断，否则「首句」会变成一句声明。
        if was_quote and (re.match(r"^(试写稿|题目|时长|场景|原子链|说明|注|引擎产出示例)[：:。，、｜|]", s)
                          or "｜" in s):
            continue
        # 稿尾的仿写声明/免责说明不是正文，否则「末句」会变成一句声明
        if re.match(r"^\*+", s) and re.search(r"(引擎产出示例|试写稿|虚构|待核|原子链)", s):
            continue
        s = re.sub(r"^[-*+]\s+", "", s)
        s = re.sub(r"^\d+[.、]\s*", "", s)
        lines.append(s)
    body = "\n".join(lines)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"[*_`]{1,3}", "", body)
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    return body, paras


def split_sentences(checker, paras):
    out = []
    for p in paras:
        out.extend(checker.split_sentences(p))
    return out


def snippet(s, n=26):
    """截到标点为止，别把一句话切成半截引号。"""
    s = re.sub(r"\s+", "", str(s)).strip()
    if len(s) <= n:
        return s
    head = s[:n]
    cut = max(head.rfind(p) for p in "。！？；，、")
    if cut >= n // 2:
        return head[:cut + 1] + "…"
    return head + "…"


def ratio(n, chars):
    return n * 1000.0 / max(chars, 400)


# ---------------------------------------------------------------- 规则
# 每条规则返回 (0-3 的强度, 证据列表, 依据一句话)。
# 强度：0 无证据 / 1 弱 / 2 中 / 3 强。阈值故意写得保守，宁可漏检。


def detect_small_start(ctx):
    first = ctx["first_sent"]
    if not first:
        return 0, [], "首句为空"
    n = len(re.sub(r"\s+", "", first))
    anchors = []
    m = RE_MEASURE.search(first)
    if m:
        anchors.append(f"数量词「{m.group(0)}」")
    for w in CONCRETE_PLACES:
        if w in first:
            anchors.append(f"场景词「{w}」")
            break
    q = RE_QUOTE.search(first)
    if q:
        anchors.append(f"引号里的具体物「{q.group(1) or q.group(2)}」")
    # 首句若是纯抽象判断（「在当今这个时代…」），有量词也不算小处起笔
    if any(w in first for w in ABSTRACT_WORDS) and not any(w in first for w in CONCRETE_PLACES):
        return 0, [snippet(first)], "首句是抽象判断，没有可指认的小处"
    if not anchors:
        return 0, [snippet(first)], "首句没有可指认的实物、数量或场景"
    if n > 40:
        return 1, [snippet(first)] + anchors, "首句有实物，但太长，起笔被铺陈冲淡"
    score = 3 if n <= 20 else 2
    return score, [snippet(first)] + anchors, "族定义＝从极小、具体的东西切入；首句短且含实物/场景即表层证据"


def detect_self_mock(ctx):
    """贬己词必须和「我/咱」在同一句、相距不远才算；「不知道」单独出现不算自嘲。"""
    hits = []
    for w in SELF_MOCK:
        if re.search(rf"(?:我|咱)[^。！？]{{0,16}}{w}|{w}[^。！？]{{0,16}}(?:我|咱)", ctx["flat"]):
            hits.append(w)
    if not hits:
        return 0, [], "没有第一人称把自己放低的词（贬己词须与「我」同句）"
    sents = [s for s in ctx["sents"] if any(w in s for w in hits) and ("我" in s or "咱" in s)]
    score = min(3, len(hits))
    return score, [snippet(s) for s in sents[:2]], "族定义＝写笨写怂、承认自己在被批评的人群里；表层证据＝第一人称＋贬己词同句"


def detect_open_end(ctx):
    last = ctx["last_sent"]
    if not last:
        return 0, [], "末句为空"
    n = len(re.sub(r"\s+", "", last))
    bad = [w for w in SUMMARY_TAIL if w in last]
    if bad or n > 30:
        return 0, [snippet(last)], (
            "末句含总结/升华词" if bad else "末句过长，像在交代结论")
    has_q = last.rstrip().endswith(("？", "?"))
    has_action = bool(re.search(
        r"(走|坐|站|看|放|收|关|开|递|拿|点|笑|睡|吃|喝|数|抬|低|转|推|"
        r"拉|按|停|回|去|来|说|问|答|响|亮|落|飘|到|进|出|起|上|下)", last))
    if not (has_q or has_action):
        return 1, [snippet(last)], "末句短，但没有动作、画面或问句"
    score = 3 if n <= 25 else 2
    return score, [snippet(last)], "族定义＝结尾不升华、停在动作/画面/问句上；末句短且无总结词即表层证据"


def detect_aphorism(ctx):
    cands = []
    for s in ctx["sents"]:
        t = s.strip()
        if len(re.sub(r"\s+", "", t)) > 34:
            continue
        if re.search(r"(不是|并非|而是|就是|才是|无非|不过是|说到底)", t):
            cands.append(t)
    if not cands:
        return 0, [], "没有 ≤20 字、可独立成立的判断句"
    score = 3 if len(cands) >= 2 else 2
    return score, [snippet(c) for c in cands[:3]], "族定义＝压成可单独转发的断语；表层证据＝短判断句（不是/就是/才是/说到底）"


def detect_parallel(ctx):
    checker = ctx["checker"]
    run = checker.max_parallel_run(ctx["sents"])
    has_three = bool(re.search(
        r"(一是.{0,30}二是.{0,30}三是|第一[，,].{0,40}第二[，,].{0,40}第三"
        r"|从.{1,10}到.{1,10}[，,].{0,8}从.{1,10}到)", ctx["flat"]))
    if run >= 3:
        return 3, [f"最长同构连续句 {run} 句"], "族定义＝同构三项连用；表层证据＝连续同构句（checker 的 parallel_run）"
    if has_three:
        return 2, ["出现「一是/第一/从…到…」三项枚举"], "三项枚举是同构排比的弱证据，结构未必完全镜像"
    return 0, [], "既无连续同构句，也无三项枚举"


def detect_classify(ctx):
    markers = re.findall(
        r"(第一[，,、]|第二[，,、]|第三[，,、]|其一[，,、]|其二[，,、]"
        r"|一是|二是|三种|两类|分成.{0,6}种|按.{0,8}分)", ctx["flat"])
    if not markers:
        return 0, [], "没有互斥枚举的标记"
    distinct = len(set(m.replace("，", "").replace(",", "").replace("、", "") for m in markers))
    score = 3 if distinct >= 3 or re.search(r"(三种|两类|分成.{0,6}种)", ctx["flat"]) else 2
    return score, ["枚举标记：" + "、".join(sorted(set(markers))[:4])], "族定义＝按一个标准拆成互斥条目；表层证据＝第一/第二/一是/二是/三种"


def detect_turn(ctx):
    """只认显式翻面词。「但是/可是」是普通转折，单独出现不算揭底——否则人人都有。"""
    pairs = re.findall(
        r"(原来|没想到|谁知|偏偏|结果|反而|竟然|不料|岂料)[^。！？]{0,30}"
        r"(不|没|却|倒|反而|竟然|原来|只)", ctx["flat"])
    if not pairs:
        return 0, [], "没有「原来/没想到/反而」这类显式翻面词"
    score = 3 if len(pairs) >= 2 else 2
    ev = [f"{a}…{b}" for a, b in pairs[:3]]
    return score, ev, "族定义＝预期翻面；表层证据＝原来/没想到/反而 + 30 字内的否定或转折"


def detect_reframe(ctx):
    """尺度切换。正则里排掉句号，避免把「从头再数。我在旁边看」当成「从…看」。"""
    pats = [
        r"按[^。！？]{0,10}算", r"要是按", r"放到[^。！？]{0,12}(?:看|里|中)",
        r"从[^。！？]{1,10}(?:角度|层面|尺度|看)", r"换个(?:说法|问法|算法)",
        r"与其[^。！？]{0,20}不如", r"一辈子", r"十年", r"历史上",
        r"(?:这么|那么)[大小]", r"很小很小", r"整座", r"整个城市", r"几百户",
    ]
    hits = []
    for p in pats:
        hits += re.findall(p, ctx["flat"])
    if not hits:
        return 0, [], "没有换尺度/换层级的标记"
    score = 3 if len(set(hits)) >= 2 else 2
    return score, ["尺度词：" + "、".join(sorted(set(hits))[:4])], (
        "族定义＝换一个尺度或层级重看；表层证据＝按…算/放到…里/与其…不如/这么大…那么小")


def detect_past_now(ctx):
    past = re.findall(r"(古人|古书|旧书|从前|以前|当年|那时|清朝|小时候|过去|多年前|老辈)", ctx["flat"])
    now = re.findall(r"(如今|现在|今天|这几年|眼下|当下|现在的人)", ctx["flat"])
    if not past or not now:
        return 0, [], "过去词与现在词没有同时出现"
    score = 3 if len(past) + len(now) >= 3 else 2
    return score, [f"过去：{'、'.join(sorted(set(past))[:3])}", f"现在：{'、'.join(sorted(set(now))[:3])}"], (
        "族定义＝拿旧事照今天；表层证据＝过去词与现在词同篇共现")


def detect_concede(ctx):
    quote = re.findall(
        r"(有人说|有人会问|你可能|你也许|诚然|固然|退一步|这话.{0,8}(?:不错|有道理|真的|对)"
        r"|一半道理|不是没有道理)", ctx["flat"])
    rebut = re.findall(r"(但|可|不过|然而)", ctx["flat"])
    if not quote:
        return 0, [], "没有替对方说话的引述或让步"
    score = 3 if quote and rebut else 2
    return score, [f"让步：{'、'.join(sorted(set(quote))[:3])}"], (
        "族定义＝先替对方说全再回答；表层证据＝有人说/这话有道理 + 转折")


def detect_data(ctx):
    """数字要能当论据才算：账目/比较/单位时间信号 + 强数字（货币、度量、时间）。

    纯叙述数量（二十个人、三百年）只给弱证据。这是启发式，「是否真的承担论据」
    仍需人工看一眼——工具只负责把可疑的地方指出来。
    """
    generic = RE_MEASURE.findall(ctx["flat"])
    strong = RE_STRONG_NUM.findall(ctx["flat"])
    arabic = RE_DIGIT.findall(ctx["flat"])
    n = len(generic)
    if n == 0 and not arabic:
        return 0, [], "没有数字或数量词"
    d = ratio(n, ctx["chars"])
    argue = re.findall(
        r"(涨|降|够买|一算|算下来|平均|百分之|倍|账|值多少|还剩|占一截|占一大截|够不够|每分钟|每小时|一年)",
        ctx["flat"])
    hard = len(strong) + len(arabic)
    if argue and hard >= 2:
        score = 3
    elif argue or hard >= 4:
        score = 2
    else:
        score = 1
    ev = [f"数字/数量 {n} 处（约 {d:.1f}/千字），可当论据的 {hard} 处",
          ("比较/账目信号：" + "、".join(sorted(set(argue))[:4])) if argue else "没有比较/账目信号"]
    return score, ev, (
        "族定义＝用具体数字替代形容词；表层证据＝货币/度量/时间类数字 + 比较或账目信号")


def detect_deadpan(ctx):
    """两种变体：推演链（假如…那么）与正话反说（这真是一种…）。"""
    chain = re.findall(
        r"(假如|如果[^。！？]{0,18}那么|按照这个道理|再往下推|推到最后|不妨设想|试想)",
        ctx["flat"])
    if chain:
        score = 3 if len(chain) >= 3 else 2
        return score, ["推演词：" + "、".join(sorted(set(chain))[:4])], (
            "族定义＝用认真语气把事推到荒唐处；表层证据＝假如/按照这个道理/推到最后")
    irony = re.findall(r"(这真是一种|好一个|真是一种了不起)", ctx["flat"])
    if irony:
        return 2, ["正话反说标记：" + "、".join(sorted(set(irony))[:3])], (
            "正话反说变体：用夸奖的语气写批评；表层证据＝「这真是一种…」后接正面大词")
    return 0, [], "既无「假如…那么」推演链，也无正话反说的标记"


def detect_metaphor(ctx):
    hits = re.findall(r"(好像|好比|似的|如同|仿佛|犹如|像)", ctx["flat"])
    if not hits:
        return 0, [], "没有喻词"
    n = len(hits)
    score = 1
    if n >= 5:
        score = 3
    elif n >= 3:
        score = 2
    return score, [f"喻词 {n} 处"], "族定义＝用另一领域的具体物照亮；表层证据＝像/好像/好比/似的"


def detect_cold(ctx):
    """白描＝不评价。零情绪词、句子短、有具体数字，三条同时成立才算强。"""
    emo = [w for w in EMOTION_WORDS if w in ctx["flat"]]
    nums = len(RE_DIGIT.findall(ctx["flat"]) + RE_MEASURE.findall(ctx["flat"]))
    avg = ctx["avg_len"]
    if emo or avg > 30:
        score = 1 if len(emo) <= 2 else 0
        return score, [f"情绪/评价词：{'、'.join(emo[:4]) or '无'}；均句长 {avg:.1f}"], (
            "族定义＝只写名词动词数字，不加形容词与评价；情绪词多或句子过长即反证")
    if nums >= 2 and avg <= 24:
        return 3, [f"情绪词 0；数字/数量 {nums} 处；均句长 {avg:.1f}"], (
            "族定义＝白描；表层证据＝零情绪词、有具体数字、均句长 ≤24")
    if avg <= 28:
        return 2, [f"情绪词 0；均句长 {avg:.1f}"], "白描的弱证据：没有评价词，但句子偏长或具体物证不足"
    return 0, [f"情绪词 0，但均句长 {avg:.1f}"], "没有评价词，但句子太长，不像白描的短句节奏"


def detect_naming(ctx):
    named = re.findall(r"(?:叫|管.{0,6}叫|所谓|人称)“([^”]{2,10})”", ctx["flat"])
    if not named:
        quoted = [m.group(1) or m.group(2) for m in RE_QUOTE.finditer(ctx["flat"])]
        rep = [q for q in quoted if ctx["flat"].count(f"“{q}”") >= 2]
        if rep:
            return 2, [f"反复使用的引号词「{rep[0]}」"], "反复出现的引号词是「命名」的弱证据：名字被当成术语用了"
        return 0, [], "没有起名动作，也没有被反复使用的引号术语"
    return 3, [f"命名「{n}」" for n in named[:3]], "族定义＝给一种人/心态起名；表层证据＝叫“X”/所谓“X”"


def detect_portrait(ctx):
    generic = re.findall(r"(这种人|有一种人|这类人|他们|她们|有的人)", ctx["flat"])
    habit = re.findall(r"(总是|从不|每次都|每天|天天|每逢|向来|老是|一.{1,6}就)", ctx["flat"])
    detail = re.findall(r"(岁|半只|穿着|戴着|个子|脸色|嗓子|头发|袖|鞋|手|脚|眼)", ctx["flat"])
    if generic and len(habit) >= 2:
        return 3, [f"类指 {len(generic)} 处，习惯副词 {len(habit)} 处"], "族定义＝几笔立住「这样的人」；表层证据＝类指 + 习惯副词"
    if generic and habit:
        return 2, [f"类指，习惯副词 {len(habit)} 处"], "有类指但习惯动作少，画像还没立住"
    # 单个人物画像：他/她 + 外貌/身体细节 + 习惯动作
    if re.search(r"[他她]", ctx["flat"]) and len(detail) >= 2 and habit:
        return 2, [f"人物细节 {len(detail)} 处，习惯副词 {len(habit)} 处"], (
            "单个人物画像：他/她 + 外貌细节 + 习惯动作（「六十来岁，左耳缺了半只」）"
        )
    if generic:
        return 1, ["只有类指"], "只有类指，没有可指认的动作习惯"
    return 0, [], "没有「这种人/他们」式的类指，也没有他/她的外貌与习惯细节"


def detect_call(ctx):
    tail = "".join(ctx["sents"][-2:]) if len(ctx["sents"]) >= 2 else ctx["last_sent"]
    we = bool(re.search(r"(我们|大家|你我|每个人|愿意|没空|读者)", tail))
    modal = bool(re.search(r"(应该|要|不妨|请|让|试一试|一起|别|不要|可以|能|会)", tail))
    if we and modal:
        return 3, [snippet(tail)], "族定义＝结尾回到「我们」与可做的行动；表层证据＝末两句同时有「我们/大家」和建议词"
    if we or modal:
        return 1, [snippet(tail)], "结尾有「我们」或建议词之一，但没同时指向行动"
    return 0, [], "结尾没有回到「我们」与行动"


def detect_ring(ctx):
    """回环只在首尾各取 20%：同一术语（引号词）或同一四字短语再现。

    不收「。我妈」这类带标点的三字串——那是分词噪声，不是母题。
    """
    if ctx["chars"] < 120 or len(ctx["paras"]) < 2:
        return 0, [], "篇幅太短或段落太少，谈不上回环"
    head = ctx["flat"][: max(60, int(ctx["chars"] * 0.2))]
    tail = ctx["flat"][-max(60, int(ctx["chars"] * 0.2)):]
    terms = []
    for m in RE_QUOTE.finditer(ctx["flat"]):
        terms.append(m.group(1) or m.group(2))
    shared = [t for t in set(terms) if len(t) >= 2 and t in head and t in tail]
    if shared:
        return 3, [f"首尾同现的术语「{shared[0]}」"], (
            "族定义＝前文元素后文再响；表层证据＝同一引号术语在首尾两段都出现")

    plain = re.sub(r"[，。！？、；：“”「」（）\s]", "", ctx["flat"])
    grams = Counter(plain[i:i + 4] for i in range(0, len(plain) - 3))
    phrases = [g for g, n in grams.items() if n >= 2 and g in head and g in tail]
    if phrases:
        return 2, [f"首尾同现的短语「{phrases[0]}」"], "同一四字短语在首尾两段都出现，是回环的弱证据"
    return 0, [], "首尾没有共享的术语或短语"


RULES = [
    ("小处起笔", detect_small_start),
    ("自嘲", detect_self_mock),
    ("不收的收尾", detect_open_end),
    ("金句断语", detect_aphorism),
    ("排比/三段", detect_parallel),
    ("分类拆解", detect_classify),
    ("反转揭底", detect_turn),
    ("换层级", detect_reframe),
    ("古今对照", detect_past_now),
    ("预设驳论", detect_concede),
    ("数据压舱", detect_data),
    ("正经夸张", detect_deadpan),
    ("比喻", detect_metaphor),
    ("冷笔白描", detect_cold),
    ("命名", detect_naming),
    ("典型画像", detect_portrait),
    ("号召落点", detect_call),
    ("回环呼应", detect_ring),
]


# ---------------------------------------------------------------- 诊断


def build_context(checker, text):
    body, paras = prepare(text)
    sents = split_sentences(checker, paras)
    flat = re.sub(r"\s+", "", body)
    chars = len(flat)
    first_para_sents = split_sentences(checker, [paras[0]]) if paras else []
    last_para_sents = split_sentences(checker, [paras[-1]]) if paras else []
    return {
        "checker": checker,
        "body": body,
        "paras": paras,
        "sents": sents,
        "flat": flat,
        "chars": chars,
        "avg_len": chars / max(1, len(sents)),
        "first_sent": first_para_sents[0] if first_para_sents else (sents[0] if sents else ""),
        "last_sent": last_para_sents[-1] if last_para_sents else (sents[-1] if sents else ""),
    }


def diagnose(path, engine=None):
    checker = load_checker()
    text = path.read_text(encoding="utf-8", errors="replace")
    ctx = build_context(checker, text)
    if ctx["chars"] == 0:
        return None

    cfg = checker.load_profiles()
    engines = ["generic"]
    if engine and engine != "generic":
        if engine not in cfg["profiles"]:
            sys.exit(f"[error] 未知引擎：{engine}\n可用：{', '.join(cfg['profiles'])}")
        engines.append(engine)
    scores = {}
    for key in engines:
        res = checker.score_text(text, cfg["profiles"][key])
        scores[key] = {
            "total": res["total"],
            "passed": res["passed"],
            "grade": checker.grade(res["total"], cfg["profiles"][key]),
            "pass_below": cfg["profiles"][key]["pass_below"],
            "label": cfg["profiles"][key]["label"],
        }

    found = {}
    for fam, fn in RULES:
        score, evidence, basis = fn(ctx)
        if score > 0:
            found[fam] = {"score": score, "evidence": evidence, "basis": basis}

    # 缺口：族内原子数（跨引擎通用度的代理）× 未命中强度
    missing = []
    for fam in SHARED_FAMILIES:
        s = found.get(fam, {}).get("score", 0)
        gap = FAMILY_COUNT[fam] * (3 - s)
        if gap > 0:
            missing.append((gap, FAMILY_COUNT[fam], s, fam))
    missing.sort(key=lambda x: (-x[0], -x[1], x[3]))

    return {
        "path": str(path),
        "chars": ctx["chars"],
        "sentences": len(ctx["sents"]),
        "avg_len": round(ctx["avg_len"], 1),
        "scores": scores,
        "found": found,
        "missing": missing,
        "family_total": len(SHARED_FAMILIES),
    }


def practice_line(fam):
    f, anchor, label = PRACTICE.get(fam, (EX01, "", ""))
    return f"{f}{anchor}（{label}）" if label else f


def report(result):
    print(f"== 风格诊断：{result['path']}")
    print(f"   规模：{result['chars']} 字 / {result['sentences']} 句 / 平均句长 {result['avg_len']} 字")
    for key, s in result["scores"].items():
        mark = "通过" if s["passed"] else "未过"
        print(f"   checker（{key}，门槛 <{s['pass_below']}）：{s['total']}/100 → {s['grade']}（{mark}）")
    print("   说明：以下族命中是**启发式估计，非人工判断**；每条给出依据与证据，可逐条反驳。")
    print()

    found = sorted(result["found"].items(), key=lambda kv: (-kv[1]["score"], kv[0]))
    print(f"命中（{len(found)}/{result['family_total']} 个共用族，按强度）：")
    if not found:
        print("   （无）——可能整篇都在铺陈，没有可判定的原子动作；也可能是本工具漏检。")
    for fam, info in found:
        star = "强" if info["score"] >= 3 else ("中" if info["score"] == 2 else "弱")
        print(f"   [{star}] {fam}")
        print(f"         依据：{info['basis']}")
        if info["evidence"]:
            print("         证据：" + "；".join(str(e) for e in info["evidence"][:3]))
    print()
    print("   注：「独有」的 63 个原子不在此估计范围内——那要读各引擎自己的原子表"
          f"（见 atoms/LIBRARY.md）。")

    print()
    print("你最缺的三个族（排序＝族内原子数 × 未命中强度；只算表面可判的 18 个共用族）：")
    for i, (_gap, n, s, fam) in enumerate(result["missing"][:3], 1):
        state = "未检出" if s == 0 else f"仅弱证据（强度 {s}/3）"
        eng = len(FAMILY_ENGINES[fam])
        print(f"   {i}. {fam}（{n} 个原子，{eng} 个引擎用到；{state}）")
        print(f"      练：{practice_line(fam)}")
    if len(result["missing"]) < 3:
        print("   （缺口不足三个：18 个共用族都有证据，下一步该看密度与顺序，而不是再找族。）")

    print()
    print("下一步：把这三族各写 100 字（用上面的练习），再用本工具复测；")
    print(f"       三条学习线见 {README_LINK}。诊断只认表层特征，不替你判断好坏。")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="风格诊断：原子族启发式估计（非人工判断）")
    ap.add_argument("file", nargs="?", help="待诊断的 .md")
    ap.add_argument("--engine", default=None,
                    help="额外跑一份该引擎的 checker 分，见 tools/ai-flavor-checker.py --list-engines")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--list-families", action="store_true", help="列出族与原子数")
    args = ap.parse_args(argv)

    if args.list_families:
        for fam in SHARED_FAMILIES:
            eng = "、".join(sorted(FAMILY_ENGINES[fam]))
            print(f"{fam:<10} {FAMILY_COUNT[fam]:>2} 个原子  {eng}")
        print(f"{'独有':<10} {FAMILY_COUNT['独有']:>2} 个原子  （不参与估计）")
        return 0

    if not args.file:
        ap.print_help()
        return 2

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"[error] 找不到文件：{path}")

    result = diagnose(path, args.engine)
    if result is None:
        print(f"== {path}\n   空输入（去掉 markdown 骨架后没有正文），跳过")
        return 0

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report(result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
