# tools · 评测与治理

> 评测器是「教人写作」产品的核心反馈环——写完不是结束，打过分才是开始。
> 但打分必须可信，否则它只是一个更快的偏见。

## 三个工具

| 工具 | 干什么 | 状态 |
|---|---|---|
| `ai-flavor-checker.py` | 给一段文本打 AI 味分（按引擎） | v0.2 |
| `lint_skill.py` | 检查一个引擎是否符合 `SPEC.md`（E1–E11） | v0.2 |
| `check_quotes.py` | 核对人物引语是否真出自素材（查编造与篡改） | v0.1 |
| `corpus_stats.py` | 语料统计（句长/标点/词表）→ `corpus/<engine>/语言DNA.md` | v0.1 |
| `rewrite_hints.py` | 行级改写建议：哪一句、什么问题、怎么改 | v0.1 |
| `build_articles.py` | 把引擎 `examples/*.md` 生成为官网文章页 | — |
| `build_compare.py` | 把 `demo/<题号>/` 的四版生成为同题对照页 | — |
| `run_prompts.py` | 按各引擎 `test-prompts.json` 的断言核对 `examples/` 产出（`--all`） | v0.1 |
| `diagnose.py` | 诊断一篇稿子：命中的原子族估计 + 最缺的三族 + 练习链接 | v0.1 |
| `tests/test_checker.py` | checker 的回归测试 | v0.2 |

## ai-flavor-checker.py v0.2

```bash
python3 tools/ai-flavor-checker.py 你的文章.md
python3 tools/ai-flavor-checker.py --engine sanlian-writing 你的文章.md
python3 tools/ai-flavor-checker.py --list-engines
python3 tools/ai-flavor-checker.py --selftest
python3 tools/ai-flavor-checker.py --json --engine feature-writing a.md b.md
```

退出码：`0` 全部过门槛，`1` 有文本没过，`2` 参数错。**可以当门禁用**（v0.1 恒为 0）。

### v0.1 → v0.2 修了什么

v0.1 有一个自相矛盾的毛病：它惩罚了三家引擎自己要求的装置。

| 问题 | v0.1 | v0.2 |
|---|---|---|
| 引号访谈 | 按「引号金句密度」扣分（最多 9 分） | 活人感引擎里是 **reward 2.0**（加分），其它引擎中性 |
| 「不是A而是B」 | 按「破公式」扣分（最多 10 分） | 活人感／官方体 **豁免**（这是原子１／原子 6），特稿保留 0.8 |
| 因此／然而／此外 | 与「赋能」「抓手」同罪 | 拆成 HARD／SOFT 两档，SOFT 权重 0.3 倍 |
| 长句 | 绝对条数（6 句＝满分，与篇幅无关） | 长句占句数比（长度无关） |
| 短文本 | 130 字里一个「因此」＝ 23 分 | 不足 400 字按 400 归一 |
| 门槛 | 全局 30 | 按引擎：活人感 30／特稿 30／**官方体 45** |
| 排比检测 | 只看句尾字，三句都以「了」结尾就误报 | 句尾相同 **且** 长度接近 |
| 测试 | 无 | 17 条断言（`tests/test_checker.py`） |

### 实测基准

| 样本 | v0.2 分 | 判定 |
|---|---|---|
| 人类散文（修鞋匠段落，140 字） | ≈ 0–5 | 通过 |
| 合成 AI 腔（108 字，含 6 个 HARD 词） | ≈ 60 | AI 味爆表 |

> 上表是按公式手算的预期值，不是运行结果——本仓库的代码在无 Python 环境下写成。
> **合并前请先跑 `--selftest`**，它会用同样两段样本自行验证；不符就说明词表或权重坏了。

**全量校准**：把 21 篇原文放进 `tools/tests/fixtures/local/`（不入库，见
`sources/INDEX.md` 第四节），`test_checker.py` 会逐篇断言「原文必须过自家门槛」。
这是 checker 最重要的一条断言：**原文都过不了自己的门槛，说明门槛定错了，
不是文章有问题。**

### 为什么不用 LLM 打分

LLM 打分不可解释、不可复现、逐次成本高，而且它会被自己的稿子说服。
词表＋密度的路线没错，v0.1 错在校准——校准能修，路线不用换。

## lint_skill.py

```bash
python3 tools/lint_skill.py --all
python3 tools/lint_skill.py sanlian-writing --strict
python3 tools/lint_skill.py --repo
```

检查 10 项（E1–E10）：frontmatter 完整、name 与目录一致、description 长度、
必需七节齐全、体积、references 指针、无版本记录小节、无 `.backup/`、无语料全文、
`examples/` 有完整产出。

`--strict` 让警告也算失败，用作 USD 准入线（见 `CONTRIBUTING.md`）。

## 词表哲学

**保守收录，宁可漏检不误报。** 词表即知识——每次实战发现新的 AI 腔词，
直接追加到 `engine_profiles.json`，并带一个会因此失败的测试用例。

HARD 档（零容忍）是真正暴露「不是人在写」的词：赋能、抓手、闭环、底层逻辑、
颗粒度、对齐、范式、彰显、重塑、颠覆、综上所述、值得注意的是、不难发现……
SOFT 档（存在合法）是正常中文连接词：因此、然而、此外、从而、进而、进行、作出。

