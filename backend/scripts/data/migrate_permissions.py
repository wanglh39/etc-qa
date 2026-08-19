import os, sys, json, pymysql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ['ETC_QA_ENV'] = 'dev'
from utils.config import load_config

cfg = load_config()
conn = pymysql.connect(
    host=cfg["mysql"]["host"],
    port=cfg["mysql"]["port"],
    user=cfg["mysql"]["user"],
    password=cfg["mysql"]["password"],
    database=cfg["mysql"]["database"],
    charset="utf8mb4",
)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE roles ADD COLUMN permissions JSON NULL")
    conn.commit()
    print("Added permissions column")
except Exception as e:
    conn.rollback()
    print(f"Column already exists or error: {e}")

default_permissions = {
    "superadmin": json.dumps([
        "/workbench/admin/account", "/workbench/admin/role",
        "/workbench/admin/operationLog", "/workbench/admin/impersonate",
        "/workbench/admin/dashboard", "/workbench/admin/knowledge",
        "/workbench/admin/category", "/workbench/admin/config",
        "/workbench/admin/auditList", "/workbench/admin/auditHistory",
        "/workbench/admin/status", "/workbench/admin/monitor",
        "/workbench/admin/scheduler", "/workbench/admin/alert",
        "/service",
        "/dept/handle/aftersale", "/dept/handle/ops", "/dept/handle/finance"
    ]),
    "admin": json.dumps([
        "/workbench/admin/dashboard", "/workbench/admin/auditList",
        "/workbench/admin/auditHistory", "/workbench/admin/knowledge",
        "/workbench/admin/category", "/workbench/admin/config"
    ]),
    "ops": json.dumps([
        "/workbench/admin/status", "/workbench/admin/monitor",
        "/workbench/admin/scheduler", "/workbench/admin/alert"
    ]),
    "service": json.dumps(["/service"]),
    "dept": json.dumps([
        "/dept/handle/aftersale", "/dept/handle/ops", "/dept/handle/finance"
    ]),
}

for role_key, perms in default_permissions.items():
    cursor.execute(
        "UPDATE roles SET permissions = %s WHERE role_key = %s AND (permissions IS NULL)",
        (perms, role_key)
    )
    print(f"Updated {role_key}: {cursor.rowcount} row(s)")

conn.commit()
cursor.close()
conn.close()
print("Done!")