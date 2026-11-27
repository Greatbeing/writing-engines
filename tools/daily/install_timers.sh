#!/usr/bin/env bash
# 在当前机器上安装每日定时器（systemd --user）。
#
#   bash tools/daily/install_timers.sh write    # 写作端（being）
#   bash tools/daily/install_timers.sh review   # 评审端（god）
#   bash tools/daily/install_timers.sh status
#   bash tools/daily/install_timers.sh remove
#
# 时间均为 UTC：写 01:00（北京 09:00），评 02:00（北京 10:00）。
set -euo pipefail

ROLE="${1:-status}"
HOME_DIR="${WRITING_HOME:-/data/home/src/writing-engines}"
UNIT_DIR="$HOME/.config/systemd/user"
PY="$(command -v python3)"
ENVF="$HOME/.dsh/.env"

mkdir -p "$UNIT_DIR"

write_unit() {  # $1=name $2=script $3=OnCalendar
  cat > "$UNIT_DIR/writing-daily-$1.service" <<EOF
[Unit]
Description=writing-engines daily $1
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$HOME_DIR
Environment=HOME=$HOME
Environment=WRITING_HOME=$HOME_DIR
Environment=PATH=/data/home/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=-$ENVF
ExecStart=/bin/bash -lc "$PY -u $HOME_DIR/tools/daily/$2.py"
StandardOutput=append:$HOME_DIR/drafts/daily/logs/$1.out
StandardError=append:$HOME_DIR/drafts/daily/logs/$1.err
TimeoutStartSec=5400
Nice=10
EOF
  cat > "$UNIT_DIR/writing-daily-$1.timer" <<EOF
[Unit]
Description=writing-engines daily $1 timer

[Timer]
OnCalendar=$3
Persistent=true
RandomizedDelaySec=300
Unit=writing-daily-$1.service

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now "writing-daily-$1.timer"
  echo "installed: writing-daily-$1.timer ($3 UTC)"
}

case "$ROLE" in
  write)
    mkdir -p "$HOME_DIR/drafts/daily/logs"
    write_unit write write "*-*-* 01:00:00"
    ;;
  review)
    mkdir -p "$HOME_DIR/drafts/daily/logs"
    write_unit review review "*-*-* 02:00:00"
    ;;
  distill)
    # 每周日 03:00 UTC 回测一个引擎，结果写 eval/distill-backtest.md 并推送
    mkdir -p "$HOME_DIR/drafts/daily/logs"
    cat > "$UNIT_DIR/writing-daily-distill.service" <<EOF
[Unit]
Description=writing-engines weekly distill backtest
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$HOME_DIR
Environment=HOME=$HOME
EnvironmentFile=-$ENVF
ExecStart=/bin/bash -lc "cd $HOME_DIR && git pull -q --rebase --autostash origin master; $PY -u tools/distill_backtest.py --next && git add eval/distill-backtest.md && git -c user.name=being -c user.email=being@caifeng commit -q -m 'eval: 蒸馏回测' && git push -q origin HEAD:master"
StandardOutput=append:$HOME_DIR/drafts/daily/logs/distill.out
StandardError=append:$HOME_DIR/drafts/daily/logs/distill.err
TimeoutStartSec=3600
Nice=10
EOF
    cat > "$UNIT_DIR/writing-daily-distill.timer" <<EOF
[Unit]
Description=writing-engines weekly distill backtest timer

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true
Unit=writing-daily-distill.service

[Install]
WantedBy=timers.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now writing-daily-distill.timer || systemctl --user start writing-daily-distill.timer
    echo "installed: writing-daily-distill.timer (Sun 03:00 UTC)"
    ;;
  remove)
    for r in write review distill; do
      systemctl --user disable --now "writing-daily-$r.timer" 2>/dev/null || true
      rm -f "$UNIT_DIR/writing-daily-$r.timer" "$UNIT_DIR/writing-daily-$r.service"
    done
    systemctl --user daemon-reload
    echo "removed"
    ;;
  status)
    systemctl --user list-timers --all 2>/dev/null | grep -E 'writing-daily|NEXT' || echo "(未安装)"
    for r in write review; do
      s="$(systemctl --user is-active writing-daily-$r.timer 2>/dev/null || true)"
      [ -n "$s" ] && echo "writing-daily-$r.timer = $s"
    done
    ;;
  *)
    sed -n '2,12p' "$0"
    exit 2
    ;;
esac