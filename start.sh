#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8020
