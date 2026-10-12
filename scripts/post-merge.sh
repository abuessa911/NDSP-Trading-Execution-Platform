#!/bin/bash
set -e
pnpm install --frozen-lockfile
# NEX uses explicit operator-run Alembic migrations only. Never mutate a database
# on merge (including the inherited, unused Drizzle template).
