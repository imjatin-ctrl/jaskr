-- =====================================================================
-- Jaskr GymGrid - Stored Procedures (MySQL 8.x)
-- Demonstrating ACID Transactions, Exception Handlers, and Rollback
-- =====================================================================

DELIMITER $$

-- 1. sp_record_payment
-- Atomic transaction processing for simulated checkout & front-desk payment
DROP PROCEDURE IF EXISTS sp_record_payment$$
CREATE PROCEDURE sp_record_payment(
    IN p_membership_id INT,
    IN p_invoice_id INT,
    IN p_branch_id INT,
    IN p_amount DECIMAL(10, 2),
    IN p_payment_method VARCHAR(30),
    IN p_user_id INT,
    IN p_simulate_failure INT, -- 1 to force rollback for Transaction Theater demonstration
    OUT p_out_payment_id INT,
    OUT p_status_code VARCHAR(30),
    OUT p_status_message VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_new_pay_id INT DEFAULT 0;
    DECLARE v_txn_ref VARCHAR(60);
    DECLARE v_ms_exists INT DEFAULT 0;
    DECLARE v_inv_exists INT DEFAULT 0;

    -- Exit handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_out_payment_id = 0;
        SET p_status_code = 'ERROR_ROLLBACK';
        SET p_status_message = 'Transaction aborted: SQL Exception encountered. All changes rolled back.';
    END;

    -- Step 1: Validate existence
    SELECT COUNT(*) INTO v_ms_exists FROM memberships WHERE membership_id = p_membership_id;
    IF v_ms_exists = 0 THEN
        SET p_out_payment_id = 0;
        SET p_status_code = 'MEMBERSHIP_NOT_FOUND';
        SET p_status_message = 'Specified membership record does not exist.';
        LEAVE proc_label;
    END IF;

    IF p_invoice_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_inv_exists FROM invoices WHERE invoice_id = p_invoice_id;
        IF v_inv_exists = 0 THEN
            SET p_out_payment_id = 0;
            SET p_status_code = 'INVOICE_NOT_FOUND';
            SET p_status_message = 'Specified invoice record does not exist.';
            LEAVE proc_label;
        END IF;
    END IF;

    -- Step 2: BEGIN TRANSACTION
    START TRANSACTION;

    -- Check if demonstrator requested forced failure (Transaction Theater)
    IF p_simulate_failure = 1 THEN
        -- Intentionally trigger an exception / rollback demonstration
        INSERT INTO audit_log (user_id, action, table_name, record_id, old_value, new_value)
        VALUES (p_user_id, 'PAYMENT_FORCED_FAIL_ATTEMPT', 'PAYMENTS', 0, NULL, JSON_OBJECT('simulated', TRUE));
        
        ROLLBACK;
        SET p_out_payment_id = 0;
        SET p_status_code = 'FORCED_FAILURE_DEMO';
        SET p_status_message = 'Transaction intentionally aborted by Transaction Theater. ROLLBACK executed successfully.';
        LEAVE proc_label;
    END IF;

    -- Step 3: Insert payment record
    INSERT INTO payments (
        membership_id, invoice_id, branch_id, amount, payment_date, 
        payment_method, payment_status, transaction_ref
    ) VALUES (
        p_membership_id, p_invoice_id, p_branch_id, p_amount, NOW(), 
        p_payment_method, 'successful', ''
    );
    SET v_new_pay_id = LAST_INSERT_ID();
    SET v_txn_ref = CONCAT('GGTXN2026', LPAD(v_new_pay_id, 7, '0'));
    
    UPDATE payments SET transaction_ref = v_txn_ref WHERE payment_id = v_new_pay_id;

    -- Step 4: Update invoice status
    IF p_invoice_id IS NOT NULL THEN
        UPDATE invoices 
        SET status = 'paid' 
        WHERE invoice_id = p_invoice_id;
    END IF;

    -- Step 5: Activate membership
    UPDATE memberships 
    SET status = 'active' 
    WHERE membership_id = p_membership_id;

    -- Step 6: Write audit trail
    INSERT INTO audit_log (
        user_id, action, table_name, record_id, old_value, new_value, created_at
    ) VALUES (
        p_user_id, 'RECORD_PAYMENT', 'PAYMENTS', v_new_pay_id,
        JSON_OBJECT('membership_id', p_membership_id, 'invoice_id', p_invoice_id),
        JSON_OBJECT('payment_id', v_new_pay_id, 'amount', p_amount, 'status', 'successful', 'ref', v_txn_ref),
        NOW()
    );

    -- Step 7: COMMIT
    COMMIT;

    SET p_out_payment_id = v_new_pay_id;
    SET p_status_code = 'SUCCESS';
    SET p_status_message = CONCAT('Payment recorded successfully. Txn Ref: ', v_txn_ref);
END$$

-- 2. sp_process_refund
-- Enforces refund rules and atomic updates
DROP PROCEDURE IF EXISTS sp_process_refund$$
CREATE PROCEDURE sp_process_refund(
    IN p_payment_id INT,
    IN p_refund_amount DECIMAL(10, 2),
    IN p_reason VARCHAR(255),
    IN p_user_id INT,
    OUT p_out_refund_id INT,
    OUT p_status_code VARCHAR(30),
    OUT p_status_message VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_orig_amount DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_existing_refunds DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_membership_id INT;
    DECLARE v_invoice_id INT;
    DECLARE v_new_ref_id INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_out_refund_id = 0;
        SET p_status_code = 'ERROR_ROLLBACK';
        SET p_status_message = 'Refund processing failed. Rolled back.';
    END;

    -- Validate payment
    SELECT amount, membership_id, invoice_id 
    INTO v_orig_amount, v_membership_id, v_invoice_id
    FROM payments 
    WHERE payment_id = p_payment_id AND payment_status = 'successful';

    IF v_orig_amount IS NULL OR v_orig_amount <= 0 THEN
        SET p_out_refund_id = 0;
        SET p_status_code = 'PAYMENT_INVALID';
        SET p_status_message = 'Original successful payment record not found.';
        LEAVE proc_label;
    END IF;

    -- Calculate existing completed/approved refunds
    SELECT COALESCE(SUM(refund_amount), 0.00) INTO v_existing_refunds
    FROM refunds
    WHERE payment_id = p_payment_id AND status IN ('completed', 'approved');

    IF (v_existing_refunds + p_refund_amount) > v_orig_amount THEN
        SET p_out_refund_id = 0;
        SET p_status_code = 'EXCEEDS_PAYMENT';
        SET p_status_message = CONCAT('Total refund would exceed original payment amount (₹', v_orig_amount, ').');
        LEAVE proc_label;
    END IF;

    START TRANSACTION;

    INSERT INTO refunds (
        payment_id, refund_amount, refund_date, reason, status
    ) VALUES (
        p_payment_id, p_refund_amount, CURDATE(), p_reason, 'completed'
    );
    SET v_new_ref_id = LAST_INSERT_ID();

    -- If this refund completes the full payment amount, cancel membership and update invoice
    IF (v_existing_refunds + p_refund_amount) >= v_orig_amount THEN
        UPDATE memberships SET status = 'cancelled' WHERE membership_id = v_membership_id;
        IF v_invoice_id IS NOT NULL THEN
            UPDATE invoices SET status = 'refunded' WHERE invoice_id = v_invoice_id;
        END IF;
    END IF;

    INSERT INTO audit_log (
        user_id, action, table_name, record_id, old_value, new_value, created_at
    ) VALUES (
        p_user_id, 'REFUND_COMPLETED', 'REFUNDS', v_new_ref_id,
        JSON_OBJECT('existing_refunds', v_existing_refunds),
        JSON_OBJECT('refund_id', v_new_ref_id, 'amount', p_refund_amount, 'payment_id', p_payment_id),
        NOW()
    );

    COMMIT;

    SET p_out_refund_id = v_new_ref_id;
    SET p_status_code = 'SUCCESS';
    SET p_status_message = 'Refund processed and completed.';
END$$

DELIMITER ;
