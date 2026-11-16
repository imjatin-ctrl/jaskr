"""
Jaskr GymGrid - Public Discovery Portal
Handles Home, Search & Discover, Branch Profile, Brand Profile,
Side-by-Side Gym Comparison, Crowd Explorer, Gap Analysis, and About Page.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.database import query_all, query_one
from app.config import Config
import json

public_bp = Blueprint("public", __name__)


@public_bp.route("/portals")
def portals():
    """Portal Hub - lets users choose Member, Staff, Owner, Admin or DBMS Lab portals."""
    return render_template("portals.html", portal_context=None)



@public_bp.route("/")
def home():
    """Home landing page with animated hero, live search bar, city pins, and DB counters."""
    stats = {
        "cities": query_one("SELECT COUNT(DISTINCT city) AS c FROM branches WHERE organization_id != 5;")["c"],
        "branches": query_one("SELECT COUNT(*) AS c FROM branches WHERE organization_id != 5;")["c"],
        "members": query_one("SELECT COUNT(*) AS c FROM members;")["c"],
        "checkins": query_one("SELECT COUNT(*) AS c FROM attendance;")["c"]
    }
    
    cities = query_all("SELECT DISTINCT city FROM branches WHERE organization_id != 5 ORDER BY city;")
    featured_orgs = query_all(
        "SELECT o.*, COUNT(b.branch_id) AS branch_count "
        "FROM organizations o "
        "LEFT JOIN branches b ON o.organization_id = b.organization_id "
        "WHERE o.status = 'active' "
        "GROUP BY o.organization_id "
        "ORDER BY branch_count DESC;"
    )
    
    # 3x3 crowd preview data
    crowd_preview = query_all(
        "SELECT b.name, v.day_of_week_0_mon, v.hour_of_day, v.total_visits "
        "FROM v_branch_crowd_hourly v "
        "JOIN branches b ON v.branch_id = b.branch_id "
        "WHERE b.branch_id = 1 AND v.day_of_week_0_mon = 0 "
        "ORDER BY v.hour_of_day "
        "LIMIT 9;"
    )

    sql_explanation = "SELECT COUNT(DISTINCT city), COUNT(*) FROM branches ... aggregate statistics dynamically computed from MySQL database."
    return render_template("public/home.html", 
                           stats=stats, 
                           cities=cities, 
                           featured_orgs=featured_orgs, 
                           crowd_preview=crowd_preview,
                           sql_explanation=sql_explanation)


@public_bp.route("/discover")
def discover():
    """Discover gyms with city filter, price slider, facility multi-select, and synchronized SVG map."""
    selected_city = request.args.get("city", "").strip()
    selected_brand = request.args.get("brand", "").strip()
    search_q = request.args.get("q", "").strip()
    facility_filter = request.args.getlist("facility")
    max_price = request.args.get("max_price", "")
    
    cities = query_all("SELECT DISTINCT city FROM branches WHERE organization_id != 5 ORDER BY city;")
    all_facilities = query_all("SELECT * FROM facilities ORDER BY facility_name;")
    all_brands = query_all("SELECT * FROM organizations WHERE status = 'active' ORDER BY name;")

    # Dynamic query with parameters
    conditions = ["b.organization_id != 5"]
    params = []

    if selected_city:
        conditions.append("b.city = %s")
        params.append(selected_city)
    
    if selected_brand:
        conditions.append("b.organization_id = %s")
        params.append(selected_brand)

    if search_q:
        conditions.append("(b.name LIKE %s OR b.address LIKE %s OR b.city LIKE %s)")
        q_wild = f"%{search_q}%"
        params.extend([q_wild, q_wild, q_wild])

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT 
            b.*, 
            o.name AS organization_name, 
            o.brand_type,
            COALESCE(min_p.min_price, 0) AS starting_price,
            (SELECT COUNT(*) FROM branch_facilities bf WHERE bf.branch_id = b.branch_id) AS facility_count
        FROM branches b
        JOIN organizations o ON b.organization_id = o.organization_id
        LEFT JOIN (
            SELECT organization_id, MIN(price) AS min_price 
            FROM membership_plans 
            GROUP BY organization_id
        ) min_p ON b.organization_id = min_p.organization_id
        WHERE {where_clause}
        ORDER BY b.city, b.name;
    """
    branches = query_all(sql, params)

    # Post-filter by facility multi-select if specified
    if facility_filter:
        fac_set = set(int(f) for f in facility_filter if f.isdigit())
        filtered_branches = []
        for b in branches:
            b_facs = query_all("SELECT facility_id FROM branch_facilities WHERE branch_id = %s;", (b["branch_id"],))
            b_fac_set = set(r["facility_id"] for r in b_facs)
            if fac_set.issubset(b_fac_set):
                filtered_branches.append(b)
        branches = filtered_branches

    # Price filter
    if max_price and max_price.isdigit():
        branches = [b for b in branches if b["starting_price"] <= float(max_price)]

    return render_template("public/discover.html", 
                           branches=branches, 
                           cities=cities, 
                           all_facilities=all_facilities, 
                           all_brands=all_brands,
                           selected_city=selected_city,
                           selected_brand=selected_brand,
                           search_q=search_q,
                           facility_filter=facility_filter,
                           max_price=max_price,
                           raw_sql=sql)


