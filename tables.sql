CREATE DATABASE payroll_app;
USE payroll_app;

-- Tabla: emitter
CREATE TABLE emitter (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    fiscal_regime VARCHAR(50) NOT NULL
);

-- Tabla: receiver
CREATE TABLE receiver (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cfdi_use VARCHAR(50) NOT NULL,
    fiscal_address VARCHAR(255) NOT NULL,
    fiscal_regime VARCHAR(50) NOT NULL
);

-- Tabla: payslip
CREATE TABLE payslip (
    id VARCHAR(50) PRIMARY KEY,
    emitter_id VARCHAR(50),
    receiver_id VARCHAR(50),
    initial_payment_date DATE NOT NULL,
    final_payment_date DATE NOT NULL,
    payment_date DATE NOT NULL,
    days_paid INT NOT NULL,
    type VARCHAR(50) NOT NULL,
    total_deductions DECIMAL(10, 2) NOT NULL,
    total_other_payments DECIMAL(10, 2) NOT NULL,
    total_perceptions DECIMAL(10, 2) NOT NULL,
    version VARCHAR(10) NOT NULL,
    FOREIGN KEY (emitter_id) REFERENCES emitter(id),
    FOREIGN KEY (receiver_id) REFERENCES receiver(id)
);

-- Tabla: movement_type
CREATE TABLE movement_type (
    id VARCHAR(4) PRIMARY KEY,
    concept VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    transaction_sub_type VARCHAR(50) NOT NULL
);

-- Tabla: movements
CREATE TABLE movements (
    payslip_id VARCHAR(50),
    movement_type_id VARCHAR(4),
    exempt_amount DECIMAL(10, 2) NOT NULL,
    taxable_amount DECIMAL(10, 2) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (payslip_id, movement_type_id),
    FOREIGN KEY (payslip_id) REFERENCES payslip(id),
    FOREIGN KEY (movement_type_id) REFERENCES movement_type(id)
);