#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p data

CHROMA_DIR="${CHROMA_DIR:-data/chroma}"

if [[ ! -d "${CHROMA_DIR}" ]] || [[ -z "$(ls -A "${CHROMA_DIR}" 2>/dev/null || true)" ]]; then
  echo "Chroma index missing or empty — running first-run competency KB ingest..."
  python -m resume_screener.rag.ingest
else
  echo "Chroma index present — skipping ingest."
fi

exec streamlit run app/streamlit_app.py \
  --server.headless=true \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --browser.gatherUsageStats=false
