import os
import time

import pytest

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["ETC_QA_ENV"] = "test"

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
    from utils.config import get_config
    cfg = get_config()
    import torch
    torch.set_num_threads(1)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(cfg["models"]["embed"]["path"])
    return model


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
        import torch
        torch.set_num_threads(1)
        from sentence_transformers import CrossEncoder
        rerank_model = CrossEncoder(cfg["models"]["rerank"]["path"])
        return Reranker(rerank_model, mysql_client=mysql_conn)
    return Reranker(None, mysql_client=mysql_conn)


@pytest.fixture(scope="session")
def qa_service(recall_engine, threshold_judge, reranker, mysql_conn):
    from rag.service import QAService
    return QAService(recall_engine, threshold_judge, reranker, mysql_conn)


@pytest.fixture(scope="session")
def real_app(qa_service, mysql_conn):
    from api import routes
    from api.work_order.client import WorkOrderClient
    from prompt.version_manager import get_version_manager
    from utils.config import get_config
    cfg = get_config()
    routes.set_service(qa_service)
    routes.set_mysql_client(mysql_conn)
    routes.set_work_order_client(WorkOrderClient(use_mock=cfg.get("work_order", {}).get("use_mock", True)))
    vm = get_version_manager()
    vm._mysql = mysql_conn
    vm._cols_cache = None
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def real_client(real_app):
    from fastapi.testclient import TestClient
    return TestClient(real_app)


def pytest_collection_modifyitems(config, items):
    marker = config.getoption("-m", default="")
    if not marker or "integration" not in marker:
        skip_integration = pytest.mark.skip(reason="需要 -m integration 才运行集成测试")
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip_integration)
