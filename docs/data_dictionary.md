# Jaskr GymGrid - Relational Data Dictionary & Normalization Notes

**Project:** Jaskr GymGrid (City-Wide Gym Discovery, Smart Access & Financial Management)  
**Database Engine:** MySQL 8.x / SQLite Dual-Engine  
**Target:** University DBMS Faculty Evaluators & Academic Reviewers  
**Schema Scope:** 24 Tables, 38 Foreign Keys, 15 CHECK Constraints, 10 B-Tree Composite Indexes  

---

## 1. Database Normalization Architecture (1NF, 2NF, 3NF)

The Jaskr GymGrid relational database is strictly normalized to **Third Normal Form (3NF)** to eliminate redundancy, avoid insert/update/delete anomalies, and ensure complete referential integrity.

### 1.1 First Normal Form (1NF) Compliance
- **Atomicity:** Every table attribute contains atomic (indivisible) values.
- **No Repeating Groups or Multi-Valued Attributes:**
  - Gym facilities are not stored as comma-separated strings inside `branches`; they are modeled as normalized individual entities in `facilities` and mapped through the associative entity `branch_facilities`.
  - Weekly operating hours are not stored in multiple columns (`monday_open`, `tuesday_open`, etc.); they are decomposed into the relation `branch_hours (branch_id, day_of_week, open_time, close_time, is_closed)`.
  - Multi-tier invoice line items (membership fee, GST tax, personal trainer fee) are isolated into `invoice_items`.

### 1.2 Second Normal Form (2NF) Compliance
- Every table is in 1NF.
- **Full Functional Dependency on Composite Primary Keys:**
  - In `branch_hours (branch_id, day_of_week)`: `open_time`, `close_time`, and `is_closed` functionally depend on both `branch_id` AND `day_of_week`. A branch has different hours depending on the day of the week.
  - In `branch_facilities (branch_id, facility_id)`: `availability_notes` depends on the specific branch-facility pair.
  - In `trainer_assignments (trainer_id, branch_id)`: `assigned_date` and `end_date` depend on the specific assignment of a coach to a branch.
  - In `branch_access_rules (plan_id, branch_id)`: `access_type` and `conditions` depend on both the plan tier and the target gym branch.
  - In `branch_budgets (branch_id, expense_category_id, budget_period)`: `budget_amount` depends on the exact branch, category, and month.

### 1.3 Third Normal Form (3NF) Compliance
- Every table is in 2NF.
- **Zero Transitive Dependencies ($X \to Y$ where $Y$ is not a superkey and $X$ is not a superkey):**
  - In `members`: Member records store `home_branch_id` as an FK. The branch name, address, city, and state are *not* stored in `members`; they reside exclusively in `branches`. Thus, updating a branch's address does not require updating member records.
  - In `payments`: The gross total and tax amount are not copied from `invoices`; `payments` stores only the settled cash transaction (`amount`, `payment_method`, `transaction_ref`) and points to `invoice_id` and `membership_id`.
  - In `expenses`: Category names and descriptions reside in `expense_categories`, not in `expenses`.
  - In `trainers`: Trainer authentication details reside in `users` (`user_id`), staff lifecycle records reside in `staff` (`staff_id`), and trainer coaching specialties reside in `trainers`.

---

## 2. Comprehensive Relational Data Dictionary (All 24 Tables)

### Module 1: Core Organizations & Physical Branches

