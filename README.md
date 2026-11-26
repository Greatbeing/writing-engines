<p align="center">
  <img src="docs/logo.svg" width="240" alt="采风">
</p>

<h1 align="center">采风 · Caifeng</h1>

<p align="center"><b>采其风，得其法，自成一体。</b><br>
<sub>Collect the style. Learn the method. Find your own.</sub></p>

<p align="center">每一种文风背后，都有一套没说出口的规则。我们把它采下来，造成引擎。<br>
<a href="https://greatbeing.github.io/writing-engines/">官网</a> · 写作引擎库 writing-engines</p>

> 一句话：**模板让你像它，引擎让你不必像它。**

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

模板让你像它，引擎让你不必像它。

模板是别人的成品，引擎是手里的零件。零件拆到原子一级，你就能拼出别人没拼过的东西——
这也是这个仓库最后想干的事：不是让你写得更像某位作者，是让你写得出只有你能写的那一段。

## 引擎清单

| 引擎 | 文体 | 蒸馏来源 | 原子 | 状态 |
|---|---|---|---|---|
| [`sanlian-writing`](sanlian-writing/SKILL.md) | 活人感城市观察文（三联生活实验室体） | 11 篇（2024–2026） | 21 | 可用 |
| [`zhexuan-writing`](zhexuan-writing/SKILL.md) | 官方时评（浙江宣传体） | 10 篇（拆解结论入库，原文不入） | 12 | 可用 |
| [`feature-writing`](feature-writing/SKILL.md) | 人物特稿（《人物》杂志体） | 10 篇（2020–2023） | 10 | 可用 |
| [`gongwen-writing`](gongwen-writing/SKILL.md) | 党政机关公文（GB/T 9704-2012，15 个法定文种） | 9 个文种模板 | 9 | 可用 |
| [`sushi-writing`](sushi-writing/SKILL.md) | 苏轼白话体随笔（散文小品＋尺牍） | 13 篇（公版） | 10 | 试用 |
| [`luxun-writing`](luxun-writing/SKILL.md) | 鲁迅体白话杂文 | 14 篇（公版） | 10 | 试用 |
| [`wangxiaobo-writing`](wangxiaobo-writing/SKILL.md) | 王小波体幽默说理杂文 | 拆解结论（原文不入库） | 10 | 试用 |
| [`zhangailing-writing`](zhangailing-writing/SKILL.md) | 张爱玲体散文与小说描写 | 拆解结论（原文不入库） | 10 | 试用 |
| [`lijuan-writing`](lijuan-writing/SKILL.md) | 李娟体散文白描 | 拆解结论（原文不入库） | 10 | 试用 |
| [`yuhua-writing`](yuhua-writing/SKILL.md) | 余华体冷静叙事 | 拆解结论（原文不入库） | 10 | 试用 |
| [`standup-writing`](standup-writing/SKILL.md) | 中文脱口秀稿 | 拆解结论（原文不入库） | 10 | 试用 |
| [`versailles-writing`](versailles-writing/SKILL.md) | 凡尔赛体（网络文体，明贬暗褒） | 句式拆解（不收网友原帖） | 10 | 试用 |
| [`guanfang-writing`](guanfang-writing/SKILL.md) | 人民日报评论体 | 拆解结论（原文不入库） | 10 | 试用 |
| [`wangzengqi-writing`](wangzengqi-writing/SKILL.md) | 汪曾祺体散文 | 拆解结论（原文不入库） | 10 | 试用 |
| [`jinyong-writing`](jinyong-writing/SKILL.md) | 金庸体武侠叙事 | 拆解结论（原文不入库） | 10 | 试用 |
| [`acheng-writing`](acheng-writing/SKILL.md) | 阿城体白描叙事 | 拆解结论（原文不入库） | 10 | 试用 |
| [`mao-writing`](mao-writing/SKILL.md) | 毛泽东文章体说理 | 拆解结论（原文不入库） | 10 | 试用 |

结构分两层：**4 个可用**（活人感／官方体／特稿／公文——过契约、过断言、有完整产出、
有实战反馈）＋ **13 个试用**（七节齐备、断言可跑，但样本与反馈还少）。
「可用／试用」是内部评审口径，不是能力上限；盲评一跑完，这个分级会换成胜率数字。

