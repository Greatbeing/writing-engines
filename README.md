# Writing Skills · 写作引擎

两个经过实战迭代的写作 skill：

| Skill | 说明 |
|---|---|
| `human-voice-writing` | 活人感写作（三联生活实验室体）v3.0 —— 选题引擎（梗考古/现象命名/反共识观察）+ 21 个原子技法 + 完整技法库 + 11 篇蒸馏原文 |
| `guanfang-writing` | 官方体写作（浙江宣传体）—— 12 个原子操作 + 组合规则 + 风格指纹 + 红线审查 |

## 安装（OpenClaw）

```bash
git clone https://github.com/lijigang/writing-skills.git
cp -r writing-skills/human-voice-writing writing-skills/guanfang-writing ~/.openclaw/workspace/skills/
```

重启后 `/skills` 即可看到。目录自包含，无代码依赖，拷贝即用。

## 适用场景

- **活人感体**：公众号/小红书叙事文，需要「现象入口 + 真实人物样本 + 网络梗锚点」
- **官方体**：政论文/时评/官方公众号文章，需要「骨架先行 + 金句工程」

## 两条红线（引擎自带）

- 活人感体：人物样本必须实名真话，禁止虚构案例；金句只放 ENDING
- 官方体：先确认骨架再填材料；金句 ≤ 3
