"""
数据库初始化脚本
1. 创建MySQL数据库和qa_pairs表
2. 从qa_filled.csv导入数据到MySQL
3. 创建Milvus Collection
4. 用bge-large-zh-v1.5编码问题向量，导入Milvus

运行：python init_db.py [env]
  env: dev / test / prod，默认test
"""

import csv
import os
import sys

import pymysql
from pymilvus import DataType, MilvusClient
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

env = sys.argv[1] if len(sys.argv) > 1 else "test"
os.environ['ETC_QA_ENV'] = env

from utils.config import load_config

cfg = load_config()

MYSQL_HOST = cfg["mysql"]["host"]
MYSQL_PORT = cfg["mysql"]["port"]
MYSQL_USER = cfg["mysql"]["user"]
MYSQL_PASSWORD = cfg["mysql"]["password"]
MYSQL_DB = cfg["mysql"]["database"]

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CSV_PATH = os.path.join(PROJECT_ROOT, cfg.get("data", {}).get("qa_csv", "data/processed/qa_filled.csv"))
MILVUS_DB = os.path.join(os.path.dirname(__file__), "..", "..", cfg["milvus"]["db_path"])
COLLECTION_NAME = cfg["milvus"]["collection_name"]
DIM = cfg["models"]["embed"]["dim"]
EMBED_MODEL_PATH = cfg["models"]["embed"]["path"]


