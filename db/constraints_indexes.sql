-- =====================================================================
-- Jaskr GymGrid - Constraints and Indexes (MySQL 8.x)
-- Carefully selected performance indexes with DBMS justifications
-- =====================================================================

-- 1. ATTENDANCE INDEXES
-- Critical for D3 crowd estimation and Front Desk "currently inside" live occupancy queries.
-- Range queries filter by branch_id and check_in date/time range.
CREATE INDEX idx_attendance_branch_checkin ON attendance (branch_id, check_in);
CREATE INDEX idx_attendance_member ON attendance (member_id, check_in);
-- Partial index simulation: quickly identify members currently inside (check_out IS NULL)
CREATE INDEX idx_attendance_open_checkout ON attendance (branch_id, check_out);

-- 2. EXPENSES & BUDGETS INDEXES
-- Critical for D4 financial aggregation: GROUP BY branch_id, expense_category_id, and date
CREATE INDEX idx_expenses_branch_date ON expenses (branch_id, expense_date);
CREATE INDEX idx_expenses_cat_date ON expenses (expense_category_id, expense_date);
CREATE INDEX idx_branch_budgets_lookup ON branch_budgets (branch_id, budget_period);

-- 3. PAYMENTS & INVOICES INDEXES
-- Financial reconciliation requires joining payments to invoices and memberships swiftly
CREATE INDEX idx_payments_membership ON payments (membership_id, payment_status);
CREATE INDEX idx_payments_branch_date ON payments (branch_id, payment_date);
CREATE INDEX idx_payments_invoice ON payments (invoice_id);
CREATE INDEX idx_invoices_member_status ON invoices (member_id, status);
CREATE INDEX idx_invoices_due_date ON invoices (due_date, status);
CREATE INDEX idx_invoice_items_inv ON invoice_items (invoice_id);

-- 4. MEMBERSHIPS & ACCESS RULES INDEXES
-- Critical for D2 Access Checker and member validity lookup
CREATE INDEX idx_memberships_member_status ON memberships (member_id, status, start_date, end_date);
CREATE INDEX idx_access_rules_plan_branch ON branch_access_rules (plan_id, branch_id);

-- 5. SESSIONS & TRAINER INDEXES
-- Accelerates Trainer Console and Member session booking lookups
CREATE INDEX idx_sessions_trainer_date ON training_sessions (trainer_id, session_start);
CREATE INDEX idx_sessions_member_date ON training_sessions (member_id, session_start);
CREATE INDEX idx_sessions_branch_date ON training_sessions (branch_id, session_start);

-- 6. AUDIT & USERS INDEXES
CREATE INDEX idx_audit_table_record ON audit_log (table_name, record_id);
CREATE INDEX idx_audit_created ON audit_log (created_at);
CREATE INDEX idx_users_role ON users (role, is_active);
CREATE INDEX idx_staff_user ON staff (user_id);
CREATE INDEX idx_staff_org_branch ON staff (organization_id, branch_id);
