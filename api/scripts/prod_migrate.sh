#!/usr/bin/env bash
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL no está definida"
  exit 1
fi

python -m alembic current
python -m alembic upgrade head
python -m alembic current