#### 1. `organizations`
Represents gym brands, chains, and fitness clubs operating on the platform.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `organization_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Unique surrogate key for the gym organization. |
| `name` | `VARCHAR(120)` | NO | | | Business trade name (e.g. IronPulse Fitness). |
| `contact_email` | `VARCHAR(120)` | NO | | | Corporate contact email address. |
| `status` | `ENUM` | NO | | `'active'`, `'pending'`, `'suspended'` | Tenant lifecycle status. |
| `brand_type` | `ENUM` | NO | | `'chain'`, `'independent'` | Single-gym vs multi-city chain indicator. |
| `headquarters_city` | `VARCHAR(60)` | NO | | | HQ city location. |
| `created_at` | `DATE` | NO | | | Onboarding date. |

#### 2. `branches`
Physical fitness facilities operated by an organization across Indian cities.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `branch_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Unique identifier for physical gym branch. |
| `organization_id` | `INT` | NO | FK | `REFERENCES organizations` | Parent organization managing the branch. |
| `name` | `VARCHAR(120)` | NO | | | Branch location name (e.g. IronPulse Saket). |
| `address` | `VARCHAR(255)` | NO | | | Physical street address. |
| `city` | `VARCHAR(60)` | NO | | | Indian city (Delhi, Mumbai, Bengaluru, etc.). |
| `state` | `VARCHAR(60)` | NO | | | State / Union Territory. |
| `pincode` | `VARCHAR(10)` | NO | | | Postal PIN code. |
| `latitude` | `DECIMAL(10,6)` | NO | | | Spatial coordinate for distance & map sync. |
| `longitude` | `DECIMAL(10,6)` | NO | | | Spatial coordinate for distance & map sync. |
| `phone` | `VARCHAR(25)` | NO | | | Front desk contact phone. |
| `description` | `TEXT` | NO | | | Public overview and promotional copy. |
| `capacity` | `INT` | NO | | `CHECK (capacity > 0)` | Maximum safe concurrent crowd capacity. |

#### 3. `branch_hours`
Weekly operating schedule per branch (Monday=0 to Sunday=6).
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `branch_id` | `INT` | NO | PK, FK | `REFERENCES branches` | Target branch identifier. |
| `day_of_week` | `TINYINT` | NO | PK | `CHECK (day_of_week BETWEEN 0 AND 6)` | 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun. |
| `open_time` | `TIME` | NO | | | Opening time (e.g. 06:00:00). |
| `close_time` | `TIME` | NO | | | Closing time (e.g. 22:00:00). |
| `is_closed` | `TINYINT(1)` | NO | | `DEFAULT 0` | 1 if branch is closed on that day. |

#### 4. `facilities`
Master catalog of amenities and features offered across gyms.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `facility_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Unique facility catalog key. |
| `facility_name` | `VARCHAR(100)` | NO | UQ | `UNIQUE` | Distinct amenity name (e.g. Olympic Lifting Platform). |
| `description` | `VARCHAR(255)` | NO | | | Amenity explanation. |

#### 5. `branch_facilities`
Many-to-Many associative mapping linking gym branches to provided facilities.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `branch_id` | `INT` | NO | PK, FK | `REFERENCES branches` | Branch providing the amenity. |
| `facility_id` | `INT` | NO | PK, FK | `REFERENCES facilities` | Amenity item identifier. |
| `availability_notes` | `VARCHAR(255)` | YES | | | Specific notes (e.g. "Available 6 AM - 10 PM"). |

---

### Module 2: Identity, Access Control & Staffing

#### 6. `users`
Central authentication credentials and global role classification.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `user_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Master surrogate identity identifier. |
| `email` | `VARCHAR(120)` | NO | UQ | `UNIQUE` | Login email address. |
| `password_hash` | `VARCHAR(255)` | NO | | | Bcrypt / PBKDF2 hashed password string. |
| `role` | `ENUM` | NO | | `'member'`, `'staff'`, `'owner'`, `'admin'` | Global system access tier. |
| `is_active` | `TINYINT(1)` | NO | | `DEFAULT 1` | Soft deactivation flag. |
| `created_at` | `DATETIME` | NO | | | Account registration timestamp. |
| `last_login` | `DATETIME` | YES | | | Most recent authenticated session timestamp. |

#### 7. `staff`
Internal employees, branch managers, coaches, and corporate finance officers.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `staff_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Staff member identifier. |
| `user_id` | `INT` | NO | FK | `REFERENCES users` | Associated authentication account. |
| `organization_id` | `INT` | YES | FK | `REFERENCES organizations` | Employer organization (NULL for superadmins). |
| `branch_id` | `INT` | YES | FK | `REFERENCES branches` | Scoped gym branch (NULL for org-wide staff). |
| `job_role` | `ENUM` | NO | | `'OWNER'`, `'BRANCH_MANAGER'`, `'FRONT_DESK'`, `'TRAINER'`, `'FINANCE'`, `'PLATFORM_ADMIN'` | Operational job assignment. |
| `full_name` | `VARCHAR(120)` | NO | | | Employee legal name. |
| `phone` | `VARCHAR(25)` | NO | | | Contact phone number. |
| `status` | `ENUM` | NO | | `'active'`, `'on_leave'`, `'terminated'` | Employment status. |
| `hired_date` | `DATE` | NO | | | Employment start date. |

#### 8. `trainers`
Certified fitness instructors providing coaching and personal training sessions.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `trainer_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Trainer identifier. |
| `organization_id` | `INT` | NO | FK | `REFERENCES organizations` | Sponsoring organization. |
| `staff_id` | `INT` | NO | FK | `REFERENCES staff` | Staff profile link. |
| `user_id` | `INT` | NO | FK | `REFERENCES users` | Authentication link. |
| `full_name` | `VARCHAR(120)` | NO | | | Coach display name. |
| `specialization` | `VARCHAR(120)` | NO | | | Specialty (e.g. Strength & Conditioning, HIIT). |
| `phone` | `VARCHAR(25)` | NO | | | Contact phone. |

