#!/usr/bin/env python3
"""
Jaskr GymGrid - Seed Data Loader
Loads deterministic seed CSVs into the relational database (MySQL 8.x or SQLite fallback).
Replaces {{HASH_ON_LOAD}} with real hashed password for demo accounts.
"""
import os
import sys
import csv
import sqlite3
import datetime as dt
from werkzeug.security import generate_password_hash

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "seed_data", "data")
SQLITE_DB = os.path.join(HERE, "gymgrid.db")
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


def init_sqlite_schema(conn):
    """Creates SQLite schema matching the MySQL schema."""
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")
    
    # Drop existing tables
    tables = [
        "audit_log", "equipment", "training_sessions", "attendance", "branch_budgets",
        "expenses", "expense_categories", "refunds", "payments", "invoice_items",
        "invoices", "memberships", "branch_access_rules", "membership_plans",
        "members", "trainer_assignments", "trainers", "staff", "users",
        "branch_facilities", "facilities", "branch_hours", "branches", "organizations"
    ]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t};")
    
    # Create tables
    cur.executescript("""
    CREATE TABLE organizations (
        organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_email TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        brand_type TEXT NOT NULL DEFAULT 'independent',
        headquarters_city TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE branches (
        branch_id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        phone TEXT NOT NULL,
        description TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
    );

    CREATE TABLE branch_hours (
        branch_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        open_time TEXT NOT NULL,
        close_time TEXT NOT NULL,
        is_closed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (branch_id, day_of_week),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE facilities (
        facility_id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL
    );

    CREATE TABLE branch_facilities (
        branch_id INTEGER NOT NULL,
        facility_id INTEGER NOT NULL,
        availability_notes TEXT DEFAULT '',
        PRIMARY KEY (branch_id, facility_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
        FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
    );

    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        last_login TEXT NULL
    );

    CREATE TABLE staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        organization_id INTEGER NULL,
        branch_id INTEGER NULL,
        job_role TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        hired_date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE trainers (
        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        phone TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
        FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE trainer_assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        trainer_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NULL,
        FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        home_branch_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        registration_date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (home_branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE membership_plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        plan_name TEXT NOT NULL,
        duration_months INTEGER NOT NULL,
        price REAL NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
    );

    CREATE TABLE branch_access_rules (
        access_rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        access_type TEXT NOT NULL,
        conditions TEXT NOT NULL,
        FOREIGN KEY (plan_id) REFERENCES membership_plans(plan_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE memberships (
        membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY (member_id) REFERENCES members(member_id),
        FOREIGN KEY (plan_id) REFERENCES membership_plans(plan_id)
    );

    CREATE TABLE invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL UNIQUE,
        member_id INTEGER NOT NULL,
        membership_id INTEGER NOT NULL,
        invoice_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY (member_id) REFERENCES members(member_id),
        FOREIGN KEY (membership_id) REFERENCES memberships(membership_id)
    );

    CREATE TABLE invoice_items (
        invoice_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
    );

    CREATE TABLE payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        membership_id INTEGER NOT NULL,
        invoice_id INTEGER NULL,
        branch_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'pending',
        transaction_ref TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (membership_id) REFERENCES memberships(membership_id),
        FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE refunds (
        refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER NOT NULL,
        refund_amount REAL NOT NULL,
        refund_date TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'requested',
        FOREIGN KEY (payment_id) REFERENCES payments(payment_id)
    );

    CREATE TABLE expense_categories (
        expense_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL
    );

    CREATE TABLE expenses (
        expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL,
        expense_category_id INTEGER NOT NULL,
        recorded_by INTEGER NOT NULL,
        expense_date TEXT NOT NULL,
        amount REAL NOT NULL,
        vendor TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
        FOREIGN KEY (expense_category_id) REFERENCES expense_categories(expense_category_id),
        FOREIGN KEY (recorded_by) REFERENCES users(user_id)
    );

    CREATE TABLE branch_budgets (
        budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL,
        expense_category_id INTEGER NOT NULL,
        budget_period TEXT NOT NULL,
        budget_amount REAL NOT NULL,
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
        FOREIGN KEY (expense_category_id) REFERENCES expense_categories(expense_category_id)
    );

    CREATE TABLE attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        check_in TEXT NOT NULL,
        check_out TEXT NULL,
        FOREIGN KEY (member_id) REFERENCES members(member_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE training_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        trainer_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        session_start TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL DEFAULT 60,
        status TEXT NOT NULL DEFAULT 'scheduled',
        focus TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (member_id) REFERENCES members(member_id),
        FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE equipment (
        equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL,
        equipment_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        condition_status TEXT NOT NULL DEFAULT 'good',
        last_serviced_on TEXT NOT NULL,
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE audit_log (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER NOT NULL,
        old_value TEXT NULL,
        new_value TEXT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # Create Views
    cur.executescript("""
    DROP VIEW IF EXISTS v_active_memberships;
    CREATE VIEW v_active_memberships AS
    SELECT 
        ms.membership_id,
        ms.member_id,
        m.full_name AS member_name,
        m.phone AS member_phone,
        u.email AS member_email,
        p.plan_id,
        p.plan_name,
        p.duration_months,
        p.price AS plan_price,
        o.organization_id,
        o.name AS organization_name,
        b.branch_id AS home_branch_id,
        b.name AS home_branch_name,
        b.city AS home_branch_city,
        ms.start_date,
        ms.end_date,
        ms.status AS membership_status,
        CAST((JULIANDAY(ms.end_date) - JULIANDAY('2026-10-30')) AS INTEGER) AS days_remaining
    FROM memberships ms
    JOIN members m ON ms.member_id = m.member_id
    JOIN users u ON m.user_id = u.user_id
    JOIN membership_plans p ON ms.plan_id = p.plan_id
    JOIN organizations o ON p.organization_id = o.organization_id
    JOIN branches b ON m.home_branch_id = b.branch_id
    WHERE ms.status = 'active';

    DROP VIEW IF EXISTS v_branch_financial_summary;
    CREATE VIEW v_branch_financial_summary AS
    SELECT 
        b.branch_id,
        b.name AS branch_name,
        b.city,
        o.organization_id,
        o.name AS organization_name,
        COALESCE(p_agg.gross_receipts, 0.0) AS gross_receipts,
        COALESCE(r_agg.total_refunds, 0.0) AS total_refunds,
        (COALESCE(p_agg.gross_receipts, 0.0) - COALESCE(r_agg.total_refunds, 0.0)) AS net_receipts,
        COALESCE(e_agg.operating_expenses, 0.0) AS operating_expenses,
        ((COALESCE(p_agg.gross_receipts, 0.0) - COALESCE(r_agg.total_refunds, 0.0)) - COALESCE(e_agg.operating_expenses, 0.0)) AS net_operating_margin
    FROM branches b
    JOIN organizations o ON b.organization_id = o.organization_id
    LEFT JOIN (
        SELECT branch_id, SUM(amount) AS gross_receipts
        FROM payments
        WHERE payment_status = 'successful'
        GROUP BY branch_id
    ) p_agg ON b.branch_id = p_agg.branch_id
    LEFT JOIN (
        SELECT p.branch_id, SUM(r.refund_amount) AS total_refunds
        FROM refunds r
        JOIN payments p ON r.payment_id = p.payment_id
        WHERE r.status = 'completed'
        GROUP BY p.branch_id
    ) r_agg ON b.branch_id = r_agg.branch_id
    LEFT JOIN (
        SELECT branch_id, SUM(amount) AS operating_expenses
        FROM expenses
        WHERE status IN ('paid', 'approved')
        GROUP BY branch_id
    ) e_agg ON b.branch_id = e_agg.branch_id;

    DROP VIEW IF EXISTS v_upcoming_invoices;
    CREATE VIEW v_upcoming_invoices AS
    SELECT 
        i.invoice_id,
        i.invoice_number,
        i.invoice_date,
        i.due_date,
        i.total AS invoice_amount,
        i.status AS invoice_status,
        m.member_id,
        m.full_name AS member_name,
        m.phone AS member_phone,
        u.email AS member_email,
        b.branch_id,
        b.name AS home_branch_name,
        o.organization_id,
        o.name AS organization_name,
        CAST((JULIANDAY('2026-10-30') - JULIANDAY(i.due_date)) AS INTEGER) AS days_overdue
    FROM invoices i
    JOIN members m ON i.member_id = m.member_id
    JOIN users u ON m.user_id = u.user_id
    JOIN branches b ON m.home_branch_id = b.branch_id
    JOIN organizations o ON b.organization_id = o.organization_id
    WHERE i.status IN ('pending', 'overdue');

    DROP VIEW IF EXISTS v_public_branch_directory;
    CREATE VIEW v_public_branch_directory AS
    SELECT 
        b.branch_id,
        b.organization_id,
        o.name AS organization_name,
        o.brand_type,
        b.name AS branch_name,
        b.address,
        b.city,
        b.state,
        b.pincode,
        b.latitude,
        b.longitude,
        b.phone AS branch_phone,
        b.description,
        b.capacity,
        COALESCE(min_plan.min_price, 0.0) AS starting_price_inr,
        COALESCE(fac_cnt.facility_count, 0) AS total_facilities
    FROM branches b
    JOIN organizations o ON b.organization_id = o.organization_id
    LEFT JOIN (
        SELECT organization_id, MIN(price) AS min_price
        FROM membership_plans
        GROUP BY organization_id
    ) min_plan ON b.organization_id = min_plan.organization_id
    LEFT JOIN (
        SELECT branch_id, COUNT(*) AS facility_count
        FROM branch_facilities
        GROUP BY branch_id
    ) fac_cnt ON b.branch_id = fac_cnt.branch_id
    WHERE o.status = 'active';

    DROP VIEW IF EXISTS v_branch_crowd_hourly;
    CREATE VIEW v_branch_crowd_hourly AS
    SELECT 
        a.branch_id,
        CAST(strftime('%w', a.check_in) AS INTEGER) AS day_of_week_0_mon,
        CAST(strftime('%H', a.check_in) AS INTEGER) AS hour_of_day,
        COUNT(*) AS total_visits
    FROM attendance a
    GROUP BY a.branch_id, strftime('%w', a.check_in), strftime('%H', a.check_in);
    """)

    # Indexes
    cur.executescript("""
    CREATE INDEX IF NOT EXISTS idx_att_branch_cin ON attendance (branch_id, check_in);
    CREATE INDEX IF NOT EXISTS idx_att_member ON attendance (member_id, check_in);
    CREATE INDEX IF NOT EXISTS idx_exp_branch_date ON expenses (branch_id, expense_date);
    CREATE INDEX IF NOT EXISTS idx_pay_ms_status ON payments (membership_id, payment_status);
    CREATE INDEX IF NOT EXISTS idx_pay_branch_date ON payments (branch_id, payment_date);
    CREATE INDEX IF NOT EXISTS idx_ms_status_dates ON memberships (member_id, status, start_date, end_date);
    CREATE INDEX IF NOT EXISTS idx_inv_due ON invoices (due_date, status);
    CREATE INDEX IF NOT EXISTS idx_sessions_tr ON training_sessions (trainer_id, session_start);
    """)
    
    cur.execute("PRAGMA foreign_keys = ON;")
    conn.commit()


def load_all_csvs(conn):
    cur = conn.cursor()
    hashed_pass = generate_password_hash(DEMO_PASS)
    counts = {}

    for table in LOAD_ORDER:
        csv_file = os.path.join(DATA_DIR, f"{table}.csv")
        if not os.path.exists(csv_file):
            print(f"Warning: {csv_file} does not exist!")
            continue

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Column mapping
            cols = []
            for col in header:
                if col == "day_of_week_0_mon":
                    cols.append("day_of_week")
                else:
                    cols.append(col)

            placeholders = ",".join(["?"] * len(cols))
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

    conn.commit()
    return counts


def main():
    print(f"Loading seed data into SQLite: {SQLITE_DB}")
    conn = sqlite3.connect(SQLITE_DB)
    init_sqlite_schema(conn)
    counts = load_all_csvs(conn)
    conn.close()

    print("\n--- SEED LOAD COMPLETE ---")
    for tbl, cnt in counts.items():
        print(f"  {tbl:22s}: {cnt:>6,d} rows")
    print(f"Total tables loaded: {len(counts)}")


if __name__ == "__main__":
    main()
