<p align="center">
  <img src="docs/logo.svg" width="240" alt="采风">
</p>

<h1 align="center">采风 · Caifeng</h1>

<p align="center"><b>采其风，得其法。</b><br>
<sub>Collect the style. Build the engine.</sub></p>

<p align="center">每一种文风背后，都有一套没说出口的规则。我们把它采下来，造成引擎。<br>
<a href="https://greatbeing.github.io/writing-engines/">官网</a> · 写作引擎库 writing-engines</p>

> 一句话：**模式归纳是尸检，原子操作是手术。**

---

## 一个引擎是什么

一种文体，本质上是一套作者没说出来的操作规则。写作课教你的「要有细节」「要克制」
「要有网感」，是这些规则**被总结之后的样子**，不是它们运转的样子。

这个仓库做的是反过来的事：把一种文体拆到「可以执行」的颗粒度，
再把拆出来的零件装回成一台能写新文章的机器。

```
引擎 = 原子技法 × 风格指纹 × 红线审查
```

三个构件各管一段，缺一不可：

| 构件 | 管什么 | 换个说法 |
|---|---|---|
| **原子技法** | 怎么**想**出来的 | 认知动作，不是句式模板。如「先替读者说出嫌弃，再给清醒回答」 |
| **风格指纹** | 写完怎么**验** | 可数的指标，不是「要有张力」。如「每 200 字至少 1 个具体画面」 |
| **红线审查** | 什么**绝对不能**出现 | 硬边界，每条配一句「改成什么」 |

- 只有原子没有指纹 → 无法自检的范文集
- 只有指纹没有原子 → 只能判卷，不能写作
- 只有红线 → 那就是提示词模板，绕了一圈回到原点

## 为什么不是提示词模板

| | 提示词模板 | 这个仓库 |
|---|---|---|
| 给你什么 | 成品**长什么样** | 成品**怎么长出来的** |
| 能不能自检 | 不能，只能凭感觉 | 指纹可数、红线可查、checker 可打分 |
| 会不会生长 | 用完即弃 | 每次实战反哺，技法库与词表持续追加 |
| 覆盖范围 | 一个腔调 | 一种文体的全部构件（选题→结构→句子→伦理） |

模板是尸检报告：把死掉的文章切开，告诉你哪里好。引擎是手术：它知道下一刀往哪下。

## 引擎清单

| 引擎 | 文体 | 蒸馏来源 | 原子 | 状态 |
|---|---|---|---|---|
| [`human-voice-writing`](human-voice-writing/SKILL.md) | 活人感城市观察文（三联生活实验室体） | 11 篇（2024–2026） | 21 | 可用 |
| [`guanfang-writing`](guanfang-writing/SKILL.md) | 官方时评（浙江宣传体） | 10 篇（拆解结论入库，原文不入） | 12 | 可用 |
| [`feature-writing`](feature-writing/SKILL.md) | 人物特稿（《人物》杂志体） | 10 篇（2020–2023） | 10 | 可用 |
| [`gongwen-writing`](gongwen-writing/SKILL.md) | 党政机关公文（GB/T 9704-2012，15 个法定文种） | 9 个文种模板 | 6 | 可用 |
| [`sushi-writing`](sushi-writing/SKILL.md) | 苏轼白话体随笔（散文小品＋尺牍） | 13 篇（公版） | 3 | 试用 |
| [`luxun-writing`](luxun-writing/SKILL.md) | 鲁迅体白话杂文 | 14 篇（公版） | 3 | 试用 |
| [`wangxiaobo-writing`](wangxiaobo-writing/SKILL.md) | 王小波体幽默说理杂文 | 拆解结论（原文不入库） | 3 | 试用 |
| [`zhangailing-writing`](zhangailing-writing/SKILL.md) | 张爱玲体散文与小说描写 | 拆解结论（原文不入库） | 3 | 试用 |
| [`lijuan-writing`](lijuan-writing/SKILL.md) | 李娟体散文白描 | 拆解结论（原文不入库） | 3 | 试用 |
| [`yuhua-writing`](yuhua-writing/SKILL.md) | 余华体冷静叙事 | 拆解结论（原文不入库） | 3 | 试用 |
| [`standup-writing`](standup-writing/SKILL.md) | 中文脱口秀稿 | 拆解结论（原文不入库） | 3 | 试用 |
| [`renminribao-writing`](renminribao-writing/SKILL.md) | 人民日报评论体 | 拆解结论（原文不入库） | 3 | 试用 |
| [`wangzengqi-writing`](wangzengqi-writing/SKILL.md) | 汪曾祺体散文 | 拆解结论（原文不入库） | 3 | 试用 |
| [`jinyong-writing`](jinyong-writing/SKILL.md) | 金庸体武侠叙事 | 拆解结论（原文不入库） | 3 | 试用 |
| [`maozedong-writing`](maozedong-writing/SKILL.md) | 毛泽东文章体说理 | 拆解结论（原文不入库） | 3 | 试用 |

