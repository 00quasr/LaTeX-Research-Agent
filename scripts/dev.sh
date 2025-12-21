#!/bin/bash
# Development mode with auto-reload
# Usage: ./scripts/dev.sh

set -e

cd "$(dirname "$0")/.."

echo "Starting in development mode (auto-reload enabled)..."

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

echo "Starting with auto-reload..."
echo "  Service: http://localhost:8000"
echo "  Press Ctrl+C to stop"
echo ""

# Run with serve (watches for file changes)
uv run serve run src.app:fast_app
