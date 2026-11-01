"""
Jaskr GymGrid - Member Portal Blueprint
Handles Dashboard, Access Checker (D2), Check-in/Out, Simulated Checkout (ACID),
Attendance Heatmap & Streaks, Billing, Invoices with GST, Refunds, Training Sessions, and Data Export.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, Response
from app.auth import login_required, roles_required, get_current_user, check_member_scoping
from app.database import query_all, query_one, execute_commit, sp_record_payment
from app.config import Config
import datetime as dt
import json

member_bp = Blueprint("member", __name__, url_prefix="/member")


def get_member_context():
    """Helper to fetch member and active membership details."""
    user = get_current_user()
    if not user or not user.get("member_id"):
        return None, None
    
    member = query_one(
        "SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name, o.organization_id "
        "FROM members m "
        "JOIN branches b ON m.home_branch_id = b.branch_id "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE m.member_id = %s;", (user["member_id"],)
    )
    
    # Active membership
    active_ms = query_one(
        "SELECT ms.*, p.plan_name, p.duration_months, p.price, p.description AS plan_desc "
        "FROM memberships ms "
        "JOIN membership_plans p ON ms.plan_id = p.plan_id "
        "WHERE ms.member_id = %s AND ms.status = 'active' "
        "ORDER BY ms.end_date DESC LIMIT 1;", (user["member_id"],)
    )
    return member, active_ms


@member_bp.route("/dashboard")
@login_required
@roles_required("member")
def dashboard():
    """Member home dashboard with quick check-in, days left, next training session, and streak."""
    member, active_ms = get_member_context()
    if not member:
        flash("Member profile not found.", "error")
        return redirect(url_for("public.home"))

    # Days remaining calculation against DEMO_TODAY (2026-10-30)
    today = Config.get_app_today()
    days_left = 0
    if active_ms:
        end_d = dt.datetime.strptime(active_ms["end_date"], "%Y-%m-%d").date()
        days_left = max(0, (end_d - today).days)

    # Next scheduled training session
    next_session = query_one(
        "SELECT ts.*, t.full_name AS trainer_name, b.name AS branch_name "
        "FROM training_sessions ts "
        "JOIN trainers t ON ts.trainer_id = t.trainer_id "
        "JOIN branches b ON ts.branch_id = b.branch_id "
        "WHERE ts.member_id = %s AND ts.status = 'scheduled' AND ts.session_start >= %s "
        "ORDER BY ts.session_start ASC LIMIT 1;", 
        (member["member_id"], Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    # Check if currently inside (attendance check_out IS NULL)
    currently_inside = query_one(
        "SELECT a.*, b.name AS branch_name "
        "FROM attendance a "
        "JOIN branches b ON a.branch_id = b.branch_id "
        "WHERE a.member_id = %s AND a.check_out IS NULL "
        "ORDER BY a.check_in DESC LIMIT 1;", (member["member_id"],)
    )

    # Attendance streak and stats
    recent_attendance = query_all(
        "SELECT a.*, b.name AS branch_name "
        "FROM attendance a "
        "JOIN branches b ON a.branch_id = b.branch_id "
        "WHERE a.member_id = %s "
        "ORDER BY a.check_in DESC LIMIT 5;", (member["member_id"],)
    )
    total_checkins = query_one("SELECT COUNT(*) AS c FROM attendance WHERE member_id = %s;", (member["member_id"],))["c"]

    # Recent Invoices
    recent_invoices = query_all(
        "SELECT * FROM invoices WHERE member_id = %s ORDER BY invoice_date DESC LIMIT 3;", (member["member_id"],)
    )

    return render_template("member/dashboard.html",
                           member=member,
                           active_ms=active_ms,
                           days_left=days_left,
                           next_session=next_session,
                           currently_inside=currently_inside,
                           recent_attendance=recent_attendance,
                           total_checkins=total_checkins,
                           recent_invoices=recent_invoices,
                           portal_context="member",
                           active_tab="dashboard")


@member_bp.route("/access-checker", methods=["GET", "POST"])
@login_required
@roles_required("member")
def access_checker():
    """D2 Cross-branch Access Checker: member picks any gym branch and receives instant plain-English verdict."""
    member, active_ms = get_member_context()
    all_branches = query_all(
        "SELECT b.*, o.name AS organization_name "
        "FROM branches b JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE o.status = 'active' ORDER BY b.city, b.name;"
    )

    target_branch_id = request.args.get("branch_id") or request.form.get("branch_id")
    result = None

    if target_branch_id:
        target_branch = query_one(
            "SELECT b.*, o.name AS organization_name "
            "FROM branches b JOIN organizations o ON b.organization_id = o.organization_id "
            "WHERE b.branch_id = %s;", (int(target_branch_id),)
        )
        if target_branch:
            result = evaluate_branch_access(member, active_ms, target_branch)

    # Compute which branches this active plan can reach for the reachability map
    reachable_branch_ids = []
    if active_ms:
        for b in all_branches:
            res = evaluate_branch_access(member, active_ms, b)
            if res["status"] in ("ALLOWED", "ALLOWED WITH CONDITIONS"):
                reachable_branch_ids.append(b["branch_id"])

    return render_template("member/access_checker.html",
                           member=member,
                           active_ms=active_ms,
                           all_branches=all_branches,
                           target_branch_id=int(target_branch_id) if target_branch_id else None,
                           result=result,
                           reachable_branch_ids=reachable_branch_ids,
                           portal_context="member",
                           active_tab="access_checker")


def evaluate_branch_access(member, active_ms, target_branch):
    """
    Core Access Rule Evaluation Engine (D2).
    Enforces HOME_ONLY, SAME_CITY, WEEKDAYS_ONLY, and FULL semantics.
    """
    today = Config.get_app_today()
    dow = today.weekday() # 0 = Monday, ..., 6 = Sunday

    # 1. Membership status check
    if not active_ms:
        return {
            "status": "DENIED",
            "badge_class": "badge-coral",
            "reason": "No active membership pass. Your current plan status is expired or inactive.",
            "rule": "None",
            "access_type": "N/A"
        }

    # 2. Organization check (a plan never reaches branches of another gym network)
    target_org_id = target_branch["organization_id"]
    rule = query_one(
        "SELECT * FROM branch_access_rules WHERE plan_id = %s AND branch_id = %s;",
        (active_ms["plan_id"], target_branch["branch_id"])
    )

    if not rule:
        return {
            "status": "DENIED",
            "badge_class": "badge-coral",
            "reason": f"Cross-brand access prohibited. '{target_branch['name']}' belongs to {target_branch['organization_name']}, while your plan '{active_ms['plan_name']}' is restricted to {member['organization_name']}.",
            "rule": "Cross-Organization Boundary Isolation",
            "access_type": "NONE"
        }

    access_type = rule["access_type"]

    # 3. HOME_ONLY
    if access_type == "HOME_ONLY":
        if target_branch["branch_id"] == member["home_branch_id"]:
            return {
                "status": "ALLOWED",
                "badge_class": "badge-mint",
                "reason": f"Allowed. '{target_branch['name']}' is your registered home branch under your {active_ms['plan_name']} plan.",
                "rule": rule["conditions"],
                "access_type": access_type
            }
        else:
            return {
                "status": "DENIED",
                "badge_class": "badge-coral",
                "reason": f"Access denied. Your plan '{active_ms['plan_name']}' is HOME_ONLY, valid exclusively at '{member['home_branch_name']}'.",
                "rule": rule["conditions"],
                "access_type": access_type
            }

    # 4. SAME_CITY
    elif access_type == "SAME_CITY":
        if target_branch["city"].lower() == member["home_branch_city"].lower():
            return {
                "status": "ALLOWED",
                "badge_class": "badge-mint",
                "reason": f"Allowed. Both your home branch and '{target_branch['name']}' are in {member['home_branch_city']}.",
                "rule": rule["conditions"],
                "access_type": access_type
            }
        else:
            return {
                "status": "DENIED",
                "badge_class": "badge-coral",
                "reason": f"Access denied. Your plan provides multi-branch access within your home city ({member['home_branch_city']}). Target branch is located in {target_branch['city']}.",
                "rule": rule["conditions"],
                "access_type": access_type
            }

    # 5. WEEKDAYS_ONLY
    elif access_type == "WEEKDAYS_ONLY":
        if dow < 5:
            return {
                "status": "ALLOWED",
                "badge_class": "badge-mint",
                "reason": f"Allowed. Today is a weekday and your plan is valid at all {member['organization_name']} branches.",
                "rule": rule["conditions"],
                "access_type": access_type
            }
        else:
            return {
                "status": "DENIED",
                "badge_class": "badge-coral",
                "reason": f"Access denied on weekends. '{active_ms['plan_name']}' is a WEEKDAYS_ONLY pass (valid Monday through Friday).",
                "rule": rule["conditions"],
                "access_type": access_type
            }

    # 6. FULL
    elif access_type == "FULL":
        return {
            "status": "ALLOWED",
            "badge_class": "badge-mint",
            "reason": f"Full All-Access granted. Your '{active_ms['plan_name']}' allows entry to every branch across India during operating hours.",
            "rule": rule["conditions"],
            "access_type": access_type
        }

    return {
        "status": "DENIED",
        "badge_class": "badge-coral",
        "reason": "Unrecognized access configuration.",
        "rule": "Unknown",
        "access_type": access_type
    }


@member_bp.route("/check-in", methods=["GET", "POST"])
@login_required
@roles_required("member")
def check_in():
    """Simulated contactless QR check-in & check-out with attendance history and heatmap streak."""
    member, active_ms = get_member_context()
    
    # Check if currently inside
    current = query_one(
        "SELECT a.*, b.name AS branch_name FROM attendance a JOIN branches b ON a.branch_id = b.branch_id "
        "WHERE a.member_id = %s AND a.check_out IS NULL ORDER BY a.check_in DESC LIMIT 1;", (member["member_id"],)
    )

    if request.method == "POST":
        action = request.form.get("action")
        target_branch_id = int(request.form.get("branch_id", member["home_branch_id"]))
        now_str = Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S")

        if action == "check_out" and current:
            execute_commit("UPDATE attendance SET check_out = %s WHERE attendance_id = %s;", (now_str, current["attendance_id"]))
            flash(f"Checked out successfully from {current['branch_name']}. Have a great recovery!", "success")
            return redirect(url_for("member.check_in"))

        elif action == "check_in":
            if current:
                flash(f"You are already checked in at {current['branch_name']}! Please check out first.", "warning")
                return redirect(url_for("member.check_in"))

            # Evaluate access first
            target_branch = query_one("SELECT b.*, o.name AS organization_name FROM branches b JOIN organizations o ON b.organization_id = o.organization_id WHERE b.branch_id = %s;", (target_branch_id,))
            verdict = evaluate_branch_access(member, active_ms, target_branch)

            if verdict["status"] not in ("ALLOWED", "ALLOWED WITH CONDITIONS"):
                flash(f"Check-in rejected: {verdict['reason']}", "error")
                return redirect(url_for("member.check_in"))

            execute_commit(
                "INSERT INTO attendance (member_id, branch_id, check_in, check_out) VALUES (%s, %s, %s, NULL);",
                (member["member_id"], target_branch_id, now_str)
            )
            flash(f"Access Allowed! Welcome to {target_branch['name']}.", "success")
            return redirect(url_for("member.check_in", celebrate="1"))

    # History
    history = query_all(
        "SELECT a.*, b.name AS branch_name, b.city "
        "FROM attendance a JOIN branches b ON a.branch_id = b.branch_id "
        "WHERE a.member_id = %s ORDER BY a.check_in DESC LIMIT 20;", (member["member_id"],)
    )
    
    all_branches = query_all("SELECT branch_id, name, city FROM branches WHERE organization_id = %s ORDER BY city, name;", (member["organization_id"],))

    return render_template("member/check_in.html",
                           member=member,
                           active_ms=active_ms,
                           current=current,
                           history=history,
                           all_branches=all_branches,
                           portal_context="member",
                           active_tab="check_in")


@member_bp.route("/memberships")
@login_required
@roles_required("member")
def memberships():
    """List all memberships (active, expired, pending) with option to buy/renew."""
    member, active_ms = get_member_context()
    all_ms = query_all(
        "SELECT ms.*, p.plan_name, p.duration_months, p.price, p.description "
        "FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id "
        "WHERE ms.member_id = %s ORDER BY ms.start_date DESC;", (member["member_id"],)
    )
    
    available_plans = query_all(
        "SELECT * FROM membership_plans WHERE organization_id = %s ORDER BY duration_months, price;", (member["organization_id"],)
    )

    return render_template("member/memberships.html",
                           member=member,
                           active_ms=active_ms,
                           all_ms=all_ms,
                           available_plans=available_plans,
                           portal_context="member",
                           active_tab="memberships")


@member_bp.route("/checkout/<int:plan_id>", methods=["GET", "POST"])
@login_required
@roles_required("member")
def checkout(plan_id):
    """Simulated membership checkout with line items, GST 18%, and atomic sp_record_payment transaction."""
    member, active_ms = get_member_context()
    plan = query_one("SELECT * FROM membership_plans WHERE plan_id = %s;", (plan_id,))
    if not plan:
        flash("Plan not found.", "error")
        return redirect(url_for("member.memberships"))

    # Financial line items calculation
    base_price = float(plan["price"])
    joining_fee = 500.0 if not active_ms else 0.0 # Joining fee only for new members
    subtotal = base_price + joining_fee
    gst_amount = round(subtotal * 0.18, 2)
    grand_total = round(subtotal + gst_amount, 2)

    if request.method == "POST":
        method = request.form.get("payment_method", "UPI")
        sim_failure = int(request.form.get("simulate_failure", 0))
        today = Config.get_app_today()
        start_date = today
        end_date = today + dt.timedelta(days=plan["duration_months"] * 30)
        
        # 1. Create membership record with status = 'pending'
        ms_id = execute_commit(
            "INSERT INTO memberships (member_id, plan_id, start_date, end_date, status) "
            "VALUES (%s, %s, %s, %s, 'pending');",
            (member["member_id"], plan["plan_id"], start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )

        # 2. Create invoice and invoice_items
        inv_number = f"JGG/{today.year}/{ms_id + 9000:06d}"
        inv_id = execute_commit(
            "INSERT INTO invoices (invoice_number, member_id, membership_id, invoice_date, due_date, total, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'pending');",
            (inv_number, member["member_id"], ms_id, today.strftime("%Y-%m-%d"), (today + dt.timedelta(days=7)).strftime("%Y-%m-%d"), grand_total)
        )

        # Line items
        execute_commit(
            "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, line_total) "
            "VALUES (%s, %s, 1, %s, %s);",
            (inv_id, f"{plan['plan_name']} - {plan['duration_months']} month(s)", base_price, base_price)
        )
        if joining_fee > 0:
            execute_commit(
                "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, line_total) "
                "VALUES (%s, 'Joining Fee', 1, %s, %s);",
                (inv_id, joining_fee, joining_fee)
            )
        execute_commit(
            "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, line_total) "
            "VALUES (%s, 'GST @ 18%', 1, %s, %s);",
            (inv_id, gst_amount, gst_amount)
        )

        # 3. Call sp_record_payment stored procedure
        res = sp_record_payment(
            membership_id=ms_id,
            invoice_id=inv_id,
            branch_id=member["home_branch_id"],
            amount=grand_total,
            payment_method=method,
            user_id=session["user_id"],
            simulate_failure=sim_failure
        )

        if res["success"]:
            flash(f"Payment Successful! {res['message']} Your plan is now ACTIVE.", "success")
            return redirect(url_for("member.receipt", payment_id=res["payment_id"]))
        else:
            flash(f"Payment Transaction Failed (ACID Rollback demonstrated): {res['message']}", "error")
            return render_template("member/checkout.html",
                                   member=member,
                                   plan=plan,
                                   base_price=base_price,
                                   joining_fee=joining_fee,
                                   gst_amount=gst_amount,
                                   grand_total=grand_total,
                                   failed=True,
                                   portal_context="member")

    return render_template("member/checkout.html",
                           member=member,
                           plan=plan,
                           base_price=base_price,
                           joining_fee=joining_fee,
                           gst_amount=gst_amount,
                           grand_total=grand_total,
                           portal_context="member")


@member_bp.route("/receipt/<int:payment_id>")
@login_required
@roles_required("member")
def receipt(payment_id):
    """Print-friendly receipt with Jaskr GymGrid branding, GST details, and transaction reference."""
    user = get_current_user()
    payment = query_one(
        "SELECT p.*, m.member_id, inv.invoice_number, inv.invoice_date, m.full_name, m.phone, b.name AS branch_name, o.name AS org_name "
        "FROM payments p "
        "JOIN invoices inv ON p.invoice_id = inv.invoice_id "
        "JOIN members m ON inv.member_id = m.member_id "
        "JOIN branches b ON p.branch_id = b.branch_id "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE p.payment_id = %s;", (payment_id,)
    )
    if not payment:
        flash("Receipt record not found.", "error")
        return redirect(url_for("member.dashboard"))

    check_member_scoping(payment["member_id"])
    items = query_all("SELECT * FROM invoice_items WHERE invoice_id = %s;", (payment["invoice_id"],))

    return render_template("member/receipt.html", payment=payment, items=items, portal_context="member")


@member_bp.route("/billing")
@login_required
@roles_required("member")
def billing():
    """Invoices, payments history, GST breakdowns, and refund requests."""
    member, active_ms = get_member_context()
    invoices = query_all(
        "SELECT * FROM invoices WHERE member_id = %s ORDER BY invoice_date DESC;", (member["member_id"],)
    )
    payments = query_all(
        "SELECT p.*, inv.invoice_number "
        "FROM payments p "
        "LEFT JOIN invoices inv ON p.invoice_id = inv.invoice_id "
        "JOIN memberships ms ON p.membership_id = ms.membership_id "
        "WHERE ms.member_id = %s ORDER BY p.payment_date DESC;", (member["member_id"],)
    )
    refunds = query_all(
        "SELECT r.*, p.amount AS orig_payment_amount, p.transaction_ref "
        "FROM refunds r "
        "JOIN payments p ON r.payment_id = p.payment_id "
        "JOIN memberships ms ON p.membership_id = ms.membership_id "
        "WHERE ms.member_id = %s ORDER BY r.refund_date DESC;", (member["member_id"],)
    )

    return render_template("member/billing.html",
                           member=member,
                           invoices=invoices,
                           payments=payments,
                           refunds=refunds,
                           portal_context="member",
                           active_tab="billing")


@member_bp.route("/request-refund", methods=["POST"])
@login_required
@roles_required("member")
def request_refund():
    """Submit refund request against a successful payment."""
    member, _ = get_member_context()
    payment_id = int(request.form.get("payment_id"))
    reason = request.form.get("reason", "Member requested cancellation").strip()
    refund_amt = float(request.form.get("refund_amount", 0.0))

    payment = query_one(
        "SELECT p.* FROM payments p JOIN memberships ms ON p.membership_id = ms.membership_id WHERE p.payment_id = %s AND ms.member_id = %s;",
        (payment_id, member["member_id"])
    )
    if not payment:
        flash("Payment not found or unauthorized.", "error")
        return redirect(url_for("member.billing"))

    # Limit check: SUM(refunds) <= payment amount
    cur_sum = query_one("SELECT COALESCE(SUM(refund_amount), 0.0) AS s FROM refunds WHERE payment_id = %s AND status != 'rejected';", (payment_id,))["s"]
    if cur_sum + refund_amt > float(payment["amount"]) + 0.01:
        flash(f"Refund request rejected: Total refunds cannot exceed initial payment amount (₹{payment['amount']:,.2f}).", "error")
        return redirect(url_for("member.billing"))

    today_str = Config.get_app_today().strftime("%Y-%m-%d")
    execute_commit(
        "INSERT INTO refunds (payment_id, refund_amount, refund_date, reason, status) "
        "VALUES (%s, %s, %s, %s, 'requested');",
        (payment_id, refund_amt, today_str, reason)
    )
    flash("Refund request submitted successfully! It is queued for owner/finance review.", "success")
    return redirect(url_for("member.billing"))


@member_bp.route("/training", methods=["GET", "POST"])
@login_required
@roles_required("member")
def training():
    """Member personal training schedule and session booking."""
    member, active_ms = get_member_context()
    trainers = query_all(
        "SELECT t.* FROM trainers t JOIN trainer_assignments ta ON t.trainer_id = ta.trainer_id "
        "WHERE ta.branch_id = %s AND (ta.end_date IS NULL OR ta.end_date >= %s) ORDER BY t.full_name;",
        (member["home_branch_id"], Config.get_app_today().strftime("%Y-%m-%d"))
    )

    if request.method == "POST":
        trainer_id = int(request.form.get("trainer_id"))
        session_time = request.form.get("session_time")
        duration = int(request.form.get("duration", 60))
        focus = request.form.get("focus", "General Strength")

        execute_commit(
            "INSERT INTO training_sessions (member_id, trainer_id, branch_id, session_start, duration_minutes, status, focus) "
            "VALUES (%s, %s, %s, %s, %s, 'scheduled', %s);",
            (member["member_id"], trainer_id, member["home_branch_id"], session_time, duration, focus)
        )
        flash("Personal training session booked successfully!", "success")
        return redirect(url_for("member.training"))

    sessions = query_all(
        "SELECT ts.*, t.full_name AS trainer_name, t.specialization, b.name AS branch_name "
        "FROM training_sessions ts "
        "JOIN trainers t ON ts.trainer_id = t.trainer_id "
        "JOIN branches b ON ts.branch_id = b.branch_id "
        "WHERE ts.member_id = %s ORDER BY ts.session_start DESC LIMIT 20;", (member["member_id"],)
    )

    return render_template("member/training.html",
                           member=member,
                           trainers=trainers,
                           sessions=sessions,
                           portal_context="member",
                           active_tab="training")


@member_bp.route("/profile", methods=["GET", "POST"])
@login_required
@roles_required("member")
def profile():
    """Edit personal contact details and download all member data as JSON."""
    member, active_ms = get_member_context()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        execute_commit("UPDATE members SET full_name = %s, phone = %s WHERE member_id = %s;", (full_name, phone, member["member_id"]))
        session["full_name"] = full_name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("member.profile"))

    return render_template("member/profile.html",
                           member=member,
                           active_ms=active_ms,
                           portal_context="member",
                           active_tab="profile")


@member_bp.route("/export-data")
@login_required
@roles_required("member")
def export_data():
    """GDPR / Privacy Data Portability: export all personal records as structured JSON."""
    member, active_ms = get_member_context()
    mid = member["member_id"]

    data = {
        "member_profile": member,
        "active_membership": active_ms,
        "memberships": query_all("SELECT * FROM memberships WHERE member_id = %s;", (mid,)),
        "attendance_history": query_all("SELECT * FROM attendance WHERE member_id = %s;", (mid,)),
        "invoices": query_all("SELECT * FROM invoices WHERE member_id = %s;", (mid,)),
        "training_sessions": query_all("SELECT * FROM training_sessions WHERE member_id = %s;", (mid,))
    }

    resp = Response(json.dumps(data, indent=2, default=str), mimetype="application/json")
    resp.headers["Content-Disposition"] = f"attachment; filename=jaskr_gymgrid_member_{mid}_data.json"
    return resp
