#!/bin/sh
set -e
cd /app
echo "Applying database schema (drizzle push)..."
pnpm --filter @workspace/db run push
exec node --enable-source-maps artifacts/api-server/dist/index.mjs
