#!/bin/bash
# Start LaTeX Research Agent (Local Development)
# Usage: ./scripts/start.sh
#
# This starts Ray Serve with your app. Access at http://localhost:8000
# For the full Kodosumi panel, run in a separate terminal:
#   uv run koco start --register http://localhost:8000/-/routes

set -e

cd "$(dirname "$0")/.."

echo "Starting LaTeX Research Agent..."

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Start Ray (if not running)
if ! uv run ray status &> /dev/null; then
    echo "Starting Ray..."
    uv run ray start --head
    sleep 2
fi

echo ""
echo "Starting Ray Serve at http://localhost:8000"
echo ""
echo "To use the Kodosumi panel, run in another terminal:"
echo "  uv run koco start --register http://localhost:8000/-/routes"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run serve (blocking)
uv run serve run src.app:fast_app