把这两档混在一起，是 v0.1 最大的判断错误。

## check_quotes.py：查引语是不是编的

`ai-flavor-checker` 不懂语义，`lint_skill` 只查格式。所以「有没有编造」这一条
靠人。实测就出过：某引擎首版给受访者补了一句没说过的话，checker 给了满分。

`check_quotes.py` 把那一遍人工对照变成机械检查。判据是**引语可以删减，不能改字**：

| 情况 | 判定 |
|---|---|
| 归一化后是素材某段的子串 | 逐字 |
| 是某段的子序列（只删了字，如省略） | 省略，算有出处 |
| 需要换字才对得上（如「半小时」→「两小时」） | **非逐字** |
| 怎么都对不上 | **疑似自造** |

只核对**被安到具体人物头上**的引语（人名或「他说/她问」在同一句内）。
作者用「」给概念命名（「出片」「能不能说」）不算引语，不核对。

```bash
python3 tools/check_quotes.py            # 检查 demo/ 全部产出
python3 tools/check_quotes.py --strict   # 非逐字也算不合格，可作门禁
python3 tools/check_quotes.py --selftest
```

20 篇实测：疑似自造 0，非逐字 4（都是「20 岁」对「二十岁」这类数字写法差异）。
注入验证过三种篡改——编造整句、改数字、改一个词——全部能抓到。

**局限**：只查引号内。不在引号里的编造（凭空写「她当时愣住了」）它看不见。

## run_prompts.py

```bash
python3 tools/run_prompts.py --all
python3 tools/run_prompts.py jinyong-writing
```

自动判定 checker_max / min_chars / length_max / no_regex / any_regex / count_min / count_max，manual 只列出。**字数口径统一为 checker 的「规模」字数**（去 markdown 与空白，含标点）。

## diagnose.py：这篇稿子缺哪几族

checker 告诉你「像不像 AI」，不告诉你「用了哪些动作」。`diagnose.py` 补这一段：

```bash
python tools/diagnose.py 稿子.md
python tools/diagnose.py --engine luxun-writing 稿子.md
python tools/diagnose.py --json 稿子.md
python tools/diagnose.py --list-families
```

它输出四样东西：字数/句数/均句长、checker 分（generic + 可选引擎）、
命中的族估计（按强度排序，每族给「依据」与「证据」）、最缺的三个族（按
「族内原子数 × 未命中强度」排序）并链接到 `learn/` 的对应练习。

**它是启发式，不是判断。** 只数表面证据：首句长度与具体物、数字的货币/度量单位、
引号术语、转折词、末句形态、类指与习惯副词、首尾共享词。反讽、留白、言外之意
都判不出，好坏更判不出。输出里每族都写了依据，就是为了让你能反驳它。
「独有」的 37 个原子不在估计范围内——那要读各引擎自己的原子表。

对练习册/合集运行（如 `learn/01-练习-认原子.md`）时统计对象是全文，
只用于确认工具能跑通，不代表其中任何一段。

跨引擎原子总库在 `atoms/LIBRARY.md`（按族汇总）与 `atoms/index.json`（机器可读）；`lint_skill.py` 的 A1–A3 校验各引擎原子文件的族标签与 index 一致。

## rewrite_hints.py：从「几分」到「哪一句、改成什么」

`ai-flavor-checker` 告诉你「AI 味 72 分，硬档命中 3 处」。这句话对想学写作的人没用——
他不知道是哪三处，也不知道改成什么。

`rewrite_hints.py` 把定位和改法一起给出：

```bash
python tools/rewrite_hints.py 稿子.md
python tools/rewrite_hints.py 稿子.md --engine luxun-writing
python tools/rewrite_hints.py 稿子.md --md 报告.md
python tools/rewrite_hints.py --selftest
```

输出长这样（AI 腔样本实测）：

```
── 第 2 句 ──
   在当今这个快速变化的时代，我们不难发现，赋能已经成为衡量价值的重要维度。
   [硬档黑话] 这类词不是错字，是「看起来像结论，其实什么都没说」。
     怎么改：要么换成具体动作，要么整句删掉——多数情况下删掉后句子更清楚。
     · 「赋能」→ 帮上忙／起到作用
     · 「不难发现」→ （直接删掉）
   [抽象名词] 一句话里出现两个以上，通常是在用大词代替具体的事。
     · 「价值」→ 具体是什么？
```

**白名单原则**：只处理清单里列出的 6 类规则（硬档黑话／连接词偏多／抽象名词／
「不是A而是B」公式／长句断句点／排比同构）。没命中的句子一个字都不动，
不重排段落，不改结构。建议要人过一遍再改，不自动写回原文件。

与 checker 共用同一套词表与分句逻辑（直接 import），两边判定不会打架。

### 顺手修掉的假阳性：「这一」

v0.2 把「这一」整词计入软档，凡出现必扣分。实测正常中文里假阳性极多——
19 篇稿子大批命中 3 分左右，全是「这一类」「这一条」「这一次」这类**指示代词**，
不是连接词。

现在按后接量词排除（`这一[类种点块次条年天切步代部些边头回场层]`）。
修正后 33 篇语料无一因此扣分，checker 自检与 18 条回归测试全部通过。