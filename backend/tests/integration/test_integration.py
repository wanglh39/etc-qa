import os
from unittest.mock import MagicMock, patch

import pytest
import yaml

ETC_QA_ENV = os.environ.get("ETC_QA_ENV", "test")


def threshold_judge_mode():
    from utils.config import get_config

    return get_config().get("threshold", {}).get("mode", "absolute")


def _set_threshold_mode(mode: str):
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "rag.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        rag_cfg = yaml.safe_load(f)
    rag_cfg["threshold"]["mode"] = mode
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(rag_cfg, f, allow_unicode=True)
    from importlib import reload

    import utils.config as cfg_mod

    reload(cfg_mod)


@pytest.mark.integration
class TestL1MySQLConnection:
    def test_connection(self, mysql_conn):
        ids = mysql_conn.get_active_ids()
        assert isinstance(ids, list)

    def test_insert_and_query(self, mysql_conn):
        qa_id = mysql_conn.insert_qa(
            question="集成测试问题_L1",
            answer="集成测试答案",
            category_l1="测试",
            category_l2="集成",
        )
        assert qa_id > 0

        record = mysql_conn.get_qa_detail(qa_id)
        assert record is not None
        assert record["question"] == "集成测试问题_L1"

        mysql_conn.update_qa_status(qa_id, "deprecated")
        ids = mysql_conn.get_active_ids()
        assert qa_id not in ids

        mysql_conn.delete_qa(qa_id)

    def test_category_tree(self, mysql_conn):
        tree = mysql_conn.get_category_tree()
        assert isinstance(tree, dict)

    def test_count_qa(self, mysql_conn):
        counts = mysql_conn.count_qa()
        assert "total" in counts
        assert "active" in counts

    def test_config_read_write(self, mysql_conn):
        mysql_conn.set_config("test_int_key", {"val": "test_value"}, "集成测试")
        result = mysql_conn.get_config("test_int_key")
        assert result is not None

    def test_qa_search(self, mysql_conn):
        result = mysql_conn.search_qa(keyword="ETC", page=1, page_size=5)
        assert "items" in result
        assert "total" in result

    def test_qa_list(self, mysql_conn):
        result = mysql_conn.get_qa_list(page=1, page_size=5)
        assert "items" in result
        assert "total" in result

    def test_qa_list_with_category(self, mysql_conn):
        result = mysql_conn.get_qa_list(page=1, page_size=5, category_l1="售后业务")
        assert "items" in result

    def test_qa_detail(self, mysql_conn):
        qa_id = mysql_conn.insert_qa(
            question="集成测试详情查询",
            answer="详情答案",
            category_l1="测试",
        )
        detail = mysql_conn.get_qa_detail(qa_id)
        assert detail is not None
        assert detail["question"] == "集成测试详情查询"
        mysql_conn.delete_qa(qa_id)

    def test_delete_qa(self, mysql_conn):
        qa_id = mysql_conn.insert_qa(
            question="集成测试删除",
            answer="待删除",
        )
        assert mysql_conn.delete_qa(qa_id) is True
        assert mysql_conn.delete_qa(999999) is False

    def test_work_order_crud(self, mysql_conn):
        wo_id = mysql_conn.insert_work_order("WO_INT_001", "工单集成测试")
        assert wo_id > 0

        mysql_conn.update_work_order("WO_INT_001", "已处理", "processed")
        by_status = mysql_conn.get_work_orders_by_status("processed")
        assert any(wo["external_id"] == "WO_INT_001" for wo in by_status)

        mysql_conn.delete_work_orders_by_status(["processed"])

    def test_get_by_ids(self, mysql_conn):
        ids = mysql_conn.get_active_ids()
        if not ids:
            pytest.skip("无活跃QA数据")
        results = mysql_conn.get_by_ids(ids[:3])
        assert isinstance(results, list)

    def test_get_by_id(self, mysql_conn):
        qa_id = mysql_conn.insert_qa(question="集成测试get_by_id", answer="答案")
        result = mysql_conn.get_by_id(qa_id)
        assert result is not None
        assert result["id"] == qa_id
        mysql_conn.delete_qa(qa_id)

    def test_search_qa_with_filters(self, mysql_conn):
        result = mysql_conn.search_qa(keyword="ETC", category_l1="售后业务", page=1, page_size=5)
        assert "items" in result

    def test_config_set_and_get(self, mysql_conn):
        mysql_conn.set_config("test_int_config", {"val": 42}, "集成测试")
        result = mysql_conn.get_config("test_int_config")
        assert result is not None

        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_config WHERE config_key='test_int_config'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

    def test_prompt_template_crud(self, mysql_conn):
        mysql_conn.set_prompt_template("test_int_tpl", "模板内容 {{q}}", "集成测试模板")
        result = mysql_conn.get_prompt_template("test_int_tpl")
        assert result != ""
        assert "{{q}}" in result

        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key='test_int_tpl'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

    def test_get_by_ids_empty(self, mysql_conn):
        result = mysql_conn.get_by_ids([])
        assert result == []

    def test_get_by_ids_inactive(self, mysql_conn):
        qa_id = mysql_conn.insert_qa(question="集成测试inactive", answer="答案")
        mysql_conn.update_qa_status(qa_id, "deprecated")
        result = mysql_conn.get_by_ids([qa_id], only_active=False)
        assert isinstance(result, list)
        active_result = mysql_conn.get_by_ids([qa_id], only_active=True)
        assert not any(r["id"] == qa_id for r in active_result)
        mysql_conn.delete_qa(qa_id)

    def test_get_all_questions(self, mysql_conn):
        result = mysql_conn.get_all_questions(only_active=True)
        assert isinstance(result, list)
        result_all = mysql_conn.get_all_questions(only_active=False)
        assert isinstance(result_all, list)

    def test_count_work_orders(self, mysql_conn):
        result = mysql_conn.count_work_orders()
        assert "total" in result

    def test_get_category_stats(self, mysql_conn):
        result = mysql_conn.get_category_stats()
        assert isinstance(result, dict)

    def test_get_work_order_list(self, mysql_conn):
        result = mysql_conn.get_work_order_list(page=1, page_size=5)
        assert "items" in result
        assert "total" in result

    def test_get_qa_list_with_status(self, mysql_conn):
        result = mysql_conn.get_qa_list(page=1, page_size=5, status="active")
        assert "items" in result

    def test_search_qa_with_status(self, mysql_conn):
        result = mysql_conn.search_qa(keyword="ETC", status="active", page=1, page_size=5)
        assert "items" in result

    def test_get_config_default(self, mysql_conn):
        result = mysql_conn.get_config("nonexistent_key_xyz", default="fallback")
        assert result == "fallback"

    def test_set_config_string_value(self, mysql_conn):
        import json

        mysql_conn.set_config("test_str_cfg", json.dumps("字符串值"), "字符串配置测试")
        result = mysql_conn.get_config("test_str_cfg")
        assert result is not None
        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_config WHERE config_key='test_str_cfg'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

    def test_reset_conn(self, mysql_conn):
        mysql_conn._reset_conn()
        assert getattr(mysql_conn._local, "conn", None) is None
        mysql_conn._get_conn()