17 个引擎共享一套结构契约（[`SPEC.md`](SPEC.md)），每个都带 `test-prompts.json` 与
可判定的断言——引擎不是「看着像」，是「可以被检查」。

## 原子总库：19 族 163 个原子

把 17 个引擎的原子表摊开对照，重复率比想象的高：鲁迅的「小处切入」、汪曾祺的
「闲闲起笔」、脱口秀的「观察切口」、官方体的「场景钩」，是同一个动作。所以有了
跨引擎的原子总库（[`atoms/LIBRARY.md`](atoms/LIBRARY.md)、机器可读版
[`atoms/index.json`](atoms/index.json)）：

- 引擎里的原子总量 **182 个**（17 个引擎，其中活人感 21、官方体 12、特稿 10、公文 9，其余各 10）
- 已标族、汇入总库 **163 个 / 19 族**（15 个引擎；`feature-writing` 与 `gongwen-writing` 的
  19 个原子还在各自 SKILL.md 里，尚未分族）
- 族里写**通用定义**，引擎里写**变体差异**

一句话：**不同作者 = 同一批原子的不同组合。** 风格不是另一套零件，是同一批零件的
另一种顺序与密度。各引擎的原子文件保持原样，只加一行 `**族**：X`；
`tools/lint_skill.py` 的 A1–A3 检查族标签与索引是否一致——缺行、不一致、索引有而
原子文件无，都会报错。这不是文档约定，是可执行的检查。

## 教学层：从认原子到找自己

原子总库解决「拆得开」，不解决「人怎么学会」。[`learn/`](learn/README.md) 是教学层的
第一块：三条学习线——认原子（单个动作）、看组合（作者 = 原子的选择与密度）、
找自己（诊断自己的稿子）。12 道识别题、8 道单原子仿写、4 道组合题，加一个诊断工具
[`tools/diagnose.py`](tools/diagnose.py)。每步有时间估计、有产出物、有可判定的过关标准；
练习材料全部取自仓库 `examples/`，注明路径，不引受版权保护的原文。

## 安装

`SKILL.md` + frontmatter 的格式是通用的，下面以 OpenClaw 为例：

