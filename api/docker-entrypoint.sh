#!/bin/bash
set -e

echo "[migrate] Running Alembic migrations..."
alembic upgrade head

echo "[migrate] Checking if DB needs seeding..."
ROW_COUNT=$(python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['SYNC_DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM organisations')
print(cur.fetchone()[0])
conn.close()
")

if [ "$ROW_COUNT" = "0" ]; then
    echo "[migrate] Seeding database..."
    psql "$SYNC_DATABASE_URL" -f /app/seed.sql
    echo "[migrate] Seed complete — admin credentials:"
    echo "  Client ID:     am2Eojw8-UcPIfNa8UuWCA"
    echo "  Client Secret: Benchmark2024!"
else
    echo "[migrate] DB already seeded ($ROW_COUNT org(s) found), skipping."
fi

echo "[migrate] Done."
