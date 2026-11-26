#!/usr/bin/env bash
# 一条命令看每日流水线的全部状态。
#   bash tools/daily/status.sh
set -uo pipefail
HOME_DIR="${WRITING_HOME:-/data/home/src/writing-engines}"
cd "$HOME_DIR" || { echo "找不到 $HOME_DIR"; exit 2; }

echo "═══ 定时器 ═══"
for r in write review; do
  u="writing-daily-$r.timer"
  printf '%-28s enabled=%-8s active=%-8s\n' "$u" \
    "$(systemctl --user is-enabled "$u" 2>/dev/null || echo -)" \
    "$(systemctl --user is-active "$u" 2>/dev/null || echo -)"
done
systemctl --user list-timers --all 2>/dev/null | grep -E 'writing-daily|^NEXT' | sed 's/^/  /'

echo
echo "═══ 最近 7 次发布 ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('drafts/daily/state.json')
if not p.exists():
    print("  (还没有记录)"); raise SystemExit
d = json.loads(p.read_text(encoding='utf-8'))
runs = d.get("runs", [])
revs = {(r["date"]): r for r in d.get("reviews", [])}
for r in runs[-7:]:
    rv = revs.get(r["date"], {})
    stars = f'{rv.get("stars","-")}/5' if rv else "待评"
    print(f'  {r["date"]}  {r["engine"]:22} 机检{r.get("score","-"):>5}  评审{stars:>6}  {r["title"][:26]}')
if runs:
    ok = sum(1 for r in runs if str(revs.get(r["date"], {}).get("verdict")) == "pass")
    print(f'  ── 共 {len(runs)} 篇，评审合格 {ok} 篇')
PY

echo
echo "═══ 最近评审指出的通病 ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('drafts/daily/state.json')
if not p.exists(): raise SystemExit
d = json.loads(p.read_text(encoding='utf-8'))
iss = []
for rv in d.get("reviews", [])[-5:]:
    for x in rv.get("issues", []) or []:
        if x not in iss: iss.append(x)
print("  " + ("；".join(iss[:8]) if iss else "(还没有)"))
PY

echo
echo "═══ 最近日志尾部 ═══"
for f in drafts/daily/logs/*.err; do
  [ -s "$f" ] && { echo "  ── $f"; tail -4 "$f" | sed 's/^/     /'; }
done 2>/dev/null | tail -20
[ -z "$(ls -A drafts/daily/logs 2>/dev/null)" ] && echo "  (无日志)"

echo
echo "═══ 仓库状态 ═══"
echo "  head: $(git log --oneline -1)"
echo "  未提交: $(git status --porcelain | wc -l) 个文件"
echo "  磁盘: $(df -h / | tail -1 | awk '{print $4}') 可用"