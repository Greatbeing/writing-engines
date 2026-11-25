# 写作引擎库 · writing-engines

> 把优秀写作**解构**成可安装、可执行、可评测的 agent skill。
> 每个引擎 = 原子技法 × 风格指纹 × 红线审查，全部从真实代表作蒸馏。
>
> 一句话：**模式归纳是尸检，原子操作是手术。**
>
> 为什么叫「引擎」不叫「技能库」：技能是成品，引擎是造法。这个仓库的重点不是
> 攒一堆 SKILL.md，而是那五步蒸馏法能不能稳定地造出下一个。

---

## 先说清楚：这个仓库现在能给你什么，还不能给你什么

写作是主观领域，所以第一件事是说清证据的成色。

| | 状态 |
|---|---|
| **技法库可用吗** | ✅ 可用。3 个引擎、43 条原子技法，全部带跨篇语料例证 |
| **能装上就跑吗** | ✅ 能。目录自包含，无代码依赖，拷进 skills 目录即可 |
| **比不用它更好吗** | ⚠️ **还没验证。** 设计好了（`eval/DESIGN.md`），工具写好了（`eval/score.py`），但**还没跑**。`eval/RESULTS.md` 里全是 `TBD` |
| **能拿去商用吗** | ✅ 可以。MIT，含商用，保留署名即可 |
| **引擎之间真的不同吗** | ⚠️ 未验证。这是 `eval` 要回答的第二个问题（H2），也是更脆弱的那个 |

如果你只想要「一个能立刻用起来的写作 SOP」，现在就可以。如果你想知道
「它到底比直接让模型写好多少」，那要到 `eval` 跑完之后——那是我下一步唯一要做的事。

> 上一版 README 把「可评测」写进了价值主张，但仓库里并没有评测。
> 这一版把那句话改成了「评测已设计、未运行」。**负承诺比空承诺值钱。**

---

## 引擎清单

| 引擎 | 文体 | 蒸馏来源 | 原子 | 状态 |
|---|---|---|---|---|
| [`human-voice-writing`](human-voice-writing/SKILL.md) | 活人感城市观察文（三联生活实验室体） | 11 篇（2024–2026） | 21 | 可用 |
| [`guanfang-writing`](guanfang-writing/SKILL.md) | 官方时评（浙江宣传体） | 10 篇（拆解结论入库，原文不入） | 12 | 可用 |
| [`feature-writing`](feature-writing/SKILL.md) | 人物特稿（《人物》杂志体） | 10 篇（2020–2023） | 10 | 可用 |

三个引擎共享一套结构契约：`SPEC.md`。每个都有 `test-prompts.json` 与可判定的断言。

## 安装

Agent skill 的格式是通用的（`SKILL.md` + frontmatter），下面以 OpenClaw 为例：

```bash
git clone https://github.com/Greatbeing/writing-engines.git
cp -r writing-engines/human-voice-writing \
      writing-engines/guanfang-writing \
      writing-engines/feature-writing \
      ~/.openclaw/workspace/skills/
```

Claude Code / 其它支持 `SKILL.md` 的宿主：把引擎目录放进对应的 skills 路径即可，
目录自包含，无代码依赖。

## 使用

一句话需求进，一篇文章出。引擎自带触发词与「不适用」路由：

| 引擎 | 会说「用这个」的话 | 会说「别用这个」的话 |
|---|---|---|
| 活人感 | 写公众号文／城市观察／避免 AI 味／网感文案 | 需要实名采访的特稿、政务时评 |
| 官方体 | 写时评／政论文／主旋律／体制内爆款 | 生活随笔、口语化观察文 |
| 特稿 | 写人物特稿／深度报道／人物群像 | 只有二手转述、无现场无采访 |

每个引擎都能反向用：给它一篇现成文章，它按原子链拆解 + 做红线体检。

## 验证它真的有效

这是本仓库目前最该被做、也还没做的事。

```bash
# 1. 生成 10 题 × 4 版（裸模型 + 3 引擎），规程见 eval/DESIGN.md
python3 eval/score.py --make-key
python3 eval/score.py --template > eval/rankings.csv

# 2. 组织 3 位评分者盲排（他们只知道 t01/A.md 这样的文件名）

# 3. 出结果
python3 eval/score.py --input eval/rankings.csv > eval/RESULTS.md
```

