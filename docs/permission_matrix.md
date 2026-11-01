# Jaskr GymGrid - RBAC & DCL Permission Matrix

**Project:** Jaskr GymGrid (City-Wide Gym Discovery, Smart Access & Financial Management)  
**Security Model:** Role-Based Access Control (RBAC) + MySQL 8.x Data Control Language (DCL) + Application Tenant Scoping  

---

## 1. Role Definitions

| Role Code | System Role | Primary Scope | Typical User Persona |
|:---|:---|:---|:---|
| `VISITOR` | Anonymous / Unauthenticated | Public catalog | Prospective gym member browsing branches & pricing |
| `MEMBER` | Authenticated Member | Self (`user_id`, `member_id`) | Active or expired gym member checking in & paying dues |
| `FRONT_DESK` | Staff (`front_desk`) | Assigned Branch (`branch_id`) | Receptionist scanning QR codes & checking occupancy |
| `TRAINER` | Staff (`trainer`) | Assigned Branch & Roster | Certified personal coach managing client sessions |
| `FINANCE` | Staff (`finance`) | Brand (`organization_id`) | Accountant auditing invoices, recording expenses & taxes |
| `MANAGER` | Staff (`branch_manager`) | Assigned Branch (`branch_id`) | Branch General Manager overseeing inventory, KPIs & staff |
| `OWNER` | Gym Franchise Owner | Brand (`organization_id`) | Franchise owner managing branches, pricing matrix & P&L |
| `ADMIN` | Platform Administrator | Global (Platform-wide) | System operator managing tenant onboarding & DB health |
| `LAB_USER` | Academic Evaluator | Read-Only / Transaction Sandbox | DBMS student or faculty testing queries & constraints |

---

## 2. Table-Level CRUD & Scope Permission Matrix

Legend:
- `S`: SELECT, `I`: INSERT, `U`: UPDATE, `D`: DELETE
- Scope tags: `[Public]`, `[Own]`, `[Branch]`, `[Org]`, `[Global]`

