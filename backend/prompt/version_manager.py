from agent.prompt_engine import PromptEngine
from db.mysql_client import MySQLClient
from utils.config_center import invalidate_cache
from utils.logger import get_logger

logger = get_logger("prompt.version_manager")

import pymysql


def _detect_columns(conn) -> set:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                       "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prompt_templates'")
        cols = {row[0] for row in cursor.fetchall()}
        cursor.close()
        return cols
    except Exception:
        return set()


def _select_fields(cols: set) -> str:
    base = ["prompt_key", "template_text", "version", "is_active", "description"]
    if "id" in cols:
        base.insert(0, "id")
    if "status" in cols:
        base.append("status")
    if "created_at" in cols:
        base.append("created_at")
    if "updated_at" in cols:
        base.append("updated_at")
    return ", ".join(base)


class PromptVersionManager:
    def __init__(self):
        self._mysql = None
        self._cols_cache = None

    def _get_mysql(self) -> MySQLClient:
        if self._mysql is None:
            self._mysql = MySQLClient()
        return self._mysql

    def _get_cols(self, conn) -> set:
        if self._cols_cache is None:
            self._cols_cache = _detect_columns(conn)
        return self._cols_cache

    def list_versions(self, prompt_key: str) -> list[dict]:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cols = self._get_cols(conn)
            fields = _select_fields(cols)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                f"SELECT {fields} FROM prompt_templates WHERE prompt_key=%s ORDER BY version DESC",
                (prompt_key,),
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            mysql._reset_conn()
            raise

    def get_version(self, prompt_key: str, version: int | None = None) -> dict | None:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cols = self._get_cols(conn)
            fields = _select_fields(cols)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            if version is None:
                where = "WHERE prompt_key=%s AND is_active=1"
                params = (prompt_key,)
            else:
                where = "WHERE prompt_key=%s AND version=%s"
                params = (prompt_key, version)
            cursor.execute(
                f"SELECT {fields} FROM prompt_templates {where}",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
            return row
        except Exception:
            mysql._reset_conn()
            raise

    def publish(self, prompt_key: str, template_text: str, description: str = "") -> dict:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT MAX(version) as max_ver FROM prompt_templates WHERE prompt_key=%s",
                (prompt_key,),
            )
            row = cursor.fetchone()
            new_version = (row["max_ver"] or 0) + 1

            cursor.execute(
                "UPDATE prompt_templates SET is_active=0 WHERE prompt_key=%s AND is_active=1",
                (prompt_key,),
            )

            cols = self._get_cols(conn)
            if "status" in cols:
                cursor.execute(
                    "INSERT INTO prompt_templates "
                    "(prompt_key, template_text, version, is_active, status, description) "
                    "VALUES (%s, %s, %s, 1, 'active', %s)",
                    (prompt_key, template_text, new_version, description),
                )
            else:
                cursor.execute(
                    "INSERT INTO prompt_templates "
                    "(prompt_key, template_text, version, is_active, description) "
                    "VALUES (%s, %s, %s, 1, %s)",
                    (prompt_key, template_text, new_version, description),
                )
            conn.commit()

            PromptEngine.invalidate_cache(prompt_key)
            invalidate_cache(f"__prompt__{prompt_key}")

            logger.info(f"发布提示词 {prompt_key} v{new_version}")
            return {"prompt_key": prompt_key, "version": new_version, "status": "active"}
        except Exception:
            conn.rollback()
            mysql._reset_conn()
            raise

    def rollback(self, prompt_key: str, target_version: int | None = None) -> dict:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            if target_version is None:
                cols = self._get_cols(conn)
                status_filter = " AND status='active'" if "status" in cols else ""
                cursor.execute(
                    f"SELECT version FROM prompt_templates "
                    f"WHERE prompt_key=%s AND is_active=0{status_filter} "
                    f"ORDER BY version DESC LIMIT 1",
                    (prompt_key,),
                )
                row = cursor.fetchone()
                if row is None:
                    return {"prompt_key": prompt_key, "error": "无可回滚版本"}
                target_version = row["version"]

            cursor.execute(
                "UPDATE prompt_templates SET is_active=0 WHERE prompt_key=%s AND is_active=1",
                (prompt_key,),
            )
            cursor.execute(
                "UPDATE prompt_templates SET is_active=1 WHERE prompt_key=%s AND version=%s",
                (prompt_key, target_version),
            )
            conn.commit()

            PromptEngine.invalidate_cache(prompt_key)
            invalidate_cache(f"__prompt__{prompt_key}")

            logger.info(f"回滚提示词 {prompt_key} 到 v{target_version}")
            return {"prompt_key": prompt_key, "version": target_version, "status": "rolled_back"}
        except Exception:
            conn.rollback()
            mysql._reset_conn()
            raise

    def start_shadow(self, prompt_key: str, shadow_version: int) -> dict:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cols = self._get_cols(conn)
            if "status" not in cols:
                return {"error": "prompt_templates表缺少status列，请先运行迁移: python scripts/data/init_db.py"}

            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT id, template_text, version FROM prompt_templates "
                "WHERE prompt_key=%s AND version=%s",
                (prompt_key, shadow_version),
            )
            row = cursor.fetchone()
            if row is None:
                return {"error": f"版本 {shadow_version} 不存在"}

            cursor.execute(
                "UPDATE prompt_templates SET status='shadow' WHERE prompt_key=%s AND version=%s",
                (prompt_key, shadow_version),
            )
            conn.commit()

            logger.info(f"启动影子测试 {prompt_key} v{shadow_version}")
            return {"prompt_key": prompt_key, "shadow_version": shadow_version, "status": "shadow"}
        except Exception:
            conn.rollback()
            mysql._reset_conn()
            raise

    def stop_shadow(self, prompt_key: str, shadow_version: int) -> dict:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE prompt_templates SET status='active' "
                "WHERE prompt_key=%s AND version=%s AND status='shadow'",
                (prompt_key, shadow_version),
            )
            conn.commit()
            logger.info(f"停止影子测试 {prompt_key} v{shadow_version}")
            return {"prompt_key": prompt_key, "shadow_version": shadow_version, "status": "stopped"}
        except Exception:
            conn.rollback()
            mysql._reset_conn()
            raise

    def get_shadow_template(self, prompt_key: str) -> str | None:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cols = self._get_cols(conn)
            if "status" not in cols:
                return None
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT template_text FROM prompt_templates "
                "WHERE prompt_key=%s AND status='shadow' "
                "ORDER BY version DESC LIMIT 1",
                (prompt_key,),
            )
            row = cursor.fetchone()
            cursor.close()
            return row["template_text"] if row else None
        except Exception:
            mysql._reset_conn()
            return None

    def list_all_keys(self) -> list[dict]:
        mysql = self._get_mysql()
        conn = mysql._get_conn()
        try:
            cols = self._get_cols(conn)
            has_status = "status" in cols
            shadow_sql = "SUM(CASE WHEN status='shadow' THEN 1 ELSE 0 END)" if has_status else "0"
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                f"SELECT prompt_key, MAX(version) as latest_version, "
                f"SUM(is_active) as active_count, "
                f"{shadow_sql} as shadow_count "
                f"FROM prompt_templates GROUP BY prompt_key ORDER BY prompt_key"
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            mysql._reset_conn()
            raise


_version_manager = None


def get_version_manager() -> PromptVersionManager:
    global _version_manager
    if _version_manager is None:
        _version_manager = PromptVersionManager()
    return _version_manager
