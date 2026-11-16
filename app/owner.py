"""
Jaskr GymGrid - Owner Portal Blueprint
Executive Bento Overview, Branches Management, Access Matrix (D2),
Staff Roles & Scoping, Financial P&L & Refund Approvals, Reports Center, and Audit Logs.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, Response
from app.auth import login_required, roles_required, get_current_user, check_org_scoping
from app.database import query_all, query_one, execute_commit, sp_process_refund
from app.config import Config
import csv
import io
import datetime as dt

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")


def get_owner_org():
    """Derives organization context strictly from server-side session."""
    user = get_current_user()
    org_id = user.get("organization_id")
    if not org_id:
        # Fallback if admin previewing
        org_id = 1
    org = query_one("SELECT * FROM organizations WHERE organization_id = %s;", (org_id,))
    return org


# ---------------------------------------------------- 1. OVERVIEW BENTO
@owner_bp.route("/dashboard")
@login_required
@roles_required("owner", "admin")
def dashboard():
    """Executive Bento KPI Grid: Net receipts, active members, expenses, variance, and branch leaderboard."""
    org = get_owner_org()
    org_id = org["organization_id"]

    # Key Performance Indicators
    kpi = query_one(
        "SELECT "
        "  COALESCE(SUM(CASE WHEN p.payment_status = 'successful' THEN p.amount ELSE 0 END), 0.0) AS gross_receipts, "
        "  COALESCE(SUM(CASE WHEN r.status = 'completed' THEN r.refund_amount ELSE 0 END), 0.0) AS completed_refunds, "
        "  (COALESCE(SUM(CASE WHEN p.payment_status = 'successful' THEN p.amount ELSE 0 END), 0.0) - "
        "   COALESCE(SUM(CASE WHEN r.status = 'completed' THEN r.refund_amount ELSE 0 END), 0.0)) AS net_receipts "
        "FROM branches b "
        "LEFT JOIN payments p ON b.branch_id = p.branch_id "
        "LEFT JOIN refunds r ON p.payment_id = r.payment_id "
        "WHERE b.organization_id = %s;", (org_id,)
    )

    total_expenses = query_one(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_exp "
        "FROM expenses e JOIN branches b ON e.branch_id = b.branch_id "
        "WHERE b.organization_id = %s AND e.status IN ('paid', 'approved');", (org_id,)
    )["total_exp"]

    active_members = query_one(
        "SELECT COUNT(DISTINCT ms.member_id) AS c "
        "FROM memberships ms "
        "JOIN membership_plans p ON ms.plan_id = p.plan_id "
        "WHERE p.organization_id = %s AND ms.status = 'active';", (org_id,)
    )["c"]

    total_checkins = query_one(
        "SELECT COUNT(*) AS c "
        "FROM attendance a "
        "JOIN branches b ON a.branch_id = b.branch_id "
        "WHERE b.organization_id = %s;", (org_id,)
    )["c"]

    # Branch Leaderboard by Net Receipts
    leaderboard = query_all(
        "SELECT b.branch_id, b.name, b.city, "
        "  COALESCE(SUM(CASE WHEN p.payment_status = 'successful' THEN p.amount ELSE 0 END), 0.0) AS gross, "
        "  (SELECT COUNT(*) FROM members m WHERE m.home_branch_id = b.branch_id) AS home_members, "
        "  (SELECT COUNT(*) FROM attendance a WHERE a.branch_id = b.branch_id) AS checkins "
        "FROM branches b "
        "LEFT JOIN payments p ON b.branch_id = p.branch_id "
        "WHERE b.organization_id = %s "
        "GROUP BY b.branch_id, b.name, b.city "
        "ORDER BY gross DESC;", (org_id,)
    )

    return render_template("owner/dashboard.html",
                           org=org,
                           kpi=kpi,
                           total_expenses=total_expenses,
                           active_members=active_members,
                           total_checkins=total_checkins,
                           leaderboard=leaderboard,
                           portal_context="owner",
                           active_tab="dashboard")


# ---------------------------------------------------- 2. BRANCHES
@owner_bp.route("/branches", methods=["GET", "POST"])
@login_required
@roles_required("owner", "admin")
def branches():
    """Branch CRUD: view branch list and create new branch."""
    org = get_owner_org()
    org_id = org["organization_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        phone = request.form.get("phone", "").strip()
        capacity = int(request.form.get("capacity", 100))
        description = request.form.get("description", "").strip()

        new_bid = execute_commit(
            "INSERT INTO branches (organization_id, name, address, city, state, pincode, latitude, longitude, phone, description, capacity) "
            "VALUES (%s, %s, %s, %s, %s, %s, 28.6139, 77.2090, %s, %s, %s);",
            (org_id, name, address, city, state, pincode, phone, description, capacity)
        )

        # Initialize standard operating hours (06:00 to 22:30 for Mon..Sun)
        for dow in range(7):
            execute_commit(
                "INSERT INTO branch_hours (branch_id, day_of_week, open_time, close_time, is_closed) "
                "VALUES (%s, %s, '06:00:00', '22:30:00', 0);",
                (new_bid, dow)
            )

        flash(f"Branch '{name}' created successfully with standard operating hours.", "success")
        return redirect(url_for("owner.branches"))

    branch_list = query_all(
        "SELECT b.*, "
        "  (SELECT COUNT(*) FROM members m WHERE m.home_branch_id = b.branch_id) AS member_count, "
        "  (SELECT COUNT(*) FROM staff s WHERE s.branch_id = b.branch_id) AS staff_count, "
        "  (SELECT COUNT(*) FROM branch_facilities bf WHERE bf.branch_id = b.branch_id) AS facility_count "
        "FROM branches b WHERE b.organization_id = %s ORDER BY b.city, b.name;", (org_id,)
    )

    return render_template("owner/branches.html",
                           org=org,
                           branches=branch_list,
                           portal_context="owner",
                           active_tab="branches")


# ---------------------------------------------------- 3. PLANS & ACCESS MATRIX
@owner_bp.route("/plans-matrix", methods=["GET", "POST"])
@login_required
@roles_required("owner", "admin")
def plans_matrix():
    """D2 Access Matrix: Plans x Branches grid with access_type and clickable cell updates."""
    org = get_owner_org()
    org_id = org["organization_id"]

    if request.method == "POST":
        rule_id = int(request.form.get("access_rule_id"))
        new_access_type = request.form.get("access_type")
        conditions = request.form.get("conditions", "")
        execute_commit(
            "UPDATE branch_access_rules SET access_type = %s, conditions = %s WHERE access_rule_id = %s;",
            (new_access_type, conditions, rule_id)
        )
        flash("Branch access rule successfully updated in matrix.", "success")
        return redirect(url_for("owner.plans_matrix"))

    branch_list = query_all("SELECT * FROM branches WHERE organization_id = %s ORDER BY branch_id;", (org_id,))
    plan_list = query_all("SELECT * FROM membership_plans WHERE organization_id = %s ORDER BY duration_months, price;", (org_id,))

    # Access matrix dictionary: (plan_id, branch_id) -> rule row
    rules = query_all(
        "SELECT r.* FROM branch_access_rules r "
        "JOIN membership_plans p ON r.plan_id = p.plan_id "
        "WHERE p.organization_id = %s;", (org_id,)
    )
    matrix = {(r["plan_id"], r["branch_id"]): r for r in rules}

    return render_template("owner/plans_matrix.html",
                           org=org,
                           branches=branch_list,
                           plans=plan_list,
                           matrix=matrix,
                           portal_context="owner",
                           active_tab="matrix")


# ---------------------------------------------------- 4. MEMBERS DIRECTORY
@owner_bp.route("/members")
@login_required
@roles_required("owner", "admin")
def members():
    """Organization-scoped members directory with drill-down profile drawer."""
    org = get_owner_org()
    org_id = org["organization_id"]

    member_list = query_all(
        "SELECT m.*, u.email, b.name AS home_branch_name, b.city, "
        "  COALESCE(ms.plan_name, 'None') AS active_plan, "
        "  COALESCE(ms.end_date, '-') AS plan_end "
        "FROM members m "
        "JOIN users u ON m.user_id = u.user_id "
        "JOIN branches b ON m.home_branch_id = b.branch_id "
        "LEFT JOIN ( "
        "  SELECT ms.member_id, p.plan_name, ms.end_date "
        "  FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id "
        "  WHERE ms.status = 'active' "
        ") ms ON m.member_id = ms.member_id "
        "WHERE b.organization_id = %s "
        "ORDER BY m.registration_date DESC LIMIT 50;", (org_id,)
    )

    return render_template("owner/members.html",
                           org=org,
                           members=member_list,
                           portal_context="owner",
                           active_tab="members")


# ---------------------------------------------------- 5. STAFF & PERMISSIONS
@owner_bp.route("/staff", methods=["GET", "POST"])
@login_required
@roles_required("owner", "admin")
def staff_mgmt():
    """Manage staff: invite, assign job role and branch scope, suspend/activate."""
    org = get_owner_org()
    org_id = org["organization_id"]
    branches = query_all("SELECT branch_id, name, city FROM branches WHERE organization_id = %s ORDER BY name;", (org_id,))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        job_role = request.form.get("job_role")
        branch_id = request.form.get("branch_id")
        branch_id = int(branch_id) if branch_id and branch_id.isdigit() else None

        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash("Demo@1234")
        now_str = Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = Config.get_app_today().strftime("%Y-%m-%d")

        user_id = execute_commit(
            "INSERT INTO users (email, password_hash, role, is_active, created_at) "
            "VALUES (%s, %s, 'staff', 1, %s);",
            (email, hashed, now_str)
        )
        execute_commit(
            "INSERT INTO staff (user_id, organization_id, branch_id, job_role, full_name, phone, status, hired_date) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'active', %s);",
            (user_id, org_id, branch_id, job_role, full_name, phone, today_str)
        )
        flash(f"Staff account for {full_name} ({job_role}) created successfully.", "success")
        return redirect(url_for("owner.staff_mgmt"))

    staff_list = query_all(
        "SELECT s.*, u.email, b.name AS branch_name, b.city "
        "FROM staff s "
        "JOIN users u ON s.user_id = u.user_id "
        "LEFT JOIN branches b ON s.branch_id = b.branch_id "
        "WHERE s.organization_id = %s ORDER BY s.job_role, s.full_name;", (org_id,)
    )

    return render_template("owner/staff_mgmt.html",
                           org=org,
                           staff_list=staff_list,
                           branches=branches,
                           portal_context="owner",
                           active_tab="staff")


# ---------------------------------------------------- 6. FINANCE & REFUND APPROVALS
@owner_bp.route("/finance")
@login_required
@roles_required("owner", "admin")
def finance():
    """Owner financial module: P&L overview, refund approvals queue, and budgets."""
    org = get_owner_org()
    org_id = org["organization_id"]

    # Pending refunds requiring owner approval
    pending_refunds = query_all(
        "SELECT r.*, p.amount AS payment_amount, p.transaction_ref, m.full_name, b.name AS branch_name "
        "FROM refunds r "
        "JOIN payments p ON r.payment_id = p.payment_id "
        "JOIN memberships ms ON p.membership_id = ms.membership_id "
        "JOIN members m ON ms.member_id = m.member_id "
        "JOIN branches b ON p.branch_id = b.branch_id "
        "WHERE b.organization_id = %s AND r.status IN ('requested', 'approved') "
        "ORDER BY r.refund_date DESC;", (org_id,)
    )

    # Invoices summary
    invoices = query_all(
        "SELECT i.*, m.full_name, b.name AS branch_name "
        "FROM invoices i "
        "JOIN members m ON i.member_id = m.member_id "
        "JOIN branches b ON m.home_branch_id = b.branch_id "
        "WHERE b.organization_id = %s ORDER BY i.invoice_date DESC LIMIT 20;", (org_id,)
    )

    # Expenses summary
    expenses = query_all(
        "SELECT e.*, ec.category_name, b.name AS branch_name "
        "FROM expenses e "
        "JOIN expense_categories ec ON e.expense_category_id = ec.expense_category_id "
        "JOIN branches b ON e.branch_id = b.branch_id "
        "WHERE b.organization_id = %s ORDER BY e.expense_date DESC LIMIT 20;", (org_id,)
    )

    return render_template("owner/finance.html",
                           org=org,
                           pending_refunds=pending_refunds,
                           invoices=invoices,
                           expenses=expenses,
                           portal_context="owner",
                           active_tab="finance")


@owner_bp.route("/refund/approve/<int:refund_id>", methods=["POST"])
@login_required
@roles_required("owner", "admin")
def approve_refund(refund_id):
    """Owner approval: transitions refund to completed and cancels membership if full refund."""
    refund = query_one("SELECT * FROM refunds WHERE refund_id = %s;", (refund_id,))
    if not refund:
        flash("Refund not found.", "error")
        return redirect(url_for("owner.finance"))

    res = sp_process_refund(
        payment_id=refund["payment_id"],
        refund_amount=refund["refund_amount"],
        reason=refund["reason"],
        user_id=session["user_id"],
        refund_id=refund_id
    )
    if res["success"]:
        flash("Refund approved and marked completed successfully.", "success")
    else:
        flash(f"Refund processing failed: {res['message']}", "error")
    return redirect(url_for("owner.finance"))


# ---------------------------------------------------- 7. ATTENDANCE & ANALYTICS
@owner_bp.route("/analytics")
@login_required
@roles_required("owner", "admin")
def attendance_analytics():
    """Branch comparison crowd and floor traffic charts."""
    org = get_owner_org()
    org_id = org["organization_id"]

    branch_traffic = query_all(
        "SELECT b.name, COUNT(a.attendance_id) AS total_visits "
        "FROM branches b "
        "LEFT JOIN attendance a ON b.branch_id = a.branch_id "
        "WHERE b.organization_id = %s "
        "GROUP BY b.branch_id, b.name "
        "ORDER BY total_visits DESC;", (org_id,)
    )

    return render_template("owner/attendance_analytics.html",
                           org=org,
                           branch_traffic=branch_traffic,
                           portal_context="owner",
                           active_tab="analytics")


# ---------------------------------------------------- 8. REPORTS CENTER
@owner_bp.route("/reports")
@login_required
@roles_required("owner", "admin")
def reports():
    """Reports center with filter controls and CSV export."""
    org = get_owner_org()
    org_id = org["organization_id"]
    branches = query_all("SELECT branch_id, name FROM branches WHERE organization_id = %s ORDER BY name;", (org_id,))

    return render_template("owner/reports.html",
                           org=org,
                           branches=branches,
                           portal_context="owner",
                           active_tab="reports")


@owner_bp.route("/reports/export-csv")
@login_required
@roles_required("owner", "admin")
def export_csv():
    """Generates downloadable CSV for financial audit."""
    org = get_owner_org()
    org_id = org["organization_id"]
    report_type = request.args.get("type", "payments")

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "payments":
        writer.writerow(["Payment ID", "Transaction Ref", "Date", "Branch", "Method", "Amount", "Status"])
        rows = query_all(
            "SELECT p.payment_id, p.transaction_ref, p.payment_date, b.name, p.payment_method, p.amount, p.payment_status "
            "FROM payments p JOIN branches b ON p.branch_id = b.branch_id "
            "WHERE b.organization_id = %s ORDER BY p.payment_date DESC;", (org_id,)
        )
        for r in rows:
            writer.writerow([r["payment_id"], r["transaction_ref"], r["payment_date"], r["name"], r["payment_method"], r["amount"], r["payment_status"]])
    else:
        writer.writerow(["Expense ID", "Branch", "Category", "Date", "Vendor", "Amount", "Status"])
        rows = query_all(
            "SELECT e.expense_id, b.name, ec.category_name, e.expense_date, e.vendor, e.amount, e.status "
            "FROM expenses e JOIN branches b ON e.branch_id = b.branch_id "
            "JOIN expense_categories ec ON e.expense_category_id = ec.expense_category_id "
            "WHERE b.organization_id = %s ORDER BY e.expense_date DESC;", (org_id,)
        )
        for r in rows:
            writer.writerow([r["expense_id"], r["name"], r["category_name"], r["expense_date"], r["vendor"], r["amount"], r["status"]])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=jaskr_{org['name'].lower().replace(' ', '_')}_{report_type}.csv"}
    )


# ---------------------------------------------------- 9. AUDIT LOG
@owner_bp.route("/audit-log")
@login_required
@roles_required("owner", "admin")
def audit_log():
    """Organization-scoped audit log."""
    org = get_owner_org()
    org_id = org["organization_id"]

    logs = query_all(
        "SELECT a.*, u.email "
        "FROM audit_log a "
        "JOIN users u ON a.user_id = u.user_id "
        "JOIN staff s ON u.user_id = s.user_id "
        "WHERE s.organization_id = %s "
        "ORDER BY a.created_at DESC LIMIT 50;", (org_id,)
    )

    return render_template("owner/audit_log.html",
                           org=org,
                           logs=logs,
                           portal_context="owner",
                           active_tab="audit")
