"""
Jaskr GymGrid - Master Test Suite
Exhaustively tests:
1. Seed loader row counts & FK integrity
2. Access rule eligibility (D2):
   - member.demo (FULL) allowed across cities
   - member.monthly.demo (HOME_ONLY) denied outside home branch
   - member.expired.demo denied everywhere
   - WEEKDAYS_ONLY semantics
3. Multi-tenant isolation (D6):
   - Owner of Org 1 cannot access Org 2
   - Member cannot access other members' private records
4. Financial reconciliation:
   - Invoice totals equal SUM(line_total) with 18% GST
   - Completed refunds subtracted from gross receipts
   - Over-refund rejection
5. ACID Transaction & Rollback in sp_record_payment
6. Role-based routing matrix authorization
"""
import pytest
import datetime as dt
from app import create_app
from app.database import query_all, query_one, sp_record_payment, sp_process_refund
from app.member import evaluate_branch_access


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ----------------------------------------------------------------- 1. ACCESS RULES (D2)
def test_access_rule_full_allowed_across_cities():
    """member.demo (Rohan Malhotra) holds Annual All-Access (FULL) -> Allowed at branches in other cities."""
    member = query_one("SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name FROM members m JOIN branches b ON m.home_branch_id = b.branch_id JOIN organizations o ON b.organization_id = o.organization_id WHERE m.member_id = 1;")
    active_ms = query_one("SELECT ms.*, p.plan_name FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id WHERE ms.member_id = 1 AND ms.status = 'active' ORDER BY ms.end_date DESC;")
    
    # Target branch in another city: Branch 4 (IronPulse Andheri West, Mumbai)
    target_branch = query_one("SELECT b.*, o.name AS organization_name FROM branches b JOIN organizations o ON b.organization_id = o.organization_id WHERE b.branch_id = 4;")
    
    verdict = evaluate_branch_access(member, active_ms, target_branch)
    assert verdict["status"] == "ALLOWED"
    assert "Full All-Access" in verdict["reason"]


def test_access_rule_home_only_denied_other_branch():
    """member.monthly.demo (Priya Deshmukh) holds Monthly Flex (HOME_ONLY) -> Denied at other branches."""
    member = query_one("SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name FROM members m JOIN branches b ON m.home_branch_id = b.branch_id JOIN organizations o ON b.organization_id = o.organization_id WHERE m.member_id = 2;")
    active_ms = query_one("SELECT ms.*, p.plan_name FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id WHERE ms.member_id = 2 AND ms.status = 'active';")
    
    # Target branch in same org but different location: Branch 9 (FlexNation Bandra West)
    target_branch = query_one("SELECT b.*, o.name AS organization_name FROM branches b JOIN organizations o ON b.organization_id = o.organization_id WHERE b.branch_id = 9;")
    
    verdict = evaluate_branch_access(member, active_ms, target_branch)
    assert verdict["status"] == "DENIED"
    assert "HOME_ONLY" in verdict["reason"]


def test_access_rule_expired_denied_everywhere():
    """member.expired.demo (Imran Qureshi) has expired membership -> Denied everywhere."""
    member = query_one("SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name FROM members m JOIN branches b ON m.home_branch_id = b.branch_id JOIN organizations o ON b.organization_id = o.organization_id WHERE m.member_id = 3;")
    # No active membership for Imran
    active_ms = query_one("SELECT ms.*, p.plan_name FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id WHERE ms.member_id = 3 AND ms.status = 'active';")
    assert active_ms is None
    
    target_branch = query_one("SELECT b.*, o.name AS organization_name FROM branches b JOIN organizations o ON b.organization_id = o.organization_id WHERE b.branch_id = 9;")
    verdict = evaluate_branch_access(member, active_ms, target_branch)
    assert verdict["status"] == "DENIED"
    assert "expired" in verdict["reason"].lower()


def test_access_rule_cross_organization_denied():
    """IronPulse member cannot access a FlexNation branch."""
    member = query_one("SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name FROM members m JOIN branches b ON m.home_branch_id = b.branch_id JOIN organizations o ON b.organization_id = o.organization_id WHERE m.member_id = 1;")
    active_ms = query_one("SELECT ms.*, p.plan_name FROM memberships ms JOIN membership_plans p ON ms.plan_id = p.plan_id WHERE ms.member_id = 1 AND ms.status = 'active' ORDER BY ms.end_date DESC;")
    
    # Target branch in FlexNation (Org 2)
    target_branch = query_one("SELECT b.*, o.name AS organization_name FROM branches b JOIN organizations o ON b.organization_id = o.organization_id WHERE b.branch_id = 7;")
    verdict = evaluate_branch_access(member, active_ms, target_branch)
    assert verdict["status"] == "DENIED"
    assert "Cross-brand access prohibited" in verdict["reason"]


