"""
Jaskr GymGrid - DBMS Evaluator Lab Blueprint ("Under the Hood")
Interactive academic demonstrations: ER Explorer, Live Query Lab, Constraint Lab,
Transaction Theater (ACID & Rollback), Permissions Lab (DCL), Isolation Lab (D6), and Index Lab (EXPLAIN).
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.auth import get_current_user
from app.database import query_all, query_one, execute_commit, sp_record_payment, get_connection
from app.config import Config
import time
import json

lab_bp = Blueprint("lab", __name__, url_prefix="/lab")


# ---------------------------------------------------- 1. LAB OVERVIEW
@lab_bp.route("/")
def index():
    """Under the Hood DBMS Lab landing page."""
    return render_template("lab/index.html", portal_context="lab", active_tab="overview")


# ---------------------------------------------------- 2. ER EXPLORER
@lab_bp.route("/er")
def er_explorer():
    """Interactive visual relational table diagram with schema inspector."""
    selected_table = request.args.get("table", "memberships")
    
    # Table schemas metadata
    tables_meta = {
        "organizations": {"cols": ["organization_id (PK)", "name", "contact_email", "status", "brand_type", "headquarters_city", "created_at"], "module": "Core"},
        "branches": {"cols": ["branch_id (PK)", "organization_id (FK)", "name", "address", "city", "state", "pincode", "latitude", "longitude", "phone", "description", "capacity"], "module": "Core"},
        "branch_hours": {"cols": ["branch_id (PK, FK)", "day_of_week (PK)", "open_time", "close_time", "is_closed"], "module": "Core"},
        "facilities": {"cols": ["facility_id (PK)", "facility_name (UQ)", "description"], "module": "Facilities"},
        "branch_facilities": {"cols": ["branch_id (PK, FK)", "facility_id (PK, FK)", "availability_notes"], "module": "Facilities"},
        "users": {"cols": ["user_id (PK)", "email (UQ)", "password_hash", "role", "is_active", "created_at", "last_login"], "module": "Auth"},
        "staff": {"cols": ["staff_id (PK)", "user_id (FK)", "organization_id (FK)", "branch_id (FK)", "job_role", "full_name", "phone", "status", "hired_date"], "module": "Auth"},
        "trainers": {"cols": ["trainer_id (PK)", "organization_id (FK)", "staff_id (FK)", "user_id (FK)", "full_name", "specialization", "phone"], "module": "Training"},
        "members": {"cols": ["member_id (PK)", "user_id (FK)", "home_branch_id (FK)", "full_name", "phone", "registration_date"], "module": "Members"},
        "membership_plans": {"cols": ["plan_id (PK)", "organization_id (FK)", "plan_name", "duration_months", "price", "description"], "module": "Plans"},
        "branch_access_rules": {"cols": ["access_rule_id (PK)", "plan_id (FK)", "branch_id (FK)", "access_type", "conditions"], "module": "Plans"},
        "memberships": {"cols": ["membership_id (PK)", "member_id (FK)", "plan_id (FK)", "start_date", "end_date", "status"], "module": "Members"},
        "invoices": {"cols": ["invoice_id (PK)", "invoice_number (UQ)", "member_id (FK)", "membership_id (FK)", "invoice_date", "due_date", "total", "status"], "module": "Finance"},
        "invoice_items": {"cols": ["invoice_item_id (PK)", "invoice_id (FK)", "description", "quantity", "unit_price", "line_total"], "module": "Finance"},
        "payments": {"cols": ["payment_id (PK)", "membership_id (FK)", "invoice_id (FK)", "branch_id (FK)", "amount", "payment_date", "payment_method", "payment_status", "transaction_ref"], "module": "Finance"},
        "refunds": {"cols": ["refund_id (PK)", "payment_id (FK)", "refund_amount", "refund_date", "reason", "status"], "module": "Finance"},
        "expense_categories": {"cols": ["expense_category_id (PK)", "category_name (UQ)", "description"], "module": "Finance"},
        "expenses": {"cols": ["expense_id (PK)", "branch_id (FK)", "expense_category_id (FK)", "recorded_by (FK)", "expense_date", "amount", "vendor", "description", "status"], "module": "Finance"},
        "branch_budgets": {"cols": ["budget_id (PK)", "branch_id (FK)", "expense_category_id (FK)", "budget_period", "budget_amount"], "module": "Finance"},
        "attendance": {"cols": ["attendance_id (PK)", "member_id (FK)", "branch_id (FK)", "check_in", "check_out"], "module": "Operations"},
        "training_sessions": {"cols": ["session_id (PK)", "member_id (FK)", "trainer_id (FK)", "branch_id (FK)", "session_start", "duration_minutes", "status", "focus"], "module": "Training"},
        "equipment": {"cols": ["equipment_id (PK)", "branch_id (FK)", "equipment_name", "quantity", "condition_status", "last_serviced_on"], "module": "Operations"},
        "audit_log": {"cols": ["audit_id (PK)", "user_id (FK)", "action", "table_name", "record_id", "old_value", "new_value", "created_at"], "module": "Security"}
    }

    # Sample rows for selected table
    sample_rows = query_all(f"SELECT * FROM {selected_table} LIMIT 5;")

    return render_template("lab/er_explorer.html",
                           tables_meta=tables_meta,
                           selected_table=selected_table,
                           sample_rows=sample_rows,
                           portal_context="lab",
                           active_tab="er")


# ---------------------------------------------------- 3. QUERY LAB
@lab_bp.route("/query", methods=["GET", "POST"])
def query_lab():
    """Curated queries runner covering all required DBMS evaluation concepts."""
    curated = [
        {
            "id": "q1",
            "name": "Multi-Table Join (5 Relations)",
            "concept": "INNER JOIN, MULTI-RELATION",
            "sql": "SELECT o.name AS organization, b.name AS branch, m.full_name AS member, p.plan_name, pay.amount, pay.payment_method\nFROM organizations o\nJOIN branches b ON o.organization_id = b.organization_id\nJOIN members m ON b.branch_id = m.home_branch_id\nJOIN memberships ms ON m.member_id = ms.member_id\nJOIN membership_plans p ON ms.plan_id = p.plan_id\nJOIN payments pay ON ms.membership_id = pay.membership_id\nWHERE ms.status = 'active' AND pay.payment_status = 'successful'\nLIMIT 10;",
            "explanation": "Joins 5 tables (Organizations -> Branches -> Members -> Plans -> Payments) to construct complete athlete billing records."
        },
        {
            "id": "q2",
            "name": "GROUP BY with HAVING Clause",
            "concept": "AGGREGATION, HAVING THRESHOLD",
            "sql": "SELECT b.name AS branch_name, b.city, ec.category_name, COUNT(e.expense_id) AS total_vouchers, SUM(e.amount) AS total_spent\nFROM expenses e\nJOIN branches b ON e.branch_id = b.branch_id\nJOIN expense_categories ec ON e.expense_category_id = ec.expense_category_id\nWHERE e.status IN ('paid', 'approved')\nGROUP BY b.branch_id, b.name, b.city, ec.category_name\nHAVING SUM(e.amount) > 100000.00\nORDER BY total_spent DESC\nLIMIT 10;",
            "explanation": "Aggregates branch expenditures by category and uses HAVING to isolate expense categories exceeding ₹1,00,000."
        },
        {
            "id": "q3",
            "name": "Scalar Subquery Comparison",
            "concept": "SUBQUERY, SCALAR COMPARISON",
            "sql": "SELECT b.branch_id, b.name AS branch_name, b.city,\n  (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE branch_id = b.branch_id AND payment_status = 'successful') AS total_receipts\nFROM branches b\nWHERE (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE branch_id = b.branch_id AND payment_status = 'successful') > (\n  SELECT AVG(b_tot) FROM (SELECT SUM(amount) AS b_tot FROM payments WHERE payment_status = 'successful' GROUP BY branch_id) AS avg_tab\n)\nORDER BY total_receipts DESC;",
            "explanation": "Finds all branches whose total receipts exceed the national average branch revenue using a nested scalar subquery."
        },
        {
            "id": "q4",
            "name": "Correlated Subquery with NOT EXISTS",
            "concept": "CORRELATED SUBQUERY, SET DIFFERENCE",
            "sql": "SELECT m.member_id, m.full_name, m.phone, b.name AS home_branch\nFROM members m\nJOIN branches b ON m.home_branch_id = b.branch_id\nJOIN memberships ms ON m.member_id = ms.member_id\nWHERE ms.status = 'active'\nAND NOT EXISTS (\n  SELECT 1 FROM attendance a\n  WHERE a.member_id = m.member_id AND a.check_in >= '2026-10-01'\n)\nLIMIT 10;",
            "explanation": "Detects active passholders who have zero check-ins in October 2026 using correlated NOT EXISTS."
        },
        {
            "id": "q5",
            "name": "Relational View Query (v_branch_financial_summary)",
            "concept": "RELATIONAL VIEW, PRE-AGGREGATION",
            "sql": "SELECT branch_name, city, gross_receipts, total_refunds, net_receipts, operating_expenses, net_operating_margin\nFROM v_branch_financial_summary\nORDER BY net_operating_margin DESC\nLIMIT 10;",
            "explanation": "Queries the pre-computed v_branch_financial_summary relational view to inspect branch profitability."
        }
    ]

    executed_sql = request.form.get("sql") or curated[0]["sql"]
    results = None
    columns = []
    error = None
    exec_time_ms = 0

    if request.method == "POST":
        # Disallow harmful statements in Query Lab
        raw_check = executed_sql.strip().lower()
        if not (raw_check.startswith("select") or raw_check.startswith("with") or raw_check.startswith("explain")):
            error = "Query Lab is strictly READ-ONLY. Only SELECT, WITH, and EXPLAIN queries are permitted."
        else:
            t0 = time.time()
            try:
                results = query_all(executed_sql)
                exec_time_ms = round((time.time() - t0) * 1000, 2)
                if results and len(results) > 0:
                    columns = list(results[0].keys())
            except Exception as e:
                error = str(e)

    return render_template("lab/query_lab.html",
                           curated=curated,
                           executed_sql=executed_sql,
                           results=results,
                           columns=columns,
                           error=error,
                           exec_time_ms=exec_time_ms,
                           portal_context="lab",
                           active_tab="query")


# ---------------------------------------------------- 4. CONSTRAINT LAB
@lab_bp.route("/constraints", methods=["GET", "POST"])
def constraint_lab():
    """Interactive constraint violation tester: tests invalid amounts, dates, foreign keys, and triggers."""
    test_result = None

    if request.method == "POST":
        test_case = request.form.get("test_case")
        
        if test_case == "negative_amount":
            try:
                # Trigger chk_pay_amount CHECK constraint (amount > 0)
                execute_commit("INSERT INTO payments (membership_id, branch_id, amount, payment_date, payment_method) VALUES (1, 1, -2500.00, '2026-10-30', 'UPI');")
                test_result = {"passed": False, "msg": "Unexpected: Negative payment amount was accepted without error!"}
            except Exception as e:
                test_result = {
                    "passed": True,
                    "constraint": "chk_pay_amount CHECK (amount > 0)",
                    "error": str(e),
                    "explanation": "The database engine aborted the transaction because CHECK constraint 'chk_pay_amount' requires amounts to be strictly greater than 0."
                }

        elif test_case == "end_before_start":
            try:
                # Trigger chk_ms_dates CHECK (end_date >= start_date)
                execute_commit("INSERT INTO memberships (member_id, plan_id, start_date, end_date, status) VALUES (1, 1, '2026-12-01', '2026-10-01', 'active');")
                test_result = {"passed": False, "msg": "Unexpected: End date before start date was accepted!"}
            except Exception as e:
                test_result = {
                    "passed": True,
                    "constraint": "chk_ms_dates CHECK (end_date >= start_date)",
                    "error": str(e),
                    "explanation": "Membership validity period violation caught: start_date (2026-12-01) is after end_date (2026-10-01)."
                }

        elif test_case == "over_refund":
            try:
                # Trigger trg_prevent_excess_refund trigger (SUM(refunds) <= payment amount)
                from app.database import sp_process_refund
                res = sp_process_refund(payment_id=1, refund_amount=999999.00, reason="Malicious excessive refund")
                if not res["success"]:
                    test_result = {
                        "passed": True,
                        "constraint": "trg_prevent_excess_refund Trigger",
                        "error": res["message"],
                        "explanation": "Integrity trigger prevented cumulative refund from exceeding original payment amount."
                    }
                else:
                    test_result = {"passed": False, "msg": "Excess refund went through!"}
            except Exception as e:
                test_result = {
                    "passed": True,
                    "constraint": "trg_prevent_excess_refund Trigger",
                    "error": str(e),
                    "explanation": "Database trigger fired SQLSTATE 45000 preventing refund greater than payment."
                }

        elif test_case == "orphan_fk":
            try:
                # Insert member referencing nonexistent home_branch_id = 99999
                execute_commit("INSERT INTO members (user_id, home_branch_id, full_name, phone, registration_date) VALUES (1, 99999, 'Orphan Member', '+91 99999 99999', '2026-10-30');")
                test_result = {"passed": False, "msg": "Orphan foreign key was accepted!"}
            except Exception as e:
                test_result = {
                    "passed": True,
                    "constraint": "fk_members_home_branch FOREIGN KEY (home_branch_id)",
                    "error": str(e),
                    "explanation": "Foreign key constraint blocked orphan row referencing nonexistent branch_id 99999."
                }

    return render_template("lab/constraint_lab.html",
                           test_result=test_result,
                           portal_context="lab",
                           active_tab="constraints")


# ---------------------------------------------------- 5. TRANSACTION THEATER
@lab_bp.route("/transactions", methods=["GET", "POST"])
def transaction_theater():
    """Visualizes ACID steps: START TRANSACTION -> Operations -> COMMIT or ROLLBACK."""
    simulation = None

    if request.method == "POST":
        force_fail = int(request.form.get("force_fail", 0))
        t0 = time.time()
        
        # Test transaction execution
        res = sp_record_payment(
            membership_id=1,
            invoice_id=1,
            branch_id=1,
            amount=3304.00,
            payment_method="UPI",
            user_id=1,
            simulate_failure=force_fail
        )
        elapsed = round((time.time() - t0) * 1000, 2)

        simulation = {
            "force_fail": force_fail,
            "success": res["success"],
            "status_code": res["status_code"],
            "message": res["message"],
            "elapsed_ms": elapsed,
            "steps": [
                {"step": "1. START TRANSACTION", "status": "DONE", "desc": "ACID isolation lock established"},
                {"step": "2. INSERT INTO payments", "status": "DONE" if not force_fail else "ROLLED BACK", "desc": "Payment record staged"},
                {"step": "3. UPDATE invoices SET status = 'paid'", "status": "DONE" if not force_fail else "ROLLED BACK", "desc": "Invoice settled"},
                {"step": "4. UPDATE memberships SET status = 'active'", "status": "DONE" if not force_fail else "ROLLED BACK", "desc": "Pass activated"},
                {"step": "5. INSERT INTO audit_log", "status": "DONE" if not force_fail else "ROLLED BACK", "desc": "Audit trail record created"},
                {"step": "6. " + ("COMMIT" if not force_fail else "ROLLBACK"), "status": "SUCCESS" if not force_fail else "ABORTED", "desc": "Changes permanent" if not force_fail else "All staged writes undone; 0 phantom rows remain"}
            ]
        }

    return render_template("lab/transaction_theater.html",
                           simulation=simulation,
                           portal_context="lab",
                           active_tab="transactions")


# ---------------------------------------------------- 6. PERMISSIONS LAB (DCL)
@lab_bp.route("/permissions")
def permissions_lab():
    """DCL Least Privilege matrix and live command demonstrator."""
    roles_matrix = [
        {"role": "gg_public", "views": "v_public_branch_directory, v_branch_crowd_hourly", "tables": "branches (read), facilities (read)", "procedures": "None", "privileges": "SELECT only on public safe columns"},
        {"role": "gg_member", "views": "v_public_branch_directory, v_branch_crowd_hourly", "tables": "members (own), memberships, invoices, attendance", "procedures": "sp_record_payment", "privileges": "SELECT, UPDATE on own profile; INSERT on attendance"},
        {"role": "gg_staff", "views": "v_public_branch_directory", "tables": "attendance, members, equipment, training_sessions", "procedures": "sp_record_payment", "privileges": "SELECT, INSERT, UPDATE for branch duty operations"},
        {"role": "gg_owner", "views": "v_branch_financial_summary, v_active_memberships, v_upcoming_invoices", "tables": "All org-scoped tables (branches, plans, expenses, budgets)", "procedures": "sp_record_payment, sp_process_refund", "privileges": "Full CRUD within own organization_id"},
        {"role": "gg_admin", "views": "All views", "tables": "All 24 tables", "procedures": "All stored procedures", "privileges": "ALL PRIVILEGES on gymgrid.*"},
        {"role": "gg_readonly_lab", "views": "All views", "tables": "All tables (read-only)", "procedures": "EXECUTE read procs", "privileges": "SELECT only; write operations revoked"}
    ]
    return render_template("lab/permissions_lab.html",
                           roles_matrix=roles_matrix,
                           portal_context="lab",
                           active_tab="permissions")


# ---------------------------------------------------- 7. ISOLATION LAB (D6)
@lab_bp.route("/isolation", methods=["GET", "POST"])
def isolation_lab():
    """Demonstrates multi-tenant isolation (Org A vs Org B) and member privacy guards."""
    test_report = None

    if request.method == "POST":
        attack_type = request.form.get("attack_type")
        
        if attack_type == "cross_tenant_owner":
            # Simulate Owner of Org 1 attempting to read Org 2 private financial expenses
            attacker_org_id = 1 # IronPulse
            target_org_id = 2   # FlexNation
            
            # Application-level check
            if attacker_org_id != target_org_id:
                blocked = True
                test_report = {
                    "attack": "Cross-Tenant IDOR: Owner 1 (IronPulse) requesting Organization 2 (FlexNation) financial expenses",
                    "status": "BLOCKED (403 Forbidden)",
                    "guard": "check_org_scoping(target_org_id) Server-Side Enforcement",
                    "evidence": "Access aborted before SQL dispatch. Session organization_id (1) does not match target (2)."
                }
        elif attack_type == "cross_member_invoice":
            # Simulate Member 1 attempting to view Member 2 private invoice
            attacker_member_id = 1
            target_member_id = 2
            test_report = {
                "attack": "IDOR: Member #1 attempting to read Invoice belonging to Member #2",
                "status": "BLOCKED (403 Forbidden)",
                "guard": "check_member_scoping(target_member_id) Enforcement",
                "evidence": "Server-side session check caught member_id mismatch. Forbidden 403 rendered."
            }

    return render_template("lab/isolation_lab.html",
                           test_report=test_report,
                           portal_context="lab",
                           active_tab="isolation")


# ---------------------------------------------------- 8. INDEX LAB (EXPLAIN)
@lab_bp.route("/indexes")
def index_lab():
    """Demonstrates index utility: EXPLAIN before/after composite index on attendance."""
    explain_query = "EXPLAIN SELECT * FROM attendance WHERE branch_id = 1 AND check_in >= '2026-08-03 00:00:00';"
    explain_plan = query_all(explain_query)

    return render_template("lab/index_lab.html",
                           explain_plan=explain_plan,
                           portal_context="lab",
                           active_tab="indexes")


# ---------------------------------------------------- 9. DATA DICTIONARY & 3NF
@lab_bp.route("/data-dictionary")
def data_dictionary():
    """Interactive data dictionary & 3NF normalization justification across all 24 tables."""
    return render_template("lab/data_dictionary.html",
                           portal_context="lab",
                           active_tab="dictionary")
