import json
import os
import sys

import pymysql

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

CONFIG_ITEMS = {
    "enterprise_name": ("enterprise_name", "企业名称（模板变量）"),
    "forbidden_new_kws": ("forbidden_new_kws", "幻觉检测关键词列表"),
    "must_preserve_kws": ("must_preserve_kws", "必须保留关键词列表"),
    "brand_keywords": ("brand_keywords", "品牌名列表"),
    "subject_keywords": ("subject_keywords", "业务主体关键词列表"),
    "question_words": ("question_words", "疑问词列表"),
    "preserve_question_words": ("preserve_question_words", "必须保留疑问词列表"),
    "filler_patterns": ("filler_patterns", "口语填充词正则列表"),
    "core_patterns": ("core_patterns", "同义替换规则列表"),
    "clean_rules": ("clean_rules", "业务特定清洗正则列表"),
    "qa_statuses": ("qa_statuses", "合法知识状态枚举"),
    "internal_process_keywords": ("internal_process_keywords", "内部流程操作关键词列表"),
}


def init_system_config():
    print("\n=== 初始化system_config表 ===")
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DB, charset="utf8mb4"
    )
    cursor = conn.cursor()

    prompts_cfg = cfg.get("prompts", {})

    for config_key, (yaml_key, desc) in CONFIG_ITEMS.items():
        value = prompts_cfg.get(yaml_key, cfg.get(yaml_key))
        if value is None:
            continue
        json_val = json.dumps(value, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO system_config (config_key, config_value, description) "
            "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE config_value=%s",
            (config_key, json_val, desc, json_val),
        )
        print(f"  {config_key}: {len(json_val)} chars")

    conn.commit()
    cursor.close()
    conn.close()
    print("  system_config初始化完成")


if __name__ == "__main__":
    init_system_config()
