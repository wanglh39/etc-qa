import threading

import pymysql

from utils.config import get_config


class MySQLClient:
    def __init__(self):
        cfg = get_config()["mysql"]
        self._conn_params = {
            "host": cfg["host"],
            "port": cfg["port"],
            "user": cfg["user"],
            "password": cfg["password"],
            "database": cfg["database"],
            "charset": "utf8mb4",
        }
        self._pool_cfg = cfg.get("pool", {})
        self._local = threading.local()

    def _get_conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
        conn = pymysql.connect(**self._conn_params, autocommit=False)
        self._local.conn = conn
        return conn

    def get_by_ids(self, qa_ids: list[int], only_active: bool = True) -> list[dict]:
        if not qa_ids:
            return []
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            placeholders = ",".join(["%s"] * len(qa_ids))
            where = f"WHERE id IN ({placeholders})"
            if only_active:
                where += " AND status = 'active'"
            cursor.execute(
                f"SELECT id, question, answer, category_l1, category_l2, "
                f"internal_process, feedback_dept FROM qa_pairs {where}",
                qa_ids,
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            self._reset_conn()
            raise

    def get_by_id(self, qa_id: int) -> dict | None:
        results = self.get_by_ids([qa_id])
        return results[0] if results else None

    def insert_qa(self, question: str, answer: str, category_l1: str = "",
                  category_l2: str = "", internal_process: str = "",
                  feedback_dept: str = "") -> int:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO qa_pairs (question, answer, category_l1, category_l2, "
                "internal_process, feedback_dept) VALUES (%s, %s, %s, %s, %s, %s)",
                (question, answer, category_l1, category_l2, internal_process, feedback_dept),
            )
            conn.commit()
            qa_id = cursor.lastrowid
            cursor.close()
            return qa_id
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_all_questions(self, only_active: bool = True) -> list[dict]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = "SELECT id, question, answer, category_l1, category_l2 FROM qa_pairs"
            if only_active:
                sql += " WHERE status = 'active'"
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            self._reset_conn()
            raise

    def insert_work_order(self, external_id: str, question: str) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO work_orders (external_id, raw_data, status) VALUES (%s, %s, %s)",
                (external_id, question, "submitted"),
            )
            conn.commit()
            wo_id = cursor.lastrowid
            cursor.close()
            return wo_id
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def update_work_order(self, external_id: str, raw_data: str, status: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE work_orders SET raw_data=%s, status=%s WHERE external_id=%s",
                (raw_data, status, external_id),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_work_orders_by_status(self, status: str) -> list[dict]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM work_orders WHERE status=%s", (status,))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            self._reset_conn()
            raise

    def delete_work_orders_by_status(self, statuses: list[str]):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["%s"] * len(statuses))
            cursor.execute(
                f"DELETE FROM work_orders WHERE status IN ({placeholders})",
                statuses,
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def update_qa_status(self, qa_id: int, status: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE qa_pairs SET status=%s WHERE id=%s",
                (status, qa_id),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_active_ids(self) -> list[int]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM qa_pairs WHERE status = 'active'")
            ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return ids
        except Exception:
            self._reset_conn()
            raise

    def get_qa_list(self, page: int = 1, page_size: int = 20,
                    category_l1: str | None = None,
                    status: str | None = None) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            where_parts = []
            params = []
            if category_l1:
                where_parts.append("category_l1 = %s")
                params.append(category_l1)
            if status:
                where_parts.append("status = %s")
                params.append(status)
            where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
            cursor.execute(f"SELECT COUNT(*) as cnt FROM qa_pairs{where}", params)
            total = cursor.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cursor.execute(
                f"SELECT id, question, answer, category_l1, category_l2, status, "
                f"created_at, updated_at FROM qa_pairs{where} "
                f"ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset],
            )
            rows = cursor.fetchall()
            cursor.close()
            return {"items": rows, "total": total, "page": page, "page_size": page_size}
        except Exception:
            self._reset_conn()
            raise

    def search_qa(self, keyword: str, page: int = 1, page_size: int = 20,
                   category_l1: str | None = None,
                   status: str | None = None) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            where_parts = ["(question LIKE %s OR answer LIKE %s)"]
            like_val = f"%{keyword}%"
            params = [like_val, like_val]
            if category_l1:
                where_parts.append("category_l1 = %s")
                params.append(category_l1)
            if status:
                where_parts.append("status = %s")
                params.append(status)
            where = " WHERE " + " AND ".join(where_parts)
            cursor.execute(f"SELECT COUNT(*) as cnt FROM qa_pairs{where}", params)
            total = cursor.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cursor.execute(
                f"SELECT id, question, answer, category_l1, category_l2, status, "
                f"created_at, updated_at FROM qa_pairs{where} "
                f"ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset],
            )
            rows = cursor.fetchall()
            cursor.close()
            return {"items": rows, "total": total, "page": page, "page_size": page_size}
        except Exception:
            self._reset_conn()
            raise

    def count_qa(self) -> dict[str, int]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT status, COUNT(*) as cnt FROM qa_pairs GROUP BY status")
            rows = cursor.fetchall()
            cursor.close()
            result = {"active": 0, "deprecated": 0, "archived": 0}
            for row in rows:
                result[row["status"]] = row["cnt"]
            result["total"] = sum(result.values())
            return result
        except Exception:
            self._reset_conn()
            raise

    def count_work_orders(self) -> dict[str, int]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT status, COUNT(*) as cnt FROM work_orders GROUP BY status")
            rows = cursor.fetchall()
            cursor.close()
            result = {}
            total = 0
            for row in rows:
                result[row["status"]] = row["cnt"]
                total += row["cnt"]
            result["total"] = total
            return result
        except Exception:
            self._reset_conn()
            raise

    def get_category_stats(self) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT category_l1, COUNT(*) as cnt FROM qa_pairs "
                "WHERE status='active' GROUP BY category_l1 ORDER BY cnt DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return {row["category_l1"]: row["cnt"] for row in rows if row["category_l1"]}
        except Exception:
            self._reset_conn()
            raise

    def get_qa_detail(self, qa_id: int) -> dict | None:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT id, question, answer, category_l1, category_l2, "
                "internal_process, feedback_dept, status, created_at, updated_at "
                "FROM qa_pairs WHERE id=%s",
                (qa_id,),
            )
            row = cursor.fetchone()
            cursor.close()
            return row
        except Exception:
            self._reset_conn()
            raise

    def delete_qa(self, qa_id: int) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM qa_pairs WHERE id=%s", (qa_id,))
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            return affected > 0
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_work_order_list(self, page: int = 1, page_size: int = 20,
                            status: str | None = None,
                            dept: str | None = None) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            where_parts = []
            params = []
            if status:
                where_parts.append("status = %s")
                params.append(status)
            if dept:
                where_parts.append("dept = %s")
                params.append(dept)
            where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
            cursor.execute(f"SELECT COUNT(*) as cnt FROM work_orders{where}", params)
            total = cursor.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cursor.execute(
                f"SELECT id, external_id, raw_data, status, dept, created_at, updated_at "
                f"FROM work_orders{where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset],
            )
            rows = cursor.fetchall()
            cursor.close()
            return {"items": rows, "total": total, "page": page, "page_size": page_size}
        except Exception:
            self._reset_conn()
            raise

    def insert_work_order_full(self, external_id: str, dept: str, raw_data: str) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO work_orders (external_id, raw_data, status, dept) "
                "VALUES (%s, %s, 'submitted', %s)",
                (external_id, raw_data, dept),
            )
            conn.commit()
            wo_id = cursor.lastrowid
            cursor.close()
            return wo_id
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_work_order_detail(self, wo_id: int) -> dict | None:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT id, external_id, raw_data, status, dept, created_at, updated_at "
                "FROM work_orders WHERE id=%s",
                (wo_id,),
            )
            row = cursor.fetchone()
            cursor.close()
            return row
        except Exception:
            self._reset_conn()
            raise

    def update_work_order_reply(self, wo_id: int, raw_data: str, status: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE work_orders SET raw_data=%s, status=%s WHERE id=%s",
                (raw_data, status, wo_id),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def insert_audit_log(self, qa_id: int, question: str, answer: str,
                         result: str, operator: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_log (qa_id, question, answer, result, operator) "
                "VALUES (%s, %s, %s, %s, %s)",
                (qa_id, question, answer, result, operator),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_audit_history(self, page: int = 1, page_size: int = 20) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT COUNT(*) as cnt FROM audit_log")
            total = cursor.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cursor.execute(
                "SELECT id, qa_id, question, answer, result, operator, created_at "
                "FROM audit_log ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (page_size, offset),
            )
            rows = cursor.fetchall()
            cursor.close()
            return {"items": rows, "total": total, "page": page, "page_size": page_size}
        except Exception:
            self._reset_conn()
            raise

    def list_categories(self) -> list[dict]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT id, label, parent_id, description FROM categories ORDER BY id"
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            self._reset_conn()
            raise

    def create_category(self, label: str, parent_id: int | None,
                        description: str = "") -> int:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categories (label, parent_id, description) VALUES (%s, %s, %s)",
                (label, parent_id, description),
            )
            conn.commit()
            cat_id = cursor.lastrowid
            cursor.close()
            return cat_id
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def update_category(self, cat_id: int, label: str,
                        parent_id: int | None, description: str = "") -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE categories SET label=%s, parent_id=%s, description=%s WHERE id=%s",
                (label, parent_id, description, cat_id),
            )
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            return affected > 0
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def delete_category(self, cat_id: int) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id=%s", (cat_id,))
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            return affected > 0
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_trend(self, days: int = 7) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT DATE(created_at) as d, COUNT(*) as cnt FROM work_orders "
                "WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
                "GROUP BY DATE(created_at) ORDER BY d",
                (days,),
            )
            rows = cursor.fetchall()
            cursor.close()
            return {"items": rows}
        except Exception:
            self._reset_conn()
            raise

    def get_category_tree(self) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT DISTINCT category_l1, category_l2 FROM qa_pairs "
                "WHERE status='active' ORDER BY category_l1, category_l2"
            )
            rows = cursor.fetchall()
            cursor.close()
            tree = {}
            for row in rows:
                l1 = row["category_l1"] or ""
                l2 = row["category_l2"] or ""
                if l1 not in tree:
                    tree[l1] = []
                if l2 and l2 not in tree[l1]:
                    tree[l1].append(l2)
            return tree
        except Exception:
            self._reset_conn()
            raise

    def _reset_conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        self._local.conn = None

    def get_config(self, key: str, default=None):
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT config_value FROM system_config WHERE config_key=%s", (key,))
            row = cursor.fetchone()
            cursor.close()
            return row["config_value"] if row else default
        except Exception:
            self._reset_conn()
            return default

    def set_config(self, key: str, value, description: str = ""):
        import json
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            json_val = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            cursor.execute(
                "INSERT INTO system_config (config_key, config_value, description) "
                "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE config_value=%s, description=%s",
                (key, json_val, description, json_val, description),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise

    def get_prompt_template(self, key: str) -> str:
        conn = self._get_conn()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT template_text FROM prompt_templates WHERE prompt_key=%s AND is_active=1 AND status='active'",
                (key,),
            )
            row = cursor.fetchone()
            cursor.close()
            return row["template_text"] if row else ""
        except Exception:
            self._reset_conn()
            return ""

    def set_prompt_template(self, key: str, template_text: str, description: str = ""):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(version) as max_ver FROM prompt_templates WHERE prompt_key=%s",
                (key,),
            )
            row = cursor.fetchone()
            new_version = (row[0] + 1) if row[0] else 1
            cursor.execute(
                "UPDATE prompt_templates SET is_active=0 WHERE prompt_key=%s AND is_active=1",
                (key,),
            )
            cursor.execute(
                "INSERT INTO prompt_templates (prompt_key, template_text, version, is_active, status, description) "
                "VALUES (%s, %s, %s, 1, 'active', %s)",
                (key, template_text, new_version, description),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            self._reset_conn()
            raise
