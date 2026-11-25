# demo · 效果展示

> 人们转发**输出**，不转发方法论。
> 这个目录放的就是「一眼能看出差别」的东西。

## 现有

三个成熟引擎各有一篇完整产出，已上线官网文章栏目：

→ https://greatbeing.github.io/writing-engines/articles/

（`guanfang-writing/examples/2026-11-02-skill评分报告.html` 是 skill 自评分卡，不是文章示例，不在此列。）

## 已做的那一件：同题四体

这一页已经做完了，不是计划：`demo/t01`、`t05`、`t07`、`t09`、`t10` 五个题目目录，
每题四版（裸模型 / 活人感 / 官方体 / 特稿），由 `tools/build_compare.py` 生成为
`docs/compare/` 的对照页。上线地址：

→ https://greatbeing.github.io/writing-engines/compare/

做法：每题从 `eval/prompts.json` 取题与统一素材包，四版由四个独立 agent 分别生成，
唯一变量是加载哪个引擎；页面用折叠长文，首屏只留每段的开头。

**这是展示，不是评测**：它说明差别存在，不说明差别显著、不说明稳定。
胜率与显著性以 `eval/RESULTS.md` 的盲评为准（尚未运行）。

**注意**：demo 页里贴的是**模型输出**，不是语料原文。语料原文不入库
（见 `sources/INDEX.md`）。
