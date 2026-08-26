import pytest


@pytest.mark.integration
class TestL2AddKnowledge:
    def test_add_knowledge_full_chain(self, qa_service, mysql_conn, milvus_conn):
        from models.schemas import AddQARequest
        req = AddQARequest(
            question="集成测试添加知识_ETC设备故障怎么办",
            answer="请先检查OBU设备指示灯，若红灯闪烁需更换电池，联系客服95022",
            category_l1="售后业务",
            category_l2="设备异常",
            internal_process="检查设备→判断故障类型→处理",
            feedback_dept="设备运维部",
        )

        qa_id = qa_service.add_knowledge(req)
        assert qa_id > 0

        record = mysql_conn.get_qa_detail(qa_id)
        assert record is not None
        assert record["question"] == "集成测试添加知识_ETC设备故障怎么办"
        assert record["answer"] == "请先检查OBU设备指示灯，若红灯闪烁需更换电池，联系客服95022"

        active_ids = mysql_conn.get_active_ids()
        assert qa_id in active_ids

        from rag.siliconflow import get_embedding_client
        vector = get_embedding_client().encode(["ETC设备故障怎么办"], normalize_embeddings=True).tolist()[0]
        results = milvus_conn.search(vector, top_k=5)
        found = any(r[0] == qa_id for r in results)
        assert found, f"新添加的qa_id={qa_id}在Milvus中搜索不到"

        bm25_results = qa_service.recall.bm25.search("ETC设备故障", top_k=10, active_qa_ids=active_ids)
        bm25_found = any(r[0] == qa_id for r in bm25_results)
        assert bm25_found, f"新添加的qa_id={qa_id}在BM25中搜索不到"

        mysql_conn.delete_qa(qa_id)
        try:
            from pymilvus import MilvusClient

            from utils.config import get_config
            cfg = get_config()
            client = MilvusClient(cfg["milvus"]["db_path"])
            client.delete(cfg["milvus"]["collection_name"], filter=f"id == {qa_id}")
            client.close()
        except Exception:
            pass

    def test_add_knowledge_via_api(self, real_client, mysql_conn):
        resp = real_client.post("/api/v1/add", json={
            "question": "集成测试API添加_ETC蓝牙连不上",
            "answer": "请打开手机蓝牙和ETC APP，靠近设备重新配对",
            "category_l1": "售后业务",
            "category_l2": "设备异常",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["qa_id"] > 0
        assert "添加成功" in data["message"]

        qa_id = data["qa_id"]
        record = mysql_conn.get_qa_detail(qa_id)
        assert record is not None
        assert record["question"] == "集成测试API添加_ETC蓝牙连不上"

        mysql_conn.delete_qa(qa_id)

    def test_add_knowledge_query_immediately(self, qa_service, mysql_conn):
        from models.schemas import AddQARequest
        req = AddQARequest(
            question="集成测试即时查询_ETC发票怎么开",
            answer="登录ETC APP，进入发票管理，选择通行记录开具电子发票",
            category_l1="售后业务",
            category_l2="发票",
        )

        qa_id = qa_service.add_knowledge(req)
        assert qa_id > 0

        result = qa_service.query("ETC发票怎么开")
        assert result.confidence in ("high", "mid", "low", "none")
        found = any(c.qa_id == qa_id for c in result.candidates)
        assert found, f"新添加的qa_id={qa_id}在查询结果中找不到"

        mysql_conn.delete_qa(qa_id)
        try:
            from utils.config import get_config
            cfg = get_config()
            from pymilvus import MilvusClient
            client = MilvusClient(cfg["milvus"]["db_path"])
            client.delete(cfg["milvus"]["collection_name"], filter=f"id == {qa_id}")
            client.close()
        except Exception:
            pass

    def test_add_knowledge_minimal_fields(self, qa_service, mysql_conn):
        from models.schemas import AddQARequest
        req = AddQARequest(
            question="集成测试最小字段_ETC客服电话",
            answer="ETC客服热线95022",
        )

        qa_id = qa_service.add_knowledge(req)
        assert qa_id > 0

        record = mysql_conn.get_qa_detail(qa_id)
        assert record["question"] == "集成测试最小字段_ETC客服电话"
        assert record["category_l1"] == ""

        mysql_conn.delete_qa(qa_id)
        try:
            from utils.config import get_config
            cfg = get_config()
            from pymilvus import MilvusClient
            client = MilvusClient(cfg["milvus"]["db_path"])
            client.delete(cfg["milvus"]["collection_name"], filter=f"id == {qa_id}")
            client.close()
        except Exception:
            pass

    def test_add_knowledge_duplicate_question(self, qa_service, mysql_conn):
        from models.schemas import AddQARequest
        req1 = AddQARequest(
            question="集成测试重复问题_ETC怎么注销",
            answer="携带设备到营业厅办理注销",
            category_l1="售后业务",
        )
        qa_id1 = qa_service.add_knowledge(req1)

        req2 = AddQARequest(
            question="集成测试重复问题_ETC怎么注销",
            answer="在线APP申请注销或到营业厅办理",
            category_l1="售后业务",
        )
        qa_id2 = qa_service.add_knowledge(req2)

        assert qa_id1 != qa_id2

        for qa_id in [qa_id1, qa_id2]:
            mysql_conn.delete_qa(qa_id)
            try:
                from utils.config import get_config
                cfg = get_config()
                from pymilvus import MilvusClient
                client = MilvusClient(cfg["milvus"]["db_path"])
                client.delete(cfg["milvus"]["collection_name"], filter=f"id == {qa_id}")
                client.close()
            except Exception:
                pass
