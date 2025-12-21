#!/bin/bash
# Stop LaTeX Research Agent
# Usage: ./scripts/stop.sh

set -e

cd "$(dirname "$0")/.."

echo "Stopping LaTeX Research Agent..."

# Stop spooler
uv run koco spool --stop 2>/dev/null || true

# Stop Ray
uv run ray stop 2>/dev/null || true

echo "Stopped."
