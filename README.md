# Jaskr GymGrid

> **City-Wide Gym Discovery, Smart Access, and Financial Management Platform**  
> An Academic Database Management Systems (DBMS) Prototype  
> All data is fictional; payments are simulated.

---

## 🌟 Overview

**Jaskr GymGrid** is an enterprise-grade multi-portal web application built on a normalized 3NF relational database schema. It unifies independent gym franchises and multi-branch fitness chains across 11 Indian cities into a single platform for discovery, smart tiered access control, staff operations, and financial auditing.

Designed specifically for academic DBMS evaluation, Jaskr GymGrid features deep relational schema modeling, composite foreign key constraints, ACID transaction theater with automated rollback demonstration, multi-tenant isolation, and an interactive **Under the Hood DBMS Lab**.

---

## 🚀 Key Differentiators (D1 – D7)

- **D1: Discovery & 4-Way Comparison Matrix** — Compare up to 4 gym branches side-by-side with weekly operational hours, equipment catalogs, monthly pricing tiers, and amenities.
- **D2: Dynamic Access Checker Engine** — Evaluates rule-based tier permissions (`HOME_ONLY`, `SAME_CITY`, `WEEKDAYS_ONLY`, `FULL`) against snapshot timestamps with clear explanations of allow/deny decisions.
- **D3: Honest Crowd Density Estimates** — Real-time and historical hourly crowd density calibrated against actual branch capacity, explicitly labeled as *"Estimate"* with visible sample sizes and last updated timestamps.
- **D4: Unified Financial Metrics & Reconciliation** — Strict cash accounting: Gross Receipts = Settled Payments, Completed Refunds subtracted, Net Receipts computed, and 100% line-item tax invoice reconciliation.
- **D5: True Multi-Role Portals** — Distinct dedicated portals for Public Visitors, Members, Staff (Front Desk, Personal Trainers, Finance Officers, Branch Managers), Franchise Owners, and Platform Administrators.
- **D6: Multi-Tenant & Horizontal Isolation** — Relational multi-tenancy enforcing brand scoping and preventing Insecure Direct Object References (IDOR).
- **D7: Interactive DBMS Lab** — Interactive in-browser database workbench featuring ER Diagram explorer, curated query executor with SQL syntax highlighting, live constraint failure testing, step-by-step transaction rollback theater, DCL permission matrix, and isolation boundary audits.

---

## 🛠️ Architecture & Tech Stack

- **Backend:** Python 3.10+ / Flask, Modular Blueprints, Jinja2 template inheritance.
- **Database Engine (Dual-Mode):**
  - **MySQL 8.x (Production/Demonstration):** Full relational schema with composite indexes, stored procedures, audit triggers, and DCL user accounts.
  - **SQLite 3 (Zero-Dependency Fallback):** Transparent automatic fallback adapter (`app/database.py`) requiring zero setup or external daemons.
- **Frontend Design System:** Custom Neo-Brutalist design tokens (`#FBF9F2` graph-paper grid canvas, `#14121F` deep ink typography and 2.5px borders, 4px solid drop-shadows, role-specific color accents: Yellow, Blue, Coral, Mint).
- **Data Visualizations:** Chart.js for crowd histograms, financial break-even analytics, and hourly check-in trends.

---

## ⚡ Quickstart (One Command)

### 1. Automated Setup & Verification
Run the automated initialization script to generate seed data, create database tables, load 24 normalized CSV relations, and run the test suite:

```bash
chmod +x setup.sh
./setup.sh
```

### 2. Start the Web Server
Launch the application:

```bash
python3 run.py
```
Open your browser at: **`http://127.0.0.1:5000`**

### 3. (Optional) Run with Docker Compose (MySQL 8.0)
To run against a containerized MySQL 8.0 instance:
```bash
docker compose up -d
python3 db/load_seed.py
python3 run.py
```

---

## 👥 Demo Logins & Persona Chips

For seamless evaluation, Jaskr GymGrid includes **1-Click Quick Login Chips** on the `/login` page. All demo accounts use the standard password: **`Demo@1234`**

