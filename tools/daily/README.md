# tools/daily · 每日自动写作流水线

两台 Instabox 云机各管一段：**being 写，god 评**。模型走各自机器上的 magpie 网关，
不需要外部 API key；推送用两台机器上已登录的 `gh`。

```
01:00 UTC（北京 09:00）  being  write.py   随机挑引擎 → 自助选题 → 写作 → 质检 → 构建 → 推送 master
02:00 UTC（北京 10:00）  god    review.py  拉最新文章 → 按风格指纹逐条核对 → 打分 → 提交评审
```

## 为什么分成两台

写和评放在同一台机器、同一个模型上，评审会倾向于替自己辩护。分机器之后，
评审端只拿到**成稿**和**引擎文档**，看不到写作时的提示词与失败重试记录。

## 一次写入长什么样

| 步骤 | 实现 |
|---|---|
| 选引擎 | `state.json` 里近 7 天用过的排除，其余随机 |
| 自助选题 | 把该引擎 `examples/` 已有标题喂给模型，明确要求避开 |
| 写作 | `llm.sh` → magpie `group/daily`，温度 0.9 |
| 质检 | 字数 850–2200、违禁词、`ai-flavor-checker` 低于该引擎 `pass_below`、首行 `# 标题` |
| 不过怎么办 | 把扣分原因回喂，重写，最多 3 稿；3 稿都不过 → 当天不发布 |
| 发布 | `build_articles.py` → `git commit` → `pull --rebase` → `push`，失败退避重试 5 次 |

## 手动操作

```bash
# 在 being 上
bash tools/daily/install_timers.sh write
python3 tools/daily/write.py --dry-run          # 看今天挑了哪个引擎、提示词长什么样
python3 tools/daily/write.py                    # 立刻跑一次
python3 tools/daily/write.py --engine mao-writing

# 在 god 上
bash tools/daily/install_timers.sh review
python3 tools/daily/review.py --dry-run
python3 tools/daily/review.py --date 2026-11-26

# 查状态 / 卸载
bash tools/daily/install_timers.sh status
bash tools/daily/install_timers.sh remove
```

日志在 `drafts/daily/logs/`（不入库）。

## 记录文件（入库，两台机器靠它协调）

| 文件 | 内容 |
|---|---|
| `drafts/daily/state.json` | `runs[]` 每次发布（日期/引擎/标题/分数）；`reviews[]` 每次评审（分数/结论） |
| `drafts/daily/reviews/YYYY-MM-DD.md` | 人读的评审正文 |

`state.json` 是唯一事实来源：写作端靠它去重，评审端靠它找当天那篇。

## 失败时的行为

- 模型连续失败 → 当天不发布，日志留痕，不影响仓库。
- 质检不过 → 不提交、不推送；落选稿全部删除，只留通过的那篇。
- 构建失败 → 不推送（避免线上出现半成品）。
- 推送失败 → 退避重试；仍失败则保留本地提交，第二天自动 rebase 再推。

## 边界

- **只写正文，不改引擎。** 这条流水线往 `*-writing/examples/` 里加文章，不碰 `SKILL.md` 与 `references/`。
- **不做选题调研。** 题目由模型自选，所以会出现"泛题"；如果连续几天题目质量差，
  说明该引擎的 `能力边界` 写得太宽，要回去改引擎，而不是改流水线。
- **评审不阻断发布。** 采用「先发布、后评审」，评审结论记在 `state.json`；
  ≤2 分时标 `needs_fix`，由人决定是否撤稿——自动撤稿风险太大，不做。
## 三个已经装上的质量机制

### 1. 字数不足时「扩写」，不换题重写

首跑实测：3 稿里 2 稿因为 806 / 805 字（门槛 850）被打回，而每次重写都换了一个新题目——
既浪费 tokens，又可能再次踩同一个坑。

现在区分处理：
- **只差字数** → 把上一稿整篇回喂，要求「保留题目、结构、语气，补到 1100–1400 字，加细节不加议论」。
- **其它不合格** → 才换一稿重写，并把扣分原因写进提示词。

### 2. 评审结论回流到写作端

`review.py` 会把「指纹逐条核对」表里判为**不过**的项抽出来，记进 `state.json` 的 `reviews[].issues`。
`write.py` 每次开写前读最近 5 次评审的 issues，作为「近期反复指出的问题」注入系统提示词。

这样评审不只是事后打分，而是第二天就起作用。

### 3. 状态一条命令看完

```bash
bash tools/daily/status.sh
```

打印：两个定时器的 enabled/active、最近 7 次发布（机检分 + 评审星级）、评审通病汇总、
日志尾部、仓库 head 与磁盘余量。

## 定时器持久化（需要 root 做过一次）

云机的 `~/.config/systemd/user/timers.target.wants/` 原本被 root 锁成只读，
导致 `systemctl --user enable` 报 `Access denied`。已用 sudo 修正属主：

```bash
sudo chown -R user:user ~/.config/systemd/user/{timers,default}.target.wants
sudo chmod u+w ~/.config/systemd/user/{timers,default}.target.wants
systemctl --user enable --now writing-daily-write.timer   # 或 review
```

现在两台都是 `enabled` + `active`，重启后自动恢复，不再依赖 healthwatch 补丁。
**如果云机重装或镜像刷新，这一步要重做。**
