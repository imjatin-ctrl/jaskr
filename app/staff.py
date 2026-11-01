"""
Jaskr GymGrid - Staff Portal Blueprint
Front Desk Console (Live Occupancy, Member Scan, Payment Collection),
Trainer Console (Sessions & Roster), Finance Desk (Invoices, Expenses & Budgets),
and Branch Manager Console (KPIs, Equipment & Facilities).
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.auth import login_required, roles_required, job_roles_required, get_current_user
from app.database import query_all, query_one, execute_commit, sp_record_payment
from app.config import Config
import datetime as dt

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


# ---------------------------------------------------- 1. FRONT DESK CONSOLE
@staff_bp.route("/front-desk", methods=["GET", "POST"])
@login_required
@roles_required("staff", "owner", "admin")
def front_desk():
    """Front desk operations: Live 'currently inside' list, member instant lookup, barcode check-in."""
    user = get_current_user()
    branch_id = user.get("branch_id") or 1  # Fallback to Branch 1 if org-wide owner/admin
    
    branch = query_one(
        "SELECT b.*, o.name AS organization_name "
        "FROM branches b JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE b.branch_id = %s;", (branch_id,)
    )

    # Currently inside athletes (attendance rows with check_out IS NULL)
    inside_athletes = query_all(
        "SELECT a.attendance_id, a.check_in, m.member_id, m.full_name, m.phone, p.plan_name "
        "FROM attendance a "
        "JOIN members m ON a.member_id = m.member_id "
        "LEFT JOIN memberships ms ON m.member_id = ms.member_id AND ms.status = 'active' "
        "LEFT JOIN membership_plans p ON ms.plan_id = p.plan_id "
        "WHERE a.branch_id = %s AND a.check_out IS NULL "
        "ORDER BY a.check_in DESC;", (branch_id,)
    )

    # Member Search / Scan Lookup
    search_query = request.args.get("search", "").strip()
    lookup_member = None
    lookup_ms = None
    if search_query:
        lookup_member = query_one(
            "SELECT m.*, u.email, b.name AS home_branch_name, b.city AS home_branch_city "
            "FROM members m "
            "JOIN users u ON m.user_id = u.user_id "
            "JOIN branches b ON m.home_branch_id = b.branch_id "
            "WHERE (m.member_id = %s OR m.phone LIKE %s OR LOWER(m.full_name) LIKE %s OR LOWER(u.email) LIKE %s) LIMIT 1;",
            (search_query if search_query.isdigit() else 0, f"%{search_query}%", f"%{search_query.lower()}%", f"%{search_query.lower()}%")
        )
        if lookup_member:
            lookup_ms = query_one(
                "SELECT ms.*, p.plan_name, p.duration_months "
                "FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id "
                "WHERE ms.member_id = %s ORDER BY ms.end_date DESC LIMIT 1;", (lookup_member["member_id"],)
            )

    return render_template("staff/front_desk.html",
                           branch=branch,
                           inside_athletes=inside_athletes,
                           search_query=search_query,
                           lookup_member=lookup_member,
                           lookup_ms=lookup_ms,
                           portal_context="staff",
                           active_tab="front_desk")


@staff_bp.route("/front-desk/check-out/<int:attendance_id>", methods=["POST"])
@login_required
@roles_required("staff", "owner", "admin")
def desk_checkout(attendance_id):
    """Front desk manual member check-out."""
    now_str = Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S")
    execute_commit("UPDATE attendance SET check_out = %s WHERE attendance_id = %s;", (now_str, attendance_id))
    flash("Member successfully checked out.", "success")
    return redirect(url_for("staff.front_desk"))


@staff_bp.route("/front-desk/check-in-member", methods=["POST"])
@login_required
@roles_required("staff", "owner", "admin")
def desk_checkin():
    """Front desk manual member check-in."""
    member_id = int(request.form.get("member_id"))
    user = get_current_user()
    branch_id = user.get("branch_id") or 1
    now_str = Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if already inside
    already = query_one("SELECT attendance_id FROM attendance WHERE member_id = %s AND check_out IS NULL;", (member_id,))
    if already:
        flash("Member is already checked in!", "warning")
        return redirect(url_for("staff.front_desk"))

    execute_commit(
        "INSERT INTO attendance (member_id, branch_id, check_in, check_out) VALUES (%s, %s, %s, NULL);",
        (member_id, branch_id, now_str)
    )
    flash(f"Member #{member_id} successfully checked into floor.", "success")
    return redirect(url_for("staff.front_desk"))


# ---------------------------------------------------- 2. TRAINER CONSOLE
@staff_bp.route("/trainer")
@login_required
@roles_required("staff", "owner", "admin")
def trainer_console():
    """Trainer dashboard: view assigned sessions, update status (completed/no-show)."""
    user = get_current_user()
    # If logged in as trainer, find trainer_id
    trainer = query_one("SELECT * FROM trainers WHERE user_id = %s;", (user["user_id"],))
    trainer_id = trainer["trainer_id"] if trainer else 1 # Default to trainer 1 for preview

    sessions = query_all(
        "SELECT ts.*, m.full_name AS member_name, m.phone AS member_phone, b.name AS branch_name "
        "FROM training_sessions ts "
        "JOIN members m ON ts.member_id = m.member_id "
        "JOIN branches b ON ts.branch_id = b.branch_id "
        "WHERE ts.trainer_id = %s ORDER BY ts.session_start DESC LIMIT 30;", (trainer_id,)
    )

    return render_template("staff/trainer_console.html",
                           trainer=trainer,
                           sessions=sessions,
                           portal_context="staff",
                           active_tab="trainer")


@staff_bp.route("/trainer/update-session/<int:session_id>", methods=["POST"])
@login_required
@roles_required("staff", "owner", "admin")
def update_session(session_id):
    """Mark session as completed or no-show."""
    new_status = request.form.get("status", "completed")
    execute_commit("UPDATE training_sessions SET status = %s WHERE session_id = %s;", (new_status, session_id))
    flash(f"Session #{session_id} status updated to {new_status}.", "success")
    return redirect(url_for("staff.trainer_console"))


# ---------------------------------------------------- 3. FINANCE DESK
@staff_bp.route("/finance")
@login_required
@roles_required("staff", "owner", "admin")
def finance_desk():
    """Finance desk: invoices reconciliation, operating expenses, and monthly budget variance."""
    user = get_current_user()
    org_id = user.get("organization_id") or 1

    # Financial Summary Metrics for the organization
    summary = query_one(
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

    # Recent Invoices & Reconciliation Status
    invoices = query_all(
        "SELECT i.*, m.full_name AS member_name, b.name AS branch_name, "
        "  (SELECT SUM(line_total) FROM invoice_items WHERE invoice_id = i.invoice_id) AS items_sum "
        "FROM invoices i "
        "JOIN members m ON i.member_id = m.member_id "
        "JOIN branches b ON m.home_branch_id = b.branch_id "
        "WHERE b.organization_id = %s ORDER BY i.invoice_date DESC LIMIT 15;", (org_id,)
    )

    # Expenses Vouchers
    expenses = query_all(
        "SELECT e.*, ec.category_name, b.name AS branch_name "
        "FROM expenses e "
        "JOIN expense_categories ec ON e.expense_category_id = ec.expense_category_id "
        "JOIN branches b ON e.branch_id = b.branch_id "
        "WHERE b.organization_id = %s ORDER BY e.expense_date DESC LIMIT 15;", (org_id,)
    )

    # Budget Variance Highlights (Overspent rows)
    overspent = query_all(
        "SELECT bb.*, b.name AS branch_name, ec.category_name, "
        "  COALESCE((SELECT SUM(amount) FROM expenses e WHERE e.branch_id = bb.branch_id AND e.expense_category_id = bb.expense_category_id AND e.status IN ('paid', 'approved') AND strftime('%Y-%m', e.expense_date) = bb.budget_period), 0.0) AS actual_spent "
        "FROM branch_budgets bb "
        "JOIN branches b ON bb.branch_id = b.branch_id "
        "JOIN expense_categories ec ON bb.expense_category_id = ec.expense_category_id "
        "WHERE b.organization_id = %s "
        "ORDER BY (actual_spent - bb.budget_amount) DESC LIMIT 6;", (org_id,)
    )

    return render_template("staff/finance_desk.html",
                           summary=summary,
                           total_expenses=total_expenses,
                           invoices=invoices,
                           expenses=expenses,
                           overspent=overspent,
                           portal_context="staff",
                           active_tab="finance")


# ---------------------------------------------------- 4. BRANCH MANAGER CONSOLE
@staff_bp.route("/manager")
@login_required
@roles_required("staff", "owner", "admin")
def branch_manager():
    """Branch manager dashboard: KPIs, equipment inventory condition, staff roster, operating hours."""
    user = get_current_user()
    branch_id = user.get("branch_id") or 1

    branch = query_one(
        "SELECT b.*, o.name AS organization_name "
        "FROM branches b JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE b.branch_id = %s;", (branch_id,)
    )

    stats = {
        "members": query_one("SELECT COUNT(*) AS c FROM members WHERE home_branch_id = %s;", (branch_id,))["c"],
        "checkins_today": query_one("SELECT COUNT(*) AS c FROM attendance WHERE branch_id = %s AND check_in >= '2026-10-30 00:00:00';", (branch_id,))["c"],
        "equipment_count": query_one("SELECT COUNT(*) AS c FROM equipment WHERE branch_id = %s;", (branch_id,))["c"],
        "needs_service": query_one("SELECT COUNT(*) AS c FROM equipment WHERE branch_id = %s AND condition_status != 'good';", (branch_id,))["c"]
    }

    equipment = query_all("SELECT * FROM equipment WHERE branch_id = %s ORDER BY condition_status, equipment_name;", (branch_id,))
    staff_roster = query_all("SELECT * FROM staff WHERE branch_id = %s ORDER BY job_role, full_name;", (branch_id,))
    hours = query_all("SELECT * FROM branch_hours WHERE branch_id = %s ORDER BY day_of_week;", (branch_id,))

    return render_template("staff/branch_manager.html",
                           branch=branch,
                           stats=stats,
                           equipment=equipment,
                           staff_roster=staff_roster,
                           hours=hours,
                           portal_context="staff",
                           active_tab="manager")
