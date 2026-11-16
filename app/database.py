"""
Jaskr GymGrid - Database Access Layer
Supports MySQL 8.x with automatic fallback to high-performance SQLite adapter.
Enforces parameterization and role-based connection switching.
"""
import os
import sqlite3
import datetime as dt
import json
from contextlib import contextmanager

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

try:
    import mysql.connector
    from mysql.connector import pooling
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))
SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(DB_DIR, "gymgrid.db"))

MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_DB = os.environ.get("MYSQL_DB", "gymgrid")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("MYSQL_PASSWORD", "root")

# Role credentials for MySQL DCL Least Privilege testing
ROLE_USERS = {
    "public": ("gg_public", "PublicPass@123"),
    "member": ("gg_member", "MemberPass@123"),
    "staff": ("gg_staff", "StaffPass@123"),
    "owner": ("gg_owner", "OwnerPass@123"),
    "admin": ("gg_admin", "AdminPass@123"),
    "readonly_lab": ("gg_readonly_lab", "LabReadOnly@123"),
}

_is_mysql_active = False


def check_mysql_connection():
    global _is_mysql_active
    if not HAS_MYSQL or os.environ.get("FORCE_SQLITE") == "1":
        _is_mysql_active = False
        return False
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASS,
            database=MYSQL_DB,
            connection_timeout=2
        )
        conn.close()
        _is_mysql_active = True
        return True
    except Exception:
        _is_mysql_active = False
        return False


# Initial probe on module load
check_mysql_connection()


def is_mysql():
    return _is_mysql_active


def get_connection(role="admin"):
    """
    Returns a database connection.
    If MySQL is available, connects as the appropriate role user.
    Otherwise, returns an SQLite connection with Row factory enabled.
    """
    if is_mysql():
        user, pwd = ROLE_USERS.get(role, (MYSQL_USER, MYSQL_PASS))
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=user,
            password=pwd,
            database=MYSQL_DB,
            autocommit=False
        )
    else:
        conn = sqlite3.connect(SQLITE_PATH, timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def _dict_from_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def execute_query(sql, params=(), role="admin", fetch="all"):
    """
    Executes a parameterized query safely.
    Handles placeholder syntax difference (%s vs ?) automatically for SQLite fallback.
    """
    conn = get_connection(role=role)
    try:
        cur = conn.cursor(buffered=True) if is_mysql() else conn.cursor()
        exec_sql = sql
        exec_params = params
        if not is_mysql():
            # Translate MySQL %s placeholders to SQLite ?
            exec_sql = sql.replace("%s", "?")
            # Replace MySQL specific date functions if any in raw sql
            exec_sql = exec_sql.replace("NOW()", "DATETIME('now', 'localtime')")
            exec_sql = exec_sql.replace("CURDATE()", "DATE('now', 'localtime')")
        
        cur.execute(exec_sql, exec_params)
        
        if fetch == "all":
            if is_mysql():
                cols = [desc[0] for desc in cur.description] if cur.description else []
                res = [dict(zip(cols, r)) for r in cur.fetchall()]
            else:
                res = [dict(r) for r in cur.fetchall()]
            return res
        elif fetch == "one":
            if is_mysql():
                cols = [desc[0] for desc in cur.description] if cur.description else []
                r = cur.fetchone()
                return dict(zip(cols, r)) if r else None
            else:
                r = cur.fetchone()
                return dict(r) if r else None
        elif fetch == "none":
            conn.commit()
            return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def query_all(sql, params=(), role="admin"):
    return execute_query(sql, params, role=role, fetch="all")


def query_one(sql, params=(), role="admin"):
    return execute_query(sql, params, role=role, fetch="one")


def execute_commit(sql, params=(), role="admin"):
    return execute_query(sql, params, role=role, fetch="none")


def sp_record_payment(membership_id, invoice_id, branch_id, amount, payment_method, user_id=1, simulate_failure=0):
    """
    Executes sp_record_payment.
    In MySQL, calls the stored procedure.
    In SQLite fallback, emulates the exact ACID transaction steps with rollback.
    """
    if is_mysql():
        conn = get_connection(role="admin")
        try:
            cur = conn.cursor()
            args = (membership_id, invoice_id, branch_id, amount, payment_method, user_id, simulate_failure, 0, "", "")
            result_args = cur.callproc("sp_record_payment", args)
            conn.commit()
            cur.close()
            return {
                "success": result_args[8] == "SUCCESS",
                "payment_id": result_args[7],
                "status_code": result_args[8],
                "message": result_args[9]
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "payment_id": 0, "status_code": "ERROR", "message": str(e)}
        finally:
            conn.close()
    else:
        # SQLite transaction emulation
        conn = get_connection(role="admin")
        try:
            cur = conn.cursor()
            cur.execute("BEGIN TRANSACTION;")
            
            # Validation
            cur.execute("SELECT COUNT(*) AS c FROM memberships WHERE membership_id = ?", (membership_id,))
            if cur.fetchone()["c"] == 0:
                conn.rollback()
                return {"success": False, "payment_id": 0, "status_code": "MEMBERSHIP_NOT_FOUND", "message": "Membership not found"}
            
            if simulate_failure == 1:
                cur.execute(
                    "INSERT INTO audit_log (user_id, action, table_name, record_id, old_value, new_value, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, "PAYMENT_FORCED_FAIL_ATTEMPT", "PAYMENTS", 0, None, json.dumps({"simulated": True}), dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.rollback()
                return {"success": False, "payment_id": 0, "status_code": "FORCED_FAILURE_DEMO", "message": "Transaction intentionally aborted by Transaction Theater. ROLLBACK executed successfully."}
            
            now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO payments (membership_id, invoice_id, branch_id, amount, payment_date, payment_method, payment_status, transaction_ref) "
                "VALUES (?, ?, ?, ?, ?, ?, 'successful', '')",
                (membership_id, invoice_id, branch_id, amount, now_str, payment_method)
            )
            pay_id = cur.lastrowid
            txn_ref = f"GGTXN2026{pay_id:07d}"
            cur.execute("UPDATE payments SET transaction_ref = ? WHERE payment_id = ?", (txn_ref, pay_id))
            
            if invoice_id:
                cur.execute("UPDATE invoices SET status = 'paid' WHERE invoice_id = ?", (invoice_id,))
            
            cur.execute("UPDATE memberships SET status = 'active' WHERE membership_id = ?", (membership_id,))
            
            cur.execute(
                "INSERT INTO audit_log (user_id, action, table_name, record_id, old_value, new_value, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, "RECORD_PAYMENT", "PAYMENTS", pay_id,
                 json.dumps({"membership_id": membership_id, "invoice_id": invoice_id}),
                 json.dumps({"payment_id": pay_id, "amount": float(amount), "status": "successful", "ref": txn_ref}),
                 now_str)
            )
            conn.commit()
            return {"success": True, "payment_id": pay_id, "status_code": "SUCCESS", "message": f"Payment recorded successfully. Txn Ref: {txn_ref}"}
        except Exception as e:
            conn.rollback()
            return {"success": False, "payment_id": 0, "status_code": "ERROR_ROLLBACK", "message": str(e)}
        finally:
            conn.close()


