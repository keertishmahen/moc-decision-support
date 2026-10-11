#!/bin/bash
set -e
cd /home/site/wwwroot
if [ -f antenv/bin/activate ]; then
  source antenv/bin/activate
elif [ -f /antenv/bin/activate ]; then
  source /antenv/bin/activate
fi
export PYTHONPATH=/home/site/wwwroot
exec python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
