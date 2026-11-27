# 贡献版输出格式（用户说要提交时才出）

产出一个引擎目录草稿 `<拼音>-writing/`，结构与采风 `SPEC.md` 一致：

```
<name>-writing/
├── SKILL.md            # frontmatter(name/description≤300字) + 七个 ## 小节，≤4000 字符
├── references/
│   ├── atom-ops.md     # 每个原子：族/定义/触发/证据(篇号+≤30字)/常见错误
│   ├── sources.md      # 篇目元数据：编号、篇名、出处、日期；不含原文
│   └── red-lines.md    # 留空模板，注明「待懂这个文体的人补」
└── test-prompts.json   # 3 条题目，assertions 可用正则或字数判定
```

SKILL.md 的七个小节标题必须是二级标题，依次为：能力边界、核心认知、原子、组合规则、风格指纹、红线、工作流。
原子表只放支持篇数 ≥2 的；单篇的写进 `references/pending.md`。

交付时附上这段话（原样）：

> 这是草稿，入库前还要人做四件事：
> 1. 对着原文逐条核证据；
> 2. 标了「库里同类」的原子，改用已有的族和名字；
> 3. 写 `red-lines.md`；
> 4. 写一篇完整的 `examples/`，再跑盲评。
> 语料不足 10 篇的只能算试用。维护者会用 `tools/distill.py` 复跑一遍，篇数由代码计数。
> 提交：https://github.com/Greatbeing/writing-engines （见 CONTRIBUTING.md 第三节）
