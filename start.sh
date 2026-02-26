#!/bin/bash
set -e

echo "=== Enterprise AI Assistant - Container Startup ==="

# Define database path - use persistent storage on HF Spaces
if [ -d "/data" ]; then
    DB_DIR="/data"
    echo "Using HF Spaces persistent storage at /data"
else
    DB_DIR="/app/database"
    echo "Using local database directory at /app/database"
fi

export DATABASE_PATH="${DB_DIR}/ecommerce.db"
mkdir -p "${DB_DIR}"

# Attempt to download DB from HuggingFace Dataset
if [ ! -f "${DATABASE_PATH}" ]; then
    echo "Database not found at ${DATABASE_PATH}, attempting download from HF Dataset..."
    python -c "
import os, sys
try:
    from huggingface_hub import hf_hub_download
    token = os.environ.get('HF_TOKEN')
    repo_id = os.environ.get('HF_DATASET_REPO', 'aniketp2009gmail/enterprise-ai-assistant-db')
    db_dir = os.environ.get('DATABASE_PATH', '/data/ecommerce.db')
    target_dir = os.path.dirname(db_dir)
    print(f'Downloading from {repo_id}...')
    hf_hub_download(
        repo_id=repo_id,
        filename='ecommerce.db',
        repo_type='dataset',
        token=token,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )
    print(f'Database downloaded successfully to {db_dir}')
except Exception as e:
    print(f'WARNING: Could not download database: {e}')
    print('The application will auto-seed a fresh database on startup.')
" || echo "Download script exited with error, will fall back to auto-seeding."
else
    echo "Database already exists at ${DATABASE_PATH}"
fi

echo "Starting FastAPI backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

echo "Waiting for FastAPI to start..."
sleep 8

# Verify FastAPI started successfully
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "ERROR: FastAPI failed to start. Check logs above."
    exit 1
fi
echo "FastAPI is running (PID: $FASTAPI_PID)"

echo "Starting Streamlit frontend on port 7860..."
streamlit run app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

echo "Streamlit started (PID: $STREAMLIT_PID)"

# Wait for either process to exit
wait -n $FASTAPI_PID $STREAMLIT_PID
EXIT_CODE=$?
echo "A process exited with code $EXIT_CODE. Shutting down..."

# If one exits, stop the other
kill $FASTAPI_PID $STREAMLIT_PID 2>/dev/null
wait
