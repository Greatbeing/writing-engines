#!/usr/bin/env bash
# 编辑部流水线定时器（替换旧的 daily write/review）
#   bash tools/pipeline/install.sh writer    # being：01:00 / 05:00 推进（选题→撰稿→修改→发布）
#   bash tools/pipeline/install.sh reviewer  # god：02:00 / 06:00 评审；周日 08:00 引擎迭代
#   bash tools/pipeline/install.sh status
set -euo pipefail
ROLE="${1:-status}"; H="${WRITING_HOME:-/data/home/src/writing-engines}"
U="$HOME/.config/systemd/user"; PY="$(command -v python3)"; mkdir -p "$U" "$H/drafts/daily/logs"
unit(){ # name args calendar...
  n=$1; a=$2; shift 2
  cat >"$U/writing-pipe-$n.service" <<EOF
[Service]
Type=oneshot
WorkingDirectory=$H
Environment=WRITING_HOME=$H
Environment=PATH=/data/home/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=-$HOME/.dsh/.env
ExecStart=/bin/bash -lc "cd $H && git pull -q --rebase --autostash origin master; $PY -u tools/pipeline/pipeline.py $a"
StandardOutput=append:$H/drafts/daily/logs/pipe-$n.out
StandardError=append:$H/drafts/daily/logs/pipe-$n.err
TimeoutStartSec=5400
EOF
  { echo "[Timer]"; for c in "$@"; do echo "OnCalendar=$c"; done; echo "Persistent=true"; echo "[Install]"; echo "WantedBy=timers.target"; } >"$U/writing-pipe-$n.timer"
  systemctl --user daemon-reload; systemctl --user enable --now "writing-pipe-$n.timer"; echo "installed $n"
}
off(){ systemctl --user disable --now "writing-daily-$1.timer" 2>/dev/null || true; }
case "$ROLE" in
  writer)   off write; unit step step "*-*-* 01:00:00" "*-*-* 05:00:00" ;;
  reviewer) off review; unit review review "*-*-* 02:00:00" "*-*-* 06:00:00"; unit evolve evolve "Sun *-*-* 08:00:00" ;;
  *) systemctl --user list-timers --all | grep -E 'writing|NEXT' ;;
esac