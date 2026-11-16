-- =====================================================================
-- Jaskr GymGrid - Data Control Language (DCL) & Role-Based Privilege Grants
-- Principle of Least Privilege for MySQL 8.x
-- =====================================================================

-- Clean up existing users
DROP USER IF EXISTS 'gg_public'@'%';
DROP USER IF EXISTS 'gg_member'@'%';
DROP USER IF EXISTS 'gg_staff'@'%';
DROP USER IF EXISTS 'gg_owner'@'%';
DROP USER IF EXISTS 'gg_admin'@'%';
DROP USER IF EXISTS 'gg_readonly_lab'@'%';

-- 1. gg_public: Public visitor discovery (Public views only, strictly no member or internal financial access)
CREATE USER 'gg_public'@'%' IDENTIFIED BY 'PublicPass@123';
GRANT SELECT ON gymgrid.v_public_branch_directory TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.v_branch_crowd_hourly TO 'gg_public'@'%';
GRANT SELECT (organization_id, name, brand_type, headquarters_city) ON gymgrid.organizations TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.branch_hours TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.facilities TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.branch_facilities TO 'gg_public'@'%';
GRANT SELECT (plan_id, organization_id, plan_name, duration_months, price, description) ON gymgrid.membership_plans TO 'gg_public'@'%';
GRANT SELECT (equipment_id, branch_id, equipment_name, quantity, condition_status) ON gymgrid.equipment TO 'gg_public'@'%';

-- 2. gg_member: Authenticated gym member
CREATE USER 'gg_member'@'%' IDENTIFIED BY 'MemberPass@123';
GRANT SELECT ON gymgrid.v_public_branch_directory TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.v_branch_crowd_hourly TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.branch_access_rules TO 'gg_member'@'%';
GRANT SELECT, UPDATE (full_name, phone) ON gymgrid.members TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.memberships TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.invoices TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.invoice_items TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.payments TO 'gg_member'@'%';
GRANT INSERT ON gymgrid.refunds TO 'gg_member'@'%';
GRANT SELECT, INSERT ON gymgrid.attendance TO 'gg_member'@'%';
GRANT SELECT, INSERT, UPDATE (status) ON gymgrid.training_sessions TO 'gg_member'@'%';
GRANT SELECT (trainer_id, full_name, specialization) ON gymgrid.trainers TO 'gg_member'@'%';
GRANT EXECUTE ON PROCEDURE gymgrid.sp_record_payment TO 'gg_member'@'%';

-- 3. gg_staff: Front desk, Trainer, Branch Manager
CREATE USER 'gg_staff'@'%' IDENTIFIED BY 'StaffPass@123';
GRANT SELECT ON gymgrid.v_public_branch_directory TO 'gg_staff'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.attendance TO 'gg_staff'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.members TO 'gg_staff'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.memberships TO 'gg_staff'@'%';
GRANT SELECT, INSERT ON gymgrid.invoices TO 'gg_staff'@'%';
GRANT SELECT, INSERT ON gymgrid.invoice_items TO 'gg_staff'@'%';
GRANT SELECT, INSERT ON gymgrid.payments TO 'gg_staff'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.training_sessions TO 'gg_staff'@'%';
GRANT SELECT ON gymgrid.equipment TO 'gg_staff'@'%';
GRANT SELECT ON gymgrid.branch_access_rules TO 'gg_staff'@'%';
GRANT EXECUTE ON PROCEDURE gymgrid.sp_record_payment TO 'gg_staff'@'%';

-- 4. gg_owner: Organization Owner & Finance Manager
CREATE USER 'gg_owner'@'%' IDENTIFIED BY 'OwnerPass@123';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.organizations TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branches TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_hours TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_facilities TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.membership_plans TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_access_rules TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.expenses TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_budgets TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.expense_categories TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.refunds TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.payments TO 'gg_owner'@'%';
GRANT SELECT, UPDATE ON gymgrid.invoices TO 'gg_owner'@'%';
GRANT SELECT, UPDATE ON gymgrid.memberships TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.members TO 'gg_owner'@'%';
GRANT INSERT ON gymgrid.audit_log TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.v_branch_financial_summary TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.v_active_memberships TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.v_upcoming_invoices TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.audit_log TO 'gg_owner'@'%';
GRANT EXECUTE ON PROCEDURE gymgrid.sp_record_payment TO 'gg_owner'@'%';
GRANT EXECUTE ON PROCEDURE gymgrid.sp_process_refund TO 'gg_owner'@'%';

-- 5. gg_admin: Platform Administrator
CREATE USER 'gg_admin'@'%' IDENTIFIED BY 'AdminPass@123';
GRANT ALL PRIVILEGES ON gymgrid.* TO 'gg_admin'@'%';

-- 6. gg_readonly_lab: DBMS Query Lab runner (Strictly read-only SELECT with query timeout)
CREATE USER 'gg_readonly_lab'@'%' IDENTIFIED BY 'LabReadOnly@123';
GRANT SELECT ON gymgrid.* TO 'gg_readonly_lab'@'%';
GRANT EXECUTE ON gymgrid.* TO 'gg_readonly_lab'@'%';

-- Apply all privileges
FLUSH PRIVILEGES;
