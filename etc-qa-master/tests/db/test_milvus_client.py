from unittest.mock import MagicMock, patch

from db.milvus_client import MilvusQA


class TestMilvusQA:
    def setup_method(self):
        self.mock_config = {
            "milvus": {"db_path": "./test_milvus.db", "collection_name": "test_qa"},
            "models": {"embed": {"dim": 1024}},
        }
        import utils.config as cfg_module
        self._original_get = getattr(cfg_module, "get_config", None)
        cfg_module.get_config = lambda: self.mock_config

    def teardown_method(self):
        import utils.config as cfg_module
        if self._original_get:
            cfg_module.get_config = self._original_get

    @patch("db.milvus_client.MilvusClient")
    def test_search_returns_ids(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            [{"id": 0, "entity": {"qa_id": 1}, "distance": 0.95}],
        ]
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus.search([0.1] * 1024, top_k=5)
        assert result == [(1, 0.95)]

    @patch("db.milvus_client.MilvusClient")
    def test_search_empty_results(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.return_value = [[]]
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus.search([0.1] * 1024, top_k=5)
        assert result == []

    @patch("db.milvus_client.MilvusClient")
    def test_insert_data(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.insert(1, [0.1] * 1024)
        mock_client.insert.assert_called_once()

    @patch("db.milvus_client.MilvusClient")
    def test_search_filters_by_active_qa_ids(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            [
                {"id": 0, "entity": {"qa_id": 1}, "distance": 0.95},
                {"id": 1, "entity": {"qa_id": 2}, "distance": 0.90},
                {"id": 2, "entity": {"qa_id": 3}, "distance": 0.85},
            ],
        ]
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus.search([0.1] * 1024, top_k=5, active_qa_ids=[1, 3])
        assert len(result) == 2
        assert result[0] == (1, 0.95)
        assert result[1] == (3, 0.85)


class TestMilvusQANewBranches:
    def setup_method(self):
        self.mock_config = {
            "milvus": {
                "db_path": "./test_milvus.db",
                "collection_name": "test_qa",
                "index": {"type": "HNSW", "M": 16, "ef_construction": 256},
                "search": {"ef": 128, "overfetch_ratio": 3},
                "schema": {"category_l1_max_length": 50},
            },
            "models": {"embed": {"dim": 1024}},
        }
        import utils.config as cfg_module
        self._original_get = getattr(cfg_module, "get_config", None)
        cfg_module.get_config = lambda: self.mock_config

    def teardown_method(self):
        import utils.config as cfg_module
        if self._original_get:
            cfg_module.get_config = self._original_get

    @patch("db.milvus_client.MilvusClient")
    def test_client_property_creates_on_first_access(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        assert milvus._client is None
        c = milvus.client
        assert c is mock_client
        assert milvus._client is mock_client

    @patch("db.milvus_client.MilvusClient")
    def test_init_collection_already_exists(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.init_collection()
        mock_client.create_collection.assert_not_called()

    @patch("db.milvus_client.MilvusClient")
    def test_init_collection_creates_new(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.init_collection()
        mock_client.create_collection.assert_called_once()

    @patch("db.milvus_client.MilvusClient")
    def test_init_collection_grpc_error_reconnect(self, mock_milvus_class):
        call_count = [0]

        def has_collection_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("too_many_pings")
            return True

        mock_client = MagicMock()
        mock_client.has_collection.side_effect = has_collection_side_effect
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.init_collection()
        mock_client.close.assert_called_once()

    @patch("db.milvus_client.MilvusClient")
    def test_init_collection_unavailable_reconnect(self, mock_milvus_class):
        call_count = [0]

        def has_collection_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("UNAVAILABLE")
            return True

        mock_client = MagicMock()
        mock_client.has_collection.side_effect = has_collection_side_effect
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.init_collection()

    @patch("db.milvus_client.MilvusClient")
    def test_init_collection_other_exception_raises(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.side_effect = Exception("unknown error")
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        try:
            milvus.init_collection()
            assert False
        except Exception as e:
            assert "unknown error" in str(e)

    @patch("db.milvus_client.MilvusClient")
    def test_ensure_loaded(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._ensure_loaded()
        mock_client.load_collection.assert_called_once()
        assert milvus._collection_loaded is True

    @patch("db.milvus_client.MilvusClient")
    def test_ensure_loaded_already_loaded(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        milvus._ensure_loaded()
        mock_client.load_collection.assert_not_called()

    @patch("db.milvus_client.MilvusClient")
    def test_ensure_loaded_grpc_reconnect(self, mock_milvus_class):
        call_count = [0]

        def load_collection_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("too_many_pings")

        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.load_collection.side_effect = load_collection_side_effect
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._ensure_loaded()
        assert milvus._collection_loaded is True

    @patch("db.milvus_client.MilvusClient")
    def test_safe_search_grpc_reconnect(self, mock_milvus_class):
        call_count = [0]

        def search_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("GOAWAY")
            return [[{"id": 0, "entity": {"qa_id": 1}, "distance": 0.9}]]

        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.side_effect = search_side_effect
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus._safe_search(collection_name="test", data=[[0.1]], limit=5)
        assert len(result[0]) == 1

    @patch("db.milvus_client.MilvusClient")
    def test_safe_search_other_error_raises(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("other error")
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        try:
            milvus._safe_search(collection_name="test", data=[[0.1]], limit=5)
            assert False
        except Exception as e:
            assert "other error" in str(e)

    @patch("db.milvus_client.MilvusClient")
    def test_insert_with_hyde_vectors(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.insert(1, [0.1] * 1024, category_l1="售后", hyde_vectors=[[0.2] * 1024, [0.3] * 1024])
        call_args = mock_client.insert.call_args
        data = call_args[1]["data"]
        assert len(data) == 3
        assert data[0]["is_hyde"] is False
        assert data[1]["is_hyde"] is True
        assert data[1]["id"] == 1001
        assert data[2]["id"] == 1002

    @patch("db.milvus_client.MilvusClient")
    def test_batch_insert(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus.batch_insert([{"id": 1, "qa_id": 1, "vector": [0.1] * 1024, "category_l1": "售后", "is_hyde": False}])
        mock_client.insert.assert_called_once()

    @patch("db.milvus_client.MilvusClient")
    def test_search_with_category_filter(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            [{"id": 0, "entity": {"qa_id": 1}, "distance": 0.95}],
        ]
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus.search([0.1] * 1024, top_k=5, category_filter="售后业务")
        call_args = mock_client.search.call_args
        assert '售后业务' in call_args[1]["filter"]

    @patch("db.milvus_client.MilvusClient")
    def test_search_no_hyde_filter(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            [{"id": 0, "entity": {"qa_id": 1}, "distance": 0.95}],
        ]
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus.search([0.1] * 1024, top_k=5, use_hyde=False)
        call_args = mock_client.search.call_args
        assert "is_hyde" in call_args[1]["filter"]

    @patch("db.milvus_client.MilvusClient")
    def test_search_empty_results_none(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_client.search.return_value = None
        mock_client.has_collection.return_value = True
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        result = milvus.search([0.1] * 1024, top_k=5)
        assert result == []

    @patch("db.milvus_client.MilvusClient")
    def test_close(self, mock_milvus_class):
        mock_client = MagicMock()
        mock_milvus_class.return_value = mock_client

        milvus = MilvusQA()
        milvus._client = mock_client
        milvus._collection_loaded = True
        milvus.close()
        mock_client.close.assert_called_once()
        assert milvus._client is None
        assert milvus._collection_loaded is False

    @patch("db.milvus_client.MilvusClient")
    def test_close_no_client(self, mock_milvus_class):
        milvus = MilvusQA()
        milvus.close()
        assert milvus._client is None

    @patch("db.milvus_client.MilvusClient")
    def test_reconnect(self, mock_milvus_class):
        old_client = MagicMock()
        new_client = MagicMock()
        mock_milvus_class.return_value = new_client

        milvus = MilvusQA()
        milvus._client = old_client
        milvus._collection_loaded = True
        milvus._reconnect()
        old_client.close.assert_called_once()
        assert milvus._client is new_client
        assert milvus._collection_loaded is False

    @patch("db.milvus_client.MilvusClient")
    def test_reconnect_close_exception(self, mock_milvus_class):
        old_client = MagicMock()
        old_client.close.side_effect = Exception("close error")
        new_client = MagicMock()
        mock_milvus_class.return_value = new_client

        milvus = MilvusQA()
        milvus._client = old_client
        milvus._reconnect()
        assert milvus._client is new_client
