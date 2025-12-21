#!/bin/bash
# Start LaTeX Research Agent
# Usage: ./scripts/start.sh

set -e

cd "$(dirname "$0")/.."

echo "Starting LaTeX Research Agent..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start Ray (if not running)
if ! ray status &> /dev/null; then
    echo "Starting Ray..."
    uv run ray start --head
    sleep 2
fi

# Deploy and start
echo "Deploying service..."
uv run koco deploy --run --file ./data/config/config.yaml

echo "Starting panel and registering routes..."
uv run koco serve --register http://localhost:8000/-/routes

echo ""
echo "LaTeX Research Agent is running!"
echo "  Panel: http://localhost:3370"
echo "  API:   http://localhost:8000"
