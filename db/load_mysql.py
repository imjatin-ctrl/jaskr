#!/usr/bin/env python3
"""
Jaskr GymGrid - MySQL Database Setup & Seed Importer
Creates all 24 tables, indexes, views, stored procedures, triggers, DCL roles,
and loads seed data into MySQL 8.x.
"""
import os
import sys
import re
import getpass
import csv
import mysql.connector
from werkzeug.security import generate_password_hash

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "seed_data", "data")
DEMO_PASS = "Demo@1234"

LOAD_ORDER = [
    "organizations",
    "branches",
    "branch_hours",
    "facilities",
    "branch_facilities",
    "users",
    "staff",
    "trainers",
    "trainer_assignments",
    "members",
    "membership_plans",
    "branch_access_rules",
    "memberships",
    "invoices",
    "invoice_items",
    "payments",
    "refunds",
    "expense_categories",
    "expenses",
    "branch_budgets",
    "attendance",
    "training_sessions",
    "equipment",
    "audit_log"
]


def execute_sql_file_direct(conn, sql_path):
    """
    Executes an SQL file directly using mysql.connector.
    Handles standard SQL, multi-statement scripts, and DELIMITER-based procedures/triggers.
    """
    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    cur = conn.cursor()

    if "DELIMITER" in content:
        # Strip all DELIMITER statements before splitting
        clean_content = re.sub(r"DELIMITER\s+\S+", "", content, flags=re.IGNORECASE)
        parts = clean_content.split("$$")
        for part in parts:
            # Remove comment-only lines
            lines = [l for l in part.splitlines() if not l.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if stmt and stmt != ";":
                if stmt.endswith(";"):
                    stmt = stmt[:-1].strip()
                try:
                    cur.execute(stmt)
                except mysql.connector.Error as e:
                    # Ignore non-fatal drop errors
                    if "does not exist" not in str(e).lower():
                        print(f"    [Notice in {os.path.basename(sql_path)}]: {e}")
    else:
        # Standard SQL split by semicolon
        statements = []
        for raw_stmt in content.split(";"):
            lines = [l for l in raw_stmt.splitlines() if not l.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if stmt:
                statements.append(stmt)

        for stmt in statements:
            try:
                cur.execute(stmt)
            except mysql.connector.Error as e:
                # Ignore non-fatal user cleanup errors in dcl.sql
                if "unknown user" in str(e).lower() or "can't drop" in str(e).lower():
                    continue
                print(f"    [Notice in {os.path.basename(sql_path)}]: {e}")

    conn.commit()
    cur.close()


def main():
    print("=" * 60)
    print("  Jaskr GymGrid - MySQL 8.x Automated Setup & Seed Loader")
    print("=" * 60)

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HERE, "..", ".env"))
    except ImportError:
        pass

    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("MYSQL_PORT", 3306))
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD")

    if not password:
        if len(sys.argv) > 1:
            password = sys.argv[1]
        else:
            try:
                password = getpass.getpass(f"Enter MySQL password for '{user}': ")
            except Exception:
                password = input(f"Enter MySQL password for '{user}': ")

    # Step 1: Connect and create database
    print(f"\n[1/7] Connecting to MySQL at {host}:{port} as '{user}'...")
    try:
        root_conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        cur = root_conn.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS gymgrid CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        root_conn.commit()
        root_conn.close()
        print("  [OK] Database 'gymgrid' is ready.")
    except mysql.connector.Error as err:
        print(f"\n[ERROR] Connection failed: {err}")
        if err.errno == 1045:
            print("\n>> Access Denied: The password you entered for MySQL user 'root' is incorrect.")
            print(">> Please check the password you set during MySQL installation or in MySQL Workbench.")
        elif err.errno == 2003:
            print("\n>> Can't connect to MySQL server. Ensure the 'MySQL80' Windows service is running.")
        sys.exit(1)

    # Reconnect targeting gymgrid database
    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="gymgrid"
    )

    # Step 2: Run schema.sql
    print("[2/7] Creating 24 relational tables (schema.sql)...")
    execute_sql_file_direct(conn, os.path.join(HERE, "schema.sql"))
    print("  [OK] Tables created.")

    # Step 3: Run constraints & indexes
    print("[3/7] Applying constraints & composite indexes (constraints_indexes.sql)...")
    execute_sql_file_direct(conn, os.path.join(HERE, "constraints_indexes.sql"))
    print("  [OK] Constraints & indexes applied.")

    # Step 4: Run views
    print("[4/7] Creating analytical database views (views.sql)...")
    execute_sql_file_direct(conn, os.path.join(HERE, "views.sql"))
    print("  [OK] Views created.")

    # Step 5: Run stored procedures
    print("[5/7] Installing stored procedures (procedures.sql)...")
    execute_sql_file_direct(conn, os.path.join(HERE, "procedures.sql"))
    print("  [OK] Stored procedures installed.")

    # Step 6: Run triggers & DCL
    print("[6/7] Installing audit triggers & DCL user accounts (triggers.sql & dcl.sql)...")
    execute_sql_file_direct(conn, os.path.join(HERE, "triggers.sql"))
    execute_sql_file_direct(conn, os.path.join(HERE, "dcl.sql"))
    print("  [OK] Triggers & DCL users created.")

    # Step 7: Load Seed CSVs
    print("[7/7] Inserting deterministic seed records across 24 relations...")
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    hashed_pass = generate_password_hash(DEMO_PASS)
    counts = {}

    for table in LOAD_ORDER:
        csv_file = os.path.join(DATA_DIR, f"{table}.csv")
        if not os.path.exists(csv_file):
            print(f"  [Warning]: {csv_file} not found!")
            continue

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

            cols = []
            for col in header:
                if col == "day_of_week_0_mon":
                    cols.append("day_of_week")
                else:
                    cols.append(col)

            placeholders = ",".join(["%s"] * len(cols))
            sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"

            rows_to_insert = []
            for raw_row in reader:
                row = []
                for idx, val in enumerate(raw_row):
                    if val == "":
                        row.append(None)
                    elif table == "users" and cols[idx] == "password_hash" and val == "{{HASH_ON_LOAD}}":
                        row.append(hashed_pass)
                    else:
                        row.append(val)
                rows_to_insert.append(row)

            cur.executemany(sql, rows_to_insert)
            counts[table] = len(rows_to_insert)

    cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  [SUCCESS] MYSQL SETUP & SEED LOAD COMPLETED!")
    print("=" * 60)
    for tbl, cnt in counts.items():
        print(f"  {tbl:22s}: {cnt:>6,d} rows loaded")
    print(f"\nTotal tables populated in MySQL: {len(counts)}")

    # Save credentials to .env for Flask web server
    env_file = os.path.join(HERE, "..", ".env")
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"MYSQL_HOST={host}\nMYSQL_PORT={port}\nMYSQL_USER={user}\nMYSQL_PASSWORD={password}\nMYSQL_DB=gymgrid\n")
    print("  [OK] Connection settings saved to .env file.")
    print("\nNext step: Start the web server:")
    print("  python run.py")


if __name__ == "__main__":
    main()
