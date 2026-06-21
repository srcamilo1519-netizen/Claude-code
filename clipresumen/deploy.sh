#!/usr/bin/env bash
# Deploy the latest code with near-zero downtime:
#   pull → build → migrate → recreate app services.
#
#   ./deploy.sh
#
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.prod.yml"

echo "==> Pulling latest code"
git pull --ff-only

echo "==> Building images (running containers stay up)"
$COMPOSE build backend frontend

echo "==> Ensuring database is up"
$COMPOSE up -d postgres

echo "==> Running database migrations"
$COMPOSE run --rm backend alembic upgrade head

echo "==> Recreating app services"
# postgres and nginx keep running; only backend/frontend are replaced, so the
# blip is limited to the few seconds those containers take to restart.
$COMPOSE up -d --no-deps backend frontend

echo "==> Pruning dangling images"
docker image prune -f >/dev/null || true

echo "==> Deploy complete"
$COMPOSE ps
