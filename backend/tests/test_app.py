from unittest.mock import MagicMock, patch


class TestCreateService:
    @patch("app.WorkOrderClient")
    @patch("app.get_rerank_client")
    @patch("app.get_embedding_client")
    @patch("app.MilvusQA")
    @patch("app.MySQLClient")
    @patch("app.validate_config", return_value=[])
    @patch("app.load_config")
    def test_create_service_initializes(
        self, mock_load_cfg, mock_validate, mock_mysql_cls, mock_milvus_cls, mock_embed, mock_rerank, mock_wo_cls
    ):
        mock_load_cfg.return_value = {
            "mysql": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "123456",
                "database": "etc_qa_test",
            },
            "milvus": {"db_path": "./test.db", "collection_name": "test"},
            "models": {
                "embed": {
                    "name": "BAAI/bge-large-zh-v1.5",
                    "dim": 1024,
                    "api_base": "https://api.siliconflow.cn/v1",
                    "api_keys": "k1,k2",
                },
                "rerank": {
                    "name": "BAAI/bge-reranker-v2-m3",
                    "api_base": "https://api.siliconflow.cn/v1",
                    "api_keys": "k1,k2",
                },
                "query_prefix": "",
            },
            "recall": {"vector_top_k": 10, "bm25_top_k": 10, "merge_method": "rrf", "rrf_k": 60},
            "rerank": {"enabled": False, "top_k": 3},
            "work_order": {"use_mock": True},
        }
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = [
            {
                "id": 1,
                "question": "ETC扣费异常",
                "answer": "核实退款",
                "category_l1": "售后业务",
                "category_l2": "ETC扣费",
            }
        ]
        mock_mysql_cls.return_value = mock_mysql

        mock_embed_obj = MagicMock()
        mock_embed.return_value = mock_embed_obj

        from app import create_service

        service = create_service()
        assert service is not None
