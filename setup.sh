#!/bin/bash

echo "🚀 Setting up Invoice Extractor..."

# Create directories
mkdir -p app/extractors app/utils

# Start Docker services
echo "📦 Starting Docker services..."
docker compose up -d

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
sleep 15

# Pull required models
echo "🤖 Pulling LLM models..."
docker compose exec -T ollama ollama pull llama3
docker compose exec -T ollama ollama pull llama3.2-vision

echo "✅ Setup complete!"
echo "📄 API available at: http://localhost:8000"
echo "📚 Docs available at: http://localhost:8000/docs"
