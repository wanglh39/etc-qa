-- ETC客服QA系统 测试数据库初始化
-- CI自动执行: mysql -h 127.0.0.1 -u root -p123456 etc_qa_test < data/init_test_db.sql

-- 表结构
CREATE TABLE IF NOT EXISTS qa_pairs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT,
    category_l1 VARCHAR(50),
    category_l2 VARCHAR(50),
    internal_process TEXT,
    feedback_dept TEXT,
    image_url VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(100) NOT NULL PRIMARY KEY,
    config_value JSON NOT NULL,
    description VARCHAR(500),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS prompt_templates (
    id INT AUTO_INCREMENT,
    prompt_key VARCHAR(100) NOT NULL,
    template_text TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_active TINYINT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    description VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_key_version (prompt_key, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS shadow_test_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prompt_key VARCHAR(100) NOT NULL,
    primary_result TEXT,
    shadow_result TEXT,
    query_text VARCHAR(500),
    pipeline VARCHAR(50),
    has_diff TINYINT NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_prompt_key (prompt_key),
    INDEX idx_has_diff (has_diff)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(100) NOT NULL,
    parent_id INT NULL,
    description VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    qa_id INT,
    question VARCHAR(500),
    answer TEXT,
    result VARCHAR(20),
    operator VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_key VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    permissions JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'service',
    dept VARCHAR(50) DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS operation_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operator VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id INT,
    detail VARCHAR(500),
    ip VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scheduler_task_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(50) NOT NULL,
    stats TEXT,
    result VARCHAR(20) NOT NULL DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS alert_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    message TEXT,
    current_value FLOAT,
    threshold_value FLOAT,
    acked TINYINT NOT NULL DEFAULT 0,
    acked_by VARCHAR(50),
    acked_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS work_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    external_id VARCHAR(100),
    raw_data TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'submitted',
    dept VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 基础数据: 5个角色账号(密码均为123456)
INSERT IGNORE INTO users (username, password_hash, role, dept, status) VALUES
    ('superadmin', 'pbkdf2_sha256$260000$52c0df4474a62b820ea9506984d2bfcc$f85cafafe7401f7a326482e74d5284f11e0fbffa791f728c367ae159447c631f', 'superadmin', '', 'active'),
    ('admin', 'pbkdf2_sha256$260000$52c0df4474a62b820ea9506984d2bfcc$f85cafafe7401f7a326482e74d5284f11e0fbffa791f728c367ae159447c631f', 'admin', '', 'active'),
    ('ops', 'pbkdf2_sha256$260000$52c0df4474a62b820ea9506984d2bfcc$f85cafafe7401f7a326482e74d5284f11e0fbffa791f728c367ae159447c631f', 'ops', '', 'active'),
    ('service', 'pbkdf2_sha256$260000$52c0df4474a62b820ea9506984d2bfcc$f85cafafe7401f7a326482e74d5284f11e0fbffa791f728c367ae159447c631f', 'service', '', 'active'),
    ('dept', 'pbkdf2_sha256$260000$52c0df4474a62b820ea9506984d2bfcc$f85cafafe7401f7a326482e74d5284f11e0fbffa791f728c367ae159447c631f', 'dept', 'aftersale', 'active');

-- 基础数据: 角色定义
INSERT IGNORE INTO roles (role_key, role_name, description) VALUES
    ('superadmin', '超级管理员', '系统全权限，含账号/角色管理'),
    ('admin', '业务管理员', '业务管理，含知识库/工单/数据看板'),
    ('ops', '运维工程师', '运维监控，含系统状态/告警/调度'),
    ('service', '客服', '客服工作台，含检索/工单提交'),
    ('dept', '部门处理员', '部门工单处理');

INSERT IGNORE INTO qa_pairs (id, question, answer, category_l1, category_l2, internal_process, feedback_dept, status) VALUES
    (1, 'ETC卡如何办理', '您可以前往ETC服务网点或通过ETC APP在线申请办理ETC卡，需要提供身份证、行驶证和银行卡。', 'ETC办理', '新办', '核对证件→录入信息→制卡发卡', '客服部', 'active'),
    (2, 'ETC卡丢失了怎么补办', '请拨打客服热线95022挂失，然后携带身份证原件前往ETC服务网点办理补卡，补卡费用10元。', 'ETC办理', '补办', '挂失→核实身份→补卡', '客服部', 'active'),
    (3, 'ETC扣费异常怎么处理', '请提供您的ETC卡号和通行记录，我们将核实扣费情况，多扣费用会在3个工作日内退还。', '扣费问题', '异常扣费', '查询通行记录→核对扣费→多退少补', '财务部', 'active'),
    (4, 'ETC发票如何申请', '您可以通过ETC APP或小程序申请电子发票，选择通行记录后填写发票信息即可开具。', '发票问题', '电子发票', '登录APP→选择行程→填写发票信息→开具', '财务部', 'active'),
    (5, 'ETC设备故障如何更换', '请携带ETC设备和车辆行驶证前往ETC服务网点检测，确认故障后可免费更换新设备。', '设备问题', '故障更换', '设备检测→确认故障→更换设备→激活', '运维部', 'active');