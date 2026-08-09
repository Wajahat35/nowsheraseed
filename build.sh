#!/usr/bin/env bash
# build.sh — Render build script for Noshera Seeds ERP
# Runs automatically on every deploy.
set -o errexit  # Exit immediately if any command fails

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Running production database setup and data import..."
python manage.py setup_production

echo "==> Build complete."