@public_bp.route("/branch/<int:branch_id>")
def branch_detail(branch_id):
    """Detailed view for a single gym branch including facilities, hours, equipment, trainers, and crowd heat grid."""
    branch = query_one(
        "SELECT b.*, o.name AS organization_name, o.brand_type "
        "FROM branches b JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE b.branch_id = %s;", (branch_id,)
    )
    if not branch:
        return render_template("errors/404.html"), 404

    hours = query_all("SELECT * FROM branch_hours WHERE branch_id = %s ORDER BY day_of_week;", (branch_id,))
    facilities = query_all(
        "SELECT f.*, bf.availability_notes "
        "FROM branch_facilities bf JOIN facilities f ON bf.facility_id = f.facility_id "
        "WHERE bf.branch_id = %s ORDER BY f.facility_name;", (branch_id,)
    )
    plans = query_all("SELECT * FROM membership_plans WHERE organization_id = %s ORDER BY duration_months, price;", (branch["organization_id"],))
    trainers = query_all(
        "SELECT t.*, ta.start_date "
        "FROM trainer_assignments ta JOIN trainers t ON ta.trainer_id = t.trainer_id "
        "WHERE ta.branch_id = %s AND (ta.end_date IS NULL OR ta.end_date >= '2026-10-30') "
        "ORDER BY t.full_name;", (branch_id,)
    )
    equipment = query_all("SELECT * FROM equipment WHERE branch_id = %s ORDER BY condition_status, equipment_name;", (branch_id,))
    
    # Crowd Heat Grid Data (Day of Week x Hour of Day)
    # Using 8-week lookback
    crowd_data = query_all(
        "SELECT "
        "  CAST(strftime('%w', check_in) AS INTEGER) AS dow, "
        "  CAST(strftime('%H', check_in) AS INTEGER) AS hour, "
        "  COUNT(*) AS visits "
        "FROM attendance "
        "WHERE branch_id = %s AND check_in >= '2026-08-03' "
        "GROUP BY dow, hour;", (branch_id,)
    )
    total_samples = sum(c["visits"] for c in crowd_data)
    
    # Construct 7x24 matrix
    crowd_matrix = {}
    for d in range(7):
        crowd_matrix[d] = {h: 0 for h in range(5, 23)} # Gym active hours 05:00 - 23:00
    for r in crowd_data:
        d = r["dow"]
        # In SQLite %w: 0=Sunday, 1=Monday... Translate to 0=Monday..6=Sunday
        dow_idx = (d - 1) % 7
        h = r["hour"]
        if h in crowd_matrix[dow_idx]:
            crowd_matrix[dow_idx][h] = r["visits"]

    # Normalize into Quiet / Moderate / Busy categories based on branch capacity
    cap = branch["capacity"]
    normalized_matrix = {}
    for d in range(7):
        normalized_matrix[d] = {}
        for h, v in crowd_matrix[d].items():
            ratio = v / (cap * 0.45) # Typical peak divisor
            if v == 0:
                label = "none"
            elif ratio < 0.4:
                label = "quiet"
            elif ratio < 0.75:
                label = "moderate"
            else:
                label = "busy"
            normalized_matrix[d][h] = {"count": v, "level": label}

    return render_template("public/branch_detail.html",
                           branch=branch,
                           hours=hours,
                           facilities=facilities,
                           plans=plans,
                           trainers=trainers,
                           equipment=equipment,
                           crowd_matrix=normalized_matrix,
                           total_samples=total_samples)


@public_bp.route("/brand/<int:organization_id>")
def brand_detail(organization_id):
    """Brand overview showing all branches across cities and shared network plans."""
    org = query_one("SELECT * FROM organizations WHERE organization_id = %s;", (organization_id,))
    if not org:
        return render_template("errors/404.html"), 404
        
    branches = query_all("SELECT * FROM branches WHERE organization_id = %s ORDER BY city, name;", (organization_id,))
    plans = query_all("SELECT * FROM membership_plans WHERE organization_id = %s ORDER BY price;", (organization_id,))
    
    return render_template("public/brand_detail.html", org=org, branches=branches, plans=plans)


