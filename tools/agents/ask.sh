#!/usr/bin/env bash
# 四个 agent 的统一入口。写文章、评审、查代码都用它，不要各写各的参数。
#
#   tools/agents/ask.sh dsh      prompt.txt
#   tools/agents/ask.sh claude   prompt.txt
#   tools/agents/ask.sh codex    prompt.txt --cwd /data/home/src/writing-engines
#   tools/agents/ask.sh opencode prompt.txt --model magpie/group/daily
#
#   echo "问题" | tools/agents/ask.sh claude -        # 从 stdin 读
#
# 选项：
#   --cwd DIR       工作目录（codex 强烈建议给，否则会把当前目录整个读进上下文）
#   --model M       覆盖模型
#   --timeout S     超时秒数，默认 300
#   --json          机器可读输出（dsh 支持；opencode 支持；其余忽略）
#   --allow-write   codex 解除只读沙箱（默认 read-only，写文件必须显式开）
#
# 退出码：0 成功；2 参数错；3 未安装；124 超时；其他 = 工具自身失败
set -uo pipefail

TOOL="${1:-}"; shift || true
PROMPT="${1:-}"; shift || true
[ -z "$TOOL" ] || [ -z "$PROMPT" ] && { sed -n '2,20p' "$0"; exit 2; }

CWD="$PWD"; MODEL=""; TIMEOUT=300; JSON=0; WRITE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --json) JSON=1; shift ;;
    --allow-write) WRITE=1; shift ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

if [ "$PROMPT" = "-" ]; then TEXT="$(cat)"; else
  [ -f "$PROMPT" ] || { echo "找不到提示词文件：$PROMPT" >&2; exit 2; }
  TEXT="$(cat "$PROMPT")"
fi

command -v "$TOOL" >/dev/null 2>&1 || { echo "$TOOL 未安装" >&2; exit 3; }

# magpie 网关的 key（claude/codex/opencode 都靠它路由，不需要外部 API key）
if [ -z "${MAGPIE_GATEWAY_KEY:-}" ] && [ -f "$HOME/.dsh/.env" ]; then
  set -a; . "$HOME/.dsh/.env"; set +a
fi

case "$TOOL" in
  dsh)
    if [ "$JSON" = 1 ]; then
      timeout "$TIMEOUT" dsh --profile headless --json "$TEXT"
    else
      timeout "$TIMEOUT" dsh --profile headless "$TEXT"
    fi
    ;;
  claude)
    # -p 一次性回答；不挂危险权限；模型可用 --model 覆盖
    args=(-p --output-format text)
    [ -n "$MODEL" ] && args+=(--model "$MODEL")
    printf '%s' "$TEXT" | timeout "$TIMEOUT" claude "${args[@]}"
    ;;
  codex)
    # 默认 read-only 沙箱：想让它改文件必须显式 --allow-write
    sandbox="read-only"; [ "$WRITE" = 1 ] && sandbox="workspace-write"
    args=(exec --skip-git-repo-check -s "$sandbox" -C "$CWD")
    [ -n "$MODEL" ] && args+=(-m "$MODEL")
    [ "$JSON" = 1 ] && args+=(--json)
    timeout "$TIMEOUT" codex "${args[@]}" "$TEXT"
    ;;
  opencode)
    args=(run)
    [ -n "$MODEL" ] && args+=(-m "$MODEL")
    [ "$JSON" = 1 ] && args+=(--format json)
    cd "$CWD" && timeout "$TIMEOUT" opencode "${args[@]}" "$TEXT"
    ;;
  *)
    echo "未知工具：$TOOL（可选 dsh / claude / codex / opencode）" >&2; exit 2 ;;
esac
