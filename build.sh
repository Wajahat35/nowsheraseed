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

echo "==> Build complete."
