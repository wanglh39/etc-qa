import threading
from datetime import datetime

from db.mysql_client import MySQLClient
from utils.logger import get_logger

logger = get_logger("prompt.shadow_recorder")

_shadow_records: list[dict] = []
_records_lock = threading.Lock()
_MAX_RECORDS = 10000


def record_shadow(prompt_key: str, primary_result: str, shadow_result: str,
                   query: str = "", pipeline: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = {
        "prompt_key": prompt_key,
        "primary_result": primary_result[:500],
        "shadow_result": shadow_result[:500],
        "query": query[:200],
        "pipeline": pipeline,
        "timestamp": now,
        "diff": primary_result != shadow_result,
    }

    with _records_lock:
        _shadow_records.append(record)
        if len(_shadow_records) > _MAX_RECORDS:
            _shadow_records.pop(0)

    if record["diff"]:
        logger.info(f"影子测试差异: {prompt_key}, query={query[:30]}")


def get_shadow_stats() -> dict:
    with _records_lock:
        total = len(_shadow_records)
        diffs = sum(1 for r in _shadow_records if r["diff"])

    by_key = {}
    with _records_lock:
        for r in _shadow_records:
            key = r["prompt_key"]
            if key not in by_key:
                by_key[key] = {"total": 0, "diff": 0}
            by_key[key]["total"] += 1
            if r["diff"]:
                by_key[key]["diff"] += 1

    return {"total": total, "diff_count": diffs, "diff_rate": diffs / total if total > 0 else 0, "by_key": by_key}


def get_shadow_records(prompt_key: str = None, diff_only: bool = False, limit: int = 100) -> list[dict]:
    with _records_lock:
        records = list(_shadow_records)

    if prompt_key:
        records = [r for r in records if r["prompt_key"] == prompt_key]
    if diff_only:
        records = [r for r in records if r["diff"]]
    return records[-limit:]


def _ensure_table(conn):
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS shadow_test_log ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "prompt_key VARCHAR(100) NOT NULL, "
        "primary_result TEXT, "
        "shadow_result TEXT, "
        "query_text VARCHAR(200), "
        "pipeline VARCHAR(50), "
        "has_diff TINYINT DEFAULT 0, "
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
        "INDEX idx_prompt_key (prompt_key)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    conn.commit()
    cursor.close()


def flush_to_db():
    mysql = MySQLClient()
    conn = mysql._get_conn()
    try:
        _ensure_table(conn)
        cursor = conn.cursor()
        with _records_lock:
            records = list(_shadow_records)

        for r in records:
            cursor.execute(
                "INSERT INTO shadow_test_log "
                "(prompt_key, primary_result, shadow_result, query_text, pipeline, has_diff, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (r["prompt_key"], r["primary_result"], r["shadow_result"],
                 r["query"], r["pipeline"], r["diff"], r["timestamp"]),
            )
        conn.commit()
        cursor.close()

        with _records_lock:
            _shadow_records.clear()

        logger.info(f"影子测试记录已写入DB: {len(records)}条")
    except Exception as e:
        logger.error(f"影子测试记录写入DB失败: {e}")
        mysql._reset_conn()


def clear_records():
    with _records_lock:
        _shadow_records.clear()