def init_mysql():
    print("\n=== 第1步：初始化MySQL ===")

    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4"
    )
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{MYSQL_DB}`")

    cursor.execute("""
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            config_key VARCHAR(100) NOT NULL PRIMARY KEY,
            config_value JSON NOT NULL,
            description VARCHAR(500),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    cursor.execute("""
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    conn.commit()

    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='qa_pairs'", (MYSQL_DB,))
    existing_cols = {row[0] for row in cursor.fetchall()}
    if "status" not in existing_cols:
        print("  检测到旧表缺少status列，执行迁移...")
        cursor.execute("ALTER TABLE qa_pairs ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'")
        conn.commit()
    if "internal_process" not in existing_cols:
        cursor.execute("ALTER TABLE qa_pairs ADD COLUMN internal_process TEXT")
        conn.commit()
    if "feedback_dept" not in existing_cols:
        cursor.execute("ALTER TABLE qa_pairs ADD COLUMN feedback_dept TEXT")
        conn.commit()
    if "image_url" not in existing_cols:
        cursor.execute("ALTER TABLE qa_pairs ADD COLUMN image_url VARCHAR(500)")
        conn.commit()

    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='prompt_templates'", (MYSQL_DB,))
    pt_cols = {row[0] for row in cursor.fetchall()}
    if "status" not in pt_cols:
        print("  prompt_templates表缺少status列，执行迁移...")
        cursor.execute("ALTER TABLE prompt_templates ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'")
        conn.commit()
    if "created_at" not in pt_cols:
        cursor.execute("ALTER TABLE prompt_templates ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
    if "id" not in pt_cols:
        print("  prompt_templates表缺少id列，执行迁移...")
        try:
            cursor.execute("ALTER TABLE prompt_templates DROP PRIMARY KEY")
        except Exception as e:
            print(f"    DROP PRIMARY KEY跳过: {e}")
        cursor.execute("ALTER TABLE prompt_templates ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")
        try:
            cursor.execute("ALTER TABLE prompt_templates ADD UNIQUE KEY uk_key_version (prompt_key, version)")
        except Exception as e:
            print(f"    ADD UNIQUE KEY跳过: {e}")
        conn.commit()

    cursor.execute("""
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()

    cursor.close()
    conn.close()
    print(f"  数据库 {MYSQL_DB} 和表 qa_pairs 创建完成")


def init_work_orders_table():
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, charset="utf8mb4"
    )
    cursor = conn.cursor()
    cursor.execute(f"USE `{MYSQL_DB}`")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            external_id VARCHAR(100),
            raw_data TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'submitted',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    cursor.close()
    conn.close()


def import_to_mysql():
    print("\n=== 第2步：导入数据到MySQL ===")

    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4"
    )
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM qa_pairs")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  qa_pairs已有 {count} 条数据，跳过导入")
        cursor.close()
        conn.close()
        return

    qa_pairs = []
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 6:
                continue
            question = row[3].strip()
            answer = row[5].strip()
            category_l1 = row[0].strip()
            category_l2 = row[1].strip()
            internal_process = row[4].strip() if len(row) > 4 else ""
            feedback_dept = row[6].strip() if len(row) > 6 else ""
            image_url = row[7].strip() if len(row) > 7 else ""

            if question and answer and len(question) > 1:
                qa_pairs.append((
                    question, answer, category_l1, category_l2,
                    internal_process, feedback_dept, image_url
                ))

    sql = """
        INSERT INTO qa_pairs 
        (question, answer, category_l1, category_l2, 
         internal_process, feedback_dept, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.executemany(sql, qa_pairs)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM qa_pairs")
    total = cursor.fetchone()[0]
    print(f"  导入了 {total} 条数据到 qa_pairs")

    cursor.close()
    conn.close()


def init_milvus():
    print("\n=== 第3步：初始化Milvus ===")

    client = MilvusClient(MILVUS_DB)

    if client.has_collection(COLLECTION_NAME):
        try:
            client.drop_collection(COLLECTION_NAME)
        except Exception as e:
            if "WinError 183" in str(e) or "FileExistsError" in str(e):
                print("  Windows文件锁冲突，尝试删除数据库文件夹后重试...")
                client.close()
                import shutil
                if os.path.exists(MILVUS_DB):
                    shutil.rmtree(MILVUS_DB, ignore_errors=True)
                client = MilvusClient(MILVUS_DB)
            else:
                raise

    milvus_index_cfg = cfg.get("milvus", {}).get("index", {})
    milvus_schema_cfg = cfg.get("milvus", {}).get("schema", {})

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="qa_id", datatype=DataType.INT64)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=DIM)
    schema.add_field(field_name="category_l1", datatype=DataType.VARCHAR, max_length=milvus_schema_cfg.get("category_l1_max_length", 50))
    schema.add_field(field_name="is_hyde", datatype=DataType.BOOL)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type=milvus_index_cfg.get("type", "HNSW"),
        metric_type="COSINE",
        params={"M": milvus_index_cfg.get("M", 16), "efConstruction": milvus_index_cfg.get("ef_construction", 256)}
    )

    client.create_collection(
        collection_name=COLLECTION_NAME, schema=schema, index_params=index_params
    )
    print(f"  Milvus Collection {COLLECTION_NAME} 创建完成")
    client.close()


def import_to_milvus():
    print("\n=== 第4步：编码向量并导入Milvus ===")

    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, category_l1 FROM qa_pairs")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"  从MySQL读取了 {len(rows)} 条问题")

    print("  加载Embedding模型...")
    embed_model = SentenceTransformer(EMBED_MODEL_PATH)

    client = MilvusClient(MILVUS_DB)

    batch_size = 100
    total_inserted = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        questions = [row[1] for row in batch]

        print(f"  编码第 {i+1}-{i+len(batch)} 条问题...")
        vectors = embed_model.encode(questions, normalize_embeddings=True).tolist()

        data = []
        for j, row in enumerate(batch):
            data.append({
                "id": row[0],
                "qa_id": row[0],
                "vector": vectors[j],
                "category_l1": row[2] if row[2] else "",
                "is_hyde": False,
            })

        client.insert(collection_name=COLLECTION_NAME, data=data)
        total_inserted += len(data)

    print(f"  向Milvus插入了 {total_inserted} 条向量")
    client.load_collection(COLLECTION_NAME)
    print("  已加载Collection到内存")
    client.close()


def main():
    print("=== ETC客服QA数据库初始化 ===\n")

    skip_milvus = "--skip-milvus" in sys.argv
    force = "--force" in sys.argv

    init_mysql()
    import_to_mysql()
    init_work_orders_table()

    if skip_milvus:
        print("\n  --skip-milvus: 跳过Milvus初始化（保留已有向量数据）")
    else:
        if not force:
            try:
                test_client = MilvusClient(MILVUS_DB)
                if test_client.has_collection(COLLECTION_NAME):
                    test_client.load_collection(COLLECTION_NAME)
                    count = test_client.query(COLLECTION_NAME, filter="id >= 0", output_fields=["id"], limit=1)
                    test_client.close()
                    print(f"\n  Milvus已有Collection {COLLECTION_NAME}，如需重建请用 --force")
                    print("  跳过Milvus初始化（保留已有向量数据）")
                    skip_milvus = True
                else:
                    test_client.close()
            except Exception:
                pass

        if not skip_milvus:
            init_milvus()
            import_to_milvus()

    print("\n=== 初始化完成 ===")
    print(f"MySQL: {MYSQL_DB}.qa_pairs")
    print(f"Milvus: {COLLECTION_NAME}")


if __name__ == "__main__":
    main()