#### 9. `trainer_assignments`
Many-to-Many association tracking multi-branch coaching coverage.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `trainer_id` | `INT` | NO | PK, FK | `REFERENCES trainers` | Trainer reference. |
| `branch_id` | `INT` | NO | PK, FK | `REFERENCES branches` | Assigned branch reference. |
| `assigned_date` | `DATE` | NO | | | Roster assignment start date. |
| `end_date` | `DATE` | YES | | | Assignment conclusion date (NULL if active). |

---

### Module 3: Members & Tiered Subscriptions

#### 10. `members`
Registered customer demographic profiles.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `member_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Member identifier. |
| `user_id` | `INT` | NO | FK | `REFERENCES users` | Authentication account link. |
| `home_branch_id` | `INT` | NO | FK | `REFERENCES branches` | Primary home gym branch. |
| `full_name` | `VARCHAR(120)` | NO | | | Member legal name. |
| `phone` | `VARCHAR(25)` | NO | | | Member contact phone number. |
| `registration_date` | `DATE` | NO | | | Initial account registration date. |

#### 11. `membership_plans`
Subscription tier products offered by gym organizations.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `plan_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Membership plan identifier. |
| `organization_id` | `INT` | NO | FK | `REFERENCES organizations` | Brand offering the plan. |
| `plan_name` | `VARCHAR(120)` | NO | | | Product name (e.g. Annual All-Access). |
| `duration_months` | `INT` | NO | | `CHECK (duration_months > 0)` | Contract validity period in months. |
| `price` | `DECIMAL(10,2)` | NO | | `CHECK (price >= 0)` | Base plan price in INR (ex-GST). |
| `description` | `VARCHAR(255)` | NO | | | Marketing and access summary. |

#### 12. `branch_access_rules`
Dynamic rule matrix configuring which branches a plan tier can enter (D2).
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `access_rule_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Unique access rule key. |
| `plan_id` | `INT` | NO | FK | `REFERENCES membership_plans` | Associated membership plan. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Target branch governed by the rule. |
| `access_type` | `ENUM` | NO | | `'HOME_ONLY'`, `'SAME_CITY'`, `'WEEKDAYS_ONLY'`, `'FULL'` | Access arbitration policy. |
| `conditions` | `VARCHAR(255)` | NO | | | Human-readable condition explanation. |

#### 13. `memberships`
Active and historical member subscription contracts.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `membership_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Membership contract identifier. |
| `member_id` | `INT` | NO | FK | `REFERENCES members` | Contract subscriber. |
| `plan_id` | `INT` | NO | FK | `REFERENCES membership_plans` | Purchased plan tier. |
| `start_date` | `DATE` | NO | | | Membership coverage start date. |
| `end_date` | `DATE` | NO | | `CHECK (end_date >= start_date)` | Membership expiry date. |
| `status` | `ENUM` | NO | | `'active'`, `'expired'`, `'cancelled'`, `'pending'` | Subscription validity state. |

---

### Module 4: Financial Ledger, Invoicing & Budgets