```bash
git clone https://github.com/Greatbeing/writing-engines.git
cp -r writing-engines/sanlian-writing \
      writing-engines/zhexuan-writing \
      writing-engines/feature-writing \
      writing-engines/gongwen-writing \
      writing-engines/sushi-writing \
      writing-engines/luxun-writing \
      writing-engines/wangxiaobo-writing \
      writing-engines/zhangailing-writing \
      writing-engines/lijuan-writing \
      writing-engines/yuhua-writing \
      writing-engines/standup-writing \
      writing-engines/guanfang-writing \
      writing-engines/wangzengqi-writing \
      writing-engines/jinyong-writing \
      writing-engines/mao-writing \
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
| 公文 | 写通知／报告／请示／函／会议纪要，或转国标版式 docx | 党报评论、新媒体时评 |
| 人民日报评论 | 写社论／评论员文章／人民时评，给评论「提站位」 | 公文、杂文、特稿，冒充人民日报署名 |
| 鲁迅体 | 写杂文／短评／社会现象批评，把温吞的评论改出锋芒 | 官方时评、松弛随笔、民国腔仿古 |

其余 9 个引擎各自带触发词与「不适用」路由，写在各自 `SKILL.md` 的 `description` 里
（3–4 个触发分支，一条不适用路由）。这几行不是全部——只是先给三种最常见的口径。

17 个引擎都能**反向用**：给它一篇现成文章，它按原子链拆解 + 做红线体检，
告诉你这篇用了哪几招、哪几处露怯、怎么改。

## 造一个引擎

这是这个仓库真正的重点：**引擎不是攒出来的，是造出来的。**

```
选样（10+ 篇代表作）→ 拆解（枚举原子技法）→ 压缩（风格指纹 + 红线）
→ 实战（真实文章验证）→ 反哺（反馈回写技法库）
```

第三步「压缩」过去没有产物定义，于是头三个引擎长出了三种结构。现在有了：
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
| [`tools/lint_skill.py`](tools/lint_skill.py) | 检查引擎是否符合 `SPEC.md`（E1–E11 十一项 + A1–A3 原子族标签，`--strict` 作准入线） |
| [`tools/run_prompts.py`](tools/run_prompts.py) | 按各引擎 `test-prompts.json` 的断言自动核对 `examples/` 产出，`--all` 跑全库 |
| [`tools/tests/test_checker.py`](tools/tests/test_checker.py) | checker 的回归测试（18 条断言） |
| [`tools/build_articles.py`](tools/build_articles.py) | 把引擎 `examples/*.md` 生成为官网文章页 `docs/articles/` |
| [`tools/build_compare.py`](tools/build_compare.py) | 把 `demo/<题号>/` 的四版生成为同题对照页 `docs/compare/` |
| [`tools/maint/`](tools/maint/README.md) | 每日维护：站点一致性构建、六项体检、周报（两台云机定时跑） |
| [`tools/agents/`](tools/agents/README.md) | 四个 agent（DSH/Claude/codex/opencode）的调用手册与统一入口 |
| [`tools/daily/`](tools/daily/README.md) | 每日自动写作流水线（写出稿 + 独立评审） |

```bash
python3 tools/ai-flavor-checker.py --engine sanlian-writing 文章.md
python3 tools/lint_skill.py --all
python3 tools/run_prompts.py --all
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
所以「用了比不用好多少」目前还没有数字。

范围要说清楚：首轮只排 3 个成熟引擎（活人感／官方体／特稿），
另外 14 个引擎**一次都没参评**。所以现在的评测证据只覆盖 17 个引擎里的 3/17，
而全库 163 个原子、19 个族，都是按可检查的规格写出来的，不是按胜率筛出来的。

判据事先定死了，包括一条自我证伪条件：

> 如果首轮这三个引擎的输出无法区分（H2 失败），那么「文体的操作系统」这个说法
> 就应该降级为「一个通用写作引擎，三种侧重」。

先定证伪条件，再看数据。不然看到数据总能自圆其说。

## 路线图

按「每步都留下可展示物」排序，不是按「想做什么」排序。

已完成：

- [x] 17 个引擎（活人感 21 原子 / 官方体 12 / 特稿 10 / 公文 9 / 其余各 10）
- [x] 引擎契约 `SPEC.md` + 合规检查器（E1–E11 + A1–A3）
- [x] 跨引擎原子总库 `atoms/`：19 族 / 163 原子，族标签由 lint 守
- [x] checker v0.2（按引擎打分）+ 回归测试（18 条断言）
- [x] checker 全量校准（21 篇原文作负样本，「原文必须过自家门槛」）
- [x] 工具链：`lint_skill` / `run_prompts` / `build_articles` / `build_compare` / `check_quotes`
- [x] 同题四体 demo（5 题 × 4 版，`docs/compare/`）——是展示，不是评测

未完成：

- [ ] **`eval` 首轮盲评** ← 当前唯一在做的事（3 个引擎，不是 17 个）
- [ ] 盲评扩到 17 个引擎（含跨族对照：同一族原子在不同文体的表现差异）
- [x] 教学层第一块：[`learn/`](learn/README.md)——三条学习线、12 道识别题、8 道仿写、
      4 道组合题、诊断工具 `tools/diagnose.py`（练习评测与迭代数据仍待补）
- [ ] 原文核对：金庸、余华、李娟、张爱玲、王小波、汪曾祺、毛选等版权期引擎的
      引文均为「未逐字核对」，`tools/check_quotes.py` 只能查素材内编造，查不了原文

## 许可与语料

- **全部原创内容**（SKILL.md、references/、atoms/ 原子总库、SPEC、eval、tools 代码）：**MIT** —
  见 [`LICENSE`](LICENSE)。随便用，包括商用，保留署名与许可声明即可。
  适用范围与第三方材料的说明见 [`NOTICE.md`](NOTICE.md)。
- **第三方文章**：不收录全文，仅存篇目元数据与技法映射；例证单条 ≤ 50 字并标注出处。
  著作权归原作者与首发媒体，**不在本仓库的授权范围内**。
  详见 [`sources/INDEX.md`](sources/INDEX.md)

MIT 的代价说清楚：**别人也可以拿这套引擎去做课程、做竞品。** 这是刻意的选择——
先让它被用起来，再靠证据、数据和交付质量拉开距离，而不是靠许可条款挡人。

---

*技法原创；蒸馏素材来自公开报道，仅为评论与教学目的引用。*
