"""
Run SQL migrations from a directory.
Intended for Docker startup: runs each *.sql file once (tracked in DB), in sorted order.
"""
import os
import sys
from pathlib import Path

# Migrations directory (set in Docker to /app/migrations)
MIGRATIONS_DIR = os.environ.get("MIGRATIONS_DIR", "/app/migrations")

# Table used to record which migrations have already been applied
TRACKING_TABLE = "schema_migrations"


def get_connection_url():
    """Convert DATABASE_URL to format psycopg expects (postgresql:// not postgresql+psycopg://)."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    if url.startswith("postgresql+psycopg"):
        url = url.replace("postgresql+psycopg", "postgresql", 1)
    return url


def ensure_tracking_table(conn):
    """Create the schema_migrations table if it doesn't exist."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            name VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def applied_migrations(conn):
    """Return set of migration filenames that have already been applied."""
    ensure_tracking_table(conn)
    with conn.cursor() as cur:
        cur.execute(f"SELECT name FROM {TRACKING_TABLE}")
        return {row[0] for row in cur.fetchall()}


def run_migrations():
    """Execute each .sql file in MIGRATIONS_DIR in sorted order, only if not already applied."""
    print(f"Migration runner: MIGRATIONS_DIR={MIGRATIONS_DIR}")
    migrations_path = Path(MIGRATIONS_DIR)
    if not migrations_path.is_dir():
        print(f"Migrations directory not found: {MIGRATIONS_DIR} (skipping)")
        return 0

    url = get_connection_url()
    if not url:
        print("DATABASE_URL not set (skipping migrations)")
        return 0

    try:
        import psycopg
    except ImportError:
        print("psycopg not installed (skipping migrations)")
        return 0

    sql_files = sorted(migrations_path.glob("*.sql"))
    if not sql_files:
        print("No .sql files in migrations directory")
        return 0

    try:
        with psycopg.connect(url) as conn:
            applied = applied_migrations(conn)
            conn.commit()

            pending = [p for p in sql_files if p.name not in applied]
            if not pending:
                print("All migrations already applied.")
                return 0

            print(f"Running {len(pending)} new migration(s) from {MIGRATIONS_DIR}...")
            for path in pending:
                print(f"  Running {path.name}...")
                sql = path.read_text(encoding="utf-8", errors="replace")
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        f"INSERT INTO {TRACKING_TABLE} (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                        (path.name,),
                    )
                conn.commit()
                print(f"  ✓ {path.name}")
            print("✓ Migrations completed successfully")
        return 0
    except Exception as e:
        print(f"ERROR running migrations: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())
