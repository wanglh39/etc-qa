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

    print("鍔犺浇閰嶇疆...")
    cfg = load_config()

    errors = validate_config()
    if errors:
        print("閰嶇疆鏍￠獙澶辫触:")
        for e in errors:
            print(f"  {e}")
        raise SystemExit(1)
    print("閰嶇疆鏍￠獙閫氳繃")

    import torch
    torch.set_num_threads(1)

    print("鍔犺浇Embedding妯″瀷...")
    embed_model = SentenceTransformer(cfg["models"]["embed"]["path"])

    print("鍔犺浇Reranker妯″瀷...")
    rerank_model = None
    if cfg["rerank"]["enabled"]:
        rerank_model = CrossEncoder(cfg["models"]["rerank"]["path"])

    print("鍒濆鍖栨暟鎹簱杩炴帴...")
    mysql = MySQLClient()
    milvus = MilvusQA()

    print("鏋勫缓BM25绱㈠紩...")
    bm25 = BM25Index()
    all_qa = mysql.get_all_questions()
    bm25.build(all_qa)

    print("鍒濆鍖栧彫鍥炲紩鎿?..")
    recall = RecallEngine(embed_model, milvus, bm25)

    print("鍒濆鍖栭槇鍊煎垽瀹?..")
    threshold = ThresholdJudge()

    print("鍒濆鍖朢eranker...")
    reranker = Reranker(rerank_model, mysql_client=mysql)

    print("鍒濆鍖朡A鏈嶅姟...")
    service = QAService(recall, threshold, reranker, mysql)

    print("鍒濆鍖栧伐鍗曞鎴风...")
    wo_client = WorkOrderClient(use_mock=cfg["work_order"]["use_mock"])
    routes.set_service(service)
    routes.set_work_order_client(wo_client)
    routes.set_mysql_client(mysql)

    print("棰勭儹娴佸紡ASR妯″瀷...")
    from asr.streaming import get_streaming_service
    get_streaming_service().warmup()

    return service