def sp_process_refund(payment_id, refund_amount, reason, user_id=1, refund_id=None):
    """
    Executes refund transaction with limit check and audit logging.
    When refund_id is provided, approves/completes the existing refund request.
    Only sums COMPLETED or APPROVED refunds to avoid double-counting pending requests.
    """
    conn = get_connection(role="admin")
    ph = "%s" if is_mysql() else "?"
    try:
        cur = conn.cursor(dictionary=True) if is_mysql() else conn.cursor()
        cur.execute(f"SELECT amount, membership_id, invoice_id FROM payments WHERE payment_id = {ph} AND payment_status = 'successful'", (payment_id,))
        p = cur.fetchone()
        if not p:
            return {"success": False, "refund_id": 0, "status_code": "PAYMENT_INVALID", "message": "Payment record not found"}
        
        orig_amount = float(p["amount"])
        ms_id = p["membership_id"]
        inv_id = p["invoice_id"]
        
        # Calculate existing completed/approved refunds (exclude current refund_id if approving existing request)
        if refund_id:
            cur.execute(
                f"SELECT COALESCE(SUM(refund_amount), 0.0) AS s FROM refunds WHERE payment_id = {ph} AND status IN ('completed', 'approved') AND refund_id != {ph}",
                (payment_id, refund_id)
            )
        else:
            cur.execute(
                f"SELECT COALESCE(SUM(refund_amount), 0.0) AS s FROM refunds WHERE payment_id = {ph} AND status IN ('completed', 'approved')",
                (payment_id,)
            )
        row = cur.fetchone()
        existing_refunds = float(row["s"] if isinstance(row, dict) else row[0])
        
        if (existing_refunds + float(refund_amount)) > orig_amount + 0.001:
            return {"success": False, "refund_id": 0, "status_code": "EXCEEDS_PAYMENT", "message": f"Total refund cannot exceed payment amount (₹{orig_amount:,.2f})"}
        
        today_str = dt.date.today().strftime("%Y-%m-%d")
        now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not is_mysql():
            # For SQLite, check if transaction already active
            try:
                cur.execute("BEGIN TRANSACTION;")
            except Exception:
                pass
        
        if refund_id:
            # Transition existing requested refund to completed
            cur.execute(
                f"UPDATE refunds SET status = 'completed', refund_date = {ph} WHERE refund_id = {ph}",
                (today_str, refund_id)
            )
            ref_id = refund_id
        else:
            # Insert new completed refund
            cur.execute(
                f"INSERT INTO refunds (payment_id, refund_amount, refund_date, reason, status) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, 'completed')",
                (payment_id, refund_amount, today_str, reason)
            )
            ref_id = cur.lastrowid
        
        # If full refund, cancel membership
        if (existing_refunds + float(refund_amount)) >= orig_amount - 0.01:
            cur.execute(f"UPDATE memberships SET status = 'cancelled' WHERE membership_id = {ph}", (ms_id,))
            if inv_id:
                cur.execute(f"UPDATE invoices SET status = 'refunded' WHERE invoice_id = {ph}", (inv_id,))
        
        # Write audit log
        cur.execute(
            f"INSERT INTO audit_log (user_id, action, table_name, record_id, old_value, new_value, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            (user_id, "REFUND_COMPLETED", "REFUNDS", ref_id,
             json.dumps({"existing_refunds": existing_refunds}),
             json.dumps({"refund_id": ref_id, "amount": float(refund_amount), "payment_id": payment_id}),
             now_str)
        )
        conn.commit()
        return {"success": True, "refund_id": ref_id, "status_code": "SUCCESS", "message": "Refund processed and approved successfully"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "refund_id": 0, "status_code": "ERROR_ROLLBACK", "message": str(e)}
    finally:
        conn.close()
