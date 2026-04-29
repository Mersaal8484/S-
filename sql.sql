-- ======================================================
-- نظام مبيعات الكهرباء المتكامل
-- Electricity Billing System - Complete Database
-- ======================================================
-- الإصدار: 1.0
-- تاريخ: 2025
-- قاعدة البيانات: MySQL 8.0+ / MariaDB 10.6+
-- ======================================================

-- ======================================================
-- القسم 1: إنشاء قاعدة البيانات
-- ======================================================

CREATE DATABASE IF NOT EXISTS electricity_billing_system
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE electricity_billing_system;

-- ======================================================
-- القسم 2: الجداول الأساسية (Core Tables)
-- ======================================================
-- الجداول التي لا تعتمد على جداول أخرى

-- 2.1 أنواع الاشتراك
CREATE TABLE subscription_type (
    type_id INT PRIMARY KEY AUTO_INCREMENT,
    name_ar VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.2 المشتركين
CREATE TABLE customer (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_number VARCHAR(50) UNIQUE NOT NULL,
    full_name_ar VARCHAR(150) NOT NULL,
    full_name_en VARCHAR(150),
    national_id VARCHAR(50) UNIQUE,
    mobile_phone VARCHAR(20) NOT NULL,
    phone2 VARCHAR(20),
    email VARCHAR(100),
    address TEXT,
    city VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    registration_date DATE DEFAULT (CURRENT_DATE),
    current_balance DECIMAL(12,2) DEFAULT 0,
    credit_limit DECIMAL(12,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.3 العقود
CREATE TABLE contract (
    contract_id INT PRIMARY KEY AUTO_INCREMENT,
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    type_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    contract_status ENUM('active', 'suspended', 'terminated', 'expired') DEFAULT 'active',
    connection_load DECIMAL(10,2) COMMENT 'الطلب الأقصى بالكيلوواط',
    deposit_amount DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (type_id) REFERENCES subscription_type(type_id) ON DELETE RESTRICT
);

-- 2.4 العدادات
CREATE TABLE meter (
    meter_id INT PRIMARY KEY AUTO_INCREMENT,
    meter_number VARCHAR(50) UNIQUE NOT NULL,
    contract_id INT NOT NULL,
    meter_model VARCHAR(100),
    meter_type ENUM('analog', 'digital', 'prepaid') DEFAULT 'analog',
    initial_reading DECIMAL(12,2) NOT NULL DEFAULT 0,
    installation_date DATE NOT NULL,
    last_reading_date DATE,
    meter_status ENUM('active', 'defective', 'replaced', 'removed') DEFAULT 'active',
    location_description VARCHAR(255),
    FOREIGN KEY (contract_id) REFERENCES contract(contract_id) ON DELETE RESTRICT
);

-- ======================================================
-- القسم 3: الجداول المرجعية (Reference Tables)
-- ======================================================

-- 3.1 قالب خطوط الفاتورة
CREATE TABLE invoice_line_template (
    template_id INT PRIMARY KEY AUTO_INCREMENT,
    type_id INT NOT NULL,
    line_order INT NOT NULL,
    line_name_ar VARCHAR(150) NOT NULL,
    line_name_en VARCHAR(150),
    calculation_type ENUM('fixed', 'percentage', 'tiered_kwh', 'single_rate_kwh', 'demand_charge', 'minimum_charge') NOT NULL,
    depends_on_template_id INT NULL,
    is_taxable BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (type_id) REFERENCES subscription_type(type_id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_template_id) REFERENCES invoice_line_template(template_id) ON DELETE SET NULL
);

-- 3.2 تفاصيل معادلات خطوط الفاتورة
CREATE TABLE invoice_line_formula_detail (
    detail_id INT PRIMARY KEY AUTO_INCREMENT,
    template_id INT NOT NULL,
    min_value DECIMAL(12,2) NULL,
    max_value DECIMAL(12,2) NULL,
    rate_or_amount DECIMAL(12,4) NOT NULL,
    is_rate_per_kwh BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (template_id) REFERENCES invoice_line_template(template_id) ON DELETE CASCADE
);

-- 3.3 فترات الفوترة
CREATE TABLE billing_period (
    period_id INT PRIMARY KEY AUTO_INCREMENT,
    period_name VARCHAR(100) NOT NULL,
    period_code VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reading_start_date DATE NOT NULL,
    reading_end_date DATE NOT NULL,
    billing_cycle ENUM('monthly', 'bi_monthly', 'quarterly', 'custom') DEFAULT 'monthly',
    status ENUM('draft', 'reading_open', 'reading_closed', 'billing_in_progress', 'billing_completed', 'closed') DEFAULT 'draft',
    created_by INT,
    approved_by INT,
    approved_at DATETIME,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_dates (start_date, end_date)
);

-- 3.4 إعدادات النظام
CREATE TABLE system_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value TEXT,
    setting_description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ======================================================
-- القسم 4: جداول الحركة والمعاملات (Transaction Tables)
-- ======================================================

-- 4.1 رفع القراءات (مع الموافقة)
CREATE TABLE meter_reading_submission (
    submission_id INT PRIMARY KEY AUTO_INCREMENT,
    period_id INT NOT NULL,
    meter_id INT NOT NULL,
    contract_id INT NOT NULL,
    customer_id INT NOT NULL,
    previous_reading DECIMAL(12,2) NOT NULL,
    submitted_reading DECIMAL(12,2) NOT NULL,
    consumption_kwh DECIMAL(12,2) GENERATED ALWAYS AS (submitted_reading - previous_reading) STORED,
    reading_date DATE NOT NULL,
    reading_source ENUM('manual_entry', 'mobile_app', 'sms', 'smart_meter', 'estimated') DEFAULT 'manual_entry',
    reader_name VARCHAR(100),
    reader_notes TEXT,
    approval_status ENUM('pending', 'approved', 'rejected', 'flagged_review') DEFAULT 'pending',
    reviewed_by INT,
    reviewed_at DATETIME,
    rejection_reason TEXT,
    approved_reading DECIMAL(12,2) NULL,
    final_consumption DECIMAL(12,2) NULL,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (period_id) REFERENCES billing_period(period_id) ON DELETE RESTRICT,
    FOREIGN KEY (meter_id) REFERENCES meter(meter_id) ON DELETE RESTRICT,
    FOREIGN KEY (contract_id) REFERENCES contract(contract_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT,
    UNIQUE KEY unique_period_meter (period_id, meter_id),
    INDEX idx_approval_status (approval_status),
    INDEX idx_period_status (period_id, approval_status)
);

-- 4.2 القراءات النهائية (المفوترة)
CREATE TABLE meter_reading (
    reading_id INT PRIMARY KEY AUTO_INCREMENT,
    meter_id INT NOT NULL,
    reading_date DATE NOT NULL,
    previous_reading DECIMAL(12,2) NOT NULL,
    current_reading DECIMAL(12,2) NOT NULL,
    consumption_kwh DECIMAL(12,2) GENERATED ALWAYS AS (current_reading - previous_reading) STORED,
    reading_source ENUM('manual', 'smart_meter', 'estimated') DEFAULT 'manual',
    reader_name VARCHAR(100),
    notes TEXT,
    is_billed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_meter_reading_date (meter_id, reading_date),
    FOREIGN KEY (meter_id) REFERENCES meter(meter_id) ON DELETE RESTRICT
);

-- 4.3 الفواتير
CREATE TABLE invoice (
    invoice_id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    contract_id INT NOT NULL,
    reading_id INT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    paid_amount DECIMAL(12,2) DEFAULT 0,
    remaining_amount DECIMAL(12,2) GENERATED ALWAYS AS (total_amount - paid_amount) STORED,
    invoice_status ENUM('draft', 'issued', 'paid', 'partially_paid', 'overdue', 'cancelled') DEFAULT 'issued',
    penalty_amount DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contract(contract_id) ON DELETE RESTRICT,
    FOREIGN KEY (reading_id) REFERENCES meter_reading(reading_id) ON DELETE SET NULL
);

-- 4.4 خطوط الفاتورة
CREATE TABLE invoice_line (
    line_id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    template_id INT NOT NULL,
    line_name_ar VARCHAR(150) NOT NULL,
    line_name_en VARCHAR(150),
    calculation_basis VARCHAR(255),
    amount DECIMAL(12,2) NOT NULL,
    line_order INT,
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES invoice_line_template(template_id)
);

-- 4.5 المدفوعات
CREATE TABLE payment (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    payment_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_id INT NOT NULL,
    customer_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    payment_method ENUM('cash', 'bank_transfer', 'card', 'online', 'cheque') NOT NULL,
    reference_number VARCHAR(100),
    cheque_number VARCHAR(50),
    bank_name VARCHAR(100),
    notes TEXT,
    recorded_by INT,
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT
);

-- 4.6 غرامات التأخير
CREATE TABLE penalty (
    penalty_id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    penalty_amount DECIMAL(10,2) NOT NULL,
    penalty_days INT NOT NULL,
    calculated_date DATE NOT NULL,
    is_paid BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id) ON DELETE CASCADE
);

-- ======================================================
-- القسم 5: الجداول المالية (Financial Tables)
-- ======================================================

-- 5.1 رصيد العميل
CREATE TABLE customer_balance (
    customer_id INT PRIMARY KEY,
    current_balance DECIMAL(12,2) DEFAULT 0,
    credit_limit DECIMAL(12,2) DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE
);

-- 5.2 سجل حركات الرصيد (Ledger)
CREATE TABLE balance_ledger (
    ledger_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    transaction_type ENUM('invoice_created', 'payment_received', 'adjustment', 'refund', 'penalty', 'write_off') NOT NULL,
    reference_id INT,
    debit DECIMAL(12,2) DEFAULT 0,
    credit DECIMAL(12,2) DEFAULT 0,
    balance_after DECIMAL(12,2) NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_by INT,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
    INDEX idx_customer_date (customer_id, transaction_date)
);

-- 5.3 التسويات المالية
CREATE TABLE financial_adjustment (
    adjustment_id INT PRIMARY KEY AUTO_INCREMENT,
    adjustment_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    invoice_id INT NULL,
    adjustment_type ENUM('debit', 'credit') NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    reason TEXT NOT NULL,
    approved_by INT,
    approval_date DATETIME,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id) ON DELETE SET NULL
);

-- 5.4 سجل تغيير العدادات
CREATE TABLE meter_change_log (
    change_id INT PRIMARY KEY AUTO_INCREMENT,
    contract_id INT NOT NULL,
    old_meter_id INT,
    new_meter_id INT NOT NULL,
    old_meter_reading DECIMAL(12,2),
    new_meter_initial_reading DECIMAL(12,2),
    change_reason ENUM('defective', 'upgrade', 'downgrade', 'damaged', 'theft', 'other'),
    change_date DATE NOT NULL,
    authorized_by INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contract(contract_id) ON DELETE RESTRICT,
    FOREIGN KEY (old_meter_id) REFERENCES meter(meter_id) ON DELETE SET NULL,
    FOREIGN KEY (new_meter_id) REFERENCES meter(meter_id) ON DELETE RESTRICT
);

-- ======================================================
-- القسم 6: نظام المعالجة (Processing/Queue)
-- ======================================================

-- 6.1 طابور معالجة الفواتير
CREATE TABLE billing_queue (
    queue_id INT PRIMARY KEY AUTO_INCREMENT,
    period_id INT NOT NULL,
    submission_id INT NOT NULL,
    contract_id INT NOT NULL,
    customer_id INT NOT NULL,
    queue_status ENUM('pending', 'processing', 'completed', 'failed', 'retry') DEFAULT 'pending',
    priority INT DEFAULT 5,
    retry_count INT DEFAULT 0,
    max_retry INT DEFAULT 3,
    invoice_id INT NULL,
    invoice_number VARCHAR(50) NULL,
    error_message TEXT,
    processing_started_at DATETIME,
    processing_completed_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (period_id) REFERENCES billing_period(period_id) ON DELETE RESTRICT,
    FOREIGN KEY (submission_id) REFERENCES meter_reading_submission(submission_id) ON DELETE RESTRICT,
    FOREIGN KEY (contract_id) REFERENCES contract(contract_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id) ON DELETE SET NULL,
    INDEX idx_status_priority (queue_status, priority, created_at),
    INDEX idx_period_status (period_id, queue_status)
);

-- 6.2 سجل معالجة الفواتير
CREATE TABLE billing_process_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    period_id INT NOT NULL,
    queue_id INT NULL,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    affected_records INT DEFAULT 0,
    processed_by VARCHAR(100) DEFAULT 'system',
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period (period_id),
    INDEX idx_created_at (created_at)
);

-- ======================================================
-- القسم 7: نظام الرسائل SMS
-- ======================================================

-- 7.1 مزود خدمة SMS
CREATE TABLE sms_provider (
    provider_id INT PRIMARY KEY AUTO_INCREMENT,
    provider_name VARCHAR(100) NOT NULL,
    api_url VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    api_secret VARCHAR(255) NULL,
    sender_name VARCHAR(50) NOT NULL,
    country_code VARCHAR(10) DEFAULT '966',
    is_active BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 1,
    cost_per_sms DECIMAL(8,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7.2 قوالب الرسائل
CREATE TABLE sms_template (
    template_id INT PRIMARY KEY AUTO_INCREMENT,
    template_type ENUM(
        'InvoiceCreated', 'PaymentReceived', 'BillDueSoon', 'BillOverdue',
        'MeterReadingReminder', 'ContractExpiryAlert', 'WelcomeMessage',
        'PaymentReminder', 'ReadingApproved', 'ReadingRejected', 'Custom'
    ) NOT NULL,
    title_ar VARCHAR(200),
    title_en VARCHAR(200),
    content_template_ar TEXT NOT NULL,
    content_template_en TEXT,
    variables_allowed TEXT,
    language CHAR(2) DEFAULT 'ar',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7.3 طابور الرسائل
CREATE TABLE sms_queue (
    sms_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    mobile_number VARCHAR(20) NOT NULL,
    template_id INT NULL,
    message_content TEXT NOT NULL,
    status ENUM('pending', 'sent', 'failed', 'retrying') DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    scheduled_time DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME NULL,
    provider_id INT NULL,
    cost DECIMAL(8,4) NULL,
    error_message TEXT,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES sms_template(template_id) ON DELETE SET NULL,
    FOREIGN KEY (provider_id) REFERENCES sms_provider(provider_id)
);

-- 7.4 سجل الرسائل
CREATE TABLE sms_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    sms_id INT NOT NULL,
    provider_response_code VARCHAR(50),
    provider_response_message TEXT,
    delivery_status VARCHAR(50),
    delivery_time DATETIME,
    FOREIGN KEY (sms_id) REFERENCES sms_queue(sms_id) ON DELETE CASCADE
);

-- ======================================================
-- القسم 8: المستخدمين والصلاحيات (Users & Roles)
-- ======================================================

-- 8.1 أدوار النظام
CREATE TABLE app_role (
    role_id INT PRIMARY KEY AUTO_INCREMENT,
    role_code VARCHAR(50) UNIQUE NOT NULL,
    role_name_ar VARCHAR(100) NOT NULL,
    role_name_en VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8.2 الصلاحيات
CREATE TABLE permission (
    permission_id INT PRIMARY KEY AUTO_INCREMENT,
    permission_code VARCHAR(100) UNIQUE NOT NULL,
    permission_name_ar VARCHAR(150) NOT NULL,
    permission_name_en VARCHAR(150),
    module VARCHAR(50),
    description TEXT
);

-- 8.3 صلاحيات كل دور
CREATE TABLE role_permission (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES app_role(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permission(permission_id) ON DELETE CASCADE
);

-- 8.4 المستخدمين الرئيسيين
CREATE TABLE system_user (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name_ar VARCHAR(150) NOT NULL,
    full_name_en VARCHAR(150),
    email VARCHAR(100),
    mobile_phone VARCHAR(20) NOT NULL,
    national_id VARCHAR(50) UNIQUE,
    hire_date DATE,
    user_status ENUM('active', 'suspended', 'terminated') DEFAULT 'active',
    last_login DATETIME,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 8.5 أدوار المستخدم
CREATE TABLE user_role (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    assigned_by INT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES system_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES app_role(role_id) ON DELETE CASCADE
);

-- 8.6 الكاشفين (قراء العدادات)
CREATE TABLE meter_reader (
    meter_reader_id INT PRIMARY KEY AUTO_INCREMENT,
    reader_code VARCHAR(50) UNIQUE NOT NULL,
    full_name_ar VARCHAR(150) NOT NULL,
    full_name_en VARCHAR(150),
    national_id VARCHAR(50) UNIQUE,
    mobile_phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    hire_date DATE NOT NULL,
    region VARCHAR(100),
    max_readings_per_day INT DEFAULT 100,
    reader_status ENUM('active', 'suspended', 'terminated') DEFAULT 'active',
    supervisor_id INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supervisor_id) REFERENCES meter_reader(meter_reader_id) ON DELETE SET NULL
);

-- 8.7 المتحصلين
CREATE TABLE collector (
    collector_id INT PRIMARY KEY AUTO_INCREMENT,
    collector_code VARCHAR(50) UNIQUE NOT NULL,
    full_name_ar VARCHAR(150) NOT NULL,
    full_name_en VARCHAR(150),
    national_id VARCHAR(50) UNIQUE,
    mobile_phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    hire_date DATE NOT NULL,
    collector_status ENUM('active', 'suspended', 'terminated') DEFAULT 'active',
    commission_percent DECIMAL(5,2) DEFAULT 0,
    manager_id INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manager_id) REFERENCES collector(collector_id) ON DELETE SET NULL
);

-- 8.8 ربط المستخدم بالكاشف
CREATE TABLE user_meter_reader_link (
    link_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    meter_reader_id INT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES system_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (meter_reader_id) REFERENCES meter_reader(meter_reader_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_reader (user_id, meter_reader_id)
);

-- 8.9 ربط المستخدم بالمتحصل
CREATE TABLE user_collector_link (
    link_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    collector_id INT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES system_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (collector_id) REFERENCES collector(collector_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_collector (user_id, collector_id)
);

-- 8.10 سجل رفع القراءات للتدقيق
CREATE TABLE meter_reading_audit (
    audit_id INT PRIMARY KEY AUTO_INCREMENT,
    submission_id INT NOT NULL,
    meter_reader_id INT NOT NULL,
    reading_date DATE NOT NULL,
    submitted_reading DECIMAL(12,2) NOT NULL,
    device_id VARCHAR(100),
    gps_location VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES meter_reading_submission(submission_id) ON DELETE CASCADE,
    FOREIGN KEY (meter_reader_id) REFERENCES meter_reader(meter_reader_id) ON DELETE RESTRICT
);

-- ======================================================
-- القسم 9: التحصيل والصناديق (Collection/Cashbox)
-- ======================================================

-- 9.1 الصناديق المالية للمتحصلين
CREATE TABLE collector_cashbox (
    cashbox_id INT PRIMARY KEY AUTO_INCREMENT,
    collector_id INT NOT NULL,
    cashbox_name VARCHAR(100) NOT NULL,
    opening_balance DECIMAL(12,2) DEFAULT 0,
    current_balance DECIMAL(12,2) DEFAULT 0,
    last_balance DECIMAL(12,2) DEFAULT 0,
    status ENUM('active', 'closed', 'suspended') DEFAULT 'active',
    opened_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_date DATETIME NULL,
    closed_by INT,
    notes TEXT,
    FOREIGN KEY (collector_id) REFERENCES collector(collector_id) ON DELETE RESTRICT
);

-- 9.2 حركات الصندوق
CREATE TABLE collector_cashbox_transaction (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    cashbox_id INT NOT NULL,
    transaction_type ENUM('collection', 'deposit_to_company', 'adjustment', 'opening_balance', 'closing_balance') NOT NULL,
    payment_id INT NULL,
    amount DECIMAL(12,2) NOT NULL,
    balance_before DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2) NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    reference_number VARCHAR(100),
    notes TEXT,
    created_by INT,
    FOREIGN KEY (cashbox_id) REFERENCES collector_cashbox(cashbox_id) ON DELETE RESTRICT,
    FOREIGN KEY (payment_id) REFERENCES payment(payment_id) ON DELETE SET NULL
);

-- 9.3 عمليات توريد الأموال
CREATE TABLE cash_deposit (
    deposit_id INT PRIMARY KEY AUTO_INCREMENT,
    deposit_number VARCHAR(50) UNIQUE NOT NULL,
    collector_id INT NOT NULL,
    cashbox_id INT NOT NULL,
    deposit_amount DECIMAL(12,2) NOT NULL,
    deposit_date DATE NOT NULL,
    deposit_time TIME NOT NULL,
    deposit_method ENUM('bank_transfer', 'cash_at_hq', 'cheque', 'online') NOT NULL,
    bank_name VARCHAR(100),
    bank_account VARCHAR(100),
    cheque_number VARCHAR(50),
    transaction_reference VARCHAR(100),
    status ENUM('pending', 'approved', 'rejected', 'under_review') DEFAULT 'pending',
    approved_by INT,
    approved_at DATETIME,
    rejection_reason TEXT,
    notes TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (collector_id) REFERENCES collector(collector_id) ON DELETE RESTRICT,
    FOREIGN KEY (cashbox_id) REFERENCES collector_cashbox(cashbox_id) ON DELETE RESTRICT
);

-- ======================================================
-- القسم 10: المحافظ الإلكترونية (E-Wallets)
-- ======================================================

-- 10.1 أنواع المحافظ الإلكترونية
CREATE TABLE ewallet_provider (
    provider_id INT PRIMARY KEY AUTO_INCREMENT,
    provider_name VARCHAR(100) NOT NULL,
    provider_code VARCHAR(50) UNIQUE NOT NULL,
    api_url VARCHAR(255),
    api_key VARCHAR(255),
    merchant_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    transaction_fee_percent DECIMAL(5,2) DEFAULT 0,
    settlement_days INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10.2 محافظ العملاء الإلكترونية
CREATE TABLE customer_ewallet (
    ewallet_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    provider_id INT NOT NULL,
    wallet_number VARCHAR(100) NOT NULL,
    wallet_owner_name VARCHAR(150),
    is_verified BOOLEAN DEFAULT FALSE,
    is_primary BOOLEAN DEFAULT FALSE,
    status ENUM('active', 'suspended', 'closed') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES ewallet_provider(provider_id) ON DELETE RESTRICT,
    UNIQUE KEY unique_customer_wallet (customer_id, provider_id, wallet_number)
);

-- 10.3 معاملات المحفظة الإلكترونية
CREATE TABLE ewallet_transaction (
    ewallet_trans_id INT PRIMARY KEY AUTO_INCREMENT,
    payment_id INT NOT NULL,
    ewallet_id INT NOT NULL,
    transaction_reference VARCHAR(100) UNIQUE NOT NULL,
    transaction_amount DECIMAL(12,2) NOT NULL,
    transaction_fee DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(12,2) GENERATED ALWAYS AS (transaction_amount - transaction_fee) STORED,
    transaction_status ENUM('pending', 'completed', 'failed', 'refunded', 'cancelled') DEFAULT 'pending',
    provider_response TEXT,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    settlement_date DATE,
    notes TEXT,
    FOREIGN KEY (payment_id) REFERENCES payment(payment_id) ON DELETE RESTRICT,
    FOREIGN KEY (ewallet_id) REFERENCES customer_ewallet(ewallet_id) ON DELETE RESTRICT,
    INDEX idx_status (transaction_status),
    INDEX idx_reference (transaction_reference)
);

-- ======================================================
-- القسم 11: خطوط السير (Routes)
-- ======================================================

-- 11.1 خط السير الرئيسي
CREATE TABLE route (
    route_id INT PRIMARY KEY AUTO_INCREMENT,
    route_code VARCHAR(50) UNIQUE NOT NULL,
    route_name_ar VARCHAR(150) NOT NULL,
    route_name_en VARCHAR(150),
    route_type ENUM('meter_reading', 'collection', 'both') NOT NULL,
    region VARCHAR(100),
    area_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11.2 عقود الخط
CREATE TABLE route_contract (
    route_contract_id INT PRIMARY KEY AUTO_INCREMENT,
    route_id INT NOT NULL,
    contract_id INT NOT NULL,
    stop_order INT NOT NULL,
    priority INT DEFAULT 5,
    estimated_reading DECIMAL(12,2) NULL,
    estimated_amount DECIMAL(12,2) NULL,
    notes TEXT,
    FOREIGN KEY (route_id) REFERENCES route(route_id) ON DELETE CASCADE,
    FOREIGN KEY (contract_id) REFERENCES contract(contract_id) ON DELETE CASCADE,
    UNIQUE KEY unique_route_contract (route_id, contract_id),
    INDEX idx_order (route_id, stop_order)
);

-- 11.3 إسناد الخط إلى موظف
CREATE TABLE route_assignment (
    assignment_id INT PRIMARY KEY AUTO_INCREMENT,
    route_id INT NOT NULL,
    assigned_to_type ENUM('meter_reader', 'collector', 'user') NOT NULL,
    assigned_to_id INT NOT NULL,
    assignment_date DATE NOT NULL,
    shift ENUM('morning', 'evening', 'full_day') DEFAULT 'full_day',
    status ENUM('planned', 'in_progress', 'completed', 'cancelled') DEFAULT 'planned',
    started_at DATETIME,
    completed_at DATETIME,
    notes TEXT,
    assigned_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES route(route_id) ON DELETE RESTRICT,
    INDEX idx_date (assignment_date, status),
    INDEX idx_assignee (assigned_to_type, assigned_to_id)
);

-- 11.4 تنفيذ العقود في الجولة
CREATE TABLE route_execution (
    execution_id INT PRIMARY KEY AUTO_INCREMENT,
    assignment_id INT NOT NULL,
    route_contract_id INT NOT NULL,
    stop_order INT NOT NULL,
    actual_reading DECIMAL(12,2) NULL,
    reading_submission_id INT NULL,
    actual_amount DECIMAL(12,2) NULL,
    payment_id INT NULL,
    execution_status ENUM('pending', 'done', 'skipped') DEFAULT 'pending',
    skip_reason TEXT,
    executed_at DATETIME,
    gps_latitude DECIMAL(10,8) NULL,
    gps_longitude DECIMAL(11,8) NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES route_assignment(assignment_id) ON DELETE CASCADE,
    FOREIGN KEY (route_contract_id) REFERENCES route_contract(route_contract_id) ON DELETE RESTRICT,
    FOREIGN KEY (reading_submission_id) REFERENCES meter_reading_submission(submission_id) ON DELETE SET NULL,
    FOREIGN KEY (payment_id) REFERENCES payment(payment_id) ON DELETE SET NULL,
    INDEX idx_assignment_status (assignment_id, execution_status)
);

-- 11.5 سجل تتبع الجولة
CREATE TABLE route_tracking_log (
    tracking_id INT PRIMARY KEY AUTO_INCREMENT,
    assignment_id INT NOT NULL,
    user_id INT NOT NULL,
    action_type ENUM('start', 'complete', 'done_contract', 'skip_contract') NOT NULL,
    route_contract_id INT NULL,
    gps_latitude DECIMAL(10,8) NULL,
    gps_longitude DECIMAL(11,8) NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES route_assignment(assignment_id) ON DELETE CASCADE,
    INDEX idx_assignment (assignment_id)
);

-- ======================================================
-- القسم 12: الفهارس (Indexes)
-- ======================================================

CREATE INDEX idx_customer_mobile ON customer(mobile_phone);
CREATE INDEX idx_customer_national ON customer(national_id);
CREATE INDEX idx_contract_customer ON contract(customer_id);
CREATE INDEX idx_contract_status ON contract(contract_status);
CREATE INDEX idx_meter_contract ON meter(contract_id);
CREATE INDEX idx_meter_status ON meter(meter_status);
CREATE INDEX idx_reading_meter_date ON meter_reading(meter_id, reading_date);
CREATE INDEX idx_reading_submission_period ON meter_reading_submission(period_id, approval_status);
CREATE INDEX idx_invoice_contract_status ON invoice(contract_id, invoice_status);
CREATE INDEX idx_invoice_due_date ON invoice(due_date);
CREATE INDEX idx_payment_invoice ON payment(invoice_id);
CREATE INDEX idx_payment_date ON payment(payment_date);
CREATE INDEX idx_ledger_customer_date ON balance_ledger(customer_id, transaction_date);
CREATE INDEX idx_adjustment_customer ON financial_adjustment(customer_id, is_approved);
CREATE INDEX idx_penalty_invoice ON penalty(invoice_id, is_paid);
CREATE INDEX idx_sms_queue_status ON sms_queue(status, scheduled_time);
CREATE INDEX idx_sms_queue_customer ON sms_queue(customer_id);
CREATE INDEX idx_queue_priority_status ON billing_queue(priority, queue_status, created_at);
CREATE INDEX idx_queue_period_status ON billing_queue(period_id, queue_status);

-- ======================================================
-- القسم 13: البيانات الافتراضية (Seed Data)
-- ======================================================

-- 13.1 أنواع الاشتراك
INSERT INTO subscription_type (name_ar, name_en, description) VALUES
('سكني', 'Residential', 'الاستخدام المنزلي'),
('تجاري', 'Commercial', 'المحلات والمكاتب التجارية'),
('صناعي', 'Industrial', 'المصانع والمنشآت الصناعية'),
('زراعي', 'Agricultural', 'المزارع والآبار الزراعية'),
('حكومي', 'Government', 'الدوائر الحكومية');

-- 13.2 قوالب خطوط الفاتورة للسكني
INSERT INTO invoice_line_template (type_id, line_order, line_name_ar, line_name_en, calculation_type, is_taxable) VALUES
(1, 1, 'رسم خدمة ثابت', 'Fixed Service Fee', 'fixed', FALSE),
(1, 2, 'استهلاك كهرباء', 'Electricity Consumption', 'tiered_kwh', FALSE),
(1, 3, 'رسم بلدي', 'Municipality Fee', 'percentage', FALSE),
(1, 4, 'ضريبة القيمة المضافة', 'Value Added Tax', 'percentage', FALSE);

-- 13.3 تفاصيل شرائح الاستهلاك للسكني
INSERT INTO invoice_line_formula_detail (template_id, min_value, max_value, rate_or_amount, is_rate_per_kwh) VALUES
(2, 0, 100, 0.08, TRUE),
(2, 101, 300, 0.12, TRUE),
(2, 301, 600, 0.18, TRUE),
(2, 601, NULL, 0.25, TRUE);

-- 13.4 تفاصيل النسب المئوية
INSERT INTO invoice_line_formula_detail (template_id, rate_or_amount, is_rate_per_kwh) VALUES
(3, 5.00, FALSE),
(4, 16.00, FALSE);

-- 13.5 قوالب الرسائل SMS
INSERT INTO sms_template (template_type, title_ar, content_template_ar, variables_allowed) VALUES
('WelcomeMessage', 'رسالة ترحيب', 'مرحباً {customer_name}، تم تسجيل اشتراكك بنجاح في نظام الكهرباء. رقم مشتركك: {customer_number}', 'customer_name,customer_number'),
('InvoiceCreated', 'فاتورة جديدة', 'عزيزي {customer_name}، تم إصدار فاتورة كهرباء رقم {invoice_number} بقيمة {amount} دينار، تاريخ الاستحقاق {due_date}', 'customer_name,invoice_number,amount,due_date'),
('PaymentReceived', 'تأكيد دفع', 'شكراً {customer_name}، تم استلام مبلغ {amount} دينار عن الفاتورة {invoice_number}. رصيدك المتبقي: {remaining_balance} دينار', 'customer_name,invoice_number,amount,remaining_balance'),
('BillDueSoon', 'اقتراب موعد السداد', 'تذكير: فاتورة الكهرباء رقم {invoice_number} تستحق بعد {days_left} يوماً بقيمة {amount} دينار', 'customer_name,invoice_number,days_left,amount'),
('BillOverdue', 'فاتورة متأخرة', 'تنبيه: فاتورة الكهرباء رقم {invoice_number} متأخرة {days_overdue} أيام. الرجاء دفع {amount} دينار + غرامة {penalty} دينار', 'customer_name,invoice_number,days_overdue,amount,penalty'),
('MeterReadingReminder', 'تذكير بقراءة العداد', 'عزيزي {customer_name}، الرجاء إرسال قراءة عداد الكهرباء (رقم {meter_number}) قبل تاريخ {due_date}', 'customer_name,meter_number,due_date'),
('ReadingApproved', 'تم اعتماد القراءة', 'عزيزي {customer_name}، تم اعتماد قراءة عدادك بتاريخ {reading_date} بقيمة {reading} كيلوواط', 'customer_name,reading_date,reading'),
('ReadingRejected', 'تم رفض القراءة', 'عزيزي {customer_name}، لم يتم اعتماد قراءة عدادك بسبب: {reason}. الرجاء إعادة الإرسال', 'customer_name,reason');

-- 13.6 إعدادات النظام
INSERT INTO system_settings (setting_key, setting_value, setting_description) VALUES
('company_name', 'شركة توزيع الكهرباء', 'اسم الشركة'),
('company_logo', '', 'شعار الشركة'),
('vat_percentage', '16', 'نسبة الضريبة المضافة'),
('late_penalty_daily_percent', '0.5', 'غرامة تأخير يومية %'),
('max_penalty_percent', '10', 'الحد الأقصى للغرامة %'),
('sms_auto_send', '1', 'تفعيل الإرسال التلقائي للرسائل 1/0'),
('default_language', 'ar', 'اللغة الافتراضية'),
('billing_queue_batch_size', '50', 'عدد الفواتير التي تتم معالجتها في كل دورة'),
('auto_approve_threshold', '500', 'الحد الأقصى للفرق للموافقة التلقائية على القراءات');

-- 13.7 مزود SMS افتراضي
INSERT INTO sms_provider (provider_name, api_url, api_key, sender_name, is_active, priority) VALUES
('LocalSMSGateway', 'https://api.smsgateway.com/v1/send', 'test_api_key_123', 'ElectricCo', TRUE, 1);

-- 13.8 الأدوار الأساسية
INSERT INTO app_role (role_code, role_name_ar, role_name_en, description) VALUES
('ADMIN', 'مدير النظام', 'System Administrator', 'صلاحيات كاملة على النظام'),
('ACCOUNTANT', 'محاسب', 'Accountant', 'إدارة الفواتير والمدفوعات والتقارير المالية'),
('METER_READER', 'كاشف', 'Meter Reader', 'رفع قراءات العدادات فقط'),
('COLLECTOR', 'متحصل', 'Collector', 'تحصيل المدفوعات وإدارة الصندوق'),
('READER_COLLECTOR', 'كاشف ومتحصل', 'Reader & Collector', 'صلاحيات الكاشف والمتحصل معاً'),
('REVIEWER', 'مراجع قراءات', 'Reading Reviewer', 'الموافقة على القراءات المرفوعة'),
('CUSTOMER_SERVICE', 'خدمة عملاء', 'Customer Service', 'إدارة بيانات العملاء والعقود');

-- 13.9 الصلاحيات
INSERT INTO permission (permission_code, permission_name_ar, permission_name_en, module, description) VALUES
-- إدارة العملاء
('CUSTOMER_VIEW', 'عرض العملاء', 'View Customers', 'customer', 'عرض قائمة وتفاصيل العملاء'),
('CUSTOMER_CREATE', 'إضافة عميل', 'Create Customer', 'customer', 'إضافة عملاء جدد'),
('CUSTOMER_EDIT', 'تعديل عميل', 'Edit Customer', 'customer', 'تعديل بيانات العملاء'),
('CUSTOMER_DELETE', 'حذف عميل', 'Delete Customer', 'customer', 'حذف عملاء'),
-- إدارة العقود والعدادات
('CONTRACT_VIEW', 'عرض العقود', 'View Contracts', 'contract', 'عرض العقود'),
('CONTRACT_CREATE', 'إضافة عقد', 'Create Contract', 'contract', 'إنشاء عقود جديدة'),
('CONTRACT_EDIT', 'تعديل عقد', 'Edit Contract', 'contract', 'تعديل العقود'),
('METER_VIEW', 'عرض العدادات', 'View Meters', 'meter', 'عرض العدادات'),
('METER_CREATE', 'إضافة عداد', 'Create Meter', 'meter', 'إضافة عدادات جديدة'),
('METER_REPLACE', 'تغيير عداد', 'Replace Meter', 'meter', 'استبدال عدادات'),
-- قراءات العدادات
('READING_SUBMIT', 'رفع قراءة', 'Submit Reading', 'reading', 'رفع قراءات العدادات'),
('READING_VIEW', 'عرض القراءات', 'View Readings', 'reading', 'عرض القراءات المرفوعة'),
('READING_APPROVE', 'الموافقة على القراءات', 'Approve Reading', 'reading', 'الموافقة أو رفض القراءات'),
('READING_REJECT', 'رفض القراءة', 'Reject Reading', 'reading', 'رفض القراءات مع سبب'),
-- الفواتير
('INVOICE_VIEW', 'عرض الفواتير', 'View Invoices', 'invoice', 'عرض الفواتير'),
('INVOICE_GENERATE', 'إصدار فاتورة', 'Generate Invoice', 'invoice', 'إصدار فواتير جديدة'),
('INVOICE_CANCEL', 'إلغاء فاتورة', 'Cancel Invoice', 'invoice', 'إلغاء فواتير'),
('INVOICE_ADJUST', 'تسوية فاتورة', 'Adjust Invoice', 'invoice', 'تسوية مالية على فاتورة'),
-- المدفوعات
('PAYMENT_RECEIVE', 'تسجيل دفعة', 'Receive Payment', 'payment', 'تسجيل مدفوعات من العملاء'),
('PAYMENT_VIEW', 'عرض المدفوعات', 'View Payments', 'payment', 'عرض سجل المدفوعات'),
('PAYMENT_REFUND', 'استرداد دفعة', 'Refund Payment', 'payment', 'استرداد مدفوعات'),
('COLLECTOR_DEPOSIT', 'توريد أموال', 'Deposit Cash', 'collector', 'توريد أموال من المتحصل للشركة'),
('CASHBOX_VIEW', 'عرض الصندوق', 'View Cashbox', 'collector', 'عرض حركات الصندوق'),
-- التقارير
('REPORT_VIEW', 'عرض التقارير', 'View Reports', 'report', 'عرض جميع التقارير'),
('REPORT_EXPORT', 'تصدير التقارير', 'Export Reports', 'report', 'تصدير التقارير بصيغ مختلفة'),
-- إدارة النظام
('USER_MANAGE', 'إدارة المستخدمين', 'Manage Users', 'admin', 'إضافة وتعديل المستخدمين'),
('ROLE_MANAGE', 'إدارة الأدوار', 'Manage Roles', 'admin', 'إدارة الأدوار والصلاحيات'),
('SYSTEM_SETTINGS', 'إعدادات النظام', 'System Settings', 'admin', 'تعديل إعدادات النظام');

-- 13.10 تعيين الصلاحيات لكل دور
INSERT INTO role_permission (role_id, permission_id)
SELECT 1, permission_id FROM permission;

INSERT INTO role_permission (role_id, permission_id)
SELECT 2, permission_id FROM permission 
WHERE permission_code IN (
    'CUSTOMER_VIEW', 'CONTRACT_VIEW', 'METER_VIEW', 'INVOICE_VIEW', 'INVOICE_GENERATE',
    'INVOICE_CANCEL', 'INVOICE_ADJUST', 'PAYMENT_RECEIVE', 'PAYMENT_VIEW', 'PAYMENT_REFUND',
    'REPORT_VIEW', 'REPORT_EXPORT'
);

INSERT INTO role_permission (role_id, permission_id)
SELECT 3, permission_id FROM permission 
WHERE permission_code IN ('READING_SUBMIT', 'READING_VIEW', 'METER_VIEW');

INSERT INTO role_permission (role_id, permission_id)
SELECT 4, permission_id FROM permission 
WHERE permission_code IN (
    'CUSTOMER_VIEW', 'INVOICE_VIEW', 'PAYMENT_RECEIVE', 'PAYMENT_VIEW',
    'COLLECTOR_DEPOSIT', 'CASHBOX_VIEW'
);

INSERT INTO role_permission (role_id, permission_id)
SELECT 5, permission_id FROM permission 
WHERE permission_code IN (
    'READING_SUBMIT', 'READING_VIEW', 'METER_VIEW',
    'CUSTOMER_VIEW', 'INVOICE_VIEW', 'PAYMENT_RECEIVE', 'PAYMENT_VIEW',
    'COLLECTOR_DEPOSIT', 'CASHBOX_VIEW', 'REPORT_VIEW'
);

INSERT INTO role_permission (role_id, permission_id)
SELECT 6, permission_id FROM permission 
WHERE permission_code IN ('READING_VIEW', 'READING_APPROVE', 'READING_REJECT', 'METER_VIEW');

INSERT INTO role_permission (role_id, permission_id)
SELECT 7, permission_id FROM permission 
WHERE permission_code IN (
    'CUSTOMER_VIEW', 'CUSTOMER_CREATE', 'CUSTOMER_EDIT',
    'CONTRACT_VIEW', 'METER_VIEW', 'INVOICE_VIEW', 'READING_VIEW'
);

-- 13.11 محافظ إلكترونية
INSERT INTO ewallet_provider (provider_name, provider_code, transaction_fee_percent, is_active) VALUES
('STC Pay', 'STCPAY', 0.5, TRUE),
('UrPay', 'URPAY', 0.75, TRUE),
('Apple Pay', 'APPLEPAY', 0.3, TRUE),
('Google Pay', 'GOOGLEPAY', 0.3, TRUE),
('مدى', 'MADA', 0.2, TRUE);

-- 13.12 مستخدم افتراضي (admin/admin123)
INSERT INTO system_user (username, password_hash, full_name_ar, email, mobile_phone, user_status) VALUES
('admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'مدير النظام', 'admin@electric.co', '0555123456', 'active');

INSERT INTO user_role (user_id, role_id) VALUES (1, 1);

-- ======================================================
-- القسم 14: الإجراءات المخزنة (Stored Procedures)
-- ======================================================

DELIMITER $$

-- 14.1 تحديث رصيد العميل
CREATE PROCEDURE UpdateCustomerBalance(
    IN p_customer_id INT,
    IN p_reference_id INT,
    IN p_transaction_type VARCHAR(50),
    IN p_debit DECIMAL(12,2),
    IN p_credit DECIMAL(12,2),
    IN p_notes TEXT
)
BEGIN
    DECLARE v_current_balance DECIMAL(12,2);
    DECLARE v_new_balance DECIMAL(12,2);
    
    SELECT current_balance INTO v_current_balance 
    FROM customer 
    WHERE customer_id = p_customer_id;
    
    SET v_new_balance = v_current_balance + p_debit - p_credit;
    
    UPDATE customer SET current_balance = v_new_balance 
    WHERE customer_id = p_customer_id;
    
    INSERT INTO customer_balance (customer_id, current_balance, last_updated)
    VALUES (p_customer_id, v_new_balance, NOW())
    ON DUPLICATE KEY UPDATE 
        current_balance = v_new_balance, 
        last_updated = NOW();
    
    INSERT INTO balance_ledger (
        customer_id, transaction_type, reference_id, 
        debit, credit, balance_after, notes
    ) VALUES (
        p_customer_id, p_transaction_type, p_reference_id,
        p_debit, p_credit, v_new_balance, p_notes
    );
    
END$$

-- 14.2 إضافة مشترك جديد
CREATE PROCEDURE AddNewCustomer(
    IN p_full_name_ar VARCHAR(150),
    IN p_mobile_phone VARCHAR(20),
    IN p_national_id VARCHAR(50),
    IN p_address TEXT,
    IN p_city VARCHAR(50),
    IN p_credit_limit DECIMAL(12,2),
    OUT p_customer_id INT
)
BEGIN
    DECLARE v_customer_number VARCHAR(50);
    
    SET v_customer_number = CONCAT('CUST-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 10000), 4, '0'));
    
    INSERT INTO customer (
        customer_number, full_name_ar, mobile_phone, national_id, 
        address, city, credit_limit, registration_date
    ) VALUES (
        v_customer_number, p_full_name_ar, p_mobile_phone, p_national_id,
        p_address, p_city, p_credit_limit, CURDATE()
    );
    
    SET p_customer_id = LAST_INSERT_ID();
    
    INSERT INTO customer_balance (customer_id, current_balance, credit_limit)
    VALUES (p_customer_id, 0, p_credit_limit);
    
    UPDATE customer SET current_balance = 0 WHERE customer_id = p_customer_id;
    
    INSERT INTO sms_queue (customer_id, mobile_number, template_id, message_content, scheduled_time)
    SELECT p_customer_id, p_mobile_phone, template_id, 
           REPLACE(REPLACE(content_template_ar, '{customer_name}', p_full_name_ar), '{customer_number}', v_customer_number),
           NOW()
    FROM sms_template
    WHERE template_type = 'WelcomeMessage' LIMIT 1;
    
END$$

-- 14.3 إضافة عداد لعقد
CREATE PROCEDURE AddMeterToContract(
    IN p_contract_number VARCHAR(50),
    IN p_meter_number VARCHAR(50),
    IN p_initial_reading DECIMAL(12,2),
    IN p_installation_date DATE,
    IN p_meter_model VARCHAR(100),
    OUT p_meter_id INT
)
BEGIN
    DECLARE v_contract_id INT;
    
    SELECT contract_id INTO v_contract_id 
    FROM contract 
    WHERE contract_number = p_contract_number AND contract_status = 'active';
    
    IF v_contract_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Contract not found or not active';
    END IF;
    
    INSERT INTO meter (
        meter_number, contract_id, initial_reading, installation_date, 
        meter_model, meter_status
    ) VALUES (
        p_meter_number, v_contract_id, p_initial_reading, p_installation_date,
        p_meter_model, 'active'
    );
    
    SET p_meter_id = LAST_INSERT_ID();
    
END$$

-- 14.4 تغيير عداد
CREATE PROCEDURE ReplaceMeter(
    IN p_contract_number VARCHAR(50),
    IN p_old_meter_number VARCHAR(50),
    IN p_new_meter_number VARCHAR(50),
    IN p_old_meter_reading DECIMAL(12,2),
    IN p_new_meter_initial_reading DECIMAL(12,2),
    IN p_change_reason VARCHAR(50),
    IN p_notes TEXT
)
BEGIN
    DECLARE v_contract_id INT;
    DECLARE v_old_meter_id INT;
    DECLARE v_new_meter_id INT;
    
    SELECT contract_id INTO v_contract_id 
    FROM contract 
    WHERE contract_number = p_contract_number;
    
    IF v_contract_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Contract not found';
    END IF;
    
    SELECT meter_id INTO v_old_meter_id 
    FROM meter 
    WHERE meter_number = p_old_meter_number AND contract_id = v_contract_id;
    
    IF v_old_meter_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Old meter not found';
    END IF;
    
    UPDATE meter SET meter_status = 'replaced', last_reading_date = CURDATE()
    WHERE meter_id = v_old_meter_id;
    
    INSERT INTO meter (meter_number, contract_id, initial_reading, installation_date, meter_status)
    VALUES (p_new_meter_number, v_contract_id, p_new_meter_initial_reading, CURDATE(), 'active');
    
    SET v_new_meter_id = LAST_INSERT_ID();
    
    INSERT INTO meter_change_log (
        contract_id, old_meter_id, new_meter_id, 
        old_meter_reading, new_meter_initial_reading,
        change_reason, change_date, notes
    ) VALUES (
        v_contract_id, v_old_meter_id, v_new_meter_id,
        p_old_meter_reading, p_new_meter_initial_reading,
        p_change_reason, CURDATE(), p_notes
    );
    
END$$

-- 14.5 إنشاء فترة فوترة
CREATE PROCEDURE CreateBillingPeriod(
    IN p_period_name VARCHAR(100),
    IN p_start_date DATE,
    IN p_end_date DATE,
    IN p_reading_start DATE,
    IN p_reading_end DATE,
    IN p_billing_cycle VARCHAR(20),
    IN p_created_by INT,
    OUT p_period_id INT
)
BEGIN
    DECLARE v_period_code VARCHAR(50);
    
    SET v_period_code = CONCAT(DATE_FORMAT(p_start_date, '%Y%m'), '_', UPPER(LEFT(p_billing_cycle, 2)));
    
    INSERT INTO billing_period (
        period_name, period_code, start_date, end_date,
        reading_start_date, reading_end_date, billing_cycle,
        status, created_by
    ) VALUES (
        p_period_name, v_period_code, p_start_date, p_end_date,
        p_reading_start, p_reading_end, p_billing_cycle,
        'reading_open', p_created_by
    );
    
    SET p_period_id = LAST_INSERT_ID();
    
    INSERT INTO billing_process_log (period_id, action, status, message)
    VALUES (p_period_id, 'create_period', 'success', CONCAT('تم إنشاء فترة فوترة: ', p_period_name));
    
END$$

-- 14.6 رفع قراءة عداد
CREATE PROCEDURE SubmitMeterReading(
    IN p_meter_number VARCHAR(50),
    IN p_reading_date DATE,
    IN p_current_reading DECIMAL(12,2),
    IN p_reader_name VARCHAR(100),
    IN p_reading_source VARCHAR(50),
    IN p_notes TEXT,
    OUT p_submission_id INT
)
BEGIN
    DECLARE v_meter_id INT;
    DECLARE v_contract_id INT;
    DECLARE v_customer_id INT;
    DECLARE v_previous_reading DECIMAL(12,2);
    DECLARE v_period_id INT;
    
    SELECT meter_id, contract_id, initial_reading 
    INTO v_meter_id, v_contract_id, v_previous_reading
    FROM meter 
    WHERE meter_number = p_meter_number AND meter_status = 'active';
    
    IF v_meter_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'العداد غير موجود أو غير نشط';
    END IF;
    
    SELECT customer_id INTO v_customer_id
    FROM contract WHERE contract_id = v_contract_id AND contract_status = 'active';
    
    SELECT current_reading INTO v_previous_reading
    FROM meter_reading
    WHERE meter_id = v_meter_id AND is_billed = TRUE
    ORDER BY reading_date DESC LIMIT 1;
    
    IF v_previous_reading IS NULL THEN
        SELECT initial_reading INTO v_previous_reading FROM meter WHERE meter_id = v_meter_id;
    END IF;
    
    IF p_current_reading <= v_previous_reading THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'القراءة الحالية يجب أن تكون أكبر من القراءة السابقة';
    END IF;
    
    SELECT period_id INTO v_period_id
    FROM billing_period
    WHERE status = 'reading_open'
      AND p_reading_date BETWEEN reading_start_date AND reading_end_date
    LIMIT 1;
    
    IF v_period_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'لا توجد فترة فوترة مفتوحة لهذا التاريخ';
    END IF;
    
    INSERT INTO meter_reading_submission (
        period_id, meter_id, contract_id, customer_id,
        previous_reading, submitted_reading, reading_date,
        reading_source, reader_name, reader_notes, approval_status
    ) VALUES (
        v_period_id, v_meter_id, v_contract_id, v_customer_id,
        v_previous_reading, p_current_reading, p_reading_date,
        p_reading_source, p_reader_name, p_notes, 'pending'
    );
    
    SET p_submission_id = LAST_INSERT_ID();
    
    INSERT INTO billing_queue (period_id, submission_id, contract_id, customer_id, queue_status)
    VALUES (v_period_id, p_submission_id, v_contract_id, v_customer_id, 'pending');
    
END$$

-- 14.7 الموافقة على القراءة
CREATE PROCEDURE ApproveMeterReading(
    IN p_submission_id INT,
    IN p_reviewed_by INT,
    IN p_approved_reading DECIMAL(12,2),
    IN p_rejection_reason TEXT
)
BEGIN
    DECLARE v_period_id INT;
    
    SELECT period_id INTO v_period_id
    FROM meter_reading_submission
    WHERE submission_id = p_submission_id AND approval_status = 'pending';
    
    IF v_period_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'القراءة غير موجودة أو تمت مراجعتها مسبقاً';
    END IF;
    
    IF p_approved_reading IS NULL THEN
        UPDATE meter_reading_submission
        SET approval_status = 'rejected',
            reviewed_by = p_reviewed_by,
            reviewed_at = NOW(),
            rejection_reason = p_rejection_reason
        WHERE submission_id = p_submission_id;
        
        UPDATE billing_queue
        SET queue_status = 'failed', error_message = p_rejection_reason
        WHERE submission_id = p_submission_id;
        
        INSERT INTO billing_process_log (period_id, action, status, message)
        VALUES (v_period_id, 'approve_reading', 'failed', CONCAT('تم رفض القراءة: ', p_rejection_reason));
    ELSE
        UPDATE meter_reading_submission
        SET approval_status = 'approved',
            reviewed_by = p_reviewed_by,
            reviewed_at = NOW(),
            approved_reading = p_approved_reading,
            final_consumption = p_approved_reading - previous_reading
        WHERE submission_id = p_submission_id;
        
        UPDATE billing_queue
        SET queue_status = 'pending', priority = 1
        WHERE submission_id = p_submission_id;
        
        INSERT INTO billing_process_log (period_id, action, status, message)
        VALUES (v_period_id, 'approve_reading', 'success', CONCAT('تم اعتماد القراءة رقم ', p_submission_id));
    END IF;
    
END$$

-- 14.8 إنشاء فاتورة من قراءة معتمدة
CREATE PROCEDURE GenerateInvoiceFromApprovedReading(
    IN p_submission_id INT,
    OUT p_invoice_id INT,
    OUT p_invoice_number VARCHAR(50),
    OUT p_total_amount DECIMAL(12,2)
)
BEGIN
    DECLARE v_contract_id INT;
    DECLARE v_customer_id INT;
    DECLARE v_consumption DECIMAL(12,2);
    DECLARE v_reading_date DATE;
    DECLARE v_type_id INT;
    DECLARE v_template_id INT;
    DECLARE v_line_amount DECIMAL(12,2);
    DECLARE v_line_name VARCHAR(150);
    DECLARE v_calc_type VARCHAR(50);
    DECLARE v_done BOOLEAN DEFAULT FALSE;
    DECLARE v_fixed_total DECIMAL(12,2) DEFAULT 0;
    DECLARE v_consumption_total DECIMAL(12,2) DEFAULT 0;
    DECLARE v_rate DECIMAL(12,4);
    
    DECLARE cur_templates CURSOR FOR 
        SELECT lt.template_id, lt.line_name_ar, lt.calculation_type
        FROM invoice_line_template lt
        JOIN contract c ON lt.type_id = c.type_id
        WHERE c.contract_id = v_contract_id AND lt.is_active = TRUE
        ORDER BY lt.line_order;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;
    
    SELECT mrs.contract_id, mrs.customer_id, mrs.final_consumption, mrs.reading_date, c.type_id
    INTO v_contract_id, v_customer_id, v_consumption, v_reading_date, v_type_id
    FROM meter_reading_submission mrs
    JOIN contract c ON mrs.contract_id = c.contract_id
    WHERE mrs.submission_id = p_submission_id AND mrs.approval_status = 'approved';
    
    IF v_contract_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'القراءة غير معتمدة';
    END IF;
    
    SET p_invoice_number = CONCAT('INV-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(p_submission_id, 6, '0'));
    
    INSERT INTO invoice (invoice_number, contract_id, issue_date, due_date, total_amount)
    VALUES (p_invoice_number, v_contract_id, v_reading_date, DATE_ADD(v_reading_date, INTERVAL 15 DAY), 0);
    
    SET p_invoice_id = LAST_INSERT_ID();
    SET p_total_amount = 0;
    
    OPEN cur_templates;
    
    read_loop: LOOP
        FETCH cur_templates INTO v_template_id, v_line_name, v_calc_type;
        IF v_done THEN
            LEAVE read_loop;
        END IF;
        
        SET v_line_amount = 0;
        
        CASE v_calc_type
            WHEN 'fixed' THEN
                SELECT rate_or_amount INTO v_line_amount
                FROM invoice_line_formula_detail
                WHERE template_id = v_template_id LIMIT 1;
                SET v_fixed_total = v_fixed_total + v_line_amount;
                
            WHEN 'single_rate_kwh' THEN
                SELECT rate_or_amount INTO v_rate
                FROM invoice_line_formula_detail
                WHERE template_id = v_template_id AND is_rate_per_kwh = TRUE LIMIT 1;
                SET v_line_amount = v_consumption * v_rate;
                SET v_consumption_total = v_line_amount;
                
            WHEN 'tiered_kwh' THEN
                SELECT SUM(
                    LEAST(GREATEST(v_consumption - COALESCE(min_value, 0) + 1, 0), 
                          COALESCE(max_value - min_value + 1, v_consumption)) * rate_or_amount
                ) INTO v_line_amount
                FROM invoice_line_formula_detail
                WHERE template_id = v_template_id AND is_rate_per_kwh = TRUE;
                SET v_consumption_total = COALESCE(v_line_amount, v_consumption * 0.12);
                
            WHEN 'percentage' THEN
                SELECT rate_or_amount INTO v_rate
                FROM invoice_line_formula_detail
                WHERE template_id = v_template_id LIMIT 1;
                SET v_line_amount = ((v_fixed_total + v_consumption_total) * v_rate) / 100;
        END CASE;
        
        IF v_line_amount > 0 THEN
            INSERT INTO invoice_line (invoice_id, template_id, line_name_ar, amount)
            VALUES (p_invoice_id, v_template_id, v_line_name, v_line_amount);
            SET p_total_amount = p_total_amount + v_line_amount;
        END IF;
        
    END LOOP;
    
    CLOSE cur_templates;
    
    UPDATE invoice SET total_amount = p_total_amount WHERE invoice_id = p_invoice_id;
    
    CALL UpdateCustomerBalance(v_customer_id, p_invoice_id, 'invoice_created', p_total_amount, 0, 
                               CONCAT('فاتورة ', p_invoice_number));
    
END$$

-- 14.9 معالجة عنصر واحد من طابور الفوترة
CREATE PROCEDURE ProcessSingleBillingQueue(
    IN p_queue_id INT,
    OUT p_invoice_id INT,
    OUT p_invoice_number VARCHAR(50)
)
BEGIN
    DECLARE v_period_id INT;
    DECLARE v_submission_id INT;
    DECLARE v_error_msg TEXT DEFAULT NULL;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
        
        UPDATE billing_queue
        SET queue_status = 'failed',
            retry_count = retry_count + 1,
            error_message = v_error_msg,
            updated_at = NOW()
        WHERE queue_id = p_queue_id;
        
        SET p_invoice_id = NULL;
        SET p_invoice_number = NULL;
    END;
    
    START TRANSACTION;
    
    SELECT period_id, submission_id INTO v_period_id, v_submission_id
    FROM billing_queue
    WHERE queue_id = p_queue_id AND queue_status IN ('pending', 'retry')
    FOR UPDATE;
    
    IF v_period_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Queue item not found';
    END IF;
    
    UPDATE billing_queue
    SET queue_status = 'processing', processing_started_at = NOW()
    WHERE queue_id = p_queue_id;
    
    CALL GenerateInvoiceFromApprovedReading(v_submission_id, p_invoice_id, p_invoice_number, @total);
    
    UPDATE billing_queue
    SET queue_status = 'completed',
        invoice_id = p_invoice_id,
        invoice_number = p_invoice_number,
        processing_completed_at = NOW()
    WHERE queue_id = p_queue_id;
    
    INSERT INTO billing_process_log (period_id, queue_id, action, status, message, affected_records)
    VALUES (v_period_id, p_queue_id, 'process_invoice', 'success', 
            CONCAT('تم إصدار فاتورة رقم ', p_invoice_number), 1);
    
    COMMIT;
    
END$$

-- 14.10 معالجة مجموعة من طابور الفوترة
CREATE PROCEDURE ProcessBillingQueueBatch(IN p_batch_size INT)
BEGIN
    DECLARE v_queue_id INT;
    DECLARE v_done BOOLEAN DEFAULT FALSE;
    DECLARE v_invoice_id INT;
    DECLARE v_invoice_number VARCHAR(50);
    
    DECLARE cur_queue CURSOR FOR
        SELECT queue_id
        FROM billing_queue
        WHERE queue_status IN ('pending', 'retry')
          AND retry_count < max_retry
        ORDER BY priority ASC, created_at ASC
        LIMIT p_batch_size;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;
    
    OPEN cur_queue;
    
    queue_loop: LOOP
        FETCH cur_queue INTO v_queue_id;
        IF v_done THEN
            LEAVE queue_loop;
        END IF;
        
        CALL ProcessSingleBillingQueue(v_queue_id, v_invoice_id, v_invoice_number);
        
        DO SLEEP(0.1);
        
    END LOOP;
    
    CLOSE cur_queue;
    
END$$

-- 14.11 تسجيل دفعة
CREATE PROCEDURE RecordPayment(
    IN p_invoice_number VARCHAR(50),
    IN p_amount DECIMAL(12,2),
    IN p_payment_method VARCHAR(20),
    IN p_reference_number VARCHAR(100),
    IN p_notes TEXT,
    OUT p_payment_id INT
)
BEGIN
    DECLARE v_invoice_id INT;
    DECLARE v_customer_id INT;
    DECLARE v_total_amount DECIMAL(12,2);
    DECLARE v_paid_amount DECIMAL(12,2);
    DECLARE v_new_paid DECIMAL(12,2);
    DECLARE v_remaining DECIMAL(12,2);
    DECLARE v_customer_name VARCHAR(150);
    DECLARE v_mobile VARCHAR(20);
    DECLARE v_payment_number VARCHAR(50);
    
    SELECT i.invoice_id, i.customer_id, i.total_amount, i.paid_amount 
    INTO v_invoice_id, v_customer_id, v_total_amount, v_paid_amount
    FROM invoice i
    WHERE i.invoice_number = p_invoice_number AND i.invoice_status != 'cancelled';
    
    IF v_invoice_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invoice not found or cancelled';
    END IF;
    
    IF p_amount > (v_total_amount - v_paid_amount) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment amount exceeds remaining balance';
    END IF;
    
    SET v_payment_number = CONCAT('PAY-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 10000), 4, '0'));
    
    INSERT INTO payment (
        payment_number, invoice_id, customer_id, amount, 
        payment_method, reference_number, notes
    ) VALUES (
        v_payment_number, v_invoice_id, v_customer_id, p_amount,
        p_payment_method, p_reference_number, p_notes
    );
    
    SET p_payment_id = LAST_INSERT_ID();
    
    SET v_new_paid = v_paid_amount + p_amount;
    SET v_remaining = v_total_amount - v_new_paid;
    
    UPDATE invoice 
    SET paid_amount = v_new_paid,
        invoice_status = CASE 
            WHEN v_new_paid >= v_total_amount THEN 'paid'
            WHEN v_new_paid > 0 THEN 'partially_paid'
            ELSE invoice_status
        END
    WHERE invoice_id = v_invoice_id;
    
    CALL UpdateCustomerBalance(v_customer_id, p_payment_id, 'payment_received', 0, p_amount, 
                               CONCAT('دفعة على فاتورة ', p_invoice_number));
    
    SELECT full_name_ar, mobile_phone INTO v_customer_name, v_mobile
    FROM customer WHERE customer_id = v_customer_id;
    
    INSERT INTO sms_queue (customer_id, mobile_number, template_id, message_content)
    SELECT v_customer_id, v_mobile, template_id,
           REPLACE(REPLACE(REPLACE(REPLACE(content_template_ar, '{customer_name}', v_customer_name),
                   '{invoice_number}', p_invoice_number),
                   '{amount}', CAST(p_amount AS CHAR)),
                   '{remaining_balance}', CAST(v_remaining AS CHAR))
    FROM sms_template
    WHERE template_type = 'PaymentReceived' LIMIT 1;
    
END$$

-- 14.12 تقرير رصيد عميل مفصل
CREATE PROCEDURE GetCustomerDetailedBalance(IN p_customer_number VARCHAR(50))
BEGIN
    SELECT 
        customer_number, full_name_ar, current_balance, credit_limit
    FROM customer
    WHERE customer_number = p_customer_number;
    
    SELECT 
        i.invoice_number, i.issue_date, i.due_date,
        i.total_amount, i.paid_amount, i.remaining_amount,
        DATEDIFF(CURDATE(), i.due_date) AS days_overdue,
        COALESCE(p.penalty_amount, 0) AS penalty_amount
    FROM invoice i
    JOIN contract c ON i.contract_id = c.contract_id
    LEFT JOIN penalty p ON i.invoice_id = p.invoice_id AND p.is_paid = FALSE
    WHERE c.customer_id = (SELECT customer_id FROM customer WHERE customer_number = p_customer_number)
      AND i.invoice_status IN ('issued', 'partially_paid', 'overdue')
    ORDER BY i.due_date;
    
    SELECT 
        transaction_type, debit, credit, balance_after, transaction_date, notes
    FROM balance_ledger bl
    WHERE bl.customer_id = (SELECT customer_id FROM customer WHERE customer_number = p_customer_number)
    ORDER BY transaction_date DESC
    LIMIT 10;
    
END$$

-- 14.13 عرض تقدم الفوترة
CREATE PROCEDURE GetBillingProgress(IN p_period_id INT)
BEGIN
    SELECT 
        bp.period_name, bp.status AS period_status,
        bp.reading_start_date, bp.reading_end_date,
        COUNT(DISTINCT mrs.submission_id) AS total_submissions,
        SUM(CASE WHEN mrs.approval_status = 'pending' THEN 1 ELSE 0 END) AS pending_approvals,
        SUM(CASE WHEN mrs.approval_status = 'approved' THEN 1 ELSE 0 END) AS approved_readings,
        SUM(CASE WHEN mrs.approval_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_readings,
        SUM(CASE WHEN bq.queue_status = 'completed' THEN 1 ELSE 0 END) AS invoices_generated,
        SUM(CASE WHEN bq.queue_status IN ('pending', 'processing', 'retry') THEN 1 ELSE 0 END) AS pending_invoices,
        SUM(CASE WHEN bq.queue_status = 'failed' THEN 1 ELSE 0 END) AS failed_invoices
    FROM billing_period bp
    LEFT JOIN meter_reading_submission mrs ON bp.period_id = mrs.period_id
    LEFT JOIN billing_queue bq ON mrs.submission_id = bq.submission_id
    WHERE bp.period_id = p_period_id
    GROUP BY bp.period_id;
    
END$$

-- 14.14 إضافة متحصل جديد
CREATE PROCEDURE AddNewCollector(
    IN p_full_name_ar VARCHAR(150),
    IN p_mobile_phone VARCHAR(20),
    IN p_national_id VARCHAR(50),
    IN p_opening_balance DECIMAL(12,2),
    IN p_commission_percent DECIMAL(5,2),
    OUT p_collector_id INT,
    OUT p_cashbox_id INT
)
BEGIN
    DECLARE v_collector_code VARCHAR(50);
    
    SET v_collector_code = CONCAT('COL-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 10000), 4, '0'));
    
    INSERT INTO collector (
        collector_code, full_name_ar, mobile_phone, national_id,
        hire_date, commission_percent, collector_status
    ) VALUES (
        v_collector_code, p_full_name_ar, p_mobile_phone, p_national_id,
        CURDATE(), p_commission_percent, 'active'
    );
    
    SET p_collector_id = LAST_INSERT_ID();
    
    INSERT INTO collector_cashbox (
        collector_id, cashbox_name, opening_balance, current_balance, status
    ) VALUES (
        p_collector_id, CONCAT('صندوق ', p_full_name_ar), 
        p_opening_balance, p_opening_balance, 'active'
    );
    
    SET p_cashbox_id = LAST_INSERT_ID();
    
    INSERT INTO collector_cashbox_transaction (
        cashbox_id, transaction_type, amount, balance_before, balance_after, notes
    ) VALUES (
        p_cashbox_id, 'opening_balance', p_opening_balance, 0, p_opening_balance,
        'رصيد افتتاحي للصندوق'
    );
    
END$$

-- 14.15 تحصيل دفعة عن طريق متحصل
CREATE PROCEDURE RecordCollectionByCollector(
    IN p_collector_code VARCHAR(50),
    IN p_invoice_number VARCHAR(50),
    IN p_amount DECIMAL(12,2),
    IN p_payment_method VARCHAR(20),
    IN p_reference_number VARCHAR(100),
    IN p_notes TEXT,
    OUT p_payment_id INT,
    OUT p_transaction_id INT
)
BEGIN
    DECLARE v_collector_id INT;
    DECLARE v_cashbox_id INT;
    DECLARE v_current_balance DECIMAL(12,2);
    DECLARE v_new_balance DECIMAL(12,2);
    DECLARE v_invoice_id INT;
    DECLARE v_customer_id INT;
    DECLARE v_total_amount DECIMAL(12,2);
    DECLARE v_paid_amount DECIMAL(12,2);
    DECLARE v_payment_number VARCHAR(50);
    DECLARE v_customer_name VARCHAR(150);
    DECLARE v_mobile VARCHAR(20);
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    SELECT c.collector_id, cb.cashbox_id, cb.current_balance
    INTO v_collector_id, v_cashbox_id, v_current_balance
    FROM collector c
    JOIN collector_cashbox cb ON c.collector_id = cb.collector_id
    WHERE c.collector_code = p_collector_code 
      AND c.collector_status = 'active'
      AND cb.status = 'active'
    LIMIT 1;
    
    IF v_collector_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'المتحصل غير موجود أو الصندوق غير نشط';
    END IF;
    
    SELECT i.invoice_id, i.customer_id, i.total_amount, i.paid_amount
    INTO v_invoice_id, v_customer_id, v_total_amount, v_paid_amount
    FROM invoice i
    WHERE i.invoice_number = p_invoice_number AND i.invoice_status != 'cancelled';
    
    IF v_invoice_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'الفاتورة غير موجودة أو ملغاة';
    END IF;
    
    IF p_amount > (v_total_amount - v_paid_amount) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'المبلغ المحصل يتجاوز المتبقي من الفاتورة';
    END IF;
    
    SET v_payment_number = CONCAT('PAY-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 10000), 4, '0'));
    
    INSERT INTO payment (
        payment_number, invoice_id, customer_id, amount, payment_date,
        payment_method, reference_number, notes
    ) VALUES (
        v_payment_number, v_invoice_id, v_customer_id, p_amount, NOW(),
        p_payment_method, p_reference_number, p_notes
    );
    
    SET p_payment_id = LAST_INSERT_ID();
    
    UPDATE invoice 
    SET paid_amount = paid_amount + p_amount,
        invoice_status = CASE 
            WHEN paid_amount + p_amount >= total_amount THEN 'paid'
            WHEN paid_amount + p_amount > 0 THEN 'partially_paid'
            ELSE invoice_status
        END
    WHERE invoice_id = v_invoice_id;
    
    CALL UpdateCustomerBalance(v_customer_id, p_payment_id, 'payment_received', 0, p_amount,
                               CONCAT('دفعة عبر متحصل على فاتورة ', p_invoice_number));
    
    SET v_new_balance = v_current_balance + p_amount;
    
    UPDATE collector_cashbox 
    SET current_balance = v_new_balance, last_balance = v_current_balance
    WHERE cashbox_id = v_cashbox_id;
    
    INSERT INTO collector_cashbox_transaction (
        cashbox_id, transaction_type, payment_id, amount, 
        balance_before, balance_after, notes
    ) VALUES (
        v_cashbox_id, 'collection', p_payment_id, p_amount,
        v_current_balance, v_new_balance,
        CONCAT('تحصيل من فاتورة ', p_invoice_number)
    );
    
    SET p_transaction_id = LAST_INSERT_ID();
    
    SELECT full_name_ar, mobile_phone INTO v_customer_name, v_mobile
    FROM customer WHERE customer_id = v_customer_id;
    
    INSERT INTO sms_queue (customer_id, mobile_number, template_id, message_content)
    SELECT v_customer_id, v_mobile, template_id,
           REPLACE(REPLACE(REPLACE(content_template_ar, '{customer_name}', v_customer_name),
                   '{invoice_number}', p_invoice_number),
                   '{amount}', CAST(p_amount AS CHAR))
    FROM sms_template
    WHERE template_type = 'PaymentReceived' LIMIT 1;
    
    COMMIT;
    
END$$

-- 14.16 توريد أموال من المتحصل إلى الشركة
CREATE PROCEDURE DepositCashFromCollector(
    IN p_collector_code VARCHAR(50),
    IN p_deposit_amount DECIMAL(12,2),
    IN p_deposit_method VARCHAR(50),
    IN p_bank_name VARCHAR(100),
    IN p_bank_account VARCHAR(100),
    IN p_cheque_number VARCHAR(50),
    IN p_transaction_reference VARCHAR(100),
    IN p_notes TEXT,
    OUT p_deposit_id INT
)
BEGIN
    DECLARE v_collector_id INT;
    DECLARE v_cashbox_id INT;
    DECLARE v_current_balance DECIMAL(12,2);
    DECLARE v_new_balance DECIMAL(12,2);
    DECLARE v_deposit_number VARCHAR(50);
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    SELECT c.collector_id, cb.cashbox_id, cb.current_balance
    INTO v_collector_id, v_cashbox_id, v_current_balance
    FROM collector c
    JOIN collector_cashbox cb ON c.collector_id = cb.collector_id
    WHERE c.collector_code = p_collector_code 
      AND c.collector_status = 'active'
      AND cb.status = 'active'
    LIMIT 1;
    
    IF v_collector_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'المتحصل غير موجود أو الصندوق غير نشط';
    END IF;
    
    IF p_deposit_amount > v_current_balance THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'المبلغ المطلوب توريده exceeds الرصيد المتاح في الصندوق';
    END IF;
    
    SET v_deposit_number = CONCAT('DEP-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 10000), 4, '0'));
    
    INSERT INTO cash_deposit (
        deposit_number, collector_id, cashbox_id, deposit_amount,
        deposit_date, deposit_time, deposit_method, bank_name,
        bank_account, cheque_number, transaction_reference, status, notes
    ) VALUES (
        v_deposit_number, v_collector_id, v_cashbox_id, p_deposit_amount,
        CURDATE(), CURTIME(), p_deposit_method, p_bank_name,
        p_bank_account, p_cheque_number, p_transaction_reference, 'pending', p_notes
    );
    
    SET p_deposit_id = LAST_INSERT_ID();
    
    SET v_new_balance = v_current_balance - p_deposit_amount;
    
    UPDATE collector_cashbox 
    SET current_balance = v_new_balance, last_balance = v_current_balance
    WHERE cashbox_id = v_cashbox_id;
    
    INSERT INTO collector_cashbox_transaction (
        cashbox_id, transaction_type, amount, balance_before, balance_after, notes
    ) VALUES (
        v_cashbox_id, 'deposit_to_company', p_deposit_amount,
        v_current_balance, v_new_balance,
        CONCAT('توريد أموال إلى الشركة رقم ', v_deposit_number)
    );
    
    COMMIT;
    
END$$

-- 14.17 إنشاء خط سير جديد
CREATE PROCEDURE CreateSimpleRoute(
    IN p_route_code VARCHAR(50),
    IN p_route_name_ar VARCHAR(150),
    IN p_route_type VARCHAR(20),
    IN p_region VARCHAR(100),
    IN p_contract_ids TEXT,
    IN p_created_by INT,
    OUT p_route_id INT
)
BEGIN
    DECLARE v_contract_id INT;
    DECLARE v_current_pos INT DEFAULT 1;
    DECLARE v_contract_count INT;
    
    INSERT INTO route (route_code, route_name_ar, route_type, region, created_by)
    VALUES (p_route_code, p_route_name_ar, p_route_type, p_region, p_created_by);
    
    SET p_route_id = LAST_INSERT_ID();
    
    SET v_contract_count = LENGTH(p_contract_ids) - LENGTH(REPLACE(p_contract_ids, ',', '')) + 1;
    
    WHILE v_current_pos <= v_contract_count DO
        SET v_contract_id = CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(p_contract_ids, ',', v_current_pos), ',', -1) AS UNSIGNED);
        
        INSERT INTO route_contract (route_id, contract_id, stop_order, priority)
        VALUES (p_route_id, v_contract_id, v_current_pos, 5);
        
        SET v_current_pos = v_current_pos + 1;
    END WHILE;
    
END$$

-- 14.18 إسناد خط سير إلى موظف
CREATE PROCEDURE AssignRouteToEmployee(
    IN p_route_code VARCHAR(50),
    IN p_assigned_to_type VARCHAR(20),
    IN p_assigned_to_username VARCHAR(50),
    IN p_assignment_date DATE,
    IN p_shift VARCHAR(20),
    IN p_assigned_by INT,
    OUT p_assignment_id INT
)
BEGIN
    DECLARE v_route_id INT;
    DECLARE v_assigned_to_id INT;
    DECLARE v_assigned_by_name VARCHAR(150);
    
    SELECT route_id INTO v_route_id FROM route WHERE route_code = p_route_code AND is_active = TRUE;
    
    IF v_route_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'خط السير غير موجود';
    END IF;
    
    IF p_assigned_to_type = 'user' THEN
        SELECT user_id INTO v_assigned_to_id FROM system_user WHERE username = p_assigned_to_username AND user_status = 'active';
    ELSEIF p_assigned_to_type = 'meter_reader' THEN
        SELECT meter_reader_id INTO v_assigned_to_id FROM meter_reader WHERE reader_code = p_assigned_to_username AND reader_status = 'active';
    ELSEIF p_assigned_to_type = 'collector' THEN
        SELECT collector_id INTO v_assigned_to_id FROM collector WHERE collector_code = p_assigned_to_username AND collector_status = 'active';
    ELSE
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'نوع المستلم غير صحيح';
    END IF;
    
    IF v_assigned_to_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'الموظف غير موجود';
    END IF;
    
    INSERT INTO route_assignment (
        route_id, assigned_to_type, assigned_to_id, assignment_date, shift, status, assigned_by
    ) VALUES (
        v_route_id, p_assigned_to_type, v_assigned_to_id, p_assignment_date, p_shift, 'planned', p_assigned_by
    );
    
    SET p_assignment_id = LAST_INSERT_ID();
    
    INSERT INTO route_execution (assignment_id, route_contract_id, stop_order, execution_status)
    SELECT p_assignment_id, route_contract_id, stop_order, 'pending'
    FROM route_contract
    WHERE route_id = v_route_id
    ORDER BY stop_order;
    
    SELECT full_name_ar INTO v_assigned_by_name FROM system_user WHERE user_id = p_assigned_by;
    
    INSERT INTO route_tracking_log (assignment_id, user_id, action_type, notes)
    VALUES (p_assignment_id, p_assigned_by, 'start', CONCAT('تم إسناد الخط إلى الموظف بواسطة ', v_assigned_by_name));
    
END$$

-- 14.19 بدء الجولة
CREATE PROCEDURE StartRoute(
    IN p_assignment_id INT,
    IN p_user_id INT,
    IN p_gps_latitude DECIMAL(10,8),
    IN p_gps_longitude DECIMAL(11,8)
)
BEGIN
    UPDATE route_assignment
    SET status = 'in_progress',
        started_at = NOW()
    WHERE assignment_id = p_assignment_id AND status = 'planned';
    
    INSERT INTO route_tracking_log (assignment_id, user_id, action_type, gps_latitude, gps_longitude, notes)
    VALUES (p_assignment_id, p_user_id, 'start', p_gps_latitude, p_gps_longitude, 'بدأ الجولة');
    
END$$

-- 14.20 تنفيذ عقد في الجولة
CREATE PROCEDURE ExecuteRouteContract(
    IN p_assignment_id INT,
    IN p_stop_order INT,
    IN p_user_id INT,
    IN p_execution_type VARCHAR(20),
    IN p_value DECIMAL(12,2),
    IN p_gps_latitude DECIMAL(10,8),
    IN p_gps_longitude DECIMAL(11,8),
    IN p_notes TEXT,
    OUT p_execution_id INT,
    OUT p_reference_id INT
)
BEGIN
    DECLARE v_route_contract_id INT;
    DECLARE v_contract_id INT;
    DECLARE v_meter_number VARCHAR(50);
    DECLARE v_invoice_number VARCHAR(50);
    DECLARE v_customer_id INT;
    DECLARE v_collector_code VARCHAR(50);
    DECLARE v_submission_id INT;
    DECLARE v_payment_id INT;
    DECLARE v_route_type VARCHAR(20);
    
    START TRANSACTION;
    
    SELECT rc.route_contract_id, rc.contract_id, r.route_type
    INTO v_route_contract_id, v_contract_id, v_route_type
    FROM route_execution re
    JOIN route_contract rc ON re.route_contract_id = rc.route_contract_id
    JOIN route_assignment ra ON re.assignment_id = ra.assignment_id
    JOIN route r ON ra.route_id = r.route_id
    WHERE re.assignment_id = p_assignment_id AND re.stop_order = p_stop_order;
    
    IF v_route_contract_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'العقد غير موجود في هذه الجولة';
    END IF;
    
    IF p_execution_type = 'reading' AND v_route_type NOT IN ('meter_reading', 'both') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'هذا الخط لا يدعم رفع القراءات';
    END IF;
    
    IF p_execution_type = 'collection' AND v_route_type NOT IN ('collection', 'both') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'هذا الخط لا يدعم التحصيل';
    END IF;
    
    IF p_execution_type = 'reading' THEN
        SELECT meter_number INTO v_meter_number
        FROM meter
        WHERE contract_id = v_contract_id AND meter_status = 'active'
        LIMIT 1;
        
        IF v_meter_number IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'لا يوجد عداد نشط لهذا العقد';
        END IF;
        
        CALL SubmitMeterReading(
            v_meter_number, CURDATE(), p_value,
            (SELECT full_name_ar FROM system_user WHERE user_id = p_user_id),
            'mobile_app', p_notes, v_submission_id
        );
        
        SET p_reference_id = v_submission_id;
        
        UPDATE route_execution
        SET actual_reading = p_value,
            reading_submission_id = v_submission_id,
            execution_status = 'done',
            executed_at = NOW(),
            gps_latitude = p_gps_latitude,
            gps_longitude = p_gps_longitude,
            notes = p_notes
        WHERE assignment_id = p_assignment_id AND stop_order = p_stop_order;
        
    ELSEIF p_execution_type = 'collection' THEN
        SELECT invoice_number, customer_id INTO v_invoice_number, v_customer_id
        FROM invoice i
        WHERE i.contract_id = v_contract_id
          AND i.invoice_status IN ('issued', 'partially_paid', 'overdue')
        ORDER BY i.due_date ASC
        LIMIT 1;
        
        IF v_invoice_number IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'لا توجد فواتير غير مدفوعة لهذا العقد';
        END IF;
        
        SELECT c.collector_code INTO v_collector_code
        FROM user_collector_link ucl
        JOIN collector c ON ucl.collector_id = c.collector_id
        WHERE ucl.user_id = p_user_id
        LIMIT 1;
        
        IF v_collector_code IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'لا يوجد متحصل مرتبط بهذا المستخدم';
        END IF;
        
        CALL RecordCollectionByCollector(
            v_collector_code, v_invoice_number, p_value, 'cash',
            CONCAT('ROUTE-', p_assignment_id), p_notes, v_payment_id, @trans_id
        );
        
        SET p_reference_id = v_payment_id;
        
        UPDATE route_execution
        SET actual_amount = p_value,
            payment_id = v_payment_id,
            execution_status = 'done',
            executed_at = NOW(),
            gps_latitude = p_gps_latitude,
            gps_longitude = p_gps_longitude,
            notes = p_notes
        WHERE assignment_id = p_assignment_id AND stop_order = p_stop_order;
        
    END IF;
    
    INSERT INTO route_tracking_log (assignment_id, user_id, action_type, route_contract_id, gps_latitude, gps_longitude, notes)
    VALUES (p_assignment_id, p_user_id, 'done_contract', v_route_contract_id, p_gps_latitude, p_gps_longitude, 
            CONCAT(p_execution_type, ' بقيمة: ', p_value));
    
    SET p_execution_id = (SELECT execution_id FROM route_execution 
                          WHERE assignment_id = p_assignment_id AND stop_order = p_stop_order);
    
    COMMIT;
    
END$$

-- 14.21 إنهاء الجولة
CREATE PROCEDURE CompleteRoute(
    IN p_assignment_id INT,
    IN p_user_id INT,
    IN p_gps_latitude DECIMAL(10,8),
    IN p_gps_longitude DECIMAL(11,8)
)
BEGIN
    DECLARE v_pending_count INT;
    DECLARE v_total_count INT;
    DECLARE v_done_count INT;
    DECLARE v_skipped_count INT;
    
    SELECT 
        COUNT(*),
        SUM(CASE WHEN execution_status = 'pending' THEN 1 ELSE 0 END),
        SUM(CASE WHEN execution_status = 'done' THEN 1 ELSE 0 END),
        SUM(CASE WHEN execution_status = 'skipped' THEN 1 ELSE 0 END)
    INTO v_total_count, v_pending_count, v_done_count, v_skipped_count
    FROM route_execution
    WHERE assignment_id = p_assignment_id;
    
    UPDATE route_assignment
    SET status = IF(v_pending_count = 0, 'completed', 'in_progress'),
        completed_at = IF(v_pending_count = 0, NOW(), NULL)
    WHERE assignment_id = p_assignment_id;
    
    INSERT INTO route_tracking_log (assignment_id, user_id, action_type, gps_latitude, gps_longitude, notes)
    VALUES (p_assignment_id, p_user_id, 'complete', p_gps_latitude, p_gps_longitude,
            CONCAT('اكتملت الجولة - تم إنجاز ', v_done_count, ' من أصل ', v_total_count, 
                   ' عقود (تخطي: ', v_skipped_count, ')'));
    
END$$

DELIMITER ;