-- =====================================================================
-- Jaskr GymGrid - Database Triggers (MySQL 8.x)
-- Demonstrating Automated Integrity Constraints and Audit Generation
-- =====================================================================

DELIMITER $$

-- 1. trg_prevent_excess_refund
-- Enforces integrity: SUM(refunds) cannot exceed original payment amount
DROP TRIGGER IF EXISTS trg_prevent_excess_refund$$
CREATE TRIGGER trg_prevent_excess_refund
BEFORE INSERT ON refunds
FOR EACH ROW
BEGIN
    DECLARE v_orig_amount DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_curr_refunds DECIMAL(10, 2) DEFAULT 0.00;

    SELECT amount INTO v_orig_amount 
    FROM payments 
    WHERE payment_id = NEW.payment_id;

    IF v_orig_amount IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Integrity violation: Payment record not found for refund.';
    END IF;

    SELECT COALESCE(SUM(refund_amount), 0.00) INTO v_curr_refunds
    FROM refunds
    WHERE payment_id = NEW.payment_id AND status != 'rejected';

    IF (v_curr_refunds + NEW.refund_amount) > v_orig_amount THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Integrity violation: Cumulative refund amount exceeds original payment amount.';
    END IF;
END$$

-- 2. trg_audit_expense_update
-- Logs financial adjustments on expenses table into audit_log
DROP TRIGGER IF EXISTS trg_audit_expense_update$$
CREATE TRIGGER trg_audit_expense_update
AFTER UPDATE ON expenses
FOR EACH ROW
BEGIN
    IF OLD.amount != NEW.amount OR OLD.status != NEW.status THEN
        INSERT INTO audit_log (
            user_id, action, table_name, record_id, old_value, new_value, created_at
        ) VALUES (
            NEW.recorded_by,
            CONCAT('EXPENSE_', UPPER(NEW.status)),
            'EXPENSES',
            NEW.expense_id,
            JSON_OBJECT('amount', OLD.amount, 'status', OLD.status, 'vendor', OLD.vendor),
            JSON_OBJECT('amount', NEW.amount, 'status', NEW.status, 'vendor', NEW.vendor),
            NOW()
        );
    END IF;
END$$

-- 3. trg_audit_payment_status
-- Logs payment status transitions into audit_log
DROP TRIGGER IF EXISTS trg_audit_payment_status$$
CREATE TRIGGER trg_audit_payment_status
AFTER UPDATE ON payments
FOR EACH ROW
BEGIN
    IF OLD.payment_status != NEW.payment_status THEN
        INSERT INTO audit_log (
            user_id, action, table_name, record_id, old_value, new_value, created_at
        ) VALUES (
            1, -- System / Administrator user
            CONCAT('PAYMENT_STATUS_', UPPER(NEW.payment_status)),
            'PAYMENTS',
            NEW.payment_id,
            JSON_OBJECT('payment_status', OLD.payment_status, 'amount', OLD.amount),
            JSON_OBJECT('payment_status', NEW.payment_status, 'amount', NEW.amount),
            NOW()
        );
    END IF;
END$$

DELIMITER ;