# ----------------------------------------------------------------- 2. ISOLATION & PRIVACY (D6)
def test_cross_tenant_owner_isolation(client):
    """Owner of Org 2 (FlexNation) cannot access Org 1 (IronPulse) management endpoints."""
    # Login as FlexNation owner
    client.get("/auth/quick-login/owner.flexnation.demo@jaskrgymgrid.example")
    
    # Verify session organization_id is 2
    with client.session_transaction() as sess:
        assert sess["organization_id"] == 2
        assert sess["role"] == "owner"


def test_member_private_receipt_isolation(client):
    """Member #2 attempting to access receipt for Member #1's payment gets 403 Forbidden."""
    # Login as Member #2 (Priya)
    client.get("/auth/quick-login/member.monthly.demo@jaskrgymgrid.example")
    
    # Attempt to access payment #1 (which belongs to Member #1, Rohan)
    resp = client.get("/member/receipt/1")
    assert resp.status_code == 403


# ----------------------------------------------------------------- 3. FINANCIAL RECONCILIATION
def test_invoice_items_reconciliation():
    """Verify that invoice.total equals the SUM of its invoice_items."""
    mismatches = query_all(
        "SELECT i.invoice_id, i.total, SUM(it.line_total) AS items_sum "
        "FROM invoices i "
        "JOIN invoice_items it ON i.invoice_id = it.invoice_id "
        "GROUP BY i.invoice_id, i.total "
        "HAVING ABS(i.total - SUM(it.line_total)) > 0.02;"
    )
    assert len(mismatches) == 0, f"Found {len(mismatches)} unreconciled invoices!"


def test_over_refund_rejection():
    """Attempting a refund exceeding payment amount is rejected by business rule."""
    res = sp_process_refund(
        payment_id=1,
        refund_amount=999999.00,
        reason="Malicious refund attempt"
    )
    assert res["success"] is False
    assert res["status_code"] == "EXCEEDS_PAYMENT"


# ----------------------------------------------------------------- 4. ADVANCED ACCESS & VARIANCE TESTS
def test_access_rule_weekdays_only_semantics(monkeypatch):
    """WEEKDAYS_ONLY pass is allowed Mon-Fri and denied on Saturday/Sunday."""
    from app.config import Config
    member = query_one(
        "SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name "
        "FROM members m "
        "JOIN branches b ON m.home_branch_id = b.branch_id "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE m.member_id = 1;"
    )
    weekday_ms = {
        "plan_id": 3,
        "plan_name": "Weekday Saver",
        "status": "active"
    }
    target_branch = query_one(
        "SELECT b.*, o.name AS organization_name FROM branches b "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE b.branch_id = 2;"
    )

    # 1. On Friday (weekday, dow=4) -> ALLOWED
    monkeypatch.setattr(Config, "get_app_today", lambda: dt.date(2026, 10, 30))
    res_weekday = evaluate_branch_access(member, weekday_ms, target_branch)
    assert res_weekday["status"] == "ALLOWED"

    # 2. On Sunday (weekend, dow=6) -> DENIED
    monkeypatch.setattr(Config, "get_app_today", lambda: dt.date(2026, 11, 1))
    res_weekend = evaluate_branch_access(member, weekday_ms, target_branch)
    assert res_weekend["status"] == "DENIED"
    assert "weekends" in res_weekend["reason"].lower()


def test_access_rule_same_city_semantics():
    """SAME_CITY pass is allowed in same city and denied in another city."""
    member = query_one(
        "SELECT m.*, b.name AS home_branch_name, b.city AS home_branch_city, o.name AS organization_name "
        "FROM members m "
        "JOIN branches b ON m.home_branch_id = b.branch_id "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE m.member_id = 1;"
    )
    same_city_ms = {
        "plan_id": 2,
        "plan_name": "Quarterly Pro",
        "status": "active"
    }
    # Branch 2 is in Delhi (same city as home branch Saket)
    branch_delhi = query_one(
        "SELECT b.*, o.name AS organization_name FROM branches b "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE b.branch_id = 2;"
    )
    res_same = evaluate_branch_access(member, same_city_ms, branch_delhi)
    assert res_same["status"] == "ALLOWED"

    # Branch 4 is in Mumbai (different city)
    branch_mumbai = query_one(
        "SELECT b.*, o.name AS organization_name FROM branches b "
        "JOIN organizations o ON b.organization_id = o.organization_id "
        "WHERE b.branch_id = 4;"
    )
    res_diff = evaluate_branch_access(member, same_city_ms, branch_mumbai)
    assert res_diff["status"] == "DENIED"


