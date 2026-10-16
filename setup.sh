#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

echo "🚀 Setting up Invoice Extractor..."

# Create directories
mkdir -p app/extractors app/utils

# Start Docker services
echo "📦 Starting Docker services..."
docker compose up -d --build

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
ready=false
for attempt in {1..60}; do
    if docker compose exec -T ollama ollama list > /dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
if [[ "$ready" != true ]]; then
    echo "Ollama did not become ready. Check: docker compose logs ollama"
    exit 1
fi

# Pull required models
echo "🤖 Pulling LLM models..."
for model in "${STRUCTURE_MODEL:-llama3}" "${VISION_MODEL:-llava}"; do
    if ! docker compose exec -T ollama ollama show "$model" > /dev/null 2>&1; then
        docker compose exec -T ollama ollama pull "$model"
    fi
done

echo "✅ Setup complete!"
echo "📄 API available at: http://localhost:8000"
echo "📚 Docs available at: http://localhost:8000/docs"