@pytest.mark.integration
class TestL1MilvusConnection:
    def test_init_collection(self, milvus_conn):
        assert milvus_conn._client is not None

    def test_insert_and_search(self, milvus_conn, embed_model):
        from utils.config import get_config

        cfg = get_config()
        dim = cfg["models"]["embed"]["dim"]

        vector = embed_model.encode(["ETC集成测试问题"], normalize_embeddings=True).tolist()[0]
        milvus_conn.insert(999999, vector, category_l1="测试")

        results = milvus_conn.search(vector, top_k=3)
        assert isinstance(results, list)

        try:
            from pymilvus import MilvusClient

            client = MilvusClient(cfg["milvus"]["db_path"])
            client.delete(cfg["milvus"]["collection_name"], filter="id == 999999")
            client.close()
        except Exception:
            pass

    def test_insert_with_hyde_vectors(self, milvus_conn, embed_model):
        vector = embed_model.encode(["ETC HyDE测试"], normalize_embeddings=True).tolist()[0]
        hyde_vec1 = embed_model.encode(["假设性问题1"], normalize_embeddings=True).tolist()[0]
        hyde_vec2 = embed_model.encode(["假设性问题2"], normalize_embeddings=True).tolist()[0]
        milvus_conn.insert(999998, vector, category_l1="测试", hyde_vectors=[hyde_vec1, hyde_vec2])

        results = milvus_conn.search(vector, top_k=3)
        assert isinstance(results, list)

        from utils.config import get_config

        cfg = get_config()
        try:
            from pymilvus import MilvusClient

            client = MilvusClient(cfg["milvus"]["db_path"])
            client.delete(cfg["milvus"]["collection_name"], filter="qa_id == 999998")
            client.close()
        except Exception:
            pass

    def test_search_with_category_filter(self, milvus_conn, embed_model, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据")
        vector = embed_model.encode(["ETC扣费异常"], normalize_embeddings=True).tolist()[0]
        results = milvus_conn.search(vector, top_k=5, category_filter="售后业务", active_qa_ids=active_ids)
        assert isinstance(results, list)

    def test_search_without_hyde(self, milvus_conn, embed_model, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据")
        vector = embed_model.encode(["ETC设备故障"], normalize_embeddings=True).tolist()[0]
        results = milvus_conn.search(vector, top_k=5, use_hyde=False, active_qa_ids=active_ids)
        assert isinstance(results, list)

    def test_batch_insert(self, milvus_conn, embed_model):
        vector = embed_model.encode(["批量插入测试"], normalize_embeddings=True).tolist()[0]
        data = [{"id": 999997, "qa_id": 999997, "vector": vector, "category_l1": "测试", "is_hyde": False}]
        milvus_conn.batch_insert(data)

        from utils.config import get_config

        cfg = get_config()
        try:
            from pymilvus import MilvusClient

            client = MilvusClient(cfg["milvus"]["db_path"])
            client.delete(cfg["milvus"]["collection_name"], filter="id == 999997")
            client.close()
        except Exception:
            pass

    def test_milvus_close_and_reconnect(self, milvus_conn):
        milvus_conn.close()
        assert milvus_conn._client is None
        milvus_conn.init_collection()
        assert milvus_conn._client is not None

    def test_milvus_reconnect_method(self, milvus_conn):
        milvus_conn._reconnect()
        assert milvus_conn._client is not None
        assert milvus_conn._collection_loaded is False

    def test_milvus_client_property(self, milvus_conn):
        milvus_conn._client = None
        client = milvus_conn.client
        assert client is not None

    def test_milvus_search_empty_result(self, milvus_conn, embed_model):
        vector = embed_model.encode(["完全不相关的查询xyz123"], normalize_embeddings=True).tolist()[0]
        results = milvus_conn.search(vector, top_k=1, category_filter="不存在的分类")
        assert isinstance(results, list)

    def test_milvus_ensure_loaded(self, milvus_conn):
        milvus_conn._collection_loaded = False
        milvus_conn._ensure_loaded()
        assert milvus_conn._collection_loaded is True


@pytest.mark.integration
class TestL2RAGRecall:
    def test_vector_recall(self, recall_engine, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据，跳过")

        vector = recall_engine.encode_query("ETC扣费异常怎么处理")
        results = recall_engine.vector_recall(vector, active_qa_ids=active_ids)
        assert isinstance(results, list)

    def test_bm25_recall(self, bm25_index, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据，跳过")

        results = bm25_index.search("ETC扣费异常", top_k=5, active_qa_ids=active_ids)
        assert isinstance(results, list)

    def test_full_recall(self, recall_engine, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据，跳过")

        results = recall_engine.recall("ETC扣费异常怎么处理", active_qa_ids=active_ids)
        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], tuple)
            assert len(results[0]) == 2

    def test_reranker(self, reranker, recall_engine, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据，跳过")

        candidates = recall_engine.recall("ETC扣费异常", active_qa_ids=active_ids)
        if not candidates:
            pytest.skip("召回结果为空，跳过")

        reranked = reranker.rerank("ETC扣费异常", candidates)
        assert isinstance(reranked, list)

    def test_threshold(self, threshold_judge, recall_engine, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据，跳过")

        candidates = recall_engine.recall("ETC扣费异常", active_qa_ids=active_ids)
        confidence, filtered = threshold_judge.filter_candidates(candidates)
        assert confidence in ("high", "mid", "low", "none")
        assert isinstance(filtered, list)

    def test_threshold_empty_candidates(self, threshold_judge):
        confidence, filtered = threshold_judge.filter_candidates([])
        assert confidence == "none"
        assert filtered == []

    def test_threshold_absolute_high(self):
        _set_threshold_mode("absolute")
        try:
            from rag.threshold import ThresholdJudge

            tj = ThresholdJudge()
            confidence, count = tj.judge([(1, 0.95)])
            assert confidence == "high"
        finally:
            _set_threshold_mode("gap")

    def test_threshold_absolute_mid(self):
        _set_threshold_mode("absolute")
        try:
            from rag.threshold import ThresholdJudge

            tj = ThresholdJudge()
            confidence, count = tj.judge([(1, 0.65)])
            assert confidence == "mid"
        finally:
            _set_threshold_mode("gap")

    def test_threshold_absolute_low(self):
        _set_threshold_mode("absolute")
        try:
            from rag.threshold import ThresholdJudge

            tj = ThresholdJudge()
            confidence, count = tj.judge([(1, 0.35)])
            assert confidence == "low"
        finally:
            _set_threshold_mode("gap")

    def test_threshold_absolute_none(self):
        _set_threshold_mode("absolute")
        try:
            from rag.threshold import ThresholdJudge

            tj = ThresholdJudge()
            confidence, count = tj.judge([(1, 0.1)])
            assert confidence == "none"
        finally:
            _set_threshold_mode("gap")

    def test_threshold_gap_single_candidate(self):
        from rag.threshold import ThresholdJudge

        original_mode = threshold_judge_mode()
        _set_threshold_mode("gap")
        try:
            tj = ThresholdJudge()
            confidence, count = tj.judge([(1, 0.9)])
            assert confidence in ("high", "mid", "low", "none")
        finally:
            _set_threshold_mode(original_mode)

    def test_threshold_gap_mode(self):
        original_mode = threshold_judge_mode()
        _set_threshold_mode("gap")
        try:
            from rag.threshold import ThresholdJudge

            tj = ThresholdJudge()
            assert tj.mode == "gap"
            candidates = [(1, 0.9), (2, 0.7)]
            confidence, count = tj.judge(candidates)
            assert confidence in ("high", "mid", "low", "none")
        finally:
            _set_threshold_mode(original_mode)

    def test_full_query(self, qa_service):
        result = qa_service.query("ETC扣费异常怎么处理")
        assert result.confidence in ("high", "mid", "low", "none")
        assert isinstance(result.candidates, list)

    def test_query_with_category(self, qa_service):
        result = qa_service.query("ETC扣费异常", category_l1="售后业务")
        assert result.confidence in ("high", "mid", "low", "none")

    def test_recall_encode_query(self, recall_engine):
        vector = recall_engine.encode_query("ETC扣费异常")
        assert isinstance(vector, list)
        assert len(vector) > 0

    def test_rrf_merge(self, recall_engine):
        vec = [(1, 0.9), (2, 0.8), (3, 0.7)]
        bm25 = [(2, 10.0), (4, 9.0), (1, 8.0)]
        merged = recall_engine.rrf_merge(vec, bm25)
        assert isinstance(merged, list)
        assert len(merged) > 0

    def test_weighted_rrf_merge(self, recall_engine):
        vec = [(1, 0.9), (2, 0.8)]
        bm25 = [(2, 10.0), (3, 9.0)]
        merged = recall_engine.weighted_rrf_merge(vec, bm25)
        assert isinstance(merged, list)

    def test_reranker_empty_candidates(self, reranker):
        result = reranker.rerank("ETC扣费异常", [])
        assert result == []

    def test_reranker_disabled(self, mysql_conn):
        from rag.reranker import Reranker

        r = Reranker(None, mysql_client=mysql_conn)
        candidates = [(1, 0.9)]
        result = r.rerank("测试", candidates)
        assert result == candidates


@pytest.mark.integration
class TestL3AgentPipeline:
    def test_preprocess_agent(self):
        from agent.graph import preprocess_agent
        from agent.state import AgentState

        state = AgentState(raw_question="我想问一下ETC扣费扣多了怎么办啊")
        result = preprocess_agent.invoke(state.model_dump())
        assert "question" in result
        assert result["question"] != ""

    def test_ingest_agent(self):
        from agent.graph import ingest_agent
        from agent.state import AgentState

        state = AgentState(
            raw_question="ETC重复扣费怎么退款",
            raw_answer="核实扣费记录后3个工作日退款到原支付账户",
        )
        result = ingest_agent.invoke(state.model_dump())
        assert "question" in result
        assert "category_l1" in result


@pytest.mark.integration
class TestL4APIEndToEnd:
    def test_health(self, real_client):
        resp = real_client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_query(self, real_client):
        resp = real_client.post("/api/v1/query", json={"question": "ETC扣费异常"})
        assert resp.status_code == 200
        data = resp.json()
        assert "confidence" in data
        assert "candidates" in data

    def test_query_with_category(self, real_client):
        resp = real_client.post("/api/v1/query", json={"question": "ETC扣费异常", "category_l1": "售后业务"})
        assert resp.status_code == 200

    def test_stats(self, real_client):
        resp = real_client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "qa_total" in data

    def test_categories(self, real_client):
        resp = real_client.get("/api/v1/categories")
        assert resp.status_code == 200

    def test_qa_list(self, real_client):
        resp = real_client.get("/api/v1/qa/list")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_qa_search(self, real_client):
        resp = real_client.post("/api/v1/qa/search", json={"keyword": "ETC"})
        assert resp.status_code == 200

    def test_config_get(self, real_client):
        resp = real_client.get("/api/v1/config/enterprise_name")
        assert resp.status_code == 200

    def test_config_reload(self, real_client):
        resp = real_client.post("/api/v1/config/reload")
        assert resp.status_code == 200

    def test_work_orders_list(self, real_client):
        resp = real_client.get("/api/v1/work_orders")
        assert resp.status_code == 200

    def test_agent_process(self, real_client):
        resp = real_client.post(
            "/api/v1/agent/process",
            json={
                "question": "ETC重复扣费怎么退款",
                "answer": "核实扣费记录后3个工作日退款到原支付账户",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "question" in data
        assert "category_l1" in data

    def test_add_qa_via_api(self, real_client, mysql_conn):
        resp = real_client.post(
            "/api/v1/add",
            json={
                "question": "集成测试API添加_ETC设备亮红灯",
                "answer": "OBU设备红灯闪烁表示电池电量不足，请更换电池",
                "category_l1": "售后业务",
                "category_l2": "设备异常",
            },
        )
        assert resp.status_code == 200
        qa_id = resp.json()["qa_id"]

        resp = real_client.get(f"/api/v1/qa/{qa_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "集成测试API添加_ETC设备亮红灯"

        resp = real_client.put("/api/v1/qa/status", json={"qa_id": qa_id, "status": "deprecated"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "deprecated"

        resp = real_client.delete(f"/api/v1/qa/{qa_id}")
        assert resp.status_code == 200

    def test_get_qa_detail_not_found(self, real_client):
        resp = real_client.get("/api/v1/qa/999999")
        assert resp.status_code == 404

    def test_delete_qa_not_found(self, real_client):
        resp = real_client.delete("/api/v1/qa/999999")
        assert resp.status_code == 404

    def test_update_status_invalid(self, real_client):
        resp = real_client.put("/api/v1/qa/status", json={"qa_id": 1, "status": "invalid_status"})
        assert resp.status_code == 400

    def test_qa_list_with_filters(self, real_client):
        resp = real_client.get("/api/v1/qa/list", params={"category_l1": "售后业务", "page_size": 5})
        assert resp.status_code == 200

    def test_qa_search_with_filters(self, real_client):
        resp = real_client.post(
            "/api/v1/qa/search",
            json={
                "keyword": "ETC",
                "category_l1": "售后业务",
                "page_size": 5,
            },
        )
        assert resp.status_code == 200

    def test_config_update_and_get(self, real_client, mysql_conn):
        resp = real_client.put(
            "/api/v1/config/test_int_cfg",
            json={
                "value": {"k": "v"},
                "description": "集成测试配置",
            },
        )
        assert resp.status_code == 200

        resp = real_client.get("/api/v1/config/test_int_cfg")
        assert resp.status_code == 200
        assert resp.json()["value"] is not None

        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_config WHERE config_key='test_int_cfg'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

    def test_work_orders_list_with_status(self, real_client):
        resp = real_client.get("/api/v1/work_orders", params={"status": "submitted"})
        assert resp.status_code == 200


@pytest.mark.integration
class TestL2WorkOrderClient:
    def test_create_mock_work_order(self):
        from api.work_order.client import WorkOrderClient

        client = WorkOrderClient(use_mock=True)
        wo_id = client.create_work_order("ETC扣费异常", "售后业务")
        assert wo_id.startswith("WO-")

    def test_fetch_processed_mock(self):
        from api.work_order.client import WorkOrderClient

        client = WorkOrderClient(use_mock=True)
        client.create_work_order("ETC退款问题", "售后业务")
        results = client.fetch_processed_work_orders()
        assert isinstance(results, list)

    def test_real_create_not_implemented(self):
        from api.work_order.client import WorkOrderClient

        client = WorkOrderClient(use_mock=False)
        with pytest.raises(NotImplementedError):
            client.create_work_order("测试", "测试")

    def test_real_fetch_not_implemented(self):
        from api.work_order.client import WorkOrderClient

        client = WorkOrderClient(use_mock=False)
        with pytest.raises(NotImplementedError):
            client.fetch_processed_work_orders()


@pytest.mark.integration
class TestL2PromptEngine:
    def test_render_with_fallback(self):
        from agent.prompt_engine import PromptEngine

        pe = PromptEngine()
        result = pe.render("nonexistent_key_xyz", fallback="测试模板 {{question}}", question="ETC扣费")
        assert "ETC扣费" in result

    def test_render_with_db_template(self, mysql_conn):
        mysql_conn.set_prompt_template("test_pe_key", "DB模板 {{question}}", "PE集成测试")
        from agent.prompt_engine import PromptEngine

        pe = PromptEngine()
        PromptEngine.invalidate_cache("test_pe_key")
        result = pe.render("test_pe_key", fallback="fallback", question="ETC退款")
        assert "DB模板" in result or "ETC退款" in result

        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key='test_pe_key'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

    def test_get_prompt_engine_singleton(self):
        from agent.prompt_engine import get_prompt_engine

        pe1 = get_prompt_engine()
        pe2 = get_prompt_engine()
        assert pe1 is pe2


@pytest.mark.integration
class TestL2LLM:
    def test_get_llm(self):
        from agent.llm import get_llm

        llm = get_llm()
        assert llm is not None

    def test_get_structured_llm(self):
        from agent.llm import get_structured_llm
        from agent.output_schemas import StandardizeOutput

        llm, supported = get_structured_llm(StandardizeOutput)
        assert llm is not None
        assert isinstance(supported, bool)

    def test_get_structured_method(self):
        from agent.llm import _get_structured_method

        method = _get_structured_method("deepseek-chat")
        assert method is None or isinstance(method, str)


@pytest.mark.integration
class TestL2RerankerNoMysql:
    def test_reranker_no_mysql(self):
        from rag.reranker import Reranker

        r = Reranker(None, mysql_client=None)
        candidates = [(1, 0.9)]
        result = r.rerank("测试", candidates)
        assert result == candidates


@pytest.mark.integration
class TestL2BM25Index:
    def test_bm25_search_no_active_ids(self, bm25_index):
        results = bm25_index.search("ETC扣费", top_k=5, active_qa_ids=[])
        assert isinstance(results, list)

    def test_bm25_search_with_active_ids(self, bm25_index, mysql_conn):
        active_ids = mysql_conn.get_active_ids()
        if not active_ids:
            pytest.skip("无活跃QA数据")
        results = bm25_index.search("ETC扣费异常", top_k=5, active_qa_ids=active_ids)
        assert isinstance(results, list)


@pytest.mark.integration
class TestL2ConfigCenter:
    def test_yaml_fallback(self):
        from utils.config_center import get_business_config, invalidate_cache

        invalidate_cache("nonexistent_yaml_key_999")
        result = get_business_config("nonexistent_yaml_key_999", default="yaml_default")
        assert result == "yaml_default"

    def test_cache_ttl_expiry(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache

        mysql_conn.set_config("test_cc_ttl", {"v": "1"}, "TTL测试")
        invalidate_cache("test_cc_ttl")
        get_business_config("test_cc_ttl")
        with _cache_lock:
            assert "test_cc_ttl" in _cache
        invalidate_cache("test_cc_ttl")
        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_config WHERE config_key='test_cc_ttl'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

    def test_get_prompt_template_from_config_center(self, mysql_conn):
        from utils.config_center import get_prompt_template, invalidate_cache

        mysql_conn.set_prompt_template("test_cc_ptpl", "CC模板 {{q}}", "CC模板测试")
        invalidate_cache("test_cc_ptpl")
        result = get_prompt_template("test_cc_ptpl")
        assert result != ""

        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key='test_cc_ptpl'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()


@pytest.mark.integration
class TestL2MySQLClientErrorHandling:
    def test_insert_qa_error_rollback(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.insert_qa("test", "test")

    def test_get_all_questions_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_all_questions()

    def test_update_qa_status_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.update_qa_status(999, "active")

    def test_delete_qa_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.delete_qa(999)

    def test_get_qa_detail_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_qa_detail(999)

    def test_search_qa_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.search_qa("test")

    def test_count_qa_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.count_qa()

    def test_count_work_orders_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.count_work_orders()

    def test_get_category_stats_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_category_stats()

    def test_get_category_tree_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_category_tree()

    def test_get_active_ids_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_active_ids()

    def test_get_qa_list_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_qa_list()

    def test_get_work_order_list_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_work_order_list()

    def test_get_config_error_returns_default(self, mysql_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("查询失败")
        mock_conn.cursor.return_value = mock_cursor
        with patch.object(mysql_conn, "_get_conn", return_value=mock_conn):
            result = mysql_conn.get_config("nonexistent_key", default="fallback")
            assert result == "fallback"

    def test_set_config_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.set_config("test_key", "test_val")

    def test_get_prompt_template_error_returns_empty(self, mysql_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("查询失败")
        mock_conn.cursor.return_value = mock_cursor
        with patch.object(mysql_conn, "_get_conn", return_value=mock_conn):
            result = mysql_conn.get_prompt_template("nonexistent_key")
            assert result == ""

    def test_get_by_ids_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_by_ids([1, 2])

    def test_insert_work_order_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.insert_work_order("ext_1", "test")

    def test_update_work_order_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.update_work_order("ext_1", "data", "processed")

    def test_get_work_orders_by_status_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_work_orders_by_status("submitted")

    def test_delete_work_orders_by_status_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.delete_work_orders_by_status(["submitted"])

    def test_set_prompt_template_error(self, mysql_conn):
        with patch.object(mysql_conn, "_get_conn", side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.set_prompt_template("test_key", "template text")

    def test_reset_conn(self, mysql_conn):
        mysql_conn._reset_conn()
        assert getattr(mysql_conn._local, "conn", None) is None


@pytest.mark.integration
class TestL2MilvusClientErrorHandling:
    def test_init_collection_grpc_error_then_reconnect(self, milvus_conn):
        original_client = milvus_conn._client
        mock_client = MagicMock()
        mock_client.has_collection.side_effect = Exception("too_many_pings")
        mock_client2 = MagicMock()
        mock_client2.has_collection.return_value = True
        call_count = [0]

        def fake_reconnect():
            milvus_conn._client = mock_client2
            milvus_conn._collection_loaded = False

        with patch.object(milvus_conn, "_reconnect", side_effect=fake_reconnect):
            milvus_conn._client = mock_client
            milvus_conn.init_collection()

        milvus_conn._client = original_client

    def test_ensure_loaded_grpc_error_then_reconnect(self, milvus_conn):
        original_client = milvus_conn._client
        milvus_conn._collection_loaded = False
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.load_collection.side_effect = [
            Exception("GOAWAY error"),
            None,
        ]
        call_count = [0]

        def fake_reconnect():
            milvus_conn._client = mock_client
            milvus_conn._collection_loaded = False

        with patch.object(milvus_conn, "_reconnect", side_effect=fake_reconnect):
            milvus_conn._client = mock_client
            milvus_conn._ensure_loaded()

        milvus_conn._client = original_client
        milvus_conn._collection_loaded = True

    def test_safe_search_grpc_error_then_reconnect(self, milvus_conn):
        original_client = milvus_conn._client
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.side_effect = [
            Exception("UNAVAILABLE"),
            [{"entity": {"qa_id": 1}, "distance": 0.9}],
        ]
        mock_client.load_collection.return_value = None

        def fake_reconnect():
            milvus_conn._client = mock_client
            milvus_conn._collection_loaded = False

        with patch.object(milvus_conn, "_reconnect", side_effect=fake_reconnect):
            milvus_conn._client = mock_client
            result = milvus_conn._safe_search(
                collection_name="test",
                data=[[0.1] * 1024],
                limit=5,
                output_fields=["qa_id"],
                filter="",
                search_params={"metric_type": "COSINE"},
            )
            assert result is not None

        milvus_conn._client = original_client

    def test_init_collection_unknown_error_raises(self, milvus_conn):
        original_client = milvus_conn._client
        mock_client = MagicMock()
        mock_client.has_collection.side_effect = Exception("unknown error")

        milvus_conn._client = mock_client
        with pytest.raises(Exception, match="unknown error"):
            milvus_conn.init_collection()

        milvus_conn._client = original_client

    def test_ensure_loaded_unknown_error_raises(self, milvus_conn):
        original_client = milvus_conn._client
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.load_collection.side_effect = Exception("unknown error")

        milvus_conn._client = mock_client
        milvus_conn._collection_loaded = False
        with pytest.raises(Exception, match="unknown error"):
            milvus_conn._ensure_loaded()

        milvus_conn._client = original_client
        milvus_conn._collection_loaded = True


@pytest.mark.integration
class TestL2LLMStructuredOutput:
    def test_structured_output_fallback_on_exception(self):
        from agent.llm import _structured_cache, get_structured_llm
        from agent.output_schemas import StandardizeOutput

        _structured_cache.clear()

        with patch("agent.llm.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.model = "test-model"
            mock_llm.with_structured_output.side_effect = Exception("不支持structured output")
            mock_get_llm.return_value = mock_llm

            with patch("agent.llm._get_structured_method", return_value="json_schema"):
                llm, supported = get_structured_llm(StandardizeOutput)
                assert supported is False

    def test_llm_not_enabled_raises(self):
        from agent.llm import get_llm

        mock_cfg = {"enabled": False, "provider": "test", "model": "test", "base_url": "test", "api_key": "test"}
        with patch("agent.llm.get_config", return_value={"llm": mock_cfg}):
            with pytest.raises(RuntimeError, match="LLM未启用"):
                get_llm()