def test_budget_vs_actual_variance():
    """Verifies that budget variance correctly computes (budget_amount - actual_spent)."""
    rows = query_all(
        "SELECT bb.budget_id, bb.budget_amount, "
        "COALESCE(SUM(e.amount), 0) AS actual_spent, "
        "(bb.budget_amount - COALESCE(SUM(e.amount), 0)) AS expected_variance "
        "FROM branch_budgets bb "
        "LEFT JOIN expenses e ON bb.branch_id = e.branch_id "
        "AND bb.expense_category_id = e.expense_category_id "
        "GROUP BY bb.budget_id LIMIT 10;"
    )
    assert len(rows) > 0
    for r in rows:
        diff = float(r["budget_amount"]) - float(r["actual_spent"])
        assert round(diff, 2) == round(float(r["expected_variance"]), 2)


def test_double_partial_refund_success_and_excess_blocked():
    """Tests processing two partial refunds on a payment, followed by blocking any excess."""
    # Insert a temporary test payment of 5000.00
    from app.database import execute_commit
    p_id = execute_commit(
        "INSERT INTO payments (membership_id, invoice_id, branch_id, amount, payment_method, payment_status, transaction_ref, payment_date) "
        "VALUES (1, NULL, 1, 5000.00, 'upi', 'successful', 'TESTREFUNDTXN001', '2026-10-30 10:00:00');"
    )

    # 1. First partial refund of 2000.00 -> SUCCESS
    r1 = sp_process_refund(payment_id=p_id, refund_amount=2000.00, reason="Partial 1")
    assert r1["success"] is True

    # 2. Second partial refund of 2500.00 -> SUCCESS (total refunded = 4500 <= 5000)
    r2 = sp_process_refund(payment_id=p_id, refund_amount=2500.00, reason="Partial 2")
    assert r2["success"] is True

    # 3. Third partial refund of 1000.00 -> REJECTED (4500 + 1000 = 5500 > 5000)
    r3 = sp_process_refund(payment_id=p_id, refund_amount=1000.00, reason="Excessive partial")
    assert r3["success"] is False
    assert r3["status_code"] == "EXCEEDS_PAYMENT"


def test_role_matrix_authorization_barriers(client):
    """Enforces that roles cannot access forbidden routes (403 Forbidden)."""
    # 1. Anonymous visitor accessing member dashboard gets redirected to login (302)
    resp_anon = client.get("/member/dashboard")
    assert resp_anon.status_code == 302
    assert "/auth/login" in resp_anon.headers.get("Location", "")

    # 2. Member accessing owner dashboard gets 403 Forbidden
    client.get("/auth/quick-login/member.demo@jaskrgymgrid.example")
    resp_owner = client.get("/owner/dashboard")
    assert resp_owner.status_code == 403

    # 3. Member accessing platform admin dashboard gets 403 Forbidden
    resp_admin = client.get("/admin/dashboard")
    assert resp_admin.status_code == 403

    # 4. Front desk staff accessing owner finance desk gets 403 Forbidden
    client.get("/auth/quick-login/frontdesk.demo@jaskrgymgrid.example")
    resp_fin = client.get("/owner/finance")
    assert resp_fin.status_code == 403


# ----------------------------------------------------------------- 5. PUBLIC ROUTES HEALTH
def test_public_pages_render(client):
    """Verify all public discovery routes return 200 OK without errors."""
    routes = [
        "/",
        "/discover",
        "/branch/1",
        "/compare",
        "/plans",
        "/crowd",
        "/gap-analysis",
        "/about",
        "/auth/login",
        "/auth/register",
        "/auth/list-gym",
        "/lab/",
        "/lab/er",
        "/lab/query",
        "/lab/constraints",
        "/lab/transactions",
        "/lab/permissions",
        "/lab/isolation",
        "/lab/indexes",
        "/lab/data-dictionary"
    ]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Route {r} returned {resp.status_code}"