| Persona / Job Role | Demo Account Email | Password | Primary Scope & Access |
|:---|:---|:---|:---|
| **Member (National Pass)** | `member.demo@jaskrgymgrid.example` | `Demo@1234` | Rohan Malhotra - Annual All-Access (FULL access), home IronPulse Saket. |
| **Member (Single Branch)** | `member.monthly.demo@jaskrgymgrid.example` | `Demo@1234` | Priya Deshmukh - Monthly Flex (HOME_ONLY), home FlexNation Baner. |
| **Member (Expired)** | `member.expired.demo@jaskrgymgrid.example` | `Demo@1234` | Imran Qureshi - Membership expired 2026-08-31; entry denied everywhere. |
| **Staff: Front Desk** | `frontdesk.demo@jaskrgymgrid.example` | `Demo@1234` | Front desk, IronPulse Saket: live occupancy, QR check-in & member lookup. |
| **Staff: Personal Trainer**| `trainer.demo@jaskrgymgrid.example` | `Demo@1234` | Trainer, IronPulse Saket: coaching sessions & attendance roster. |
| **Staff: Finance Officer** | `finance.demo@jaskrgymgrid.example` | `Demo@1234` | Finance officer, IronPulse Fitness (org-wide): invoices, expenses, budgets. |
| **Staff: Branch Manager** | `manager.demo@jaskrgymgrid.example` | `Demo@1234` | Branch manager, IronPulse Saket: branch KPIs, equipment health & roster. |
| **Gym Franchise Owner (Org 1)** | `owner.ironpulse.demo@jaskrgymgrid.example` | `Demo@1234` | Owner of IronPulse Fitness (6 branches): P&L, 2D matrix, refund queue. |
| **Gym Franchise Owner (Org 2)** | `owner.flexnation.demo@jaskrgymgrid.example` | `Demo@1234` | Owner of FlexNation Gyms: used for cross-tenant isolation verification. |
| **Gym Franchise Owner (Pending)** | `owner.zenith.demo@jaskrgymgrid.example` | `Demo@1234` | Owner of Zenith Strength Lab - pending platform admin approval. |
| **Platform Super Admin** | `admin.demo@jaskrgymgrid.example` | `Demo@1234` | Superuser: approve gym listings, platform statistics & DB health. |
| **Academic Evaluator** | Browse anonymously or visit `/lab` | N/A | Explore ER diagrams, run SQL queries, test rollbacks. |

---

## 🔬 DBMS Evaluator Tour ("Under the Hood" Lab)

Navigate to the **DBMS Lab** via the navigation bar or `/lab`:
1. **ER Diagram Explorer (`/lab/er`):** Interactive visual representation of the 24 relational tables, PK/FK relationships, and cascading rules.
2. **Curated Query Runner (`/lab/query`):** Run pre-built SQL queries illustrating complex joins, `GROUP BY ... HAVING`, correlated subqueries, analytical views, and window functions, with execution timers and raw SQL inspection.
3. **Constraint Failure Lab (`/lab/constraints`):** Test database integrity by firing invalid queries (negative pricing, inverted operational hours, excessive refunds, duplicate unique keys) to observe constraint enforcement.
4. **Transaction Theater (`/lab/transactions`):** Execute multi-statement payment recording with a live interactive toggle to force simulated mid-transaction failures, demonstrating atomic `ROLLBACK` vs `COMMIT`.
5. **Permissions & DCL Matrix (`/lab/permissions`):** Review MySQL least-privilege `GRANT`/`REVOKE` statements for each system user.
6. **Multi-Tenant Isolation Audit (`/lab/isolation`):** Execute cross-tenant exploit tests to verify that tenant data is never leaked across brands or member IDs.
7. **Query Optimization & Indexes (`/lab/indexes`):** Inspect `EXPLAIN` query plans showing composite B-Tree index utilization (`idx_attendance_branch_checkin`, `idx_payments_membership_date`).

---

## 📁 Repository Structure