`score.py` 会算三个数：**引擎对裸模型的胜率**、**引擎之间的可区分度**、
**评分者一致性**。判据在 `eval/DESIGN.md` §四 事先定死了，包括：

> 如果三个引擎的输出无法区分（H2 失败），那么「文体的操作系统」这个说法
> 就应该降级为「一个通用写作引擎，三种侧重」。

先定证伪条件，再看数据。不然看到数据总能自圆其说。

## 工具

| 工具 | 干什么 |
|---|---|
| [`tools/ai-flavor-checker.py`](tools/ai-flavor-checker.py) | AI 味评分（v0.2，**按引擎**打分，可当门禁） |
| [`tools/lint_skill.py`](tools/lint_skill.py) | 检查引擎是否符合 `SPEC.md`（9 项，`--strict` 可作准入线） |
| [`tools/tests/`](tools/tests/test_checker.py) | checker 的回归测试（14 条断言） |

```bash
python3 tools/ai-flavor-checker.py --engine human-voice-writing 文章.md
python3 tools/lint_skill.py --all
python3 tools/tests/test_checker.py
```

v0.2 修了 v0.1 最要命的一个毛病：v0.1 会惩罚活人感引擎自己要求的
「大量「」访谈式引用」和「不是A而是B」金句结构。现在这两样在自家引擎里是加分项。
细节见 [`tools/README.md`](tools/README.md)。

## 方法论：引擎是怎么造出来的

```
选样（10+ 篇代表作）→ 拆解（枚举原子技法）→ 压缩（风格指纹 + 红线）
→ 实战（真实文章验证）→ 反哺（反馈回写技法库）
```

第三步「压缩」过去没有产物定义，导致三个引擎长出三种结构。现在有了：`SPEC.md`。
任何人按这五步造新引擎，都要过 `SPEC.md` + `CONTRIBUTING.md` 的四条准入线。

## 收录标准（也是这个库的自律）

1. 语料 ≥ 10 篇同源、可追溯，**不存全文**（见 [`sources/INDEX.md`](sources/INDEX.md)）
2. 原子技法 ≥ 8 条，每条 ≥ 2 篇交叉验证
3. 通过 `eval` 盲评：对裸模型胜率 ≥ 60%，且与其他引擎可区分
4. 通过 `python3 tools/lint_skill.py <engine> --strict`

第 3 条是唯一无法靠写作技巧通过的一条。达不到就改引擎，不降低门槛。

## 路线图

按「每步都留下可展示物」排序，不是按「想做什么」排序。

- [x] 三个引擎（活人感 21 原子 / 官方体 12 / 特稿 10）
- [x] 引擎契约 `SPEC.md` + 合规检查器
- [x] checker v0.2（按引擎打分）+ 回归测试
- [ ] **`eval` 第一轮盲评** ← 当前唯一在做的事
- [ ] checker 全量校准（用 21 篇原文做负样本）
- [ ] 同题三体 demo（一眼看出差别，最好的分发物）
- [ ] 学习路径原型（拆解课／模仿课／创作课）
- [ ] 第 4 个引擎 ← **明确押后**。见 `PRODUCT.md` 的说明

## 许可与语料

- **全部原创内容**（SKILL.md、references/、SPEC、eval、tools 代码）：**MIT** —
  见 [`LICENSE`](LICENSE)。随便用，包括商用，保留署名与许可声明即可。
- **第三方文章**：不收录全文，仅存篇目元数据与技法映射；例证单条 ≤ 50 字并标注出处。
  著作权归原作者与首发媒体，**不在本仓库的授权范围内**。
  详见 [`sources/INDEX.md`](sources/INDEX.md)

MIT 的代价说清楚：**别人也可以拿这套引擎去做课程、做竞品。** 这是刻意的选择——
先让它被用起来，再靠证据、数据和交付质量拉开距离，而不是靠许可条款挡人。

---

*技法原创；蒸馏素材来自公开报道，仅为评论与教学目的引用。*
