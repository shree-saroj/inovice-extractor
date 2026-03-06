#!/bin/bash

echo "🚀 Running Invoice Extractor Locally..."

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "📦 Starting Ollama service..."
    ollama serve &
    sleep 5
fi

# Check if models are available
echo "🤖 Checking models..."
if ! ollama list | grep -q "llama3"; then
    echo "⬇️  Pulling llama3..."
    ollama pull llama3
fi

if ! ollama list | grep -q "llama3.2-vision"; then
    echo "⬇️  Pulling llama3.2-vision..."
    ollama pull llama3.2-vision
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Run the application
echo "✅ Starting API server..."
echo "📄 API: http://localhost:8000"
echo "📚 Docs: http://localhost:8000/docs"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
