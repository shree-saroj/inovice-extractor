#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export VISION_MODEL="${VISION_MODEL:-llava}"
export STRUCTURE_MODEL="${STRUCTURE_MODEL:-llama3}"
if ! curl -fsS --max-time 5 "$OLLAMA_HOST/api/version"; then
    echo "Start Ollama separately (ollama serve), or set OLLAMA_HOST to a running server."
    exit 1
fi
if [[ ! -x venv/bin/python ]]; then
    python3 -m venv venv
fi
venv/bin/python -m pip install -r requirements.txt
for model in "$VISION_MODEL" "$STRUCTURE_MODEL"; do
    venv/bin/python - "$model" <<'PY'
import ollama, sys
client = ollama.Client()
try:
    client.show(sys.argv[1])
except ollama.ResponseError as error:
    if error.status_code != 404:
        raise
    print(f"Downloading missing model: {sys.argv[1]}", flush=True)
    client.pull(sys.argv[1])
PY
done
export API_PORT="${API_PORT:-8001}"
echo "API docs: http://127.0.0.1:$API_PORT/docs"
if [[ "${1:-}" == "--debug" ]]; then
    exec venv/bin/python -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT"
fi
exec venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT"