@public_bp.route("/compare")
def compare():
    """Side-by-side comparison of up to 4 selected gym branches."""
    branch_ids = request.args.getlist("id")
    if not branch_ids:
        # Default comparison sample across cities
        branch_ids = [1, 4, 10, 14]
    else:
        branch_ids = [int(i) for i in branch_ids if str(i).isdigit()][:4]
        
    all_branches = query_all("SELECT branch_id, name, city FROM branches WHERE organization_id != 5 ORDER BY city, name;")
    
    compared = []
    for bid in branch_ids:
        b = query_one(
            "SELECT b.*, o.name AS organization_name, o.brand_type, "
            "COALESCE(min_p.min_price, 0) AS starting_price "
            "FROM branches b "
            "JOIN organizations o ON b.organization_id = o.organization_id "
            "LEFT JOIN (SELECT organization_id, MIN(price) AS min_price FROM membership_plans GROUP BY organization_id) min_p "
            "ON b.organization_id = min_p.organization_id "
            "WHERE b.branch_id = %s;", (bid,)
        )
        if b:
            facs = query_all("SELECT f.facility_name FROM branch_facilities bf JOIN facilities f ON bf.facility_id = f.facility_id WHERE bf.branch_id = %s;", (bid,))
            b["facilities_list"] = [f["facility_name"] for f in facs]
            b["hours"] = query_all("SELECT * FROM branch_hours WHERE branch_id = %s ORDER BY day_of_week;", (bid,))
            compared.append(b)

    return render_template("public/compare.html", compared=compared, all_branches=all_branches, selected_ids=branch_ids)


@public_bp.route("/plans")
def plans():
    """Directory of all membership plans grouped by organization with access rules preview."""
    orgs = query_all("SELECT * FROM organizations WHERE status = 'active' ORDER BY name;")
    plans_by_org = {}
    for o in orgs:
        p_list = query_all("SELECT * FROM membership_plans WHERE organization_id = %s ORDER BY duration_months, price;", (o["organization_id"],))
        for p in p_list:
            rules = query_all(
                "SELECT r.access_type, r.conditions, b.name AS branch_name, b.city "
                "FROM branch_access_rules r JOIN branches b ON r.branch_id = b.branch_id "
                "WHERE r.plan_id = %s;", (p["plan_id"],)
            )
            p["access_rules"] = rules
        plans_by_org[o["organization_id"]] = p_list
        
    return render_template("public/plans.html", orgs=orgs, plans_by_org=plans_by_org)


@public_bp.route("/crowd")
def crowd():
    """Crowd Explorer: pick branch and day, view hourly crowd bars and best time to visit."""
    branch_id = int(request.args.get("branch_id", 1))
    day_of_week = int(request.args.get("day", 0)) # 0 = Monday
    
    all_branches = query_all("SELECT branch_id, name, city FROM branches WHERE organization_id != 5 ORDER BY city, name;")
    branch = query_one("SELECT * FROM branches WHERE branch_id = %s;", (branch_id,))
    
    # SQLite strftime weekday: 0=Sunday, 1=Monday...
    sqlite_dow = (day_of_week + 1) % 7
    hourly_rows = query_all(
        "SELECT "
        "  CAST(strftime('%H', check_in) AS INTEGER) AS hour, "
        "  COUNT(*) AS visits "
        "FROM attendance "
        "WHERE branch_id = %s AND CAST(strftime('%w', check_in) AS INTEGER) = %s "
        "GROUP BY hour ORDER BY hour;", (branch_id, sqlite_dow)
    )
    
    total_samples = sum(r["visits"] for r in hourly_rows)
    hours_dict = {h: 0 for h in range(5, 23)}
    for r in hourly_rows:
        if r["hour"] in hours_dict:
            hours_dict[r["hour"]] = r["visits"]
            
    best_time = "13:00 - 16:00 (Early Afternoon)"
    if total_samples > 0:
        min_hour = min(hours_dict.keys(), key=lambda h: hours_dict[h] if h >= 7 else 9999)
        best_time = f"{min_hour:02d}:00 - {min_hour+1:02d}:00"

    return render_template("public/crowd.html",
                           all_branches=all_branches,
                           branch=branch,
                           selected_branch_id=branch_id,
                           selected_day=day_of_week,
                           hours_data=hours_dict,
                           total_samples=total_samples,
                           best_time=best_time)


@public_bp.route("/gap-analysis")
def gap_analysis():
    """Honest Gap Analysis matrix comparing Jaskr GymGrid vs ClassPass, Mindbody, and traditional sites."""
    return render_template("public/gap_analysis.html")


@public_bp.route("/about")
def about():
    """About Jaskr GymGrid, group project details, team members, and architecture notes."""
    return render_template("public/about.html")
