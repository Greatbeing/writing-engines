# NOTICE · 适用范围与第三方素材

本文件是 `LICENSE`（MIT）的说明，**不是对 MIT 条款的修改**。

## 一、许可覆盖什么

MIT 适用于本仓库的**全部原创内容**：17 个引擎（`*-writing/`）的 `SKILL.md`、`references/`、
`examples/` 中的原创示范与 `atoms/` 原子总库、`SPEC.md`、`eval/` 的设计文档与脚本、
`tools/` 下的代码、`README` 与 `CHANGELOG`。

此处的 "Software" 应理解为「本仓库的全部作品（the Work）」——代码与文字一体适用。
我们的意图很简单：**随便用，包括商用，只要保留 `LICENSE` 里的署名与许可声明。**

## 二、许可不覆盖什么

`sources/INDEX.md` 中提及的作品篇名、媒体名，以及各引擎里不超过 50 字的例证引文，
其著作权属于原作者与首发媒体。这些内容仅用于评论、教学与技法溯源，属于合理引用，
**本仓库无权也不对其再许可**。如需使用原文，请向原媒体取得授权。

## 三、为什么单独放一个文件

因为 GitHub 的许可证识别只看 `LICENSE` 这一个文件，并且在里面出现附加说明时会
放弃识别，结果仓库页面显示 `NOASSERTION` 而不是「MIT license」。

实测过：把中文说明附在 MIT 全文后面，`api.github.com` 返回
`"license": "NOASSERTION"`；拆出来之后才回到 `MIT`。

所以：**`LICENSE` 保持纯净，说明放进 `NOTICE.md`。** 这是惯例，也是机械可读性的要求。

## 四、署名建议

> 技法参考：Greatbeing/writing-engines — https://github.com/Greatbeing/writing-engines
