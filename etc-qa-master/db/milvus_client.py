
from pymilvus import DataType, MilvusClient

from utils.config import get_config


class MilvusQA:
    def __init__(self):
        cfg = get_config()["milvus"]
        model_cfg = get_config()["models"]["embed"]
        self.db_path = cfg["db_path"]
        self.collection_name = cfg["collection_name"]
        self.dim = model_cfg["dim"]
        self.index_cfg = cfg.get("index", {"type": "HNSW", "M": 16, "ef_construction": 256})
        self.search_cfg = cfg.get("search", {"ef": 128, "overfetch_ratio": 3})
        self.schema_cfg = cfg.get("schema", {"category_l1_max_length": 50})
        self._client = None
        self._collection_loaded = False

    def _reconnect(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = MilvusClient(self.db_path)
        self._collection_loaded = False

    @property
    def client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(self.db_path)
        return self._client

    def init_collection(self):
        try:
            if self.client.has_collection(self.collection_name):
                return
        except Exception as e:
            if "too_many_pings" in str(e) or "UNAVAILABLE" in str(e):
                self._reconnect()
                if self.client.has_collection(self.collection_name):
                    return
            raise
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="qa_id", datatype=DataType.INT64)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.dim)
        schema.add_field(field_name="category_l1", datatype=DataType.VARCHAR, max_length=self.schema_cfg["category_l1_max_length"])
        schema.add_field(field_name="is_hyde", datatype=DataType.BOOL)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector", index_type=self.index_cfg.get("type", "HNSW"),
            metric_type="COSINE", params={"M": self.index_cfg.get("M", 16), "efConstruction": self.index_cfg.get("ef_construction", 256)}
        )
        self.client.create_collection(
            collection_name=self.collection_name, schema=schema, index_params=index_params
        )

    def _ensure_loaded(self):
        try:
            self.init_collection()
            if not self._collection_loaded:
                self.client.load_collection(self.collection_name)
                self._collection_loaded = True
        except Exception as e:
            if "too_many_pings" in str(e) or "UNAVAILABLE" in str(e) or "GOAWAY" in str(e):
                from utils.logger import get_logger
                get_logger("milvus").warning(f"_ensure_loaded gRPC错误，重连: {e}")
                self._reconnect()
                self.client.load_collection(self.collection_name)
                self._collection_loaded = True
            else:
                raise

    def _safe_search(self, **kwargs):
        try:
            return self.client.search(**kwargs)
        except Exception as e:
            if "too_many_pings" in str(e) or "UNAVAILABLE" in str(e) or "GOAWAY" in str(e):
                from utils.logger import get_logger
                get_logger("milvus").warning("gRPC连接断开，正在重连...")
                self._reconnect()
                self._ensure_loaded()
                return self.client.search(**kwargs)
            raise

    def insert(self, qa_id: int, vector: list[float], category_l1: str = "",
               hyde_vectors: list[list[float]] = None):
        self.init_collection()
        data = [{"id": qa_id, "qa_id": qa_id, "vector": vector, "category_l1": category_l1, "is_hyde": False}]
        if hyde_vectors:
            for i, hv in enumerate(hyde_vectors, start=1):
                data.append({
                    "id": qa_id * 1000 + i,
                    "qa_id": qa_id,
                    "vector": hv,
                    "category_l1": category_l1,
                    "is_hyde": True,
                })
        self.client.insert(collection_name=self.collection_name, data=data)
        self.client.load_collection(self.collection_name)
        self._collection_loaded = True

    def batch_insert(self, data: list[dict]):
        self.init_collection()
        self.client.insert(collection_name=self.collection_name, data=data)
        self.client.load_collection(self.collection_name)
        self._collection_loaded = True

    def search(self, query_vector: list[float], top_k: int = 10,
               category_filter: str | None = None,
               use_hyde: bool = True,
               active_qa_ids: list[int] | None = None) -> list[tuple]:
        self._ensure_loaded()
        ef = self.search_cfg.get("ef", 128)
        overfetch = self.search_cfg.get("overfetch_ratio", 3)
        search_params = {"metric_type": "COSINE", "params": {"ef": ef}}
        filter_parts = []
        if category_filter:
            filter_parts.append(f'category_l1 == "{category_filter}"')
        if not use_hyde:
            filter_parts.append("is_hyde == false")
        filter_expr = " and ".join(filter_parts)

        results = self._safe_search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k * overfetch if active_qa_ids else top_k,
            output_fields=["qa_id"],
            filter=filter_expr,
            search_params=search_params,
        )
        if not results or not results[0]:
            return []
        raw = [(r["entity"]["qa_id"], float(r["distance"])) for r in results[0]]
        if active_qa_ids is not None:
            active_set = set(active_qa_ids)
            raw = [(qid, score) for qid, score in raw if qid in active_set]
        return raw[:top_k]

    def close(self):
        if self._client:
            self._client.close()
        self._client = None
        self._collection_loaded = False
