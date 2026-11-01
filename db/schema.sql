-- =====================================================================
-- Jaskr GymGrid - Relational Database Schema (MySQL 8.x)
-- Project: Jaskr GymGrid (City-Wide Gym Discovery, Smart Access & Finance)
-- Official Academic Prototype - All demo data fictional
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 1. ORGANIZATIONS
DROP TABLE IF EXISTS organizations;
CREATE TABLE organizations (
    organization_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    contact_email VARCHAR(120) NOT NULL,
    status ENUM('active', 'pending', 'suspended') NOT NULL DEFAULT 'active',
    brand_type ENUM('chain', 'independent') NOT NULL DEFAULT 'independent',
    headquarters_city VARCHAR(60) NOT NULL,
    created_at DATE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. BRANCHES
DROP TABLE IF EXISTS branches;
CREATE TABLE branches (
    branch_id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    name VARCHAR(120) NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(60) NOT NULL,
    state VARCHAR(60) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    description TEXT NOT NULL,
    capacity INT NOT NULL,
    CONSTRAINT fk_branches_org FOREIGN KEY (organization_id) 
        REFERENCES organizations (organization_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_branches_capacity CHECK (capacity > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. BRANCH_HOURS
DROP TABLE IF EXISTS branch_hours;
CREATE TABLE branch_hours (
    branch_id INT NOT NULL,
    day_of_week TINYINT NOT NULL COMMENT '0=Monday, ..., 6=Sunday',
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    is_closed TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (branch_id, day_of_week),
    CONSTRAINT fk_branch_hours_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_branch_hours_dow CHECK (day_of_week BETWEEN 0 AND 6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. FACILITIES
DROP TABLE IF EXISTS facilities;
CREATE TABLE facilities (
    facility_id INT AUTO_INCREMENT PRIMARY KEY,
    facility_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. BRANCH_FACILITIES
DROP TABLE IF EXISTS branch_facilities;
CREATE TABLE branch_facilities (
    branch_id INT NOT NULL,
    facility_id INT NOT NULL,
    availability_notes VARCHAR(255) DEFAULT '',
    PRIMARY KEY (branch_id, facility_id),
    CONSTRAINT fk_branch_facilities_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_branch_facilities_fac FOREIGN KEY (facility_id) 
        REFERENCES facilities (facility_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. USERS
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('visitor', 'member', 'staff', 'owner', 'admin') NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    last_login DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. STAFF
DROP TABLE IF EXISTS staff;
CREATE TABLE staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    organization_id INT NULL,
    branch_id INT NULL,
    job_role ENUM('OWNER', 'BRANCH_MANAGER', 'FRONT_DESK', 'TRAINER', 'FINANCE', 'PLATFORM_ADMIN') NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    status ENUM('active', 'inactive', 'suspended') NOT NULL DEFAULT 'active',
    hired_date DATE NOT NULL,
    CONSTRAINT fk_staff_user FOREIGN KEY (user_id) 
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_staff_org FOREIGN KEY (organization_id) 
        REFERENCES organizations (organization_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_staff_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. TRAINERS
DROP TABLE IF EXISTS trainers;
CREATE TABLE trainers (
    trainer_id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    staff_id INT NOT NULL,
    user_id INT NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    specialization VARCHAR(120) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    CONSTRAINT fk_trainers_org FOREIGN KEY (organization_id) 
        REFERENCES organizations (organization_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_trainers_staff FOREIGN KEY (staff_id) 
        REFERENCES staff (staff_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_trainers_user FOREIGN KEY (user_id) 
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. TRAINER_ASSIGNMENTS
DROP TABLE IF EXISTS trainer_assignments;
CREATE TABLE trainer_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    trainer_id INT NOT NULL,
    branch_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT fk_ta_trainer FOREIGN KEY (trainer_id) 
        REFERENCES trainers (trainer_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ta_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_ta_dates CHECK (end_date IS NULL OR end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. MEMBERS
DROP TABLE IF EXISTS members;
CREATE TABLE members (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    home_branch_id INT NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    registration_date DATE NOT NULL,
    CONSTRAINT fk_members_user FOREIGN KEY (user_id) 
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_members_home_branch FOREIGN KEY (home_branch_id) 
        REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. MEMBERSHIP_PLANS
DROP TABLE IF EXISTS membership_plans;
CREATE TABLE membership_plans (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    duration_months INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT fk_plans_org FOREIGN KEY (organization_id) 
        REFERENCES organizations (organization_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_plans_duration CHECK (duration_months > 0),
    CONSTRAINT chk_plans_price CHECK (price >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. BRANCH_ACCESS_RULES
DROP TABLE IF EXISTS branch_access_rules;
CREATE TABLE branch_access_rules (
    access_rule_id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id INT NOT NULL,
    branch_id INT NOT NULL,
    access_type ENUM('HOME_ONLY', 'SAME_CITY', 'WEEKDAYS_ONLY', 'FULL') NOT NULL,
    conditions TEXT NOT NULL,
    CONSTRAINT fk_access_plan FOREIGN KEY (plan_id) 
        REFERENCES membership_plans (plan_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_access_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_plan_branch UNIQUE (plan_id, branch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 13. MEMBERSHIPS
DROP TABLE IF EXISTS memberships;
CREATE TABLE memberships (
    membership_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('active', 'expired', 'cancelled', 'pending') NOT NULL DEFAULT 'pending',
    CONSTRAINT fk_ms_member FOREIGN KEY (member_id) 
        REFERENCES members (member_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ms_plan FOREIGN KEY (plan_id) 
        REFERENCES membership_plans (plan_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_ms_dates CHECK (end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 14. INVOICES
DROP TABLE IF EXISTS invoices;
CREATE TABLE invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(40) NOT NULL UNIQUE,
    member_id INT NOT NULL,
    membership_id INT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    status ENUM('paid', 'pending', 'overdue', 'refunded') NOT NULL DEFAULT 'pending',
    CONSTRAINT fk_inv_member FOREIGN KEY (member_id) 
        REFERENCES members (member_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_inv_membership FOREIGN KEY (membership_id) 
        REFERENCES memberships (membership_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_inv_total CHECK (total >= 0),
    CONSTRAINT chk_inv_due CHECK (due_date >= invoice_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 15. INVOICE_ITEMS
DROP TABLE IF EXISTS invoice_items;
CREATE TABLE invoice_items (
    invoice_item_id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    line_total DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_items_invoice FOREIGN KEY (invoice_id) 
        REFERENCES invoices (invoice_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_items_qty CHECK (quantity > 0),
    CONSTRAINT chk_items_total CHECK (line_total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 16. PAYMENTS
DROP TABLE IF EXISTS payments;
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    membership_id INT NOT NULL,
    invoice_id INT NULL,
    branch_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_date DATETIME NOT NULL,
    payment_method ENUM('UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'Cash') NOT NULL,
    payment_status ENUM('successful', 'pending', 'failed') NOT NULL DEFAULT 'pending',
    transaction_ref VARCHAR(60) NOT NULL DEFAULT '',
    CONSTRAINT fk_pay_membership FOREIGN KEY (membership_id) 
        REFERENCES memberships (membership_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_pay_invoice FOREIGN KEY (invoice_id) 
        REFERENCES invoices (invoice_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_pay_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_pay_amount CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 17. REFUNDS
DROP TABLE IF EXISTS refunds;
CREATE TABLE refunds (
    refund_id INT AUTO_INCREMENT PRIMARY KEY,
    payment_id INT NOT NULL,
    refund_amount DECIMAL(10, 2) NOT NULL,
    refund_date DATE NOT NULL,
    reason VARCHAR(255) NOT NULL,
    status ENUM('requested', 'approved', 'completed', 'rejected') NOT NULL DEFAULT 'requested',
    CONSTRAINT fk_refund_payment FOREIGN KEY (payment_id) 
        REFERENCES payments (payment_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_refund_amount CHECK (refund_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 18. EXPENSE_CATEGORIES
DROP TABLE IF EXISTS expense_categories;
CREATE TABLE expense_categories (
    expense_category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 19. EXPENSES
DROP TABLE IF EXISTS expenses;
CREATE TABLE expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    expense_category_id INT NOT NULL,
    recorded_by INT NOT NULL,
    expense_date DATE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    vendor VARCHAR(120) NOT NULL,
    description VARCHAR(255) NOT NULL,
    status ENUM('paid', 'approved', 'pending', 'rejected') NOT NULL DEFAULT 'pending',
    CONSTRAINT fk_exp_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_exp_cat FOREIGN KEY (expense_category_id) 
        REFERENCES expense_categories (expense_category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_exp_recorder FOREIGN KEY (recorded_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_exp_amount CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 20. BRANCH_BUDGETS
DROP TABLE IF EXISTS branch_budgets;
CREATE TABLE branch_budgets (
    budget_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    expense_category_id INT NOT NULL,
    budget_period VARCHAR(7) NOT NULL COMMENT 'Format YYYY-MM',
    budget_amount DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_bb_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_bb_cat FOREIGN KEY (expense_category_id) 
        REFERENCES expense_categories (expense_category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_branch_cat_period UNIQUE (branch_id, expense_category_id, budget_period),
    CONSTRAINT chk_bb_amount CHECK (budget_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 21. ATTENDANCE
DROP TABLE IF EXISTS attendance;
CREATE TABLE attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    branch_id INT NOT NULL,
    check_in DATETIME NOT NULL,
    check_out DATETIME NULL,
    CONSTRAINT fk_att_member FOREIGN KEY (member_id) 
        REFERENCES members (member_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_att_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_att_dates CHECK (check_out IS NULL OR check_out > check_in)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 22. TRAINING_SESSIONS
DROP TABLE IF EXISTS training_sessions;
CREATE TABLE training_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    trainer_id INT NOT NULL,
    branch_id INT NOT NULL,
    session_start DATETIME NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 60,
    status ENUM('scheduled', 'completed', 'cancelled', 'no_show') NOT NULL DEFAULT 'scheduled',
    focus VARCHAR(120) NOT NULL DEFAULT '',
    CONSTRAINT fk_ts_member FOREIGN KEY (member_id) 
        REFERENCES members (member_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ts_trainer FOREIGN KEY (trainer_id) 
        REFERENCES trainers (trainer_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ts_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_ts_duration CHECK (duration_minutes > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 23. EQUIPMENT
DROP TABLE IF EXISTS equipment;
CREATE TABLE equipment (
    equipment_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    equipment_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    condition_status ENUM('good', 'needs_service', 'out_of_order') NOT NULL DEFAULT 'good',
    last_serviced_on DATE NOT NULL,
    CONSTRAINT fk_eq_branch FOREIGN KEY (branch_id) 
        REFERENCES branches (branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_eq_quantity CHECK (quantity > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 24. AUDIT_LOG
DROP TABLE IF EXISTS audit_log;
CREATE TABLE audit_log (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action VARCHAR(60) NOT NULL,
    table_name VARCHAR(60) NOT NULL,
    record_id INT NOT NULL,
    old_value JSON NULL,
    new_value JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) 
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
