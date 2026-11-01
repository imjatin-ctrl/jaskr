"""
Jaskr GymGrid - Admin Portal Blueprint
Platform Superuser Management: Organization Approvals Queue (Zenith Strength Lab pending),
Users Directory, Database Health Monitor, and Global Audit Log.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.auth import login_required, roles_required, get_current_user
from app.database import query_all, query_one, execute_commit
from app.config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@roles_required("admin")
def dashboard():
    """Platform administrator overview: network statistics and pending approvals."""
    stats = {
        "orgs": query_one("SELECT COUNT(*) AS c FROM organizations;")["c"],
        "pending_orgs": query_one("SELECT COUNT(*) AS c FROM organizations WHERE status = 'pending';")["c"],
        "branches": query_one("SELECT COUNT(*) AS c FROM branches;")["c"],
        "users": query_one("SELECT COUNT(*) AS c FROM users;")["c"],
        "members": query_one("SELECT COUNT(*) AS c FROM members;")["c"],
        "checkins": query_one("SELECT COUNT(*) AS c FROM attendance;")["c"],
        "gross_revenue": query_one("SELECT COALESCE(SUM(amount), 0.0) AS s FROM payments WHERE payment_status = 'successful';")["s"]
    }

    pending_list = query_all("SELECT * FROM organizations WHERE status = 'pending' ORDER BY created_at DESC;")
    recent_users = query_all("SELECT user_id, email, role, is_active, created_at FROM users ORDER BY created_at DESC LIMIT 8;")

    return render_template("admin/dashboard.html",
                           stats=stats,
                           pending_list=pending_list,
                           recent_users=recent_users,
                           portal_context="admin",
                           active_tab="dashboard")


@admin_bp.route("/approvals")
@login_required
@roles_required("admin")
def approvals():
    """Organization onboarding approvals queue."""
    pending = query_all("SELECT * FROM organizations WHERE status = 'pending' ORDER BY created_at DESC;")
    active = query_all("SELECT * FROM organizations WHERE status = 'active' ORDER BY name;")
    return render_template("admin/approvals.html",
                           pending=pending,
                           active=active,
                           portal_context="admin",
                           active_tab="approvals")


@admin_bp.route("/approve-org/<int:organization_id>", methods=["POST"])
@login_required
@roles_required("admin")
def approve_org(organization_id):
    """Admin approves a pending organization (e.g. Zenith Strength Lab)."""
    execute_commit("UPDATE organizations SET status = 'active' WHERE organization_id = %s;", (organization_id,))
    org = query_one("SELECT name FROM organizations WHERE organization_id = %s;", (organization_id,))
    org_name = org["name"] if org else f"Organization #{organization_id}"
    flash(f"Organization '{org_name}' approved and activated on Jaskr GymGrid!", "success")
    return redirect(url_for("admin.approvals"))


@admin_bp.route("/users")
@login_required
@roles_required("admin")
def users_mgmt():
    """Platform users directory with status toggle."""
    search_q = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "").strip()

    conditions = []
    params = []

    if search_q:
        conditions.append("(email LIKE %s OR user_id = %s)")
        params.extend([f"%{search_q}%", search_q if search_q.isdigit() else 0])
    if role_filter:
        conditions.append("role = %s")
        params.append(role_filter)

    where_str = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    users = query_all(f"SELECT * FROM users {where_str} ORDER BY user_id ASC LIMIT 50;", params)

    return render_template("admin/users_mgmt.html",
                           users=users,
                           search_q=search_q,
                           role_filter=role_filter,
                           portal_context="admin",
                           active_tab="users")


@admin_bp.route("/toggle-user-active/<int:user_id>", methods=["POST"])
@login_required
@roles_required("admin")
def toggle_user_active(user_id):
    """Toggle user active / suspended state."""
    u = query_one("SELECT is_active FROM users WHERE user_id = %s;", (user_id,))
    if u:
        new_val = 0 if u["is_active"] == 1 else 1
        execute_commit("UPDATE users SET is_active = %s WHERE user_id = %s;", (new_val, user_id))
        flash(f"User #{user_id} active status changed to {new_val}.", "info")
    return redirect(url_for("admin.users_mgmt"))


@admin_bp.route("/health")
@login_required
@roles_required("admin")
def health():
    """Database health monitor: row counts for all 24 tables and schema status."""
    tables = [
        "organizations", "branches", "branch_hours", "facilities", "branch_facilities",
        "users", "staff", "trainers", "trainer_assignments", "members",
        "membership_plans", "branch_access_rules", "memberships", "invoices",
        "invoice_items", "payments", "refunds", "expense_categories", "expenses",
        "branch_budgets", "attendance", "training_sessions", "equipment", "audit_log"
    ]
    counts = {}
    for t in tables:
        counts[t] = query_one(f"SELECT COUNT(*) AS c FROM {t};")["c"]

    return render_template("admin/health.html",
                           counts=counts,
                           total_rows=sum(counts.values()),
                           portal_context="admin",
                           active_tab="health")


@admin_bp.route("/audit")
@login_required
@roles_required("admin")
def platform_audit():
    """Global system-wide audit trail."""
    logs = query_all(
        "SELECT a.*, u.email "
        "FROM audit_log a JOIN users u ON a.user_id = u.user_id "
        "ORDER BY a.created_at DESC LIMIT 60;"
    )
    return render_template("admin/platform_audit.html",
                           logs=logs,
                           portal_context="admin",
                           active_tab="audit")