#### 14. `invoices`
Formal tax billing documents issued for memberships and services.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `invoice_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Invoice record key. |
| `invoice_number` | `VARCHAR(40)` | NO | UQ | `UNIQUE` | Sequential GST invoice number (e.g. `JGG/2026/000001`). |
| `member_id` | `INT` | NO | FK | `REFERENCES members` | Billed customer. |
| `membership_id` | `INT` | YES | FK | `REFERENCES memberships` | Associated membership contract. |
| `invoice_date` | `DATE` | NO | | | Date of billing issuance. |
| `due_date` | `DATE` | NO | | | Payment deadline. |
| `total` | `DECIMAL(10,2)` | NO | | `CHECK (total >= 0)` | Total invoice payable in INR. |
| `status` | `ENUM` | NO | | `'paid'`, `'pending'`, `'overdue'`, `'cancelled'` | Invoicing settlement status. |

#### 15. `invoice_items`
Itemized line entries constituting each invoice (1NF decomposition).
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `invoice_item_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Line item identifier. |
| `invoice_id` | `INT` | NO | FK | `REFERENCES invoices` | Parent tax invoice. |
| `description` | `VARCHAR(255)` | NO | | | Line description (e.g. "Base Membership Fee", "GST 18%"). |
| `quantity` | `INT` | NO | | `CHECK (quantity > 0)` | Billed quantity units. |
| `unit_price` | `DECIMAL(10,2)` | NO | | | Price per unit in INR. |
| `line_total` | `DECIMAL(10,2)` | NO | | | Subtotal (`quantity * unit_price`). |

#### 16. `payments`
Cash and electronic transactions received for settling invoices and memberships.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `payment_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Payment transaction key. |
| `membership_id` | `INT` | NO | FK | `REFERENCES memberships` | Membership paid for. |
| `invoice_id` | `INT` | YES | FK | `REFERENCES invoices` | Reconciled invoice settled. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Branch collecting cash or settlement. |
| `amount` | `DECIMAL(10,2)` | NO | | `CHECK (amount > 0)` | Settled payment amount in INR. |
| `payment_date` | `DATETIME` | NO | | | Transaction execution timestamp. |
| `payment_method` | `ENUM` | NO | | `'upi'`, `'credit_card'`, `'debit_card'`, `'net_banking'`, `'cash'` | Payment rail. |
| `payment_status` | `ENUM` | NO | | `'successful'`, `'pending'`, `'failed'` | Payment state. |
| `transaction_ref` | `VARCHAR(60)` | NO | | | Audit banking reference (e.g. `GGTXN20260000001`). |

#### 17. `refunds`
Reversals and partial refunds linked to original settled payments.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `refund_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Refund ledger key. |
| `payment_id` | `INT` | NO | FK | `REFERENCES payments` | Original transaction refunded. |
| `refund_amount` | `DECIMAL(10,2)` | NO | | `CHECK (refund_amount > 0)` | Refunded amount in INR. |
| `refund_date` | `DATETIME` | NO | | | Date requested or processed. |
| `reason` | `VARCHAR(255)` | NO | | | Customer or managerial rationale. |
| `status` | `ENUM` | NO | | `'requested'`, `'approved'`, `'completed'`, `'rejected'` | Refund workflow state. |

#### 18. `expense_categories`
Master chart of accounts categorizing branch expenditures.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `expense_category_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Category key. |
| `category_name` | `VARCHAR(100)` | NO | UQ | `UNIQUE` | Distinct category name (Rent, Utilities, Maintenance, etc.). |
| `description` | `VARCHAR(255)` | NO | | | Scope of expenditure. |

#### 19. `expenses`
Operational disbursements incurred by gym branches.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `expense_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Expense voucher key. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Branch cost center incurring cost. |
| `expense_category_id`| `INT` | NO | FK | `REFERENCES expense_categories` | Accounting category. |
| `recorded_by` | `INT` | NO | FK | `REFERENCES users` | Finance officer or manager user ID. |
| `expense_date` | `DATE` | NO | | | Date expense was incurred. |
| `amount` | `DECIMAL(10,2)` | NO | | `CHECK (amount > 0)` | Disbursed amount in INR. |
| `vendor` | `VARCHAR(120)` | NO | | | Paid supplier or vendor. |
| `description` | `VARCHAR(255)` | NO | | | Voucher explanation. |
| `status` | `ENUM` | NO | | `'paid'`, `'approved'`, `'pending'` | Voucher approval state. |

