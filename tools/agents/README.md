# 四个 agent 的调用手册

> 两台云机（being / god）都装了 DeepSeek Harness、Claude Code、codex、opencode。
> 三家外部 CLI 全部经本机 magpie 网关路由（`127.0.0.1:3425`），**不需要任何外部 API key**。
> 本文回答两件事：**怎么调**（命令）、**什么时候调**（路由规则）。默认不调用——大多数任务一个都够。

## 一、什么时候该调（先看这张表）

| 场景 | 用谁 | 为什么不是别人 |
|---|---|---|
| 写文章、改稿、拆解、策划 | **不调任何外部 agent**，DSH 直调 magpie | 一次生成就够，加一层是净亏 |
| 要读遍整个仓库、跨文件改代码 | **codex** | 沙箱与工具链最完备；但必须限定 `--cwd` |
| 需要第二意见 / 两方对照评审 | **claude** | 便宜、快（实测 6 秒），文风判断稳 |
| 需要浏览器、多模态、或 opencode 特有 agent | **opencode** | 慢（实测 21.7 秒），只在非它不可时用 |
| 需要 skill、记忆、子代理编排 | **DSH** | 只有它有这套 |
| 一句事实、一次翻译、一条命令 | **都不调** | 直接自己答，调用的启动成本比答案还大 |

**默认结论：能不调就不调。** 上面只有“第二意见”和“跨文件改代码”两类，是外部 agent 真正赚钱的场景。

## 二、怎么调（统一入口）

```bash
tools/agents/ask.sh <dsh|claude|codex|opencode> <提示词文件|-> [选项]
```

示例：

```bash
# 让 claude 给一篇文章挑毛病（第二意见）
tools/agents/ask.sh claude /tmp/review_prompt.txt --timeout 120

# 让 codex 在指定仓库里做只读检查（不会改文件）
tools/agents/ask.sh codex /tmp/check_prompt.txt \
  --cwd /data/home/src/writing-engines --timeout 300

# codex 真要改文件，必须显式解锁
tools/agents/ask.sh codex /tmp/fix_prompt.txt --cwd /data/home/src/writing-engines --allow-write

# 让 DSH 跑一个带 skill 的任务
tools/agents/ask.sh dsh /tmp/task.txt

# 从 stdin 读提示词
echo "用一句话解释什么叫零度叙述" | tools/agents/ask.sh claude -
```

### 各工具的关键参数（原始命令，供不用封装时参考）

| 工具 | 非交互命令 | 关键开关 |
|---|---|---|
| DSH | `dsh --profile headless "任务"` | `--json` 机器可读；`--session-id` 续会话；支持 stdin |
| Claude Code | `claude -p "任务"` | `--model`、`--output-format text/json`、`--max-turns`、`--append-system-prompt` |
| codex | `codex exec --skip-git-repo-check -s read-only -C <dir> "任务"` | `-s read-only/workspace-write`、`-C`、`-m`、`--json`、`--output-schema` |
| opencode | `opencode run -m magpie/group/daily "任务"` | `--agent`、`--format json`、`--file`、`-c` 续会话 |

## 三、实测数据（being，2026-11-26）

同一句极短任务「只回复：ok」：

| 工具 | 耗时 | 备注 |
|---|---|---|
| codex | **4.1 s** | 但**一句"可用"烧了 9,960 tokens**——它把工作目录读进上下文。不给 `--cwd` 会更糟 |
| claude | **6.0 s** | 配置里模型名带 `[1m]` 后缀会报 `unrecognized_model`，仍可用但走兜底，建议修 |
| opencode | **21.7 s** | 最慢，启动开销大 |
| DSH headless | 数秒 | 每次会拉起一批 MCP（chrome-devtools、sequential-thinking 等），服务器上无用 |

**资源：4 核 / 7G（已用约 3G）。并发上限设 2，别同时开四个。**

## 四、三条硬规矩

1. **codex 必须给 `--cwd`。** 不给就按当前目录读，token 成本会失控。
2. **codex 默认只读。** 要它写文件必须显式 `--allow-write`，否则改不动还不知道为什么。
3. **全部带超时。** 封装默认 300 秒；长任务用 `--timeout` 显式给，别让它挂着。

## 五、什么时候**不要**调

- 能自己一次答完的（事实、改写、润色、格式化）——直接做。
- 需要多轮来回确认的——外部 agent 都是单轮，来回传话的成本高于收益。
- 需要读大量私有上下文又不想外发的——`--cwd` 决定它能看什么，给它大目录等于把仓库交出去。
- 只是"想多一个意见"但没人会看结论的——评审不落地就是浪费。

## 六、和每日流水线的关系

`tools/daily/` 的写作端**不用**这四个 agent，直接调 `tools/daily/llm.sh`（一次 magpie 请求）。
评审端同理。只有当你想要「第二意见」时才加：

```bash
# 在 review.py 之后追加一次 claude 评审，两方分歧大的稿子人工看
tools/agents/ask.sh claude /tmp/second_review.txt --timeout 180
```

这是当前唯一建议引入外部 agent 的地方。
