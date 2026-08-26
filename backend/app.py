import os
import tempfile

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from filelock import FileLock

from api import routes
from api.work_order.client import WorkOrderClient
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.service import QAService
from rag.siliconflow import get_embedding_client, get_rerank_client
from rag.threshold import ThresholdJudge
from utils.config import load_config, validate_config
from utils.jwt_utils import set_mysql_client
from utils.logger import get_logger

logger = get_logger("app")

_MILVUS_LOCK_PATH = os.path.join(tempfile.gettempdir(), "etc_qa_milvus_init.lock")
_MILVUS_LOCK_TIMEOUT = 30


def create_service():

    logger.info("加载配置...")
    cfg = load_config()

    errors = validate_config()
    if errors:
        logger.error("配置校验失败:")
        for e in errors:
            logger.error(f"  {e}")
        raise SystemExit(1)
    logger.info("配置校验通过")

    rag_enabled = cfg.get("rag", {}).get("enabled", True)

    logger.info("初始化数据库连接...")
    mysql = MySQLClient()

    service = None
    if rag_enabled:
        logger.info("初始化Embedding客户端...")
        embed_model = get_embedding_client()

        logger.info("初始化Reranker客户端...")
        rerank_model = None
        if cfg["rerank"]["enabled"]:
            rerank_model = get_rerank_client()

        milvus = MilvusQA()

        logger.info("构建BM25索引...")
        bm25 = BM25Index()
        all_qa = mysql.get_all_questions()
        bm25.build(all_qa)

        logger.info("初始化召回引擎...")
        recall = RecallEngine(embed_model, milvus, bm25)

        logger.info("初始化阈值判定...")
        threshold = ThresholdJudge()

        logger.info("初始化Reranker...")
        reranker = Reranker(rerank_model, mysql_client=mysql)

        logger.info("初始化QA服务...")
        service = QAService(recall, threshold, reranker, mysql)

        logger.info(f"获取Milvus初始化锁: {_MILVUS_LOCK_PATH} (超时{_MILVUS_LOCK_TIMEOUT}s)")
        with FileLock(_MILVUS_LOCK_PATH, timeout=_MILVUS_LOCK_TIMEOUT):
            logger.info("预热RAG检索 (持有Milvus锁)...")
            try:
                service.query("ETC扣费异常怎么处理")
                logger.info("  RAG预热完成")
            except Exception as e:
                logger.warning(f"  RAG预热失败(不影响启动，首次查询时会重试): {e}")
        logger.info("Milvus初始化锁已释放")
    else:
        logger.info("RAG未启用，跳过Embedding/Reranker/Milvus加载")

    logger.info("初始化工单客户端...")
    wo_client = WorkOrderClient(use_mock=cfg["work_order"]["use_mock"])
    routes.set_service(service)
    routes.set_work_order_client(wo_client)
    routes.set_mysql_client(mysql)
    set_mysql_client(mysql)

    asr_enabled = cfg.get("asr", {}).get("enabled", False)
    if asr_enabled:
        logger.info("ASR API连通检查...")
        from asr.streaming import get_streaming_service

        get_streaming_service().warmup()
    else:
        logger.info("ASR未启用，跳过模型预热")

    return service
