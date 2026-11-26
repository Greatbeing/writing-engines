#!/usr/bin/env bash
# 统一模型调用层：默认走后端自带的 magpie 网关，无需任何外部 API key。
#
#   首选  magpie（127.0.0.1:3425，key 从 ~/.dsh/.env 取）
#   兜底  ANTHROPIC_API_KEY / OPENAI_API_KEY（若将来换环境）
#
# 用法： llm.sh <system_prompt_file> <user_prompt_file>
# 输出： stdout = 模型正文
set -euo pipefail

SYS="${1:?system prompt file}"
USR="${2:?user prompt file}"

# magpie 的 key 只存在于 ~/.dsh/.env
if [ -z "${MAGPIE_GATEWAY_KEY:-}" ] && [ -f "$HOME/.dsh/.env" ]; then
  set -a; . "$HOME/.dsh/.env"; set +a
fi

BASE="${MAGPIE_BASE:-http://127.0.0.1:3425/v1}"
MODEL="${LLM_MODEL:-group/daily}"
CONNECT_TIMEOUT="${LLM_CONNECT_TIMEOUT:-30}"
READ_TIMEOUT="${LLM_READ_TIMEOUT:-600}"

if [ -n "${MAGPIE_GATEWAY_KEY:-}" ]; then
  exec python3 - "$SYS" "$USR" "$BASE" "$MODEL" "${MAGPIE_GATEWAY_KEY}" \
                   "$CONNECT_TIMEOUT" "$READ_TIMEOUT" <<'PY'
import json, sys, time, urllib.request, urllib.error

sysf, usrf, base, model, key, ct, rt = sys.argv[1:8]
payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": open(sysf, encoding="utf-8").read()},
        {"role": "user", "content": open(usrf, encoding="utf-8").read()},
    ],
    "temperature": 0.9,
}
body = json.dumps(payload).encode()
url = base.rstrip("/") + "/chat/completions"

last = None
for attempt in range(1, 4):
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    })
    try:
        with urllib.request.urlopen(req, timeout=float(ct) + float(rt)) as r:
            d = json.load(r)
        print(d["choices"][0]["message"]["content"].strip())
        sys.exit(0)
    except Exception as exc:                       # noqa: BLE001
        last = exc
        print(f"[llm] 第 {attempt} 次失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        time.sleep(5 * attempt)
print(f"[llm] magpie 调用连续失败：{last}", file=sys.stderr)
sys.exit(4)
PY
fi

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  exec claude -p --model "${LLM_MODEL:-claude-sonnet-4-5-20250929}" \
    --append-system-prompt "$(cat "$SYS")" < "$USR"
fi

echo "[llm] 既没有 magpie 网关，也没有 ANTHROPIC_API_KEY / OPENAI_API_KEY" >&2
exit 3