| Table | Visitor | Member | Front Desk | Trainer | Finance | Branch Manager | Gym Owner | Platform Admin |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`organizations`** | S `[Active]` | S `[Active]` | S `[Org]` | S `[Org]` | S `[Org]` | S `[Org]` | S,U `[Org]` | S,I,U,D `[Global]` |
| **`branches`** | S `[Public]` | S `[Public]` | S `[Branch]` | S `[Branch]` | S `[Org]` | S,U `[Branch]` | S,I,U `[Org]` | S,I,U,D `[Global]` |
| **`branch_hours`** | S `[Public]` | S `[Public]` | S `[Branch]` | S `[Branch]` | S `[Org]` | S,U `[Branch]` | S,I,U,D `[Org]` | S,I,U,D `[Global]` |
| **`facilities`** | S `[Public]` | S `[Public]` | S `[Public]` | S `[Public]` | S `[Public]` | S `[Public]` | S `[Public]` | S,I,U,D `[Global]` |
| **`branch_facilities`**| S `[Public]` | S `[Public]` | S `[Branch]` | S `[Branch]` | S `[Org]` | S,I,D `[Branch]` | S,I,D `[Org]` | S,I,U,D `[Global]` |
| **`users`** | I `[Register]`| S,U `[Own]` | S `[Branch Members]` | S `[Clients]` | S `[Org Staff]` | S `[Branch Staff]` | S,U `[Org Staff]`| S,I,U,D `[Global]` |
| **`staff`** | — | — | S `[Own]` | S `[Own]` | S `[Org]` | S `[Branch]` | S,I,U `[Org]` | S,I,U,D `[Global]` |
| **`trainers`** | S `[Public Directory]` | S `[Public]` | S `[Branch]` | S,U `[Own]` | S `[Org]` | S `[Branch]` | S,I,U `[Org]` | S,I,U,D `[Global]` |
| **`trainer_assignments`**| S `[Public]` | S `[Public]` | S `[Branch]` | S `[Own]` | S `[Org]` | S,I,D `[Branch]` | S,I,D `[Org]` | S,I,U,D `[Global]` |
| **`members`** | — | S,U `[Own]` | S `[Branch Scanned]` | S `[Clients]` | S `[Org]` | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`membership_plans`**| S `[Public]` | S `[Public]` | S `[Org]` | S `[Org]` | S `[Org]` | S `[Org]` | S,I,U `[Org]` | S,I,U,D `[Global]` |
| **`branch_access_rules`**| S `[Public]`| S `[Public]` | S `[Org]` | — | S `[Org]` | S `[Org]` | S,I,U,D `[Org]` | S,I,U,D `[Global]` |
| **`memberships`** | — | S `[Own]` | S `[Branch Scanned]` | S `[Clients]` | S `[Org]` | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`invoices`** | — | S `[Own]` | — | — | S,I `[Org]` | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`invoice_items`** | — | S `[Own]` | — | — | S,I `[Org]` | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`payments`** | — | S `[Own]`, I `[Checkout]` | S `[Branch Check]` | — | S,I `[Org]` | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`refunds`** | — | S `[Own]`, I `[Request]` | — | — | S,U `[Org]` | S `[Branch]` | S,U `[Approve Org]`| S,I,U,D `[Global]` |
| **`expense_categories`**| — | — | — | — | S `[Global]` | S `[Global]` | S `[Global]` | S,I,U,D `[Global]` |
| **`expenses`** | — | — | — | — | S,I,U `[Org]` | S,I `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`branch_budgets`** | — | — | — | — | S,I,U `[Org]` | S `[Branch]` | S,I,U `[Org]` | S,I,U,D `[Global]` |
| **`attendance`** | — | S `[Own]`, I `[Check-in]` | S,I,U `[Branch]` | S `[Clients]` | — | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`training_sessions`**| — | S `[Own]`, I `[Book]` | S `[Branch]` | S,U `[Own]` | — | S `[Branch]` | S `[Org]` | S,I,U,D `[Global]` |
| **`equipment`** | — | — | — | — | S `[Org Assets]` | S,I,U,D `[Branch]`| S `[Org]` | S,I,U,D `[Global]` |
| **`audit_log`** | — | — | — | — | — | — | S `[Org Triggers]` | S,I `[Global]` |

---

## 3. MySQL 8.x DCL Role Accounts & Grants

The system defines 6 dedicated MySQL database user accounts with least-privilege grants (see [db/dcl.sql](file:///Users/jatinsingh/Downloads/dbms%20project/db/dcl.sql)):

```sql
-- Public / Anonymous catalog browsing
CREATE USER IF NOT EXISTS 'gg_public'@'%' IDENTIFIED BY 'PublicPass@123';
GRANT SELECT ON gymgrid.organizations TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.branches TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.branch_hours TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.facilities TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.branch_facilities TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.membership_plans TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.branch_access_rules TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.trainers TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.v_public_branch_directory TO 'gg_public'@'%';
GRANT SELECT ON gymgrid.v_branch_crowd_hourly TO 'gg_public'@'%';
GRANT INSERT ON gymgrid.users TO 'gg_public'@'%';

-- Member role account
CREATE USER IF NOT EXISTS 'gg_member'@'%' IDENTIFIED BY 'MemberPass@123';
-- Inherits gg_public SELECT rights +
GRANT SELECT, UPDATE ON gymgrid.users TO 'gg_member'@'%';
GRANT SELECT, UPDATE ON gymgrid.members TO 'gg_member'@'%';
GRANT SELECT, INSERT ON gymgrid.memberships TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.invoices TO 'gg_member'@'%';
GRANT SELECT ON gymgrid.invoice_items TO 'gg_member'@'%';
GRANT SELECT, INSERT ON gymgrid.payments TO 'gg_member'@'%';
GRANT SELECT, INSERT ON gymgrid.refunds TO 'gg_member'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.attendance TO 'gg_member'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.training_sessions TO 'gg_member'@'%';
GRANT EXECUTE ON PROCEDURE gymgrid.sp_record_payment TO 'gg_member'@'%';

-- Staff role account
CREATE USER IF NOT EXISTS 'gg_staff'@'%' IDENTIFIED BY 'StaffPass@123';
GRANT SELECT, INSERT, UPDATE ON gymgrid.attendance TO 'gg_staff'@'%';
GRANT SELECT, UPDATE ON gymgrid.training_sessions TO 'gg_staff'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.equipment TO 'gg_staff'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.expenses TO 'gg_staff'@'%';
GRANT SELECT ON gymgrid.branch_budgets TO 'gg_staff'@'%';
GRANT SELECT ON gymgrid.expense_categories TO 'gg_staff'@'%';
GRANT SELECT ON gymgrid.v_branch_crowd_hourly TO 'gg_staff'@'%';

