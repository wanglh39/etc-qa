import pymysql

from utils.config import get_config


def create_work_orders_table():
    cfg = get_config()["mysql"]
    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            external_id VARCHAR(64) NOT NULL COMMENT '外部工单系统ID',
            raw_data TEXT COMMENT '工单返回的原始JSON',
            status VARCHAR(20) NOT NULL DEFAULT 'submitted' COMMENT 'submitted/answered/processed/deduped/imported/rejected',
            duplicate_of INT DEFAULT NULL COMMENT '重复的qa_id或同批工单id',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_external_id (external_id),
            KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("work_orders表创建成功")


if __name__ == "__main__":
    create_work_orders_table()
