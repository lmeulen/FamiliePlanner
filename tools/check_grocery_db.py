#!/usr/bin/env python3
"""Check if grocery tables exist in database."""

import sqlite3

try:
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    # Check for grocery tables
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name LIKE 'grocery%'
        ORDER BY name
    """
    )

    tables = cursor.fetchall()

    if tables:
        print("Grocery tables found:")
        for table in tables:
            print(f"  - {table[0]}")

            # Count rows
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"    ({count} rows)")
    else:
        print("No grocery tables found in database")
        print("\nNeed to run: alembic upgrade head")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    print("\nDatabase may not exist yet. Run migrations with: alembic upgrade head")