三个引擎共享一套结构契约（[`SPEC.md`](SPEC.md)），每个都带 `test-prompts.json` 与
可判定的断言——引擎不是「看着像」，是「可以被检查」。

## 安装

`SKILL.md` + frontmatter 的格式是通用的，下面以 OpenClaw 为例：

```bash
git clone https://github.com/Greatbeing/writing-engines.git
cp -r writing-engines/human-voice-writing \
      writing-engines/guanfang-writing \
      writing-engines/feature-writing \
      writing-engines/gongwen-writing \
      writing-engines/sushi-writing \
      writing-engines/luxun-writing \
      writing-engines/wangxiaobo-writing \
      writing-engines/zhangailing-writing \
      writing-engines/lijuan-writing \
      writing-engines/yuhua-writing \
      writing-engines/standup-writing \
      writing-engines/renminribao-writing \
      writing-engines/wangzengqi-writing \
      writing-engines/jinyong-writing \
      writing-engines/maozedong-writing \
      ~/.openclaw/workspace/skills/
```

Claude Code 或其它支持 `SKILL.md` 的宿主：把引擎目录放进对应的 skills 路径即可。
目录自包含，无代码依赖，拷进去就能用。

## 使用

一句话需求进，一篇文章出。引擎自带触发词与「不适用」路由：

| 引擎 | 会说「用这个」的话 | 会说「别用这个」的话 |
|---|---|---|
| 活人感 | 写公众号文／城市观察／避免 AI 味／网感文案 | 需要实名采访的特稿、政务时评 |
| 官方体 | 写时评／政论文／主旋律／体制内爆款 | 生活随笔、口语化观察文 |
| 特稿 | 写人物特稿／深度报道／人物群像 | 只有二手转述、无现场无采访 |

三个引擎都能**反向用**：给它一篇现成文章，它按原子链拆解 + 做红线体检，
告诉你这篇用了哪几招、哪几处露怯、怎么改。

## 造一个引擎

这是这个仓库真正的重点：**引擎不是攒出来的，是造出来的。**

```
选样（10+ 篇代表作）→ 拆解（枚举原子技法）→ 压缩（风格指纹 + 红线）
→ 实战（真实文章验证）→ 反哺（反馈回写技法库）
```

第三步「压缩」过去没有产物定义，于是三个引擎长出了三种结构。现在有了：
[`SPEC.md`](SPEC.md) 规定七节结构、体积上限（按字符不按字节）、
description／红线／指纹各自的写法。`tools/lint_skill.py` 让它可执行。

想贡献新引擎，要过四条准入门槛（[`CONTRIBUTING.md`](CONTRIBUTING.md)）：

1. 语料 ≥ 10 篇同源、可追溯，**不存全文**（见 [`sources/INDEX.md`](sources/INDEX.md)）
2. 原子技法 ≥ 8 条，每条 ≥ 2 篇交叉验证
3. 通过 `eval` 盲评：对裸模型胜率显著领先，且与其他引擎可区分
4. 通过 `python3 tools/lint_skill.py <engine> --strict`

