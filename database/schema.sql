
CREATE DATABASE IF NOT EXISTS hybrid_ids
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE hybrid_ids;


CREATE TABLE employees (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    department      VARCHAR(100)    NOT NULL,
    role            VARCHAR(100)    NOT NULL,
    ip_address      VARCHAR(45)     NOT NULL UNIQUE,  
    work_start      TIME            NOT NULL,
    work_end        TIME            NOT NULL,
    clearance_level ENUM('low','medium','high','admin') NOT NULL DEFAULT 'low',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_employees_ip (ip_address)
) ENGINE=InnoDB;



CREATE TABLE tickets (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT NOT NULL,
    type            ENUM('access_request','it_maintenance','after_hours_approval','incident') NOT NULL,
    description     TEXT NOT NULL,
    status          ENUM('open','in_progress','resolved','closed') NOT NULL DEFAULT 'open',
    created_at      DATETIME NOT NULL,
    resolved_at     DATETIME NULL,

    CONSTRAINT fk_tickets_employee
        FOREIGN KEY (employee_id) REFERENCES employees(id)
        ON DELETE CASCADE,

    INDEX idx_tickets_employee (employee_id),
    INDEX idx_tickets_status (status)
) ENGINE=InnoDB;



CREATE TABLE leave_records (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT NOT NULL,
    leave_type      ENUM('annual','sick','unpaid','remote_work') NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    approved        BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_leave_employee
        FOREIGN KEY (employee_id) REFERENCES employees(id)
        ON DELETE CASCADE,

    INDEX idx_leave_employee (employee_id),
    INDEX idx_leave_dates (start_date, end_date)
) ENGINE=InnoDB;



CREATE TABLE alerts (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    src_ip              VARCHAR(45)  NOT NULL,
    dst_port            INT          NOT NULL,
    protocol            VARCHAR(20)  NOT NULL,
    label               VARCHAR(100) NOT NULL,      
    ground_truth_label  VARCHAR(100) NULL,          
    confidence          FLOAT        NOT NULL,    
    timestamp           DATETIME     NOT NULL,      


    reasoning_status    ENUM('pending','reasoning','complete') NOT NULL DEFAULT 'pending',
    agent_verdict       ENUM('true_positive','false_positive') NULL,
    agent_reasoning     TEXT NULL,

    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reasoning_started_at   DATETIME NULL,
    reasoning_completed_at DATETIME NULL,

    INDEX idx_alerts_src_ip (src_ip),
    INDEX idx_alerts_status (reasoning_status),
    INDEX idx_alerts_verdict (agent_verdict),
    INDEX idx_alerts_timestamp (timestamp)
) ENGINE=InnoDB;