```
dbms project/
├── app/                        # Flask Application Core
│   ├── __init__.py             # Factory, blueprint registration & template filters
│   ├── config.py               # Demo clock (2026-10-30 10:00:00), secrets & DB config
│   ├── database.py             # Dual-engine DB adapter (MySQL 8.x + SQLite fallback)
│   ├── auth.py                 # RBAC session guards, scoping & login chips
│   ├── public.py               # Public catalog, discovery & compare routes
│   ├── member.py               # Member portal, check-in, billing & checkout
│   ├── staff.py                # Staff portal (Front Desk, Trainer, Finance, Manager)
│   ├── owner.py                # Owner portal (P&L, 2D matrix, refund queue)
│   ├── admin.py                # Platform admin (approvals, users, DB health)
│   └── lab.py                  # Under the Hood DBMS Lab interactive testbed
├── db/                         # Database Relational Assets
│   ├── schema.sql              # 24 tables with DDL, types & CHECK constraints
│   ├── constraints_indexes.sql # Composite B-tree indexes & foreign keys
│   ├── views.sql               # 5 analytical views (financial, crowd, directory)
│   ├── procedures.sql          # Stored procedures (sp_record_payment, sp_process_refund)
│   ├── triggers.sql            # Audit triggers (expense changes, refund limits)
│   ├── dcl.sql                 # User accounts & least-privilege GRANTs
│   ├── queries_demo.sql        # 6 Curated academic SQL demonstration queries
│   ├── load_seed.py            # Automated CSV seed importer (hashes Demo@1234)
│   └── seed_data/              # Seed generator and 24 normalized CSV datasets
├── docs/                       # Project Technical Documentation
│   ├── schema_delta.md         # Full schema evolution and 3NF normalization proof
│   ├── er_diagram.md           # Mermaid ER diagram & relationship dictionary
│   ├── data_dictionary.md      # Master 24-table data dictionary & normalization notes
│   ├── permission_matrix.md    # RBAC CRUD matrix & scoping architecture
│   └── test_report.md          # 20/20 test results & DBMS concept mapping
├── static/                     # CSS, SVG Logos & Vanilla ES Modules
├── templates/                  # Jinja2 Modular HTML5 Templates
├── tests/                      # Automated Verification Suites
│   ├── test_db_layer.py        # Database row counts, views & ACID rollback tests
│   └── test_full_suite.py      # Access rules, isolation, refund & route tests
├── docker-compose.yml          # Containerized MySQL 8.0 environment
├── setup.sh                    # One-command automated build & test script
└── run.py                      # Application entry point
```

---

## 🧪 Running Automated Tests

Run the full automated test suite anytime with `pytest`:

```bash
python3 -m pytest -v
```

Expected output:
```
tests/test_db_layer.py::test_table_row_counts PASSED
tests/test_db_layer.py::test_view_public_branch_directory PASSED
tests/test_db_layer.py::test_view_active_memberships PASSED
tests/test_db_layer.py::test_view_branch_financial_summary PASSED
tests/test_db_layer.py::test_sp_record_payment_success PASSED
tests/test_db_layer.py::test_sp_record_payment_rollback_on_failure PASSED
tests/test_full_suite.py::test_access_rule_full_allowed_across_cities PASSED
tests/test_full_suite.py::test_access_rule_home_only_denied_other_branch PASSED
tests/test_full_suite.py::test_access_rule_expired_denied_everywhere PASSED
tests/test_full_suite.py::test_access_rule_cross_organization_denied PASSED
tests/test_full_suite.py::test_cross_tenant_owner_isolation PASSED
tests/test_full_suite.py::test_member_private_receipt_isolation PASSED
tests/test_full_suite.py::test_invoice_items_reconciliation PASSED
tests/test_full_suite.py::test_over_refund_rejection PASSED
tests/test_full_suite.py::test_access_rule_weekdays_only_semantics PASSED
tests/test_full_suite.py::test_access_rule_same_city_semantics PASSED
tests/test_full_suite.py::test_budget_vs_actual_variance PASSED
tests/test_full_suite.py::test_double_partial_refund_success_and_excess_blocked PASSED
tests/test_full_suite.py::test_role_matrix_authorization_barriers PASSED
tests/test_full_suite.py::test_public_pages_render PASSED
============================== 20 passed in 0.24s ==============================
```

---

## ⚖️ Academic Disclaimer
*Jaskr GymGrid is an academic DBMS prototype developed for educational demonstration. All gym brands, branches, members, personal details, and financial transactions are completely fictional. Payment gateways and biometric scans are simulated within local application state.*
