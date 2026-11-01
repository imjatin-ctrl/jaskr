-- =====================================================================
-- Jaskr GymGrid - Evaluator Query Demonstrations
-- Demonstrating Joins, GROUP BY/HAVING, Subqueries, Views & Window Functions
-- =====================================================================

-- QUERY 1: Multi-Table Join across 5 Relations (Organizations, Branches, Plans, Memberships, Payments)
-- Purpose: Retrieve full member lifecycle and revenue breakdown for active memberships
SELECT 
    o.name AS organization_name,
    b.name AS home_branch,
    b.city,
    m.full_name AS member_name,
    p.plan_name,
    ms.start_date,
    ms.end_date,
    pay.amount AS paid_amount_inr,
    pay.payment_method,
    pay.transaction_ref
FROM organizations o
JOIN branches b ON o.organization_id = b.organization_id
JOIN members m ON b.branch_id = m.home_branch_id
JOIN memberships ms ON m.member_id = ms.member_id
JOIN membership_plans p ON ms.plan_id = p.plan_id
JOIN payments pay ON ms.membership_id = pay.membership_id
WHERE ms.status = 'active' AND pay.payment_status = 'successful'
ORDER BY pay.payment_date DESC
LIMIT 15;

-- QUERY 2: Aggregation with GROUP BY and HAVING Clause
-- Purpose: Find branch expense categories that have exceeded an aggregate threshold of ₹1,00,000 in 2026
SELECT 
    b.name AS branch_name,
    b.city,
    ec.category_name,
    COUNT(e.expense_id) AS total_expense_vouchers,
    SUM(e.amount) AS total_spent_inr,
    ROUND(AVG(e.amount), 2) AS average_voucher_amount_inr
FROM expenses e
JOIN branches b ON e.branch_id = b.branch_id
JOIN expense_categories ec ON e.expense_category_id = ec.expense_category_id
WHERE e.status IN ('paid', 'approved') AND e.expense_date >= '2026-01-01'
GROUP BY b.branch_id, b.name, b.city, ec.category_name
HAVING SUM(e.amount) > 100000.00
ORDER BY total_spent_inr DESC;

-- QUERY 3: Subquery in WHERE Clause (Scalar Subquery)
-- Purpose: Find branches whose net receipts exceed the city-wide branch average
SELECT 
    b.branch_id,
    b.name AS branch_name,
    b.city,
    (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE branch_id = b.branch_id AND payment_status = 'successful') AS total_receipts
FROM branches b
WHERE (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE branch_id = b.branch_id AND payment_status = 'successful') > (
    SELECT AVG(branch_total)
    FROM (
        SELECT branch_id, SUM(amount) AS branch_total
        FROM payments
        WHERE payment_status = 'successful'
        GROUP BY branch_id
    ) AS avg_calc
)
ORDER BY total_receipts DESC;

-- QUERY 4: Correlated Subquery with NOT EXISTS
-- Purpose: Identify members who have an active membership but zero check-ins in the last 30 days
SELECT 
    m.member_id,
    m.full_name,
    m.phone,
    b.name AS home_branch,
    ms.start_date,
    ms.end_date
FROM members m
JOIN branches b ON m.home_branch_id = b.branch_id
JOIN memberships ms ON m.member_id = ms.member_id
WHERE ms.status = 'active'
AND NOT EXISTS (
    SELECT 1 
    FROM attendance a 
    WHERE a.member_id = m.member_id 
    AND a.check_in >= DATE_SUB('2026-10-30', INTERVAL 30 DAY)
)
LIMIT 10;

-- QUERY 5: Relational View Query with Filter and Sorting
-- Purpose: Query the precomputed v_branch_financial_summary view to identify top profitable branches
SELECT 
    branch_name,
    city,
    organization_name,
    gross_receipts,
    total_refunds,
    net_receipts,
    operating_expenses,
    net_operating_margin
FROM v_branch_financial_summary
ORDER BY net_operating_margin DESC;

-- QUERY 6: Complex Aggregation with CTE / Window Function
-- Purpose: Rank branches by gross receipts within each city
SELECT 
    b.city,
    b.name AS branch_name,
    SUM(p.amount) AS total_gross_receipts,
    RANK() OVER (PARTITION BY b.city ORDER BY SUM(p.amount) DESC) AS city_revenue_rank
FROM branches b
JOIN payments p ON b.branch_id = p.branch_id
WHERE p.payment_status = 'successful'
GROUP BY b.city, b.name
ORDER BY b.city, city_revenue_rank;
