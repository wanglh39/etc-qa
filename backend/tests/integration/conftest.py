import os
import sys
import time
from unittest.mock import MagicMock

import pytest

for _mod in ["sentence_transformers", "pymilvus", "langchain_openai"]:
    if _mod in sys.modules and isinstance(sys.modules[_mod], MagicMock):
        del sys.modules[_mod]

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["ETC_QA_ENV"] = "test"

try:
    import utils.config as _cfg_mod
    _cfg_mod._CONFIG = None
except Exception:
    pass

import pymysql


def wait_for_mysql(host="localhost", port=3306, user="root", password="123456",
                   database="etc_qa_test", timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            conn = pymysql.connect(host=host, port=port, user=user,
                                   password=password, database=database)
            conn.close()
            return True
        except Exception:
            time.sleep(1)
    return False


@pytest.fixture(scope="session")
def mysql_conn():
    if not wait_for_mysql():
        pytest.skip("MySQL不可用，跳过集成测试")
    from db.mysql_client import MySQLClient
    mysql = MySQLClient()
    yield mysql
    try:
        mysql.close()
    except Exception:
        pass


@pytest.fixture(scope="session")
def milvus_conn():
    from db.milvus_client import MilvusQA
    milvus = MilvusQA()
    milvus.init_collection()
    yield milvus
    try:
        milvus.close()
    except Exception:
        pass


@pytest.fixture(scope="session")
def embed_model():
    from rag.siliconflow import get_embedding_client
    return get_embedding_client()


@pytest.fixture(scope="session")
def bm25_index(mysql_conn):
    from rag.bm25_index import BM25Index
    bm25 = BM25Index()
    all_qa = mysql_conn.get_all_questions()
    bm25.build(all_qa)
    return bm25


@pytest.fixture(scope="session")
def recall_engine(embed_model, milvus_conn, bm25_index):
    from rag.recall import RecallEngine
    return RecallEngine(embed_model, milvus_conn, bm25_index)


@pytest.fixture(scope="session")
def threshold_judge():
    from rag.threshold import ThresholdJudge
    return ThresholdJudge()


@pytest.fixture(scope="session")
def reranker(mysql_conn):

    from utils.config import get_config
    cfg = get_config()
    from rag.reranker import Reranker
    if cfg["rerank"]["enabled"]:
        from rag.siliconflow import get_rerank_client
        return Reranker(get_rerank_client(), mysql_client=mysql_conn)
    return Reranker(None, mysql_client=mysql_conn)


@pytest.fixture(scope="session")
def qa_service(recall_engine, threshold_judge, reranker, mysql_conn):
    from rag.service import QAService
    return QAService(recall_engine, threshold_judge, reranker, mysql_conn)


@pytest.fixture(scope="session")
def real_app(qa_service, mysql_conn):
    from api import routes
    from api.work_order.client import WorkOrderClient
    from utils.config import get_config
    cfg = get_config()
    routes.set_service(qa_service)
    routes.set_mysql_client(mysql_conn)
    routes.set_work_order_client(WorkOrderClient(use_mock=cfg.get("work_order", {}).get("use_mock", True)))
    from fastapi import FastAPI

    from utils.auth_middleware import get_current_user
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test_user", "role": "admin"}
    app.include_router(routes.router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def real_client(real_app):
    from fastapi.testclient import TestClient
    return TestClient(real_app)


def pytest_collection_modifyitems(config, items):
    pass


_TEST_PROMPT_KEYS = [
    "test_int_prompt", "test_api_prompt", "test_int_tpl",
    "test_pe_key", "test_pe_syntax",
    "test_pe_cache", "test_cc_ptpl", "test_cc_prompt",
]


@pytest.fixture(autouse=True, scope="class")
def _cleanup_test_data():
    try:
        conn = pymysql.connect(host="localhost", port=3306, user="root",
                               password="123456", database="etc_qa_test")
        cursor = conn.cursor()
        for key in _TEST_PROMPT_KEYS:
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key=%s", (key,))
        cursor.execute("DELETE FROM system_config WHERE config_key='test_int_cfg'")
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass
    try:
        from utils.config_center import invalidate_cache
        invalidate_cache()
    except Exception:
        pass
    yield
