import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from sentence_transformers import CrossEncoder, SentenceTransformer

from api import routes
from api.work_order.client import WorkOrderClient
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.service import QAService
from rag.threshold import ThresholdJudge
from utils.config import load_config, validate_config


def create_service():

    print("加载配置...")
    cfg = load_config()

    errors = validate_config()
    if errors:
        print("配置校验失败:")
        for e in errors:
            print(f"  {e}")
        raise SystemExit(1)
    print("配置校验通过")

    import torch
    torch.set_num_threads(1)

    print("加载Embedding模型...")
    embed_model = SentenceTransformer(cfg["models"]["embed"]["path"])

    print("加载Reranker模型...")
    rerank_model = None
    if cfg["rerank"]["enabled"]:
        rerank_model = CrossEncoder(cfg["models"]["rerank"]["path"])

    print("初始化数据库连接...")
    mysql = MySQLClient()
    milvus = MilvusQA()

    print("构建BM25索引...")
    bm25 = BM25Index()
    all_qa = mysql.get_all_questions()
    bm25.build(all_qa)

    print("初始化召回引擎...")
    recall = RecallEngine(embed_model, milvus, bm25)

    print("初始化阈值判定...")
    threshold = ThresholdJudge()

    print("初始化Reranker...")
    reranker = Reranker(rerank_model, mysql_client=mysql)

    print("初始化QA服务...")
    service = QAService(recall, threshold, reranker, mysql)

    print("初始化工单客户端...")
    wo_client = WorkOrderClient(use_mock=cfg["work_order"]["use_mock"])
    routes.set_service(service)
    routes.set_work_order_client(wo_client)
    routes.set_mysql_client(mysql)


    return service
