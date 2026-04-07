#!/bin/bash
# Run this from New_Doc_Hub/ folder
# It reads NOTION_TOKEN and NOTION_DATABASE_ID from .env automatically

cd ~/Desktop/Intership_work/New_Doc_Hub

# Load .env values
export $(grep -v '^#' .env | grep -v '^$' | xargs)

echo "Ingesting Notion docs..."
echo "Token prefix: ${NOTION_TOKEN:0:10}..."
echo "Database ID: $NOTION_DATABASE_ID"

curl -s -X POST http://localhost:8000/rag/ingest \
     -H "Content-Type: application/json" \
     -d "{
       \"token\": \"$NOTION_TOKEN\",
       \"database_id\": \"$NOTION_DATABASE_ID\",
       \"force_reingest\": false
     }" | python3 -m json.tool

echo ""
echo "Checking stats..."
curl -s http://localhost:8000/rag/stats | python3 -m json.tool