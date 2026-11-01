"""
Jaskr GymGrid - Authentication & Role-Based Authorization
Enforces least privilege, multi-tenant isolation, IDOR guards, and demo personas.
"""
from functools import wraps
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, abort, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import query_one, query_all, execute_commit
from app.config import Config
import datetime as dt

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def get_current_user():
    """Retrieves session profile for currently logged-in user."""
    if "user_id" not in session:
        return None
    return {
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "role": session.get("role"),
        "full_name": session.get("full_name", "User"),
        "member_id": session.get("member_id"),
        "home_branch_id": session.get("home_branch_id"),
        "staff_id": session.get("staff_id"),
        "job_role": session.get("job_role"),
        "organization_id": session.get("organization_id"),
        "branch_id": session.get("branch_id"),
        "organization_name": session.get("organization_name")
    }


def login_user(user, member=None, staff=None):
    """Establishes authenticated session with complete scoping context."""
    session.clear()
    session["user_id"] = user["user_id"]
    session["email"] = user["email"]
    session["role"] = user["role"]
    
    if user["role"] == "member" and member:
        session["member_id"] = member["member_id"]
        session["home_branch_id"] = member["home_branch_id"]
        session["full_name"] = member["full_name"]
    elif user["role"] in ("staff", "owner", "admin"):
        if staff:
            session["staff_id"] = staff["staff_id"]
            session["job_role"] = staff["job_role"]
            session["organization_id"] = staff["organization_id"]
            session["branch_id"] = staff["branch_id"]
            session["full_name"] = staff["full_name"]
            if staff["organization_id"]:
                org = query_one("SELECT name FROM organizations WHERE organization_id = %s;", (staff["organization_id"],))
                if org:
                    session["organization_name"] = org["name"]
        else:
            session["full_name"] = "Administrator" if user["role"] == "admin" else "Staff"


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login", next=request.url))
            curr_role = session.get("role")
            if curr_role not in allowed_roles:
                return render_template("errors/403.html", 
                                       reason=f"Role '{curr_role}' is not authorized. Required: {', '.join(allowed_roles)}.",
                                       user=get_current_user()), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def job_roles_required(*allowed_job_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login", next=request.url))
            curr_job = session.get("job_role")
            # Owners and Admins generally have supervisory access unless specifically excluded
            if curr_job not in allowed_job_roles and session.get("role") not in ("owner", "admin"):
                return render_template("errors/403.html",
                                       reason=f"Staff job role '{curr_job}' is not authorized. Required: {', '.join(allowed_job_roles)}.",
                                       user=get_current_user()), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_org_scoping(target_org_id):
    """Multi-tenant isolation check: raises 403 if user cannot access target_org_id."""
    user = get_current_user()
    if not user:
        abort(403)
    if user["role"] == "admin":
        return True  # Platform admin is global
    if not target_org_id:
        return True
    if str(user.get("organization_id")) != str(target_org_id):
        abort(403)
    return True


def check_member_scoping(target_member_id):
    """Member isolation check: raises 403 if member tries to access someone else's data."""
    user = get_current_user()
    if not user:
        abort(403)
    if user["role"] in ("admin", "owner", "staff"):
        return True  # Staff/Owner have lookup permissions subject to their org
    if str(user.get("member_id")) != str(target_member_id):
        abort(403)
    return True


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        user = query_one("SELECT * FROM users WHERE LOWER(email) = %s AND is_active = 1;", (email,))
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password. For demo accounts use password 'Demo@1234'.", "error")
            return render_template("auth/login.html", email=email, demo_mode=Config.DEMO_MODE)
        
        member = None
        staff = None
        if user["role"] == "member":
            member = query_one("SELECT * FROM members WHERE user_id = %s;", (user["user_id"],))
        elif user["role"] in ("staff", "owner", "admin"):
            staff = query_one("SELECT * FROM staff WHERE user_id = %s;", (user["user_id"],))
            
        login_user(user, member, staff)
        
        # Route to respective portal
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        
        if user["role"] == "member":
            return redirect(url_for("member.dashboard"))
        elif user["role"] == "owner":
            return redirect(url_for("owner.dashboard"))
        elif user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        elif user["role"] == "staff":
            job = staff.get("job_role") if staff else ""
            if job == "FRONT_DESK":
                return redirect(url_for("staff.front_desk"))
            elif job == "TRAINER":
                return redirect(url_for("staff.trainer_console"))
            elif job == "FINANCE":
                return redirect(url_for("staff.finance_desk"))
            else:
                return redirect(url_for("staff.branch_manager"))
        return redirect(url_for("public.home"))
        
    return render_template("auth/login.html", demo_mode=Config.DEMO_MODE)


@auth_bp.route("/quick-login/<path:email>")
def quick_login(email):
    """One-click instant login for evaluators in DEMO_MODE."""
    if not Config.DEMO_MODE:
        abort(404)
    email = email.strip().lower()
    user = query_one("SELECT * FROM users WHERE LOWER(email) = %s;", (email,))
    if not user:
        flash(f"Demo user '{email}' not found.", "error")
        return redirect(url_for("auth.login"))
    
    member = None
    staff = None
    if user["role"] == "member":
        member = query_one("SELECT * FROM members WHERE user_id = %s;", (user["user_id"],))
    else:
        staff = query_one("SELECT * FROM staff WHERE user_id = %s;", (user["user_id"],))
        
    login_user(user, member, staff)
    flash(f"Switched session to {session['full_name']} ({user['role'].upper()})", "success")
    
    if user["role"] == "member":
        return redirect(url_for("member.dashboard"))
    elif user["role"] == "owner":
        return redirect(url_for("owner.dashboard"))
    elif user["role"] == "admin":
        return redirect(url_for("admin.dashboard"))
    elif user["role"] == "staff":
        job = staff.get("job_role") if staff else ""
        if job == "FRONT_DESK":
            return redirect(url_for("staff.front_desk"))
        elif job == "TRAINER":
            return redirect(url_for("staff.trainer_console"))
        elif job == "FINANCE":
            return redirect(url_for("staff.finance_desk"))
        else:
            return redirect(url_for("staff.branch_manager"))
    return redirect(url_for("public.home"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("public.home"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Member registration flow."""
    branches = query_all("SELECT branch_id, name, city FROM branches ORDER BY city, name;")
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        home_branch_id = request.form.get("home_branch_id")
        
        if not full_name or not email or not password or not home_branch_id:
            flash("All fields are required.", "error")
            return render_template("auth/register.html", branches=branches)
            
        existing = query_one("SELECT user_id FROM users WHERE LOWER(email) = %s;", (email,))
        if existing:
            flash("An account with that email already exists.", "error")
            return render_template("auth/register.html", branches=branches)
            
        hashed = generate_password_hash(password)
        now_str = Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = Config.get_app_today().strftime("%Y-%m-%d")
        
        user_id = execute_commit(
            "INSERT INTO users (email, password_hash, role, is_active, created_at, last_login) "
            "VALUES (%s, %s, 'member', 1, %s, %s);",
            (email, hashed, now_str, now_str)
        )
        member_id = execute_commit(
            "INSERT INTO members (user_id, home_branch_id, full_name, phone, registration_date) "
            "VALUES (%s, %s, %s, %s, %s);",
            (user_id, home_branch_id, full_name, phone, today_str)
        )
        
        user = query_one("SELECT * FROM users WHERE user_id = %s;", (user_id,))
        member = query_one("SELECT * FROM members WHERE member_id = %s;", (member_id,))
        login_user(user, member)
        
        flash("Registration successful! Welcome to Jaskr GymGrid.", "success")
        return redirect(url_for("member.dashboard"))
        
    return render_template("auth/register.html", branches=branches)


@auth_bp.route("/list-gym", methods=["GET", "POST"])
def list_gym():
    """Business registration for Gym Owners (creates PENDING organization)."""
    if request.method == "POST":
        org_name = request.form.get("org_name", "").strip()
        brand_type = request.form.get("brand_type", "independent")
        hq_city = request.form.get("hq_city", "").strip()
        contact_email = request.form.get("contact_email", "").strip().lower()
        owner_name = request.form.get("owner_name", "").strip()
        owner_email = request.form.get("owner_email", "").strip().lower()
        owner_phone = request.form.get("owner_phone", "").strip()
        password = request.form.get("password", "")
        
        if not org_name or not contact_email or not owner_email or not password:
            flash("Please fill in all mandatory fields.", "error")
            return render_template("auth/list_gym.html")
            
        existing = query_one("SELECT user_id FROM users WHERE LOWER(email) = %s;", (owner_email,))
        if existing:
            flash("A user with this owner email already exists.", "error")
            return render_template("auth/list_gym.html")
            
        hashed = generate_password_hash(password)
        now_str = Config.get_app_now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = Config.get_app_today().strftime("%Y-%m-%d")
        
        org_id = execute_commit(
            "INSERT INTO organizations (name, contact_email, status, brand_type, headquarters_city, created_at) "
            "VALUES (%s, %s, 'pending', %s, %s, %s);",
            (org_name, contact_email, brand_type, hq_city, today_str)
        )
        
        user_id = execute_commit(
            "INSERT INTO users (email, password_hash, role, is_active, created_at) "
            "VALUES (%s, %s, 'owner', 1, %s);",
            (owner_email, hashed, now_str)
        )
        
        execute_commit(
            "INSERT INTO staff (user_id, organization_id, branch_id, job_role, full_name, phone, status, hired_date) "
            "VALUES (%s, %s, NULL, 'OWNER', %s, %s, 'active', %s);",
            (user_id, org_id, owner_name, owner_phone, today_str)
        )
        
        flash(f"Application for '{org_name}' submitted successfully! It is now pending approval by the Platform Admin.", "success")
        return redirect(url_for("auth.login"))
        
    return render_template("auth/list_gym.html")
