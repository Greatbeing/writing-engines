# tools · 评测与治理

> 评测器是「教人写作」产品的核心反馈环——写完不是结束，打过分才是开始。
> 但打分必须可信，否则它只是一个更快的偏见。

## 三个工具

| 工具 | 干什么 | 状态 |
|---|---|---|
| `ai-flavor-checker.py` | 给一段文本打 AI 味分（按引擎） | v0.2 |
| `lint_skill.py` | 检查一个引擎是否符合 `SPEC.md` | v0.1 |
| `tests/test_checker.py` | checker 的回归测试 | v0.2 |

## ai-flavor-checker.py v0.2

```bash
python3 tools/ai-flavor-checker.py 你的文章.md
python3 tools/ai-flavor-checker.py --engine human-voice-writing 你的文章.md
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
| 测试 | 无 | 14 条断言（`tests/test_checker.py`） |

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
python3 tools/lint_skill.py human-voice-writing --strict
python3 tools/lint_skill.py --repo
```

检查 9 项（E1–E9）：frontmatter 完整、name 与目录一致、description 长度、
必需七节齐全、体积、references 指针、无版本记录小节、无 `.backup/`、无语料全文。

`--strict` 让警告也算失败，用作 USD 准入线（见 `CONTRIBUTING.md`）。

## 词表哲学

**保守收录，宁可漏检不误报。** 词表即知识——每次实战发现新的 AI 腔词，
直接追加到 `engine_profiles.json`，并带一个会因此失败的测试用例。

HARD 档（零容忍）是真正暴露「不是人在写」的词：赋能、抓手、闭环、底层逻辑、
颗粒度、对齐、范式、彰显、重塑、颠覆、综上所述、值得注意的是、不难发现……
SOFT 档（存在合法）是正常中文连接词：因此、然而、此外、从而、进而、进行、作出。

把这两档混在一起，是 v0.1 最大的判断错误。