第 3 条是唯一无法靠写作技巧通过的一条。达不到就改引擎，不降低门槛——
**一个过不了盲评的引擎进库，会稀释整个库的可信度。**

## 工具

| 工具 | 干什么 |
|---|---|
| [`tools/ai-flavor-checker.py`](tools/ai-flavor-checker.py) | AI 味评分（v0.2，**按引擎**打分，可当门禁） |
| [`tools/lint_skill.py`](tools/lint_skill.py) | 检查引擎是否符合 `SPEC.md`（10 项，`--strict` 作准入线） |
| [`tools/tests/test_checker.py`](tools/tests/test_checker.py) | checker 的回归测试（17 条断言） |

```bash
python3 tools/ai-flavor-checker.py --engine human-voice-writing 文章.md
python3 tools/lint_skill.py --all
python3 tools/tests/test_checker.py
```

关键的一点：**同一个装置，在不同文体里权重不同。** 「大量「」访谈式引用」在活人感里
是签名装置（加分），在特稿里是噪音；「不是A而是B」在活人感与官方体是原子，
在特稿里要克制。v0.1 用一张全局词表把两者一起罚了——那是评测器在反对自家引擎。
细节见 [`tools/README.md`](tools/README.md)。

## 评测

[`eval/`](eval/README.md) 是一套已经就位的盲评流程：

```
10 题 × 4 版（裸模型 + 3 个引擎）= 40 篇
× 每题 2 位评分者盲排（他们只看到 t01/A.md 这样的文件名）
→ 胜率 / 可区分度 / 评分者一致性
```

流程、题目、统一素材包、泄露拦截、汇总脚本、判据都已写好。
**第一轮还没跑**，[`eval/RESULTS.md`](eval/RESULTS.md) 里全是 `TBD`——
所以「用了比不用好多少」目前还没有数字。这是下一步唯一在做的事。

判据事先定死了，包括一条自我证伪条件：

> 如果三个引擎的输出无法区分（H2 失败），那么「文体的操作系统」这个说法
> 就应该降级为「一个通用写作引擎，三种侧重」。

先定证伪条件，再看数据。不然看到数据总能自圆其说。

## 路线图

按「每步都留下可展示物」排序，不是按「想做什么」排序。

- [x] 三个引擎（活人感 21 原子 / 官方体 12 / 特稿 10）
- [x] 引擎契约 `SPEC.md` + 合规检查器
- [x] checker v0.2（按引擎打分）+ 回归测试
- [ ] **`eval` 第一轮盲评** ← 当前唯一在做的事
- [ ] checker 全量校准（用 21 篇原文做负样本）
- [ ] 同题三体 demo（一眼看出差别，最好的分发物）
- [ ] 学习路径原型（拆解课／模仿课／创作课）
- [ ] 第 4 个引擎 ← **明确押后**，理由见 [`PRODUCT.md`](PRODUCT.md)

## 许可与语料

- **全部原创内容**（SKILL.md、references/、SPEC、eval、tools 代码）：**MIT** —
  见 [`LICENSE`](LICENSE)。随便用，包括商用，保留署名与许可声明即可。
  适用范围与第三方材料的说明见 [`NOTICE.md`](NOTICE.md)。
- **第三方文章**：不收录全文，仅存篇目元数据与技法映射；例证单条 ≤ 50 字并标注出处。
  著作权归原作者与首发媒体，**不在本仓库的授权范围内**。
  详见 [`sources/INDEX.md`](sources/INDEX.md)

MIT 的代价说清楚：**别人也可以拿这套引擎去做课程、做竞品。** 这是刻意的选择——
先让它被用起来，再靠证据、数据和交付质量拉开距离，而不是靠许可条款挡人。

---

*技法原创；蒸馏素材来自公开报道，仅为评论与教学目的引用。*
