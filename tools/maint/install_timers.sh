#!/usr/bin/env bash
# 在当前机器上安装维护定时器（systemd --user）。
#
#   bash tools/maint/install_timers.sh build     # being：每天重建站点 + 轻体检
#   bash tools/maint/install_timers.sh audit     # god：每天只读体检
#   bash tools/maint/install_timers.sh weekly    # god：每周一出一份周报
#   bash tools/maint/install_timers.sh status
#   bash tools/maint/install_timers.sh remove
#
# 时间均为 UTC。北京 = UTC+8。
set -euo pipefail

ROLE="${1:-status}"
HOME_DIR="${WRITING_HOME:-/data/home/src/writing-engines}"
UNIT_DIR="$HOME/.config/systemd/user"
PY="$(command -v python3)"
ENVF="$HOME/.dsh/.env"

mkdir -p "$UNIT_DIR" "$HOME_DIR/drafts/maint" "$HOME_DIR/drafts/daily/logs"

mk() {  # $1=名字 $2=OnCalendar
  cat > "$UNIT_DIR/writing-maint-$1.service" <<EOF
[Unit]
Description=writing-engines maintenance $1
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$HOME_DIR
Environment=HOME=$HOME
Environment=WRITING_HOME=$HOME_DIR
Environment=PATH=/data/home/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=-$ENVF
ExecStart=/bin/bash -lc "$PY -u $HOME_DIR/tools/maint/maintain.py --mode $1"
StandardOutput=append:$HOME_DIR/drafts/daily/logs/maint-$1.out
StandardError=append:$HOME_DIR/drafts/daily/logs/maint-$1.err
TimeoutStartSec=5400
Nice=15
EOF
  cat > "$UNIT_DIR/writing-maint-$1.timer" <<EOF
[Unit]
Description=writing-engines maintenance $1 timer

[Timer]
OnCalendar=$2
Persistent=true
RandomizedDelaySec=420
Unit=writing-maint-$1.service

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now "writing-maint-$1.timer" 2>&1 | tail -1
  echo "installed: writing-maint-$1.timer ($2 UTC)"
}

case "$ROLE" in
  # 写作端跑完（01:00）再重建站点，商品页才跟得上当天新文章
  build)  mk build  "*-*-* 03:00:00" ;;
  # 评审端跑完（02:00）再体检，报告才包含当天评审结论
  audit)  mk audit  "*-*-* 03:30:00" ;;
  weekly) mk weekly "Mon *-*-* 04:00:00" ;;
  remove)
    for r in build audit weekly; do
      systemctl --user disable --now "writing-maint-$r.timer" 2>/dev/null || true
      rm -f "$UNIT_DIR/writing-maint-$r.timer" "$UNIT_DIR/writing-maint-$r.service"
    done
    systemctl --user daemon-reload
    echo removed ;;
  status)
    systemctl --user list-timers --all 2>/dev/null | grep -E 'writing-(daily|maint)|^NEXT' || echo "(未安装)"
    for r in build audit weekly; do
      s="$(systemctl --user is-active "writing-maint-$r.timer" 2>/dev/null || true)"
      [ -n "$s" ] && echo "writing-maint-$r.timer = $s"
    done ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac