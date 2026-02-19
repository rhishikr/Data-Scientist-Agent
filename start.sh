#!/usr/bin/env bash
# Start both backend and frontend servers.
# Frontend only starts after the backend is fully ready.
# Usage: bash start.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo "Shutting down servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# --- Backend ---
echo "Starting backend (uvicorn) on http://localhost:8000 ..."
cd "$ROOT_DIR/backend"
if [ -d "venv" ]; then
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
fi
python app.py 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
while ! curl -s http://127.0.0.1:8000/docs > /dev/null 2>&1; do
  # Exit if backend process died
  if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start."
    exit 1
  fi
  sleep 1
done
echo "Backend is ready."

# --- Frontend ---
echo "Starting frontend (vite) ..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend  → http://localhost:8000"
echo "Frontend → http://localhost:5173"
echo "Press Ctrl+C to stop both servers."

wait