-- Gym Franchise Owner account
CREATE USER IF NOT EXISTS 'gg_owner'@'%' IDENTIFIED BY 'OwnerPass@123';
GRANT SELECT, UPDATE ON gymgrid.organizations TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.branches TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_hours TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_facilities TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.membership_plans TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.branch_access_rules TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.staff TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE ON gymgrid.trainers TO 'gg_owner'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON gymgrid.trainer_assignments TO 'gg_owner'@'%';
GRANT SELECT, UPDATE ON gymgrid.refunds TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.v_branch_financial_summary TO 'gg_owner'@'%';
GRANT SELECT ON gymgrid.audit_log TO 'gg_owner'@'%';
GRANT EXECUTE ON PROCEDURE gymgrid.sp_process_refund TO 'gg_owner'@'%';

-- Platform Super Admin
CREATE USER IF NOT EXISTS 'gg_admin'@'%' IDENTIFIED BY 'AdminPass@123';
GRANT ALL PRIVILEGES ON gymgrid.* TO 'gg_admin'@'%' WITH GRANT OPTION;

-- Academic DBMS Read-Only Lab Account
CREATE USER IF NOT EXISTS 'gg_readonly_lab'@'%' IDENTIFIED BY 'LabReadOnly@123';
GRANT SELECT ON gymgrid.* TO 'gg_readonly_lab'@'%';
```

---

## 4. Multi-Tenant Scoping Architecture: WHERE Clauses vs. DBMS Views vs. DCL

### 4.1 The Need for Hybrid Scoping
In a shared relational database hosting multiple competing gym brands (e.g. FitZone India, IronCore Fitness, CultFit Elite, Urban Active), table-level DCL grants (`GRANT SELECT ON branches`) cannot prevent Owner A from inspecting Owner B's financial figures. MySQL 8.x does not support PostgreSQL-style declarative Row-Level Security (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).

To solve this rigorously without security compromises, Jaskr GymGrid employs a **defense-in-depth triple-layer scoping architecture**:

```
[Layer 1: DCL Engine Boundary]
       ↓ (Limits allowed SQL statements: SELECT, INSERT, UPDATE, EXECUTE)
[Layer 2: Application Scoping Interceptors]
       ↓ (@check_org_scoping, @check_member_scoping, Parameterized WHERE injection)
[Layer 3: Pre-aggregated Analytical Views]
         (v_branch_financial_summary, v_branch_crowd_hourly)
```

### 4.2 Layer 2 Application-Level Parameterized Scoping
Every data query executed on behalf of a tenant or member is forced through parameterization decorators:
1. **Organization Scoping:**
   ```python
   # In app/auth.py
   def check_org_scoping(target_org_id):
       user = get_current_user()
       if user["role"] == "admin":
           return True
       if user["role"] == "owner" and user.get("organization_id") == target_org_id:
           return True
       abort(403)
   ```
2. **Strict Query Injection:** All SQL queries join or filter on the tenant primary key:
   ```sql
   -- Staff & Finance Scoping
   SELECT * FROM expenses WHERE branch_id IN (
       SELECT branch_id FROM branches WHERE organization_id = %s
   );

   -- Member Identity Scoping
   SELECT * FROM payments p
   JOIN memberships m ON p.membership_id = m.membership_id
   WHERE m.member_id = %s;
   ```

### 4.3 Layer 3 Analytical Views with Built-In Grouping
Analytical views (such as `v_branch_financial_summary`) compute pre-aggregated sums across invoice and payment records. Even when evaluated across branches, queries must explicitly supply `WHERE b.organization_id = %s`, ensuring zero risk of unauthenticated data exposure.

---

## 5. Security Edge Cases & Attack Prevention

1. **Direct Object Reference (IDOR):**
   - Attempting to view receipt `/member/receipt/<payment_id>` verifies that `payment.member_id == session.member_id`. Any mismatch yields an immediate `403 Forbidden`.
2. **Cross-Tenant Plan Manipulation:**
   - Attempting to update branch access rules `/owner/plans-matrix` verifies that both the plan and the target branch belong to the logged-in owner's `organization_id`.
3. **Privilege Escalation:**
   - Route decorators `@roles_required('admin')` enforce that standard users, front desk receptionists, or owners cannot trigger organization approvals or health metrics.
