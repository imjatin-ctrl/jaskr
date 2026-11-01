#!/usr/bin/env bash
# =====================================================================
# Jaskr GymGrid - One-Command Setup Script
# Initializes seed data, verifies database schema, runs tests, and prepares server
# =====================================================================

set -e

echo "=== 1. Generating Deterministic Seed CSVs ==="
cd db/seed_data
python3 seed_data.py data
cd ../..

echo "=== 2. Loading Seed Dataset into Database ==="
python3 db/load_seed.py

echo "=== 3. Executing Pytest Verification Suite ==="
python3 -m pytest tests/ -v

echo ""
echo "=========================================================="
echo "  Jaskr GymGrid Setup Successfully Completed!"
echo "  Run the server: python3 run.py"
echo "  Access Port: http://127.0.0.1:5000 (or 5050 if 5000 is occupied)"
echo "=========================================================="
