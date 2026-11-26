# tools/maint · 项目维护

两台云机在写稿之外，各自还有一份"值班"工作。这里是那部分。

## 值班表（UTC，北京 +8）

| 时间 | 机器 | 任务 | 做什么 |
|---|---|---|---|
| 01:00 | being | `daily/write.py` | 写一篇（已有） |
| 02:00 | god | `daily/review.py` | 评一篇（已有） |
| **03:00** | **being** | `maint --mode build` | 重建站点；产物与源不一致才提交 |
| **03:30** | **god** | `maint --mode audit` | 六项只读体检，出报告 |
| **周一 04:00** | **god** | `maint --mode weekly` | 汇总一周，出周报 |

写作和评审跑完再构建、再体检，所以周报和报告里都含当天结果。

## 体检六项

| 检查 | 命令 | 判据 |
|---|---|---|
| 引擎契约 | `lint_skill.py --all` | 0 错误 |
| 引擎断言 | `run_prompts.py --all` | 0 失败 |
| checker 回归 | `tests/test_checker.py` | 用例全过 |
| 引语核对 | `check_quotes.py` | 疑似自造 0 处 |
| 站点链接 | `maintain.py` 内置 | `docs/` 内本地链接 0 断裂 |
| 示例齐全 | `maintain.py` 内置 | 每个引擎至少 1 篇 examples |

## 三条安全边界

1. **只读的活不提交。** `audit` 模式只写 `drafts/maint/health-*.md`，不碰引擎、不碰站点。
2. **确定性的活才自动修。** `build` 模式只做一件事：重跑生成器，产物变了才提交。
   因为产物完全由源文件决定，人不需要判断。除此之外不让机器自己改代码。
3. **失败不掩盖。** 任一检查失败都会进报告并让退出码非 0，但不中断、不回滚、不"顺手修好"。

`build` 模式还有一道闸：产物有变化时**先跑一遍体检，全过才提交**——避免把坏产物推上线。

## 产物

```
drafts/maint/
├── health-YYYY-MM-DD.md    每日体检（god 生成并提交，留 45 天）
└── weekly-YYYY-MM-DD.md    周报（god 每周一生成并提交）
```

日志在 `drafts/daily/logs/maint-*.out/.err`（不入库，留 45 天）。

## 手动操作

```bash
bash tools/maint/install_timers.sh build     # being
bash tools/maint/install_timers.sh audit     # god
bash tools/maint/install_timers.sh weekly    # god
bash tools/maint/install_timers.sh status
bash tools/maint/install_timers.sh remove

python3 tools/maint/maintain.py --mode audit --no-push   # 只跑不提交
python3 tools/maint/maintain.py --mode weekly
```

`--no-push` 用于调试：跑完全部检查但不产生提交。

## 这层维护真正抓过的东西

上线当天就抓到一个真 bug 并修掉，是它自己该干的事：

- **R2「语料全文不入库」误判**：写作时生成的 `drafts/daily/_sys.txt` 含整份 SKILL.md、超过 5KB，
  在 `.gitignore` 里根本不会入库，但 lint 扫的是磁盘文件，于是报错。
  修法两条：提示词改写到仓库外的临时目录；`lint_skill.py` 的 R2 跳过被 git 忽略的路径。
  修复过程中还发现 `_git_ignored()` 因缺少 `subprocess` 导入而静默失效——
  这类"看起来生效其实没生效"的检查，比不检查更危险。