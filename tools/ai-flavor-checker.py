#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 味检测器 —— 把反 AI 味红线变成可执行的评分
（v0.1 · 写作引擎库评测器原型）

用法:
  python3 ai-flavor-checker.py <文件路径>
  python3 ai-flavor-checker.py --stdin < input.txt

输出: 总分 0-100（越高越 AI 味）+ 六维报告 + 行级命中

维度:
  [书面腔]    官腔/书面连词密度（值得注意的是/综上所述/赋能/抓手…）
  [空转词]    抽象名词密度（价值/意义/格局/认知…）
  [排比堆叠]  连续排比（句尾同构 ≥3）+ 引号金句密度
  [破公式]    "不是…而是…" 频率
  [长句]      >60 字句子
  [口语抵充]  口语标记（说白了/其实/咱/呗…）——正分,抵消 AI 味

局限: 面向活人感叙事/新媒体文。官方体/论文等文体自带书面腔,
      检测结果不代表该文体失败（见 tools/README.md 校准说明）。
"""
import os
import re
import sys

# —— 词表（保守收录，宁可漏检不误报）——
OFFICIAL_WORDS = [
    "总而言之", "综上所述", "值得注意的是", "不难发现", "显而易见", "毋庸置疑",
    "众所周知", "与此同时", "由此可见", "归根结底", "换而言之", "换言之",
    "从某种意义上说", "在一定程度上", "不可否认", "然而", "此外", "因此",
    "从而", "进而", "赋能", "抓手", "闭环", "底层逻辑", "颗粒度", "对齐",
    "重构", "颠覆", "重塑", "范式", "彰显", "这一", "进行", "作出",
]
ABSTRACT_WORDS = [
    "价值", "意义", "未来", "格局", "认知", "智慧", "本质", "真相", "层面",
    "维度", "系统", "力量", "精神", "灵魂", "境界", "高度", "情怀", "初心",
    "远方", "使命", "愿景", "担当", "责任", "人生", "生命", "时代",
]
COLLOQUIAL_MARKS = [
    "说白了", "就是说", "怎么说呢", "其实", "反正", "的事儿", "还挺", "确实",
    "算了吧", "搞", "整", "扯", "哥们", "呗", "嘛", "哦", "嗯", "咱",
]

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[。！？!?])', text) if s.strip()]

def count_hits(text, words):
    return {w: text.count(w) for w in words if text.count(w) > 0}

def max_parallel_run(sentences):
    """连续句尾同构的最大长度（≥3 即排比堆叠嫌疑）"""
    tails = []
    for s in sentences:
        m = re.search(r'([^，。！？]{1,3})[。！？]?$', s)
        tails.append(m.group(1)[-1] if m else "")
    run = best = 0
    for i in range(1, len(tails)):
        run = run + 1 if tails[i] and tails[i] == tails[i-1] else 0
        best = max(best, run)
    return best + 1 if best else 0

def main():
    if len(sys.argv) > 1 and sys.argv[1] != "--stdin":
        text = open(sys.argv[1], encoding="utf-8").read()
    else:
        text = sys.stdin.read()
    text = re.sub(r'\s+', '', text)
    if not text:
        print("empty input"); return

    sentences = split_sentences(text)
    chars = len(text)
    nsent = len(sentences) or 1
    per1k = 1000.0 / chars if chars else 0

    oh = count_hits(text, OFFICIAL_WORDS)
    ah = count_hits(text, ABSTRACT_WORDS)
    ch = count_hits(text, COLLOQUIAL_MARKS)
    n_off = sum(oh.values())
    n_abs = sum(ah.values())
    n_col = sum(ch.values())
    n_quote = len(re.findall(r'[“「]', text))
    n_par = max_parallel_run(sentences)
    n_nb = len(re.findall(r'不是[^。]{1,30}而是', text))
    n_dash = len(re.findall(r'——', text))
    longs = [s for s in sentences if len(s) > 60]

    # —— 评分（各维 ≤ 上限，总分 100）——
    s_off = min(30, int(n_off * 4 * per1k))          # 书面腔 0-30
    s_abs = min(15, int(n_abs * 2 * per1k))          # 空转词 0-15
    s_par = min(15, int(n_par >= 3) * 6 + min(9, int(n_quote * 1.2 * per1k)))  # 排比+金句堆叠 0-15
    s_nb  = min(10, n_nb * 3)                         # 破公式 0-10
    s_long = min(15, int(len(longs) * 2.5))           # 长句 0-15
    s_col = min(15, int(n_col * 2 * per1k))           # 口语抵充 0-15
    total = max(0, min(100, s_off + s_abs + s_par + s_nb + s_long - s_col))

    level = ("活人感" if total < 30 else
             "轻度 AI 味" if total < 50 else
             "明显 AI 味" if total < 70 else "AI 味爆表")

    print(f"总分: {total}/100  → {level}")
    print(f"规模: {chars} 字 / {nsent} 句")
    print("-" * 44)
    print(f"[书面腔] {s_off:>2}/30  命中 {n_off} 次: {top(oh, 5)}")
    print(f"[空转词] {s_abs:>2}/15  命中 {n_abs} 次: {top(ah, 5)}")
    print(f"[排比堆叠] {s_par:>2}/15  句尾同构最长 {n_par} 句, 引号金句 {n_quote} 处, 破折号 {n_dash}")
    print(f"[破公式] {s_nb:>2}/10  '不是…而是…' {n_nb} 次")
    print(f"[长句]   {s_long:>2}/15  >60字 {len(longs)} 句")
    print(f"[口语抵充] {s_col:>2}/15  口语标记 {n_col} 次 {top(ch, 4)}")
    print("-" * 44)
    if longs:
        print(f"长句示例: {longs[0][:50]}…")

def top(d, k):
    if not d: return "-"
    return " ".join(f"{w}×{n}" for w, n in sorted(d.items(), key=lambda x: -x[1])[:k])

if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # 配合 head 等截断管道时安静退出
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except OSError:
            pass
        sys.exit(0)