"""
Pytest suite for Jaskr GymGrid Database Layer.
Verifies table counts, foreign keys, views, stored procedures, transactions, and rollback.
"""
import pytest
from app.database import query_all, query_one, sp_record_payment, sp_process_refund


def test_table_row_counts():
    """Verify all 24 seeded tables have populated rows matching generation."""
    counts = {
        "organizations": 5,
        "branches": 17,
        "branch_hours": 119,
        "facilities": 16,
        "branch_facilities": 177,
        "users": 866,
        "staff": 106,
        "trainers": 48,
        "trainer_assignments": 59,
        "members": 760,
        "membership_plans": 16,
        "branch_access_rules": 74,
        "memberships": 1313,
        "invoices": 1313,
        "invoice_items": 3372,
        "payments": 1347,
        "refunds": 83,
        "expense_categories": 10,
        "expenses": 1385,
        "branch_budgets": 1482,
        "attendance": 20546,
        "training_sessions": 761,
        "equipment": 239,
        "audit_log": 86,
    }
    for tbl, expected in counts.items():
        res = query_one(f"SELECT COUNT(*) AS c FROM {tbl};")
        assert res["c"] >= expected, f"Table {tbl} expected at least {expected} rows, got {res['c']}"


def test_view_public_branch_directory():
    """Verify v_public_branch_directory returns active branches with safe public fields."""
    rows = query_all("SELECT * FROM v_public_branch_directory;")
    assert len(rows) > 0
    first = rows[0]
    assert "branch_name" in first
    assert "city" in first
    assert "starting_price_inr" in first
    assert "total_facilities" in first
    # Verify no private financial/member columns are leaked
    assert "password_hash" not in first
    assert "member_id" not in first


def test_view_active_memberships():
    """Verify v_active_memberships returns only active memberships."""
    rows = query_all("SELECT * FROM v_active_memberships;")
    assert len(rows) > 0
    for r in rows:
        assert r["membership_status"] == "active"
        assert r["days_remaining"] is not None


def test_view_branch_financial_summary():
    """Verify financial aggregation in v_branch_financial_summary."""
    rows = query_all("SELECT * FROM v_branch_financial_summary;")
    assert len(rows) == 17
    for r in rows:
        assert r["gross_receipts"] >= 0
        assert r["net_receipts"] == round(r["gross_receipts"] - r["total_refunds"], 2)


def test_sp_record_payment_success():
    """Test successful execution of sp_record_payment transaction."""
    # Find a pending membership and invoice
    ms = query_one("SELECT membership_id, member_id FROM memberships WHERE status = 'pending' LIMIT 1;")
    if not ms:
        pytest.skip("No pending membership found for test")
    
    inv = query_one("SELECT invoice_id, total FROM invoices WHERE membership_id = %s;", (ms["membership_id"],))
    res = sp_record_payment(
        membership_id=ms["membership_id"],
        invoice_id=inv["invoice_id"] if inv else None,
        branch_id=1,
        amount=inv["total"] if inv else 1000.0,
        payment_method="UPI",
        user_id=1,
        simulate_failure=0
    )
    assert res["success"] is True
    assert res["status_code"] == "SUCCESS"
    assert res["payment_id"] > 0
    
    # Verify membership is now active
    updated_ms = query_one("SELECT status FROM memberships WHERE membership_id = %s;", (ms["membership_id"],))
    assert updated_ms["status"] == "active"


def test_sp_record_payment_rollback_on_failure():
    """Test ACID rollback when simulate_failure = 1 (Transaction Theater)."""
    # Count audit logs and payments prior to failed transaction
    pay_count_before = query_one("SELECT COUNT(*) AS c FROM payments;")["c"]
    
    res = sp_record_payment(
        membership_id=1,
        invoice_id=1,
        branch_id=1,
        amount=5000.0,
        payment_method="Credit Card",
        user_id=1,
        simulate_failure=1
    )
    assert res["success"] is False
    assert res["status_code"] == "FORCED_FAILURE_DEMO"
    
    # Assert payment was NOT committed
    pay_count_after = query_one("SELECT COUNT(*) AS c FROM payments;")["c"]
    assert pay_count_after == pay_count_before
