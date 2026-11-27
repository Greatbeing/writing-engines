# 编辑部流水线

选题 → 撰稿 → 评审 → 修改（≤2 轮）→ 发布，外加每周一次的引擎迭代。

| 角色 | 机器 | 时间（北京） | 命令 |
|---|---|---|---|
| 撰稿人 | being | 09:00 / 13:00 | `pipeline.py step` |
| 评审人 | god | 10:00 / 14:00 | `pipeline.py review` |
| 引擎迭代 | god | 周日 16:00 | `pipeline.py evolve` |

一天两轮，一篇稿子当天就能走完「写 → 评 → 改 → 再评 → 发布」。

## 状态机

`topic → drafted → reviewed → drafted(v2) → … → approved → published`；评 ≤1 星或改满 2 轮仍不过 → `rejected`。
每篇一个目录 `drafts/pipeline/<日期>-<引擎>/`：`topic.md`、`draft-vN.md`、`review-vN.md`、`meta.json`。

## 评审标准（替代指纹打勾）

读下去意愿、最像作者的一句、最不像的一句、只改一处。≥4 星发布。
**禁止为凑指纹加词**（反例：句首硬加「说白了」）。

## 引擎迭代

取该引擎近期评审的「最不像」证据 → 模型给 SKILL.md 提一处修改 → 同题旧版/新版各写一篇 →
评审人随机顺序盲比 → 新版胜且 lint 通过才落盘，否则只在 `drafts/pipeline/_evolve/` 留记录。
每次只改一处，可追溯、可回滚（git）。

## 轮换

选题按「最久没写过的引擎」挑，17 个引擎轮流上，不再随机。

## 外部情报搜集员

每天北京 08:00（being，在撰稿前）抓浙江宣传、三联生活实验室、三联生活周刊、人民日报评论的新公开文章。
原文只存本机 `tools/tests/fixtures/local/`（不入库），入库的只有手法拆解 `drafts/pipeline/_intel/<引擎>.md`（引文每处 ≤30 字）。
拆解里「引擎没写到的新手法」会作为证据喂给周日的引擎迭代，同样要过 A/B 盲比才落盘。来源在 `scout.py` 的 `SOURCES` 里加。

```bash
python3 tools/pipeline/scout.py                    # 全部来源
python3 tools/pipeline/scout.py --source 浙江宣传 --dry-run
```

安装定时器：`bash tools/daily/install_timers.sh intel`（being，00:00 UTC = 北京 08:00）。


