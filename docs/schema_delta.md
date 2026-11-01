# Jaskr GymGrid - Schema Delta Documentation

**Project:** Jaskr GymGrid (City-Wide Gym Discovery, Smart Access & Financial Management)  
**Database Engine:** MySQL 8.x (3NF Relational Model)  
**Target:** University DBMS Evaluators & Faculty Reviewers  

---

## Executive Summary of Schema Evolution
The original database proposal specified 21 tables. However, to fully implement all required capabilities—such as uniform multi-tenant role delegation, side-by-side branch comparison of opening hours, spatial GIS coordinates, invoice-payment reconciliation, and immutable financial audit logging—several critical enhancements and 3 new relations were required.

All enhancements are 100% backward-compatible, strictly adhere to Third Normal Form (3NF), and are populated in the authoritative dataset.

---

## 1. Newly Added Relations (Tables 22, 23, 24)

### 1.1 `staff`
- **Schema:** `(staff_id PK, user_id FK, organization_id FK NULL, branch_id FK NULL, job_role ENUM, full_name, phone, status, hired_date)`
- **Architectural Justification:** The initial proposal lacked a unified staff relation, leading to ambiguous scoping for branch managers, front desk staff, trainers, and finance officers. The `staff` table provides uniform role-based access control (RBAC), multi-tenant organization scoping, and branch assignment. Owners, finance officers, and platform admins have a `NULL` branch scope (allowing organization-wide or platform-wide visibility).

### 1.2 `branch_hours`
- **Schema:** `(branch_id PK/FK, day_of_week PK, open_time, close_time, is_closed)`
- **Architectural Justification:** Required for Differentiator D1 (side-by-side gym comparison) and D2 (access rule checking). Without this relation, gym opening hours could not be compared across different days of the week, nor could weekend-only or morning-only schedules be validated.

### 1.3 `audit_log`
- **Schema:** `(audit_id PK, user_id FK, action, table_name, record_id, old_value JSON, new_value JSON, created_at)`
- **Architectural Justification:** Demonstrates enterprise auditing compliance and automated database triggers (`trg_audit_expense_update`, `trg_audit_payment_status`). Captures before-and-after states as structured JSON whenever financial vouchers or refund statuses are modified.

---

## 2. Table Column Extensions & Foreign Key Enhancements

| Table | Added Columns | Type & Constraints | Architectural Justification |
|:---|:---|:---|:---|
| **`branches`** | `state`, `pincode` | `VARCHAR(60)`, `VARCHAR(10)` | Indian postal address normalization across the 11 covered cities. |
| **`branches`** | `latitude`, `longitude` | `DECIMAL(10, 6)` | Spatial map visualization for discovery and distance calculations. |
| **`branches`** | `phone`, `description` | `VARCHAR(25)`, `TEXT` | Public branch profile details and customer contact channels. |
| **`branches`** | `capacity` | `INT CHECK (capacity > 0)` | Critical for D3 crowd normalization (Quiet / Moderate / Busy scale). |
| **`payments`** | `invoice_id` | `INT FK NULL REFERENCES invoices` | Solves payment-to-invoice reconciliation; payments settle specific invoices. |
| **`payments`** | `transaction_ref` | `VARCHAR(60) NOT NULL` | Financial audit identifier (e.g. `GGTXN20260000001`). |
| **`invoices`** | `invoice_number` | `VARCHAR(40) UNIQUE` | Unique sequential tax invoice identifier (e.g. `JGG/2026/000001`). |
| **`membership_plans`** | `description` | `VARCHAR(255)` | Marketing and access summary displayed on public pricing cards. |
| **`equipment`** | `last_serviced_on` | `DATE` | Maintenance scheduling tracking in the Branch Manager console. |
| **`training_sessions`** | `focus` | `VARCHAR(120)` | Training discipline (e.g. Strength, Weight Loss, Boxing, Pilates). |
| **`organizations`** | `brand_type`, `headquarters_city`, `created_at` | `ENUM('chain', 'independent')`, `VARCHAR(60)`, `DATE` | Differentiates multi-branch chains from independent fitness clubs. |
| **`users`** | `is_active`, `created_at`, `last_login` | `TINYINT(1)`, `DATETIME`, `DATETIME NULL` | Security lifecycle, administrative suspension, and session tracking. |

---

## 3. Normalization Proof (3NF Compliance)
- **1NF Compliance:** All attributes contain atomic values. Multi-valued facilities and hours are decomposed into separate tables (`branch_facilities`, `branch_hours`).
- **2NF Compliance:** All non-key attributes are fully functionally dependent on the entire primary key. In composite-key tables like `branch_hours (branch_id, day_of_week)`, opening and closing times depend on both attributes.
- **3NF Compliance:** There are zero transitive dependencies. For example, `members` references `home_branch_id` and does not store the branch address or city; those remain in `branches`. `trainers` references `staff_id` and `organization_id` cleanly.
