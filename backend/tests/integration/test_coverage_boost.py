import os
from unittest.mock import MagicMock, patch

import pytest

os.environ["ETC_QA_ENV"] = "test"


@pytest.mark.integration
class TestL2MySQLClientErrorHandling:
    def test_insert_qa_error_rollback(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.insert_qa("test", "test")

    def test_get_all_questions_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_all_questions()

    def test_update_qa_status_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.update_qa_status(999, "active")

    def test_delete_qa_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.delete_qa(999)

    def test_get_qa_detail_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_qa_detail(999)

    def test_search_qa_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.search_qa("test")

    def test_count_qa_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.count_qa()

    def test_count_work_orders_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.count_work_orders()

    def test_get_category_stats_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_category_stats()

    def test_get_category_tree_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_category_tree()

    def test_get_active_ids_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_active_ids()

    def test_get_qa_list_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_qa_list()

    def test_get_work_order_list_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_work_order_list()

    def test_get_config_error_returns_default(self, mysql_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("查询失败")
        mock_conn.cursor.return_value = mock_cursor
        with patch.object(mysql_conn, '_get_conn', return_value=mock_conn):
            result = mysql_conn.get_config("nonexistent_key", default="fallback")
            assert result == "fallback"

    def test_set_config_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.set_config("test_key", "test_val")

    def test_get_prompt_template_error_returns_empty(self, mysql_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("查询失败")
        mock_conn.cursor.return_value = mock_cursor
        with patch.object(mysql_conn, '_get_conn', return_value=mock_conn):
            result = mysql_conn.get_prompt_template("nonexistent_key")
            assert result == ""

    def test_get_by_ids_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_by_ids([1, 2])

    def test_insert_work_order_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.insert_work_order("ext_1", "test")

    def test_update_work_order_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.update_work_order("ext_1", "data", "processed")

    def test_get_work_orders_by_status_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.get_work_orders_by_status("submitted")

    def test_delete_work_orders_by_status_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                mysql_conn.delete_work_orders_by_status(["submitted"])

    def test_set_prompt_template_error(self, mysql_conn):
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
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

        with patch.object(milvus_conn, '_reconnect', side_effect=fake_reconnect):
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

        with patch.object(milvus_conn, '_reconnect', side_effect=fake_reconnect):
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

        with patch.object(milvus_conn, '_reconnect', side_effect=fake_reconnect):
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

        with patch('agent.llm.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.model = "test-model"
            mock_llm.with_structured_output.side_effect = Exception("不支持structured output")
            mock_get_llm.return_value = mock_llm

            with patch('agent.llm._get_structured_method', return_value="json_schema"):
                llm, supported = get_structured_llm(StandardizeOutput)
                assert supported is False

    def test_llm_not_enabled_raises(self):
        from agent.llm import get_llm
        mock_cfg = {"enabled": False, "provider": "test", "model": "test", "base_url": "test", "api_key": "test"}
        with patch('agent.llm.get_config', return_value={"llm": mock_cfg}):
            with pytest.raises(RuntimeError, match="LLM未启用"):
                get_llm()


@pytest.mark.integration
class TestL2StructureIngestStructuredResult:
    def test_process_structured_result_invalid_l1(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC设备故障",
            answer="请检查OBU设备",
            category_l1="不存在的分类",
            category_l2="子分类",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常", "账单问题"]}
        result = _process_structured_result(mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state)
        assert result["category_l1"] == "售后业务"
        assert result["category_l2"] == "设备异常"

    def test_process_structured_result_invalid_l2(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC扣费异常",
            answer="请查看账单",
            category_l1="售后业务",
            category_l2="不存在的子分类",
            category_confidence=0.8,
            internal_process="查看账单",
            feedback_dept="客服部",
        )
        state = AgentState(raw_question="ETC扣费异常", raw_answer="请查看账单")
        tree = {"售后业务": ["设备异常", "账单问题"]}
        result = _process_structured_result(mock_result, "ETC扣费异常", "请查看账单", tree, "售后业务", "设备异常", state)
        assert result["category_l1"] == "售后业务"
        assert result["category_l2"] == "设备异常"

    def test_process_structured_result_hallucination(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC设备故障银行卡退款",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["银行卡", "退款"], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state)
        assert result["question"] == "ETC设备故障"
        assert result["needs_review"] is True

    def test_process_structured_result_lost_keywords(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="设备故障",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["银行卡"], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state)
        assert result["needs_review"] is True

    def test_process_structured_result_short_rewrite(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="E",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["银行卡"], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state)
        assert result["question"] == "ETC设备故障"
        assert result["needs_review"] is True

    def test_process_structured_result_low_confidence(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC设备故障",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.2,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["银行卡"], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state)
        assert result["needs_review"] is True


@pytest.mark.integration
class TestL2APIRoutesASRError:
    def test_asr_disabled_returns_503(self, real_client):
        from asr.service import get_asr_service
        svc = get_asr_service()
        original_enabled = svc._enabled
        svc._enabled = False
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"fake audio")
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
            assert resp.status_code == 503
            os.unlink(tmp_path)
        finally:
            svc._enabled = original_enabled

    def test_asr_file_not_found_returns_404(self, real_client):
        from asr.service import get_asr_service
        svc = get_asr_service()
        with patch.object(svc, 'transcribe', side_effect=FileNotFoundError("文件不存在")):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"fake audio")
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
            assert resp.status_code == 404
            os.unlink(tmp_path)

    def test_asr_runtime_error_returns_503(self, real_client):
        from asr.service import get_asr_service
        svc = get_asr_service()
        with patch.object(svc, 'transcribe', side_effect=RuntimeError("模型未加载")):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"fake audio")
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
            assert resp.status_code == 503
            os.unlink(tmp_path)


@pytest.mark.integration
class TestL2VersionManagerErrorHandling:
    def test_list_versions_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                vm.list_versions("test_key")

    def test_get_version_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                vm.get_version("test_key")

    def test_publish_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                vm.publish("test_key", "template", "desc")

    def test_rollback_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                vm.rollback("test_key")

    def test_start_shadow_no_status_column(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "description"}
        result = vm.start_shadow("test_key", shadow_version=1)
        assert "error" in result

    def test_get_shadow_template_no_status(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "description"}
        result = vm.get_shadow_template("test_key")
        assert result is None

    def test_list_all_keys_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("模拟连接失败")):
            with pytest.raises(Exception, match="模拟连接失败"):
                vm.list_all_keys()


@pytest.mark.integration
class TestL2ConfigCenterEdgeCases:
    def test_get_business_config_json_string_value(self, mysql_conn):
        mysql_conn.set_config("test_json_str", {"key": "val"}, "JSON字符串测试")
        from utils.config_center import get_business_config, invalidate_cache
        invalidate_cache("test_json_str")
        result = get_business_config("test_json_str")
        assert isinstance(result, dict)
        assert result.get("key") == "val"

    def test_get_business_config_string_value(self, mysql_conn):
        mysql_conn.set_config("test_str_val", {"_str": "just_a_string"}, "字符串值测试")
        from utils.config_center import get_business_config, invalidate_cache
        invalidate_cache("test_str_val")
        result = get_business_config("test_str_val")
        assert isinstance(result, dict)
        assert result.get("_str") == "just_a_string"

    def test_cache_ttl_expiry(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache
        mysql_conn.set_config("test_ttl_key", {"v": "1"}, "TTL测试")
        invalidate_cache("test_ttl_key")
        get_business_config("test_ttl_key")
        with _cache_lock:
            assert "test_ttl_key" in _cache

    def test_get_prompt_template_nonexistent(self):
        from utils.config_center import get_prompt_template, invalidate_cache
        invalidate_cache("nonexistent_prompt_xyz")
        result = get_prompt_template("nonexistent_prompt_xyz", default="default_template")
        assert result == "default_template"