#### 20. `branch_budgets`
Monthly financial spending limits allocated per branch and category.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `budget_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Budget allocation key. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Scoped gym branch. |
| `expense_category_id`| `INT` | NO | FK | `REFERENCES expense_categories` | Scoped expense category. |
| `budget_period` | `VARCHAR(7)` | NO | | `Format YYYY-MM` | Target budget month. |
| `budget_amount` | `DECIMAL(10,2)` | NO | | `CHECK (budget_amount >= 0)` | Monthly cap limit in INR. |

---

### Module 5: Operations, Sessions, Equipment & Audit

#### 21. `attendance`
Biometric and scan check-ins recorded at gym branches.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `attendance_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Scan log identifier. |
| `member_id` | `INT` | NO | FK | `REFERENCES members` | Scanned member. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Branch where scan occurred. |
| `check_in` | `DATETIME` | NO | | | Entrance timestamp. |
| `check_out` | `DATETIME` | YES | | `CHECK (check_out IS NULL OR check_out >= check_in)` | Exit timestamp (NULL = currently inside). |

#### 22. `training_sessions`
Scheduled personal coaching appointments between members and trainers.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `session_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Session appointment key. |
| `member_id` | `INT` | NO | FK | `REFERENCES members` | Client attending session. |
| `trainer_id` | `INT` | NO | FK | `REFERENCES trainers` | Assigned coach. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Branch hosting appointment. |
| `session_start` | `DATETIME` | NO | | | Scheduled start datetime. |
| `duration_minutes` | `INT` | NO | | `CHECK (duration_minutes > 0)` | Session length in minutes (e.g. 60). |
| `status` | `ENUM` | NO | | `'scheduled'`, `'completed'`, `'cancelled'`, `'no_show'` | Appointment status. |
| `focus` | `VARCHAR(120)` | NO | | | Discipline (Strength, Cardio, Recovery, etc.). |

#### 23. `equipment`
Machinery and workout apparatus tracking maintenance lifecycles.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `equipment_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Asset inventory identifier. |
| `branch_id` | `INT` | NO | FK | `REFERENCES branches` | Location branch housing asset. |
| `equipment_name` | `VARCHAR(120)` | NO | | | Machine name (e.g. Olympic Squat Rack). |
| `quantity` | `INT` | NO | | `CHECK (quantity > 0)` | Number of available units. |
| `condition_status` | `ENUM` | NO | | `'excellent'`, `'good'`, `'fair'`, `'maintenance_required'` | Operational health state. |
| `last_serviced_on` | `DATE` | NO | | | Preventive maintenance log date. |

#### 24. `audit_log`
Immutable system audit journal recorded via database triggers and application transactions.
| Column | Type | Nullable | Key | Constraints / Defaults | Description |
|:---|:---|:---:|:---:|:---|:---|
| `audit_id` | `INT` | NO | PK | `AUTO_INCREMENT` | Journal entry key. |
| `user_id` | `INT` | NO | FK | `REFERENCES users` | User or actor executing change. |
| `action` | `VARCHAR(60)` | NO | | | Action verb (`RECORD_PAYMENT`, `UPDATE_EXPENSE`, etc.). |
| `table_name` | `VARCHAR(60)` | NO | | | Modified entity name. |
| `record_id` | `INT` | NO | | | Modified row primary key ID. |
| `old_value` | `JSON` | YES | | | Structured snapshot before modification. |
| `new_value` | `JSON` | YES | | | Structured snapshot after modification. |
| `created_at` | `DATETIME` | NO | | | Timestamp of journal write. |

---

## 3. Summary of Key Constraints & Business Rules

1. **Refund Constraint:** Total cumulative refunds on any payment cannot exceed the original settled payment amount:
   $$\sum \text{refund\_amount} \le \text{payment.amount}$$
   Enforced by both application business procedures (`sp_process_refund`) and database trigger (`trg_prevent_excess_refund`).
2. **Invoice Item Reconciliation:** Total invoice amount must exactly match the sum of its decomposed line items:
   $$\text{invoices.total} = \sum \text{invoice\_items.line\_total}$$
   Enforced during simulated checkout and verified across all 1,313 seeded invoices.
3. **Temporal Validity Checks:**
   - Memberships: `end_date >= start_date`.
   - Attendance: `check_out IS NULL OR check_out >= check_in`.
   - Operational Hours: `day_of_week BETWEEN 0 AND 6`.
4. **Positive Value Constraints:**
   - `branches.capacity > 0`
   - `membership_plans.price >= 0`
   - `payments.amount > 0`
   - `refunds.refund_amount > 0`
   - `expenses.amount > 0`
   - `branch_budgets.budget_amount >= 0`
   - `equipment.quantity > 0`
   - `training_sessions.duration_minutes > 